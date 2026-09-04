from __future__ import annotations

import argparse
import csv
import hashlib
import io
import textwrap
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


SCRIPT_DIR = Path(__file__).resolve().parent


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def cache_path(cache_dir: Path, url: str) -> Path:
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".img"
    return cache_dir / f"{hashlib.sha256(url.encode()).hexdigest()}{suffix}"


def download(url: str, cache_dir: Path, timeout: int) -> tuple[str, Path | None, str]:
    path = cache_path(cache_dir, url)
    if path.exists() and path.stat().st_size:
        return url, path, ""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "hybrid-ground-truth-review/1.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        path.write_bytes(data)
        return url, path, ""
    except Exception as exc:  # review packet must report every inaccessible asset
        return url, None, f"{type(exc).__name__}: {exc}"


def load_thumbnail(path: Path | None, size: tuple[int, int], label: str) -> Image.Image:
    canvas = Image.new("RGB", size, "#eeeeee")
    draw = ImageDraw.Draw(canvas)
    if path is None:
        draw.text((10, 10), "DOWNLOAD FAILED", fill="#b00020")
    else:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((size[0] - 8, size[1] - 30), Image.Resampling.LANCZOS)
            canvas.paste(image, ((size[0] - image.width) // 2, 24 + (size[1] - 30 - image.height) // 2))
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline="#999999")
    draw.text((6, 5), label, fill="#111111")
    return canvas


def wrapped(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, width: int, fill: str = "#111111") -> None:
    draw.multiline_text(xy, "\n".join(textwrap.wrap(value, width=width)[:4]), fill=fill, spacing=2)


def reference_card(row: dict[str, str], assets: dict[str, Path | None]) -> Image.Image:
    card = Image.new("RGB", (900, 420), "white")
    draw = ImageDraw.Draw(card)
    draw.rectangle((0, 0, 899, 419), outline="#555555", width=2)
    draw.text((10, 8), f"{row['query_id']} | {row['transformation_type']} | product {row['source_product_id']}", fill="#111111")
    wrapped(draw, (10, 28), row.get("image_edit_request", "reused image"), 105, "#333333")
    card.paste(load_thumbnail(assets.get(row["source_image_url"]), (430, 320), "SOURCE"), (10, 90))
    card.paste(load_thumbnail(assets.get(row["reference_image_url"]), (430, 320), "REFERENCE"), (460, 90))
    return card


def candidate_card(row: dict[str, str], assets: dict[str, Path | None]) -> Image.Image:
    card = Image.new("RGB", (900, 420), "white")
    draw = ImageDraw.Draw(card)
    draw.rectangle((0, 0, 899, 419), outline="#555555", width=2)
    draw.text((10, 8), f"{row['query_id']} | candidate {row['candidate_product_id']} | rule {row['rule_grade']}", fill="#111111")
    wrapped(draw, (10, 28), row.get("candidate_product_name", ""), 105)
    wrapped(draw, (10, 62), f"{row.get('candidate_color','')} | {row.get('candidate_material','')}", 105, "#333333")
    candidate_url = next((url for url in row.get("candidate_image_urls", "").split(" | ") if url), "")
    card.paste(load_thumbnail(assets.get(row["reference_image_url"]), (430, 320), "QUERY"), (10, 90))
    card.paste(load_thumbnail(assets.get(candidate_url), (430, 320), "CANDIDATE"), (460, 90))
    return card


def write_sheets(rows, assets, output_dir: Path, prefix: str, card_builder, per_sheet: int = 8) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for index in range(0, len(rows), per_sheet):
        subset = rows[index:index + per_sheet]
        sheet = Image.new("RGB", (1820, 20 + 430 * 4), "#dfe3e6")
        for offset, row in enumerate(subset):
            x = 5 + (offset % 2) * 910
            y = 5 + (offset // 2) * 430
            sheet.paste(card_builder(row, assets), (x, y))
        sheet.save(output_dir / f"{prefix}_{index // per_sheet + 1:03d}.jpg", quality=90, optimize=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download review assets and create local visual contact sheets.")
    root = SCRIPT_DIR.parent
    parser.add_argument("--reference-review-csv", type=Path, default=root / "reports" / "review" / "hybrid_reference_review.csv")
    parser.add_argument("--candidate-review-csv", type=Path, default=root / "reports" / "review" / "hybrid_candidate_review.csv")
    parser.add_argument("--queries-csv", type=Path, default=root / "data" / "multimodal_queries.csv")
    parser.add_argument("--output-dir", type=Path, default=root / "reports" / "review" / "contact_sheets")
    parser.add_argument("--cache-dir", type=Path, default=root / "reports" / "review" / "asset_cache")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    references = [row for row in read_csv(args.reference_review_csv) if row["review_status"] == "pending"]
    target_by_query = {row["query_id"]: row["target_product_id"] for row in read_csv(args.queries_csv)}
    candidates = [
        row for row in read_csv(args.candidate_review_csv)
        if row["review_status"] == "pending" and row["candidate_product_id"] != target_by_query[row["query_id"]]
    ]
    urls = {row["source_image_url"] for row in references} | {row["reference_image_url"] for row in references}
    for row in candidates:
        urls.add(row["reference_image_url"])
        urls.update(url for url in row.get("candidate_image_urls", "").split(" | ") if url)
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    assets: dict[str, Path | None] = {}
    failures: list[tuple[str, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(download, url, args.cache_dir, args.timeout) for url in sorted(urls)]
        for future in as_completed(futures):
            url, path, error = future.result()
            assets[url] = path
            if error:
                failures.append((url, error))
    write_sheets(references, assets, args.output_dir, "references", reference_card)
    write_sheets(candidates, assets, args.output_dir, "candidates", candidate_card)
    failure_path = args.output_dir / "download_failures.csv"
    with failure_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("url", "error"))
        writer.writerows(failures)
    print(f"reference_cards={len(references)} candidate_cards={len(candidates)} assets={len(urls)} failures={len(failures)}")
    print(f"contact_sheets={args.output_dir}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
