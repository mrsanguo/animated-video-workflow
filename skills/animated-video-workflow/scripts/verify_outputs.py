#!/usr/bin/env python3
"""Verify animated-video workflow deliverables and write qc-report.json."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable


OUTPUT_PATTERNS = {
    "16x9": re.compile(r"^final-16x9-v([1-9][0-9]*)\.mp4$"),
    "9x16": re.compile(r"^final-9x16-v([1-9][0-9]*)\.mp4$"),
}
EXPECTED_DIMENSIONS = {"16x9": (1920, 1080), "9x16": (1080, 1920)}
REQUIRED_WORK_FILES = ("storyboard.json", "asset-register.json", "render-plan.json")


def default_probe(path: Path) -> dict:
    executable = shutil.which("ffprobe")
    if not executable:
        return {"status": "unavailable", "reason": "ffprobe was not found"}
    command = [
        executable,
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type,width,height,r_frame_rate,channels",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return {"status": "failed", "reason": result.stderr.strip() or "ffprobe failed"}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        return {"status": "failed", "reason": f"invalid ffprobe JSON: {error}"}
    payload["status"] = "ok"
    return payload


def _check(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def _latest_versioned_output(output_dir: Path, aspect: str) -> Path | None:
    pattern = OUTPUT_PATTERNS[aspect]
    candidates: list[tuple[int, Path]] = []
    if output_dir.is_dir():
        for path in output_dir.iterdir():
            if not path.is_file():
                continue
            match = pattern.match(path.name)
            if match:
                candidates.append((int(match.group(1)), path))
    return max(candidates, default=(0, None), key=lambda item: item[0])[1]


def _searched_assets_present(register_path: Path) -> bool:
    if not register_path.is_file():
        return False
    try:
        payload = json.loads(register_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    assets = payload.get("assets", []) if isinstance(payload, dict) else []
    return any(
        isinstance(asset, dict)
        and (
            bool(asset.get("source_url"))
            or asset.get("strategy") in {"search", "capture"}
            or str(asset.get("path", "")).replace("\\", "/").startswith("assets/searched/")
        )
        for asset in assets
    )


def _probe_checks(path: Path, aspect: str, payload: dict) -> list[dict]:
    status = payload.get("status")
    if status == "unavailable":
        return [_check(f"{aspect}-media-probe", "skipped", payload.get("reason", "probe unavailable"))]
    if status != "ok":
        return [_check(f"{aspect}-media-probe", "fail", payload.get("reason", "probe failed"))]

    streams = payload.get("streams", [])
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    checks = [
        _check(f"{aspect}-video-stream", "pass" if video_streams else "fail", "video stream present" if video_streams else "video stream missing"),
        _check(f"{aspect}-audio-stream", "pass" if audio_streams else "fail", "audio stream present" if audio_streams else "audio stream missing"),
    ]
    if video_streams:
        expected = EXPECTED_DIMENSIONS[aspect]
        actual = (video_streams[0].get("width"), video_streams[0].get("height"))
        checks.append(
            _check(
                f"{aspect}-dimensions",
                "pass" if actual == expected else "fail",
                f"expected {expected[0]}x{expected[1]}, got {actual[0]}x{actual[1]}",
            )
        )
    return checks


def verify_project(project_dir: Path, *, probe: Callable[[Path], dict] = default_probe) -> dict:
    root = project_dir.resolve()
    work = root / "work"
    output = root / "output"
    checks: list[dict] = []

    for name in REQUIRED_WORK_FILES:
        path = work / name
        checks.append(_check(f"{name}-present", "pass" if path.is_file() else "fail", str(path)))

    register_path = work / "asset-register.json"
    if _searched_assets_present(register_path):
        review = work / "copyright-review.md"
        checks.append(
            _check(
                "copyright-review-present",
                "pass" if review.is_file() else "fail",
                str(review),
            )
        )

    outputs: list[str] = []
    for aspect in ("16x9", "9x16"):
        path = _latest_versioned_output(output, aspect)
        if path is None:
            checks.append(_check(f"final-{aspect}-versioned-output", "fail", f"no final-{aspect}-vN.mp4 found"))
            continue
        outputs.append(str(path.relative_to(root)).replace("\\", "/"))
        checks.append(_check(f"final-{aspect}-versioned-output", "pass", str(path)))
        checks.extend(_probe_checks(path, aspect, probe(path)))

    status = "fail" if any(item["status"] == "fail" for item in checks) else "pass"
    return {"version": 1, "status": status, "outputs": outputs, "checks": checks}


def run(project_dir: Path, report_path: Path, *, probe: Callable[[Path], dict] = default_probe) -> int:
    report = verify_project(project_dir, probe=probe)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["status"] == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--report", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report_path = args.report or args.project_dir / "work" / "qc-report.json"
    try:
        result = run(args.project_dir, report_path)
    except OSError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {report_path}")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
