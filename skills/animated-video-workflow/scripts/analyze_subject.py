#!/usr/bin/env python3
"""Analyze presenter location and emit shot-level safe regions for animation layout."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, NamedTuple


Box = tuple[float, float, float, float]


class Sample(NamedTuple):
    time: float
    boxes: list[Box]
    scene_score: float


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def normalize_box(box: tuple[int, int, int, int], width: int, height: int) -> Box:
    x, y, box_width, box_height = box
    return (
        _clamp(x / width),
        _clamp(y / height),
        _clamp(box_width / width),
        _clamp(box_height / height),
    )


def union_boxes(boxes: list[Box]) -> Box | None:
    if not boxes:
        return None
    left = min(box[0] for box in boxes)
    top = min(box[1] for box in boxes)
    right = max(box[0] + box[2] for box in boxes)
    bottom = max(box[1] + box[3] for box in boxes)
    return (left, top, right - left, bottom - top)


def expand_box(box: Box, margin_x: float = 0.04, margin_y: float = 0.06) -> Box:
    x, y, width, height = box
    left = _clamp(x - margin_x)
    top = _clamp(y - margin_y)
    right = _clamp(x + width + margin_x)
    bottom = _clamp(y + height + margin_y)
    return (left, top, right - left, bottom - top)


def box_to_json(box: Box | None) -> dict[str, float] | None:
    if box is None:
        return None
    x, y, width, height = box
    return {key: round(value, 4) for key, value in zip(("x", "y", "width", "height"), box)}


def estimate_body_from_face(face: Box) -> Box:
    """Expand a face box to a conservative talking-head body region."""
    x, y, width, height = face
    center_x = x + width / 2
    body_width = min(0.62, width * 3.2)
    body_height = min(0.95, height * 5.2)
    left = _clamp(center_x - body_width / 2)
    top = _clamp(y - height * 0.45)
    right = _clamp(center_x + body_width / 2)
    bottom = _clamp(top + body_height)
    return (left, top, right - left, bottom - top)


def intersection_over_union(first: Box, second: Box) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[0] + first[2], second[0] + second[2])
    bottom = min(first[1] + first[3], second[1] + second[3])
    intersection = max(0.0, right - left) * max(0.0, bottom - top)
    union = first[2] * first[3] + second[2] * second[3] - intersection
    return intersection / union if union else 0.0


def merge_overlapping(boxes: list[Box], threshold: float = 0.15) -> list[Box]:
    merged: list[Box] = []
    for candidate in sorted(boxes, key=lambda item: item[2] * item[3], reverse=True):
        for index, existing in enumerate(merged):
            if intersection_over_union(candidate, existing) >= threshold:
                merged[index] = union_boxes([candidate, existing]) or existing
                break
        else:
            merged.append(candidate)
    return merged


def choose_primary(boxes: list[Box], previous: Box | None) -> Box | None:
    if not boxes:
        return None
    if previous is None:
        return max(boxes, key=lambda box: box[2] * box[3])

    previous_center = (previous[0] + previous[2] / 2, previous[1] + previous[3] / 2)

    def score(box: Box) -> float:
        center = (box[0] + box[2] / 2, box[1] + box[3] / 2)
        distance = math.dist(center, previous_center)
        return intersection_over_union(box, previous) * 2 + box[2] * box[3] - distance * 0.35

    return max(boxes, key=score)


def classify_layout(width: int, height: int, safe_region: Box | None, people_count: int) -> str:
    if safe_region is None:
        return "unknown"
    x, y, box_width, box_height = safe_region
    coverage = box_width * box_height
    if people_count > 1:
        return "multi-person"
    if coverage < 0.18 and y > 0.45:
        return "picture-in-picture"
    if height > width:
        return "portrait-presenter"
    if coverage >= 0.48 or box_width >= 0.58:
        return "full-frame-presenter"
    return "landscape-presenter"


def recommend_animation_regions(safe_region: Box | None) -> list[dict[str, Any]]:
    if safe_region is None:
        return [{"side": "full", "x": 0.06, "y": 0.08, "width": 0.88, "height": 0.76}]
    x, y, width, height = safe_region
    gap = 0.035
    regions: list[dict[str, Any]] = []
    left_width = max(0.0, x - gap)
    right_x = min(1.0, x + width + gap)
    right_width = max(0.0, 1.0 - right_x)
    top_height = max(0.0, y - gap)
    if left_width >= 0.24:
        regions.append({"side": "left", "x": 0.04, "y": 0.07, "width": round(left_width - 0.04, 4), "height": 0.76})
    if right_width >= 0.24:
        regions.append({"side": "right", "x": round(right_x, 4), "y": 0.07, "width": round(right_width - 0.05, 4), "height": 0.76})
    if top_height >= 0.18:
        regions.append({"side": "top", "x": 0.06, "y": 0.05, "width": 0.88, "height": round(top_height - 0.05, 4)})
    return regions


def _load_cv2():
    try:
        import cv2  # type: ignore
    except ImportError as error:
        raise RuntimeError(
            "OpenCV is required. Install scripts/requirements-subject.txt into the project dependency directory."
        ) from error
    return cv2


class SubjectDetector:
    def __init__(self, include_body: bool = True) -> None:
        cv2 = _load_cv2()
        self.cv2 = cv2
        cascade_source = Path(cv2.data.haarcascades) / "haarcascade_frontalface_alt2.xml"
        cascade_dir = Path(tempfile.gettempdir()) / "animated-video-workflow-models"
        cascade_dir.mkdir(parents=True, exist_ok=True)
        cascade_path = cascade_dir / cascade_source.name
        if not cascade_path.exists() or cascade_path.stat().st_size != cascade_source.stat().st_size:
            shutil.copyfile(cascade_source, cascade_path)
        self.face = cv2.CascadeClassifier(str(cascade_path))
        if self.face.empty():
            raise RuntimeError(f"Unable to load face cascade: {cascade_path}")
        self.hog = None
        if include_body:
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame, body_scan: bool) -> list[Box]:
        cv2 = self.cv2
        original_height, original_width = frame.shape[:2]
        scale = min(1.0, 720 / max(original_width, original_height))
        resized = cv2.resize(frame, None, fx=scale, fy=scale) if scale < 1 else frame
        height, width = resized.shape[:2]
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        min_face = max(24, int(min(width, height) * 0.045))
        faces = self.face.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(min_face, min_face),
        )
        boxes = [estimate_body_from_face(normalize_box(tuple(map(int, face)), width, height)) for face in faces]
        if body_scan and self.hog is not None:
            bodies, _ = self.hog.detectMultiScale(
                resized,
                winStride=(8, 8),
                padding=(8, 8),
                scale=1.05,
            )
            boxes.extend(normalize_box(tuple(map(int, body)), width, height) for body in bodies)
        return merge_overlapping(boxes)


def _scene_score(cv2, previous_hist, frame) -> tuple[float, Any]:
    thumbnail = cv2.resize(frame, (160, 90))
    hsv = cv2.cvtColor(thumbnail, cv2.COLOR_BGR2HSV)
    histogram = cv2.calcHist([hsv], [0, 1], None, [32, 16], [0, 180, 0, 256])
    cv2.normalize(histogram, histogram)
    if previous_hist is None:
        return 0.0, histogram
    correlation = cv2.compareHist(previous_hist, histogram, cv2.HISTCMP_CORREL)
    return _clamp(1.0 - correlation), histogram


def analyze_video(
    video_path: Path,
    sample_interval: float = 0.75,
    scene_threshold: float = 0.52,
    body_every: int = 3,
) -> dict[str, Any]:
    cv2 = _load_cv2()
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"Unable to open video: {video_path}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
        capture.release()
        raise ValueError("Video metadata is incomplete")
    duration = frame_count / fps
    detector = SubjectDetector(include_body=body_every > 0)
    samples: list[Sample] = []
    previous_hist = None
    sample_index = 0
    time_value = 0.0
    while time_value < duration:
        capture.set(cv2.CAP_PROP_POS_MSEC, time_value * 1000)
        ok, frame = capture.read()
        if not ok:
            break
        score, previous_hist = _scene_score(cv2, previous_hist, frame)
        body_scan = body_every > 0 and sample_index % body_every == 0
        boxes = detector.detect(frame, body_scan=body_scan)
        samples.append(Sample(time=round(time_value, 3), boxes=boxes, scene_score=score))
        sample_index += 1
        time_value += sample_interval
    capture.release()
    if not samples:
        raise ValueError("No frames could be sampled")
    return build_report(video_path, width, height, duration, sample_interval, scene_threshold, samples)


def build_report(
    video_path: Path,
    width: int,
    height: int,
    duration: float,
    sample_interval: float,
    scene_threshold: float,
    samples: list[Sample],
) -> dict[str, Any]:
    groups: list[list[Sample]] = [[]]
    for sample in samples:
        if groups[-1] and sample.scene_score >= scene_threshold:
            groups.append([])
        groups[-1].append(sample)

    shots: list[dict[str, Any]] = []
    all_safe_regions: list[Box] = []
    for index, group in enumerate(groups, start=1):
        primary_track: list[Box] = []
        all_people: list[Box] = []
        previous: Box | None = None
        detected_samples = 0
        max_people = 0
        for sample in group:
            if sample.boxes:
                detected_samples += 1
                max_people = max(max_people, len(sample.boxes))
                all_people.extend(sample.boxes)
                previous = choose_primary(sample.boxes, previous)
                if previous is not None:
                    primary_track.append(previous)
        motion_envelope = union_boxes(primary_track)
        people_envelope = union_boxes(all_people)
        safe_region = expand_box(people_envelope or motion_envelope) if (people_envelope or motion_envelope) else None
        if safe_region is not None:
            all_safe_regions.append(safe_region)
        detection_ratio = detected_samples / len(group)
        confidence = round(min(1.0, detection_ratio * 0.8 + (0.2 if detected_samples >= 2 else 0.0)), 3)
        layout_type = classify_layout(width, height, safe_region, max_people)
        animation_regions = recommend_animation_regions(safe_region)
        review_required = confidence < 0.55 or not animation_regions or layout_type in {"unknown", "multi-person"}
        shots.append(
            {
                "id": f"shot-{index:03d}",
                "start": round(group[0].time, 3),
                "end": round(min(duration, group[-1].time + sample_interval), 3),
                "sample_count": len(group),
                "detected_sample_count": detected_samples,
                "people_count_max": max_people,
                "confidence": confidence,
                "layout_type": layout_type,
                "primary_motion_envelope": box_to_json(motion_envelope),
                "subject_safe_region": box_to_json(safe_region),
                "animation_regions": animation_regions,
                "review_required": review_required,
            }
        )

    global_region = union_boxes(all_safe_regions)
    return {
        "version": 1,
        "source": str(video_path),
        "canvas": {"width": width, "height": height},
        "duration": round(duration, 3),
        "sample_interval": sample_interval,
        "detector": "opencv-haar-face+hog-person",
        "coordinate_space": "normalized",
        "shots": shots,
        "global_subject_safe_region": box_to_json(global_region),
        "review_required": any(shot["review_required"] for shot in shots),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--output", type=Path, default=Path("work/subject-layout.json"))
    parser.add_argument("--sample-interval", type=float, default=0.75)
    parser.add_argument("--scene-threshold", type=float, default=0.52)
    parser.add_argument("--body-every", type=int, default=3, help="Run full-body detection every N samples; 0 disables it")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.sample_interval <= 0 or args.scene_threshold <= 0 or args.scene_threshold > 1 or args.body_every < 0:
        print("ERROR: invalid analysis parameters", file=sys.stderr)
        return 2
    try:
        report = analyze_video(
            args.video,
            sample_interval=args.sample_interval,
            scene_threshold=args.scene_threshold,
            body_every=args.body_every,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Subject layout written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
