#!/usr/bin/env python3
"""Validate animated-video workflow JSON plans."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


MODES = {"semi-auto", "full-auto"}
ASPECTS = {"16:9", "9:16"}
VISUAL_TYPES = {"live", "image", "video", "screenshot", "generated", "animation", "chart", "caption"}
ENGINES = {"source", "hyperframes", "remotion", "ffmpeg"}
ASSET_KINDS = {"image", "video", "screenshot", "generated", "audio", "logo", "data"}
ASSET_STRATEGIES = {"user", "search", "capture", "generate"}
LAYOUT_TYPES = {
    "unknown",
    "picture-in-picture",
    "portrait-presenter",
    "full-frame-presenter",
    "landscape-presenter",
    "multi-person",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_manifest(data: dict) -> None:
    _require(data.get("version") == 1, "manifest version must be 1")
    _require(data.get("mode") in MODES, f"mode must be one of {sorted(MODES)}")
    inputs = data.get("inputs")
    _require(isinstance(inputs, dict), "inputs must be an object")
    _require(bool(inputs.get("video") or inputs.get("audio")), "inputs must include video or audio")
    outputs = data.get("outputs")
    _require(isinstance(outputs, dict), "outputs must be an object")
    aspects = outputs.get("aspects")
    _require(isinstance(aspects, list) and bool(aspects), "outputs.aspects must be a non-empty list")
    _require(set(aspects).issubset(ASPECTS), f"outputs.aspects must use {sorted(ASPECTS)}")
    rough_requested = data.get("rough_cut_requested")
    _require(isinstance(rough_requested, bool), "rough_cut_requested must be boolean")
    if "rough_cut" in data:
        _require(rough_requested, "rough_cut artifacts require rough_cut_requested=true")


def validate_storyboard(data: dict) -> set[str]:
    _require(data.get("version") == 1, "storyboard version must be 1")
    scenes = data.get("scenes")
    _require(isinstance(scenes, list) and bool(scenes), "scenes must be a non-empty list")
    scene_ids: set[str] = set()
    previous_end = 0.0
    for index, scene in enumerate(scenes):
        prefix = f"scene[{index}]"
        _require(isinstance(scene, dict), f"{prefix} must be an object")
        scene_id = scene.get("id")
        _require(isinstance(scene_id, str) and bool(scene_id), f"{prefix}.id is required")
        _require(scene_id not in scene_ids, f"duplicate scene id: {scene_id}")
        start = scene.get("start")
        end = scene.get("end")
        _require(isinstance(start, (int, float)) and isinstance(end, (int, float)), f"{scene_id} times must be numeric")
        _require(start >= 0, f"{scene_id} start must be non-negative")
        _require(start < end, f"{scene_id} start must be before end")
        _require(index == 0 or start >= previous_end, f"{scene_id} overlaps the previous scene")
        visual_type = scene.get("visual_type")
        _require(visual_type in VISUAL_TYPES, f"{scene_id} visual_type must be one of {sorted(VISUAL_TYPES)}")
        scene_ids.add(scene_id)
        previous_end = float(end)
    return scene_ids


def validate_asset_plan(data: dict, scene_ids: set[str]) -> set[str]:
    _require(data.get("version") == 1, "asset plan version must be 1")
    assets = data.get("assets")
    _require(isinstance(assets, list), "assets must be a list")
    asset_ids: set[str] = set()
    for index, asset in enumerate(assets):
        prefix = f"asset[{index}]"
        asset_id = asset.get("id")
        _require(isinstance(asset_id, str) and bool(asset_id), f"{prefix}.id is required")
        _require(asset_id not in asset_ids, f"duplicate asset id: {asset_id}")
        _require(asset.get("kind") in ASSET_KINDS, f"{asset_id} kind must be one of {sorted(ASSET_KINDS)}")
        _require(asset.get("strategy") in ASSET_STRATEGIES, f"{asset_id} strategy must be one of {sorted(ASSET_STRATEGIES)}")
        linked = asset.get("scene_ids", [])
        _require(isinstance(linked, list), f"{asset_id}.scene_ids must be a list")
        unknown = set(linked) - scene_ids
        _require(not unknown, f"{asset_id} references unknown scenes: {sorted(unknown)}")
        asset_ids.add(asset_id)
    return asset_ids


def validate_render_plan(data: dict, scene_ids: set[str]) -> None:
    _require(data.get("version") == 1, "render plan version must be 1")
    scenes = data.get("scenes")
    _require(isinstance(scenes, list), "render scenes must be a list")
    seen: set[str] = set()
    for index, scene in enumerate(scenes):
        scene_id = scene.get("scene_id")
        _require(scene_id in scene_ids, f"render scene[{index}] references unknown scene: {scene_id}")
        _require(scene_id not in seen, f"duplicate render scene: {scene_id}")
        engine = scene.get("engine")
        _require(engine in ENGINES, f"{scene_id} engine must be one of {sorted(ENGINES)}")
        aspects = scene.get("aspects", ["16:9", "9:16"])
        _require(isinstance(aspects, list) and set(aspects).issubset(ASPECTS), f"{scene_id} has invalid aspects")
        seen.add(scene_id)


def _validate_normalized_region(region: object, prefix: str) -> None:
    _require(isinstance(region, dict), f"{prefix} must be an object")
    values = [region.get(key) for key in ("x", "y", "width", "height")]
    _require(all(isinstance(value, (int, float)) for value in values), f"{prefix} values must be numeric")
    x, y, width, height = values
    _require(0 <= x <= 1 and 0 <= y <= 1, f"{prefix} origin must be normalized")
    _require(width >= 0 and height >= 0, f"{prefix} size must be non-negative")
    _require(x + width <= 1.0001 and y + height <= 1.0001, f"{prefix} must fit the canvas")


def validate_subject_layout(data: dict) -> None:
    _require(data.get("version") == 1, "subject layout version must be 1")
    canvas = data.get("canvas")
    _require(isinstance(canvas, dict), "subject layout canvas must be an object")
    _require(isinstance(canvas.get("width"), int) and canvas["width"] > 0, "subject layout canvas.width must be positive")
    _require(isinstance(canvas.get("height"), int) and canvas["height"] > 0, "subject layout canvas.height must be positive")
    _require(data.get("coordinate_space") == "normalized", "subject layout coordinates must be normalized")
    shots = data.get("shots")
    _require(isinstance(shots, list) and bool(shots), "subject layout shots must be a non-empty list")
    previous_end = 0.0
    shot_ids: set[str] = set()
    for index, shot in enumerate(shots):
        prefix = f"subject shot[{index}]"
        _require(isinstance(shot, dict), f"{prefix} must be an object")
        shot_id = shot.get("id")
        _require(isinstance(shot_id, str) and bool(shot_id), f"{prefix}.id is required")
        _require(shot_id not in shot_ids, f"duplicate subject shot id: {shot_id}")
        start = shot.get("start")
        end = shot.get("end")
        _require(isinstance(start, (int, float)) and isinstance(end, (int, float)), f"{shot_id} times must be numeric")
        _require(start >= 0 and start < end, f"{shot_id} has invalid time bounds")
        _require(index == 0 or start >= previous_end, f"{shot_id} overlaps the previous subject shot")
        confidence = shot.get("confidence")
        _require(isinstance(confidence, (int, float)) and 0 <= confidence <= 1, f"{shot_id} confidence must be 0..1")
        _require(shot.get("layout_type") in LAYOUT_TYPES, f"{shot_id} has invalid layout_type")
        _require(isinstance(shot.get("review_required"), bool), f"{shot_id}.review_required must be boolean")
        for key in ("primary_motion_envelope", "subject_safe_region"):
            if shot.get(key) is not None:
                _validate_normalized_region(shot[key], f"{shot_id}.{key}")
        regions = shot.get("animation_regions")
        _require(isinstance(regions, list), f"{shot_id}.animation_regions must be a list")
        for region_index, region in enumerate(regions):
            _validate_normalized_region(region, f"{shot_id}.animation_regions[{region_index}]")
        shot_ids.add(shot_id)
        previous_end = float(end)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    _require(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--storyboard", type=Path)
    parser.add_argument("--asset-plan", type=Path)
    parser.add_argument("--render-plan", type=Path)
    parser.add_argument("--subject-layout", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_manifest(load_json(args.manifest))
        scene_ids: set[str] = set()
        if args.storyboard:
            scene_ids = validate_storyboard(load_json(args.storyboard))
        if args.asset_plan:
            _require(bool(scene_ids), "--asset-plan requires --storyboard")
            validate_asset_plan(load_json(args.asset_plan), scene_ids)
        if args.render_plan:
            _require(bool(scene_ids), "--render-plan requires --storyboard")
            validate_render_plan(load_json(args.render_plan), scene_ids)
        if args.subject_layout:
            validate_subject_layout(load_json(args.subject_layout))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Plan validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
