# Project schemas

Use UTF-8 JSON. Store time values as non-negative seconds. Treat paths as relative to the project root unless absolute.

## `project-manifest.json`

```json
{
  "version": 1,
  "mode": "semi-auto",
  "rough_cut_requested": false,
  "inputs": {
    "video": "input/talk.mp4",
    "audio": null,
    "subtitle": "input/talk.srt",
    "script": null
  },
  "outputs": {"aspects": ["16:9", "9:16"]},
  "transcription_needed": false,
  "probe_status": "ok"
}
```

- `mode`: `semi-auto` or `full-auto`.
- Include at least one of `inputs.video` or `inputs.audio`.
- Set `rough_cut_requested` only from an explicit user request.
- Include a `rough_cut` object only when rough cutting was requested.
- `outputs.aspects` may contain `16:9` and `9:16`.

## `storyboard.json`

```json
{
  "version": 1,
  "scenes": [
    {
      "id": "scene-001",
      "start": 0.0,
      "end": 4.2,
      "narration": "Example narration",
      "visual_type": "live",
      "asset_ids": [],
      "notes": "Keep the speaker on screen"
    }
  ]
}
```

Scenes must be ordered and must not overlap. Valid `visual_type` values are `live`, `image`, `video`, `screenshot`, `generated`, `animation`, `chart`, and `caption`.

## `asset-plan.json`

```json
{
  "version": 1,
  "assets": [
    {
      "id": "asset-001",
      "scene_ids": ["scene-002"],
      "kind": "video",
      "strategy": "search",
      "query": "example product workflow",
      "required": true
    }
  ]
}
```

Valid `kind` values are `image`, `video`, `screenshot`, `generated`, `audio`, `logo`, and `data`. Valid `strategy` values are `user`, `search`, `capture`, and `generate`.

## `asset-register.json`

```json
{
  "version": 1,
  "assets": [
    {
      "id": "asset-001",
      "path": "assets/searched/example.mp4",
      "source_url": "https://example.com/item",
      "platform": "example.com",
      "author": "unknown",
      "acquired_at": "2026-08-19T12:00:00+08:00",
      "scene_ids": ["scene-002"],
      "copyright_status": "pending-review"
    }
  ]
}
```

Never set `copyright_status` to `commercially-cleared` without evidence or user confirmation.

## `render-plan.json`

```json
{
  "version": 1,
  "scenes": [
    {
      "scene_id": "scene-001",
      "engine": "source",
      "reason": "Retain the presenter",
      "aspects": ["16:9", "9:16"]
    }
  ]
}
```

Valid engines are `source`, `hyperframes`, `remotion`, and `ffmpeg`. Every `scene_id` must exist in the storyboard.

## `subject-layout.json`

```json
{
  "version": 1,
  "source": "input/talk.mp4",
  "canvas": {"width": 1920, "height": 1080},
  "duration": 52.2,
  "sample_interval": 0.75,
  "detector": "opencv-haar-face+hog-person",
  "coordinate_space": "normalized",
  "shots": [
    {
      "id": "shot-001",
      "start": 0.0,
      "end": 8.25,
      "sample_count": 11,
      "detected_sample_count": 10,
      "people_count_max": 1,
      "confidence": 0.927,
      "layout_type": "landscape-presenter",
      "primary_motion_envelope": {"x": 0.05, "y": 0.18, "width": 0.34, "height": 0.74},
      "subject_safe_region": {"x": 0.01, "y": 0.12, "width": 0.42, "height": 0.86},
      "animation_regions": [
        {"side": "right", "x": 0.47, "y": 0.07, "width": 0.48, "height": 0.76}
      ],
      "review_required": false
    }
  ],
  "review_required": false
}
```

All regions use normalized `0..1` coordinates. Treat `subject_safe_region` as non-overlapping space. When `review_required` is true, confirm a representative preview before full rendering.

## `qc-report.json`

```json
{
  "version": 1,
  "status": "pass",
  "checks": [
    {"name": "final-16x9-present", "status": "pass", "detail": "output/final-16x9-v1.mp4"}
  ]
}
```

Use `pass`, `fail`, or `skipped` per check. A skipped media probe is not a pass.
