# Design Spec: Generative Cover Art & Image Sourcing System

This document outlines the design for the generative cover art and image sourcing system for Arqive Reseller. The system will create unique visual designs for every run, differentiate pack types by naming badges, download background textures, and overlay branding logos.

---

## 1. Pack Type Naming & Subtitle Badge
On both the cover art and the 3D mockup spine, we will draw a clean, stylish subtitle badge:
- **Location**: Centered immediately below the main title on the cover, and rotated vertically on the spine.
- **Design**: A small capsule badge (rounded rectangle with a neon outline) containing the uppercase pack type text (e.g. `DRUM KIT`, `LOOP KIT`, `ONE-SHOTS`, `PRESETS BANK`).
- **Color**: Matches the genre's accent text color (from `GENRE_COLORS` with random $\pm 20$ jitter).

---

## 2. Image Sourcing & Branding Overlays
We will implement an image loader in `src/cover_generator.py`:
- **Background Sourcing**:
  - The pipeline will search `assets/backgrounds/` for local images.
  - If empty, it will attempt to download a random high-quality background from `https://picsum.photos/1200/1200` (or fallback to the generative gradient if offline).
  - Apply a dark/neon multiply blend overlay to fit the genre's color scheme.
- **Branding Overlays (Cover & Mockup)**:
  - **Parental Advisory Logo** (`assets/parental_advisory.png`): Placed on the **bottom-left corner** of the cover art (scaled to `160px` width).
  - **Main Logo** (`assets/producer_icon_or_logo.png`): Placed on the **top-right corner** of the cover art (scaled to `120x120px`).
  - **Producer Icon** (`assets/producer_icon_or_logo(1).png`): Placed on the **top-left corner** of the cover art (scaled to `80x80px`).
  - **Spine Branding**: Paste the **Producer Icon** at the top of the 3D box's vertical spine (rotated and scaled to `40x40px`).


---

## 3. Components & Architecture
1. **`src/pipeline.py`**:
   - Detect `pack_type` from pack name.
   - Resolve `color_palette`.
2. **`src/cover_generator.py`**:
   - Add image download logic with caching (saved in `test_output/temp_bg.png` or `assets/cache/`).
   - Draw the capsule subtitle badge under the main title.
   - Overlay local branding assets.
