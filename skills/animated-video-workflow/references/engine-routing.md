# Engine routing

Choose an engine per scene. Record the engine and a short reason in `render-plan.json`. Prefer the simplest engine that satisfies the scene.

## Source video

Use `source` when the presenter, demonstration, or real-world evidence should remain visible. Use FFmpeg for trimming, reframing, crop tracking, picture-in-picture, and audio handoff. Keep the source video muted inside animation engines and use one authoritative audio track.

## HyperFrames

Choose HyperFrames for animated typography, captions, title cards, process diagrams, metric cards, lightweight charts, deterministic GSAP motion, and short web-like explanatory scenes.

Before authoring, load `$hyperframes:hyperframes`. Require a project visual identity. For multi-scene work, follow its transition rules; for captions, typography, or data, load the corresponding references. Run HyperFrames lint, validate, inspect, and representative-frame checks before handoff.

## Remotion

Choose Remotion for reusable React components, parameterized templates, dense multi-layer timing, complex responsive layouts, Lottie, 3D, maps, advanced charts, and scenes that need independent 16:9 and 9:16 component layouts.

Before authoring, load `$remotion-best-practices` and only the relevant rule files. Use composition metadata for duration and dimensions. Validate resource loading, representative frames, text measurement, scene duration, and transitions before rendering.

## FFmpeg

Choose FFmpeg for probing, extracting audio or frames, trimming, concatenating, overlaying, mixing audio, burning subtitles, transcoding, packaging, and composing rendered scene clips into the master timeline.

Use exact re-encoding for arbitrary-frame cuts. Use stream copy only for fast previews when keyframe-level imprecision is acceptable.

## Routing order

1. Keep useful real footage as `source`.
2. Use FFmpeg for media-only transforms.
3. Use HyperFrames for lightweight, typography-led or diagram-led animation.
4. Use Remotion when component reuse or complex timing/layout justifies React.
5. Do not introduce both animation engines in one scene unless a rendered clip from one is an input to the other.

If the preferred engine is unavailable, install and validate it. If installation is blocked, route to another engine only when the result remains equivalent; otherwise pause and report the missing capability.

## Scene handoff

Each rendered scene must provide a versioned clip with known dimensions, frame rate, duration, and audio policy; a scene identifier matching `storyboard.json`; a record of input asset IDs; and a short validation result with any intentional exceptions.

The final FFmpeg stage consumes clips in storyboard order and retains the authoritative narration track.
