#!/usr/bin/env python3
"""Add a subtle polygon-grid motif to the corners of a PowerPoint deck.

The script works directly with the OOXML package, so it does not require
PowerPoint or third-party Python packages. Existing shapes created by this
script are replaced, making repeated runs safe.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


EMU_PER_INCH = 914_400
SLIDE_WIDTH = 12_192_000
SLIDE_HEIGHT = 6_858_000
MARKER = "PolygonGrid_"


def emu(inches: float) -> int:
    return round(inches * EMU_PER_INCH)


def triangle_xml(
    shape_id: int,
    name: str,
    x: float,
    y: float,
    width: float,
    height: float,
    color: str,
    alpha: int,
    point_down: bool,
) -> str:
    rotation = ' rot="10800000"' if point_down else ""
    return (
        "<p:sp>"
        "<p:nvSpPr>"
        f'<p:cNvPr id="{shape_id}" name="{name}"/>'
        "<p:cNvSpPr/><p:nvPr/>"
        "</p:nvSpPr>"
        "<p:spPr>"
        f"<a:xfrm{rotation}>"
        f'<a:off x="{emu(x)}" y="{emu(y)}"/>'
        f'<a:ext cx="{emu(width)}" cy="{emu(height)}"/>'
        "</a:xfrm>"
        '<a:prstGeom prst="triangle"><a:avLst/></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{color}"><a:alpha val="{alpha}"/>'
        "</a:srgbClr></a:solidFill>"
        '<a:ln><a:noFill/></a:ln>'
        "</p:spPr>"
        "</p:sp>"
    )


def motif_xml(start_id: int, slide_number: int) -> str:
    # Strong brand colors at low opacity read as pale blue/teal on white.
    colors = ("1F5BA0", "00756D", "4BA3C7", "8FCBD3", "9BC7E5", "15477A")
    alphas = (18_000, 24_000, 30_000, 22_000, 34_000, 16_000)
    pieces: list[str] = []
    next_id = start_id
    width, height = 0.48, 0.416

    # Top-right: three tapered rows, partially clipped by the slide edge.
    top_rows = ((11.58, -0.15, 9), (11.82, 0.266, 8), (12.06, 0.682, 6))
    index = 0
    for row, (x0, y0, count) in enumerate(top_rows):
        for column in range(count):
            palette_index = (index + slide_number * 2 + row) % len(colors)
            pieces.append(
                triangle_xml(
                    next_id,
                    f"{MARKER}TR_{index + 1:02d}",
                    x0 + column * (width / 2),
                    y0,
                    width,
                    height,
                    colors[palette_index],
                    alphas[palette_index],
                    point_down=((column + row) % 2 == 1),
                )
            )
            next_id += 1
            index += 1

    # Bottom-left: a smaller counterweight, also clipped at the edges.
    bottom_rows = ((-0.24, 6.68, 7), (0.00, 7.096, 5))
    index = 0
    for row, (x0, y0, count) in enumerate(bottom_rows):
        for column in range(count):
            palette_index = (index + slide_number * 3 + row + 2) % len(colors)
            pieces.append(
                triangle_xml(
                    next_id,
                    f"{MARKER}BL_{index + 1:02d}",
                    x0 + column * (width / 2),
                    y0,
                    width,
                    height,
                    colors[palette_index],
                    max(12_000, alphas[palette_index] - 5_000),
                    point_down=((column + row) % 2 == 0),
                )
            )
            next_id += 1
            index += 1

    return "".join(pieces)


def remove_existing_motif(xml_text: str) -> str:
    shape_pattern = re.compile(
        r"<p:sp>(?:(?!</?p:sp>).)*?"
        + re.escape(MARKER)
        + r'[^\"]*"(?:(?!</?p:sp>).)*?</p:sp>',
        re.DOTALL,
    )
    return shape_pattern.sub("", xml_text)


def maximum_shape_id(xml_text: str) -> int:
    ids = [int(value) for value in re.findall(r'<p:cNvPr\s+[^>]*id="(\d+)"', xml_text)]
    return max(ids, default=1)


def insertion_point(xml_text: str) -> int:
    group_end = xml_text.find("</p:grpSpPr>")
    if group_end < 0:
        raise ValueError("Slide does not contain p:grpSpPr")
    group_end += len("</p:grpSpPr>")

    first_start = xml_text.find("<p:sp>", group_end)
    if first_start < 0:
        return group_end
    first_end = xml_text.find("</p:sp>", first_start)
    if first_end < 0:
        return group_end
    first_end += len("</p:sp>")
    first_shape = xml_text[first_start:first_end]

    offset = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/>', first_shape)
    extent = re.search(r'<a:ext cx="(\d+)" cy="(\d+)"/>', first_shape)
    if offset and extent:
        x, y = int(offset.group(1)), int(offset.group(2))
        width, height = int(extent.group(1)), int(extent.group(2))
        is_background = (
            abs(x) < 20_000
            and abs(y) < 20_000
            and width >= int(SLIDE_WIDTH * 0.98)
            and height >= int(SLIDE_HEIGHT * 0.98)
        )
        if is_background:
            return first_end
    return group_end


def update_slide(xml_bytes: bytes, slide_number: int) -> bytes:
    xml_text = xml_bytes.decode("utf-8")
    xml_text = remove_existing_motif(xml_text)
    start_id = maximum_shape_id(xml_text) + 1
    insert_at = insertion_point(xml_text)
    motif = motif_xml(start_id, slide_number)
    return (xml_text[:insert_at] + motif + xml_text[insert_at:]).encode("utf-8")


def slide_number(name: str) -> int | None:
    match = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", name)
    return int(match.group(1)) if match else None


def build_deck(source: Path, destination: Path) -> int:
    modified = 0
    with zipfile.ZipFile(source, "r") as incoming, zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as outgoing:
        for item in incoming.infolist():
            payload = incoming.read(item.filename)
            number = slide_number(item.filename)
            if number is not None and number > 1:
                payload = update_slide(payload, number)
                modified += 1
            outgoing.writestr(item, payload)
    return modified


def validate_deck(path: Path, expected_slides: int) -> None:
    motif_counts: list[int] = []
    with zipfile.ZipFile(path, "r") as deck:
        bad_entry = deck.testzip()
        if bad_entry:
            raise ValueError(f"Corrupt ZIP entry: {bad_entry}")
        for item in deck.infolist():
            number = slide_number(item.filename)
            if number is None:
                continue
            payload = deck.read(item.filename)
            ET.fromstring(payload)
            text = payload.decode("utf-8")
            count = text.count(f'name="{MARKER}')
            if number == 1 and count != 0:
                raise ValueError("Cover slide unexpectedly contains polygon-grid shapes")
            if number > 1:
                motif_counts.append(count)
                if count != 35:
                    raise ValueError(
                        f"Slide {number} has {count} polygon-grid shapes; expected 35"
                    )
                ids = re.findall(r'<p:cNvPr\s+[^>]*id="(\d+)"', text)
                if len(ids) != len(set(ids)):
                    raise ValueError(f"Slide {number} contains duplicate shape IDs")
    if len(motif_counts) != expected_slides - 1:
        raise ValueError("Unexpected slide count during validation")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    default_deck = script_dir.parent / "Presentation.pptx"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("presentation", nargs="?", type=Path, default=default_deck)
    parser.add_argument(
        "--no-backup", action="store_true", help="Do not create a timestamped backup"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    presentation = args.presentation.resolve()
    if not presentation.is_file():
        raise FileNotFoundError(presentation)

    with zipfile.ZipFile(presentation, "r") as deck:
        slide_count = sum(slide_number(item.filename) is not None for item in deck.infolist())

    if not args.no_backup:
        archive = presentation.parent / "archive" / "versions"
        archive.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = archive / f"{presentation.stem}-before-polygons-{stamp}.pptx"
        shutil.copy2(presentation, backup)
        print(f"Backup: {backup}")

    descriptor, temp_name = tempfile.mkstemp(
        prefix=f"{presentation.stem}-polygons-", suffix=".tmp.pptx", dir=presentation.parent
    )
    os.close(descriptor)
    temporary = Path(temp_name)
    try:
        modified = build_deck(presentation, temporary)
        validate_deck(temporary, slide_count)
        os.replace(temporary, presentation)
    finally:
        if temporary.exists():
            temporary.unlink()

    print(f"Updated: {presentation}")
    print(f"Decorated slides: {modified} (cover slide left unchanged)")


if __name__ == "__main__":
    main()
