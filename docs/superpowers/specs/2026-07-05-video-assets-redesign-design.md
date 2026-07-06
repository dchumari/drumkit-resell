# Design Spec - Video Showcase & Visual Assets Upgrade (2026-07-05)

## Overview
This specification details the upgrades to the visual assets generation pipeline for the Drumkit Resell automations, specifically targeting the 16:9 landscape YouTube video, the 9:16 portrait Shorts video, the 3D Mockup Box projection, and dynamic background tinting.

---

## 1. Shared Color Palette Randomization
To ensure each drumkit generation has a unique visual aesthetic while remaining true to the genre mood:
- At the start of the pipeline run, the base color palette for the genre is retrieved from `config.GENRE_COLORS`.
- A random RGB jitter of $\pm 20$ (clamped to `[0, 255]`) is applied to each of the gradient colors (`color1` and `color2`).
- This resolved color palette is passed into the cover, mockup, overlay, and video generator modules so that all visual elements are perfectly cohesive for that specific run.

---

## 2. 3D Mockup Box Projection
- **Coordinates & Shape**: The 3D box coordinates are mapped directly to the proportions of `assets/Product - Box - PSD Mock up by DareToDream on @creativemarket.jpg`.
- **Vertices Map (736x736 Canvas)**:
  - `A (Back-Left-Top)`: `(241, 87)`
  - `B (Spine-Left-Top)`: `(169, 172)`
  - `C (Front-Center-Top)`: `(243, 198)`
  - `D (Cover-Right-Top)`: `(568, 195)`
  - `E (Spine-Left-Bottom)`: `(169, 620)`
  - `F (Front-Center-Bottom)`: `(243, 643)`
  - `G (Cover-Right-Bottom)`: `(568, 595)`
- **Destinations**:
  - **Spine (Left Face)**: `[B, E, F, C]` $\rightarrow$ `[(169, 172), (169, 620), (243, 643), (243, 198)]`
  - **Cover (Front Face)**: `[C, F, G, D]` $\rightarrow$ `[(243, 198), (243, 643), (568, 595), (568, 195)]`
  - **Top Face**: `[B, C, D, A]` $\rightarrow$ `[(169, 172), (243, 198), (568, 195), (241, 87)]`
- **Transparency**: Source faces are converted to `RGBA` prior to applying the transform, ensuring clear edges and transparent borders on the final `rebranded_mockup.png`.

---

## 3. 16:9 Showcase Video Redesign
- **Background Panned Gradient**: If a background loop video does not exist, a large `2000x2000` linear gradient image is generated. In FFmpeg, a slow circular pan is applied:
  `crop=w=1920:h=1080:x='(in_w-1920)/2 + (in_w-1920)/2*sin(t*0.1)':y='(in_h-1080)/2 + (in_h-1080)/2*cos(t*0.1)'`
- **Tracklist Layout (Minimalist Glass + Option A Badges)**:
  - Frosted glass panel backdrop `rgba(255, 255, 255, 0.03)` with blur.
  - Categories are drawn as solid block badges/tags using the genre text color with dark monospace text inside.
  - No brackets `[]` around category text.
- **Scrolling Selection Capsule**:
  - A neon capsule matching the genre scheme is rendered.
  - A nested FFmpeg conditional math expression determines the Y coordinate of the capsule based on the active marker start/end timestamps.
  - Smooth 0.5s transitions interpolate the capsule's position between tracks.
  - Fallback highlights center on the "...and more premium samples" indicator when the playing track is off-screen (14th index or later).

---

## 4. 9:16 Shorts Video Redesign
- **Layout & Structure**: Mockup box centered at `(200, 420)` scaled to `680x680`. Showwaves line waveform at the bottom.
- **Spotify-style Scrolling Lyrics**:
  - Sequence of 30fps frames generated programmatically.
  - Active track name highlighted in the center with large bold text (font size `56`), colored in the genre accent color.
  - Previous and next track names rendered in smaller font (size `32`) and lower opacity, positioned above/below the active track.
  - Vertical spacing (gap) set to `80` pixels.
  - Transitions animate smoothly with ease-in-ease-out curve.

---

## 5. Verification Plan
- **Mockup Alignment Test**: Ensure the final box aligns perfectly with the template edges.
- **Video Compilations**: Execute local pipeline integration test to verify the FFmpeg filters render without errors and output valid MP4s.
