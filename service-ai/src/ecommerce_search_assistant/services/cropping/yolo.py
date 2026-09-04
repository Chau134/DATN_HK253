from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from PIL import Image

from ecommerce_search_assistant.core.config import Settings, get_settings

BBox = tuple[int, int, int, int]


@dataclass(frozen=True)
class CropResult:
    image: Image.Image
    bbox: BBox
    confidence: float
    class_id: int | None
    is_fallback: bool = False


class CropService(Protocol):
    def warmup(self) -> None: ...

    def is_ready(self) -> bool: ...

    def detect_and_crop(self, image: Image.Image) -> list[CropResult]: ...


@dataclass
class OriginalImageCropService:
    """No-model cropper used while object detection is disabled."""

    def warmup(self) -> None:
        return None

    def is_ready(self) -> bool:
        return True

    def detect_and_crop(self, image: Image.Image) -> list[CropResult]:
        source_image = image.convert("RGB")
        width, height = source_image.size
        return [
            CropResult(
                image=source_image,
                bbox=(0, 0, width, height),
                confidence=0.0,
                class_id=None,
                is_fallback=True,
            )
        ]


@dataclass
class YoloCropService:
    settings: Settings = field(default_factory=get_settings)
    max_crops: int = 3
    min_area_ratio: float = 0.01
    max_area_ratio: float = 0.95
    _model: Any | None = field(default=None, init=False, repr=False)
    _load_error: RuntimeError | None = field(default=None, init=False, repr=False)

    def warmup(self) -> None:
        self._get_model()

    def is_ready(self) -> bool:
        return self._model is not None

    def detect_and_crop(self, image: Image.Image) -> list[CropResult]:
        source_image = image.convert("RGB")
        width, height = source_image.size
        image_area = width * height
        if image_area <= 0:
            return [self._fallback(source_image)]

        detections = self._detect(source_image)
        crop_candidates: list[CropResult] = []
        for bbox, confidence, class_id in detections:
            clamped_bbox = self._clamp_bbox(bbox, width, height)
            area_ratio = self._area_ratio(clamped_bbox, image_area)
            if not self._is_reasonable_crop(clamped_bbox, area_ratio):
                continue

            crop_candidates.append(
                CropResult(
                    image=source_image.crop(clamped_bbox),
                    bbox=clamped_bbox,
                    confidence=confidence,
                    class_id=class_id,
                )
            )

        crop_candidates.sort(
            key=lambda crop: self._crop_score(crop, image_area),
            reverse=True,
        )
        return crop_candidates[: self.max_crops] or [self._fallback(source_image)]

    def _detect(self, image: Image.Image) -> list[tuple[tuple[float, float, float, float], float, int]]:
        results = self._get_model().predict(
            source=image,
            conf=self.settings.yolo_conf_threshold,
            iou=self.settings.yolo_iou_threshold,
            imgsz=self.settings.yolo_input_size,
            device=self.settings.yolo_device,
            save=False,
            verbose=False,
        )
        if not results or results[0].boxes is None:
            return []

        boxes = results[0].boxes.cpu()
        xyxy_values = boxes.xyxy.tolist()
        confidence_values = boxes.conf.tolist()
        class_values = boxes.cls.tolist()
        return [
            (
                tuple(float(coordinate) for coordinate in bbox),  # type: ignore[arg-type]
                float(confidence),
                int(class_id),
            )
            for bbox, confidence, class_id in zip(xyxy_values, confidence_values, class_values, strict=True)
        ]

    def _get_model(self) -> Any:
        if self._load_error is not None:
            raise self._load_error
        if self._model is None:
            weights_path = Path(self.settings.yolo_weights_path).expanduser().resolve()
            if not weights_path.is_file():
                self._load_error = RuntimeError(f"YOLO weights file does not exist: {weights_path}")
                raise self._load_error

            from ultralytics import YOLO

            try:
                self._model = YOLO(str(weights_path))
            except Exception as exc:
                self._load_error = RuntimeError(f"Could not load YOLO weights: {weights_path}")
                raise self._load_error from exc
        return self._model

    def _fallback(self, image: Image.Image) -> CropResult:
        width, height = image.size
        return CropResult(
            image=image.copy(),
            bbox=(0, 0, width, height),
            confidence=0.0,
            class_id=None,
            is_fallback=True,
        )

    @staticmethod
    def _clamp_bbox(bbox: tuple[float, float, float, float], width: int, height: int) -> BBox:
        x1, y1, x2, y2 = bbox
        x_min, x_max = sorted((x1, x2))
        y_min, y_max = sorted((y1, y2))
        left = max(0, min(width - 1, int(round(x_min))))
        top = max(0, min(height - 1, int(round(y_min))))
        right = max(left + 1, min(width, int(round(x_max))))
        bottom = max(top + 1, min(height, int(round(y_max))))
        return (left, top, right, bottom)

    @staticmethod
    def _area_ratio(bbox: BBox, image_area: int) -> float:
        left, top, right, bottom = bbox
        area = max(0, right - left) * max(0, bottom - top)
        return area / image_area

    def _is_reasonable_area(self, area_ratio: float) -> bool:
        return self.min_area_ratio <= area_ratio <= self.max_area_ratio

    def _is_reasonable_crop(self, bbox: BBox, area_ratio: float) -> bool:
        left, top, right, bottom = bbox
        min_side = min(right - left, bottom - top)
        return min_side >= self.settings.yolo_min_crop_side_px and self._is_reasonable_area(area_ratio)

    def _crop_score(self, crop: CropResult, image_area: int) -> tuple[float, float]:
        area_ratio = self._area_ratio(crop.bbox, image_area)
        # Prefer confident boxes, then boxes near the middle of the accepted area range.
        ideal_area_ratio = 0.30
        area_quality = 1.0 - min(1.0, abs(area_ratio - ideal_area_ratio) / ideal_area_ratio)
        return (crop.confidence, area_quality)
