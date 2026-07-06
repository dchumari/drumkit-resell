# Design Spec: Hybrid Pack-Type Visual Variety System

This document outlines the design for introducing visual variety (color moods, procedural overlays, and background video motion effects) based on the pack type (Drumkit, Loopkit, One-shots, Presets), without requiring AI.

---

## 1. Pack Type Detection
We will parse the rebranded pack name using regex/substring matching:
- **Drumkit**: Matches `drumkit`, `drum kit`, `drums`
- **Loopkit**: Matches `loopkit`, `loop kit`, `melody`, `loops`, `melody loops`
- **One-shot**: Matches `oneshot`, `one shot`, `oneshots`
- **Presets**: Matches `presets`, `bank`, `serum`, `electra`, `sylenth`
- **Default**: Fallback if no keywords match.

---

## 2. Visual Design System

### A. Procedural Overlay Graphics (PIL)
Instead of relying on missing static image assets, we will draw overlay graphics dynamically using PIL:
- **Drumkit**: A grid of coordinates with a dot matrix pattern, representing drum pad controllers.
- **Loopkit**: A styled retro cassette tape wireframe in the center + smooth wavy lines.
- **One-shot**: Concentric rings representing vinyl grooves and sound waves radiating from the center.
- **Presets**: A geometric circuit connection pattern (lines meeting at angled dots).

### B. Color Scheme (Mood Tinting)
We will modify the resolved genre color palette using distinct offsets based on the pack type:
- **Drumkit**: Gritty mood. We subtract `35` RGB values from the background to make it deep charcoal/dark, and boost the neon green/red contrast.
- **Loopkit**: Melodic mood. Shift the secondary color towards warm purple/sunset pink.
- **One-shot**: Electric mood. Shift colors towards high-frequency cyan/magenta neon.
- **Presets**: Digital mood. Cool cyan and blue tinting with pure white accents.

### C. Background Video Motion (FFmpeg)
We will select different FFmpeg background pan/scale filters for the fallback gradient:
- **Drumkit (Grid Pan)**: Move the crop window in a stepping matrix motion (simulating beats/steps).
- **Loopkit (Flowing Wave)**: Move the crop window using a smooth sinusoidal wave path `sin(t*0.08)`.
- **One-shot (Soundwave Ripple)**: Use a zoom/scale crop filter that pulses (zooms in and out) in time with a low-frequency oscillator `scale*sin(t*0.5)`.

---

## 3. Architecture & Components

1. **`src/pipeline.py`**:
   - Detect pack type from name.
   - Pass `pack_type` to `resolve_randomized_palette`.
2. **`src/cover_generator.py`**:
   - Draw the specific procedural overlay on the cover canvas based on `pack_type`.
   - **Important**: Clean up unused imports/configurations of missing asset files.
3. **`src/video_generator.py`**:
   - Select the motion background crop filter matching the `pack_type` during FFmpeg video compilation.
