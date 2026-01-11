from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Iterable

import cv2
from insightface.app import FaceAnalysis


@dataclass
class FaceGateResult:
    face_present: bool
    face_big_enough: bool
    facing_camera: bool
    bbox_ratio: float
    yaw: Optional[float]
    pitch: Optional[float]

    @property
    def should_refine(self) -> bool:
        return self.face_present and self.face_big_enough and self.facing_camera


class FaceGate:
    def __init__(
        self,
        *,
        min_face_height_ratio: float = 0.0001,
        max_abs_yaw: float = 50.0,
        max_abs_pitch: float = 40.0,
        provider: str = "CPUExecutionProvider",
    ):
        self.min_face_height_ratio = min_face_height_ratio
        self.max_abs_yaw = max_abs_yaw
        self.max_abs_pitch = max_abs_pitch

        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=[provider],
        )
        self.app.prepare(ctx_id=-1, det_size=(640, 640))

    def evaluate(self, image_path: Path) -> FaceGateResult:
        img = cv2.imread(str(image_path))
        if img is None:
            raise RuntimeError(f"Could not read image: {image_path}")

        h, _ = img.shape[:2]
        faces = self.app.get(img)

        if not faces:
            return FaceGateResult(False, False, False, 0.0, None, None)

        face = max(
            faces,
            key=lambda f: (f.bbox[3] - f.bbox[1]) * (f.bbox[2] - f.bbox[0]),
        )

        x1, y1, x2, y2 = face.bbox
        face_h = y2 - y1
        bbox_ratio = face_h / float(h)

        yaw, pitch, _ = face.pose

        return FaceGateResult(
            face_present=True,
            face_big_enough=bbox_ratio >= self.min_face_height_ratio,
            facing_camera=(
                abs(yaw) <= self.max_abs_yaw
                and abs(pitch) <= self.max_abs_pitch
            ),
            bbox_ratio=bbox_ratio,
            yaw=float(yaw),
            pitch=float(pitch),
        )


def gate_images(
    gate: FaceGate,
    image_paths: Iterable[Path],
) -> dict[Path, FaceGateResult]:
    results = {}
    for p in image_paths:
        results[p] = gate.evaluate(p)
    return results
