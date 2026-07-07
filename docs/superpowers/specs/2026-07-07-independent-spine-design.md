# Design Spec: Independent Spine Design for 3D Mockup Box

This document outlines the independent visual layout and styling for the 3D mockup box spine (left side), separating it from the photographic front cover art.

---

## 1. Spine Styling & Background
- **Background**: Solid matte charcoal/black color (`RGB(18, 18, 20)`) representing a physical packaging material.
- **Borders**: Subtle vertical divider line on the right edge (`RGB(35, 35, 40)`) to cleanly separate the spine face from the front cover face in 3D perspective.

---

## 2. Text & Logo Layout
- **Producer Icon** (`assets/producer_icon_or_logo(1).png`):
  - Placed at the top of the spine, centered horizontally, and scaled to `60x60px`.
  - Position: 60px from the top.
- **Vertical Title Text**:
  - Centered vertically and horizontally on the spine.
  - Text: The clean, uppercase pack name in solid bright white (`RGB(245, 245, 250)`).
- **Pack-Type Capsule Badge**:
  - Located at the bottom of the spine, rotated 270 degrees.
  - Text: Capsule pill outline containing `DRUM KIT`, `LOOP KIT`, `ONE-SHOTS`, or `PRESETS BANK`.
  - Color: Drawn using the genre's accent neon text color (e.g. Cyan for Trap/House, Pink for RnB) to add a touch of colored brand personality to the dark spine.
  - Position: Center horizontally, placed 40px below the end of the vertical title text.

---

## 3. Implementation Files
- **`src/mockup_generator.py`**:
  - Update `generate_spine` to build the spine image from scratch with a solid background color and independent layout, rather than cropping from `cover_path`.
  - Retrieve the genre accent color from `GENRE_COLORS` (or the passed `color_palette`) to color the spine capsule badge.
