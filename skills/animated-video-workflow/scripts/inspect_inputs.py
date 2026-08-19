#!/usr/bin/env python3
"""Inspect animation-video inputs and write a deterministic project manifest."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass"}
SCRIPT_EXTENSIONS = {".txt", ".md"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
KNOWN_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | SUBTITLE_EXTENSIONS | SCRIPT_EXTENSIONS | IMAGE_EXTENSIONS


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def default_probe(path: Path) -> dict:
    executable = shutil.which("ffprobe")
    if not executable:
        return {"status": "unavailable", "reason": "ffprobe was not found"}
    command = [
        executable,
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,width,height,r_frame_rate",
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


def inspect_directory(
    input_dir: Path,
    *,
    mode: str = "semi-auto",
    rough_cut: bool = False,
    probe: Callable[[Path], dict] = default_probe,
) -> dict:
    root = input_dir.resolve()
    if mode not in {"semi-auto", "full-auto"}:
        raise ValueError("mode must be semi-auto or full-auto")
    if not root.is_dir():
        raise ValueError(f"input directory does not exist: {root}")

    files = sorted((path for path in root.rglob("*") if path.is_file()), key=lambda value: value.as_posix().lower())

    def matches(extensions: set[str]) -> list[Path]:
        return [path for path in files if path.suffix.lower() in extensions]

    videos = matches(VIDEO_EXTENSIONS)
    audio = matches(AUDIO_EXTENSIONS)
    subtitles = matches(SUBTITLE_EXTENSIONS)
    scripts = matches(SCRIPT_EXTENSIONS)
    images = matches(IMAGE_EXTENSIONS)
    unsupported = [path for path in files if path.suffix.lower() not in KNOWN_EXTENSIONS]
    if not videos and not audio:
        raise ValueError("input directory must contain at least one video or audio file")

    selected_video = videos[0] if videos else None
    selected_audio = audio[0] if audio else None
    selected_subtitle = subtitles[0] if subtitles else None
    selected_script = scripts[0] if scripts else None
    media_files = [path for path in (selected_video, selected_audio) if path]
    probes = {_relative(path, root): probe(path) for path in media_files}
    statuses = {value.get("status", "failed") for value in probes.values()}
    if "failed" in statuses:
        probe_status = "failed"
    elif statuses == {"ok"}:
        probe_status = "ok"
    else:
        probe_status = "unavailable"

    return {
        "version": 1,
        "mode": mode,
        "rough_cut_requested": rough_cut,
        "input_root": str(root),
        "inputs": {
            "video": _relative(selected_video, root) if selected_video else None,
            "audio": _relative(selected_audio, root) if selected_audio else None,
            "subtitle": _relative(selected_subtitle, root) if selected_subtitle else None,
            "script": _relative(selected_script, root) if selected_script else None,
        },
        "outputs": {"aspects": ["16:9", "9:16"]},
        "transcription_needed": selected_subtitle is None,
        "probe_status": probe_status,
        "media_probe": probes,
        "available_assets": [_relative(path, root) for path in images],
        "unsupported_files": [_relative(path, root) for path in unsupported],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output", type=Path, default=Path("work/project-manifest.json"))
    parser.add_argument("--mode", choices=("semi-auto", "full-auto"), default="semi-auto")
    parser.add_argument("--rough-cut", action="store_true", help="Record an explicit request to rough cut before animation")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = inspect_directory(args.input_dir, mode=args.mode, rough_cut=args.rough_cut)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
