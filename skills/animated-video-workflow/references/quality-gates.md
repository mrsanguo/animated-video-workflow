# Quality gates

Stop at the first failed required gate. Preserve intermediate files and rerender only affected scenes where possible.

## Input gate

- At least one playable video or audio file exists.
- ffprobe reports expected streams, or the missing probe is explicitly reported.
- Subtitle cues are ordered, non-negative, and within media duration.
- Source files remain unchanged.

## Storyboard gate

- Scenes are ordered, non-overlapping, and cover the intended narration.
- Every scene has one primary visual strategy.
- Real footage and animation switches are purposeful rather than constant.
- Factual claims use real screenshots, supplied media, cited sources, or clearly illustrative generated media.

## Asset gate

- Required scene assets exist and are readable.
- Images and video are large enough for their target crop.
- Every searched or captured asset has a source entry and `pending-review` copyright status.
- Missing required assets trigger re-planning or a pause; placeholders cannot silently enter the final render.

## Preview gate

Render 2 to 3 representative excerpts before the full video. Check typography, hierarchy, wrapping, contrast, safe areas, synchronization, transitions, natural presenter/material handoff, asset clarity, animation smoothness, and both aspect layouts for at least one dense scene.

For presenter-led layouts, also check that the animation panel begins near the protected presenter boundary instead of after an arbitrary full-height sidebar. Treat the presenter as visual weight: avoid a large unused region above or beside a small circular window while important content crowds the opposite edge. Preserve a deliberate outer breathing area on the side away from the presenter.

Confirm that every live-presenter scene respects the matching `subject_safe_region` in `work/subject-layout.json`. Require preview confirmation for `review_required`, `multi-person`, and `unknown` shots; in full-auto mode use a conservative overlay or full-screen asset. Keep animation placement stable inside a shot and reject overlays that jitter in response to individual sampled detections.

In semi-auto mode, obtain user approval. In full-auto mode, continue only when all automated checks pass.

## Engine gates

### HyperFrames

- `lint` and `validate` pass.
- `inspect` reports no unapproved overflow.
- Multi-scene transitions and entrance animations follow HyperFrames rules.
- Animation map has no unexplained collisions, invisible elements, or dead zones.

### Remotion

- Composition duration and dimensions match the plan.
- Assets decode and fonts load deterministically.
- Representative frames have no overflow or missing content.
- Transitions do not shorten narration or create unintended blank frames.

### FFmpeg

- Every scene clip has compatible or intentionally normalized streams.
- Final duration matches narration and storyboard within an explained tolerance.
- There is one authoritative narration track and no accidental doubled audio.

## Final media gate

- Both versioned 16:9 and 9:16 outputs exist and are playable.
- Video and audio streams are present.
- Duration, dimensions, frame rate, and channel layout meet the render plan.
- No unexplained black frames, frozen segments, abnormal silence, clipping, or sync drift.
- Captions remain legible and inside safe areas; faces, product UI, and charts are not obscured.
- Presenter and animation areas remain visually balanced; no unexplained empty rail or edge-crowded asset survives from the preview.
- `copyright-review.md`, project files, source registry, render plan, and `qc-report.json` are delivered.

Mark an unavailable technical check as `skipped`, never `pass`. Disclose required skipped checks before delivery.
