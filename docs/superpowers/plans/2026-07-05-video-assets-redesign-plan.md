# Video Assets Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign and upgrade the visual generation pipeline, fixing 3D mockup coordinates, implementing a dynamic scrolling selection glass tracklist, custom background tint/gradients, and updated 9:16 Shorts text sizing/spacing.

**Architecture:** 
- Generates a randomized color palette per run with RGB jitter, ensuring unique designs.
- Projects cover images onto precise 3D Mockup dimensions matching the template.
- Animates a scrolling highlight capsule on 16:9 videos and a Spotify-style scrolling layout on 9:16 portrait videos.
- Falls back to a slow, panning gradient motion background when no loop video is present.

**Tech Stack:** Python 3, Pillow (PIL), FFmpeg, NumPy.

## Global Constraints
- Do not use external libraries not already present in `pyproject.toml` (pillow, numpy).
- Keep all dimensions, coordinates, and color math exact.
- Do not write print logs inside library functions unless they are warnings or errors.

---

### Task 1: Color Palette Jitter & Base Pipeline Integration

**Files:**
- Modify: `src/pipeline.py`
- Modify: `src/cover_generator.py`
- Modify: `src/mockup_generator.py`
- Modify: `src/video_generator.py`
- Test: `src/test_pipeline_local.py`

**Interfaces:**
- Consumes: `config.GENRE_COLORS`
- Produces: 
  - `generate_cover_art(rebranded_name: str, genre: str, cover_path: str, color_palette: Tuple[Tuple[int,int,int], Tuple[int,int,int]])`
  - `generate_3d_mockup(cover_path: str, output_mockup_path: str, title: str, genre: str, color_palette: Tuple[Tuple[int,int,int], Tuple[int,int,int]])`
  - `compile_video_16_9(audio_path, mockup_path, overlay_path, video_path, genre, markers, srt_path, color_palette)`
  - `compile_video_9_16_shorts(audio_path, mockup_path, shorts_path, genre, rebranded_name, markers, color_palette)`

- [ ] **Step 1: Implement color palette resolver in pipeline.py**
  In `src/pipeline.py`, add a function to generate a randomized palette:
  ```python
  def resolve_randomized_palette(genre: str):
      import config, random
      gconfig = config.GENRE_COLORS.get(genre, config.GENRE_COLORS["Default"])
      base_c1, base_c2 = gconfig["bg_gradient"]
      
      def jitter_color(rgb):
          r = max(0, min(255, rgb[0] + random.randint(-20, 20)))
          g = max(0, min(255, rgb[1] + random.randint(-20, 20)))
          b = max(0, min(255, rgb[2] + random.randint(-20, 20)))
          return (r, g, b)
      
      return (jitter_color(base_c1), jitter_color(base_c2))
  ```

- [ ] **Step 2: Update cover_generator.py and mockup_generator.py to accept color_palette**
  Modify function headers to accept the resolved palette instead of reading statically from `GENRE_COLORS`.
  In `src/cover_generator.py`:
  ```python
  def generate_cover_art(rebranded_name: str, genre: str, output_path: str, color_palette=None) -> str:
      # Use color_palette if provided:
      if color_palette:
          color1, color2 = color_palette
      else:
          gconfig = GENRE_COLORS.get(genre, GENRE_COLORS["Default"])
          color1, color2 = gconfig["bg_gradient"]
  ```
  In `src/mockup_generator.py`:
  ```python
  def generate_3d_mockup(cover_path: str, output_path: str, rebranded_name: str, genre: str, color_palette=None) -> str:
  ```

- [ ] **Step 3: Update pipeline.py calls to pass resolved palette**
  Pass the generated palette into all generator functions.

- [ ] **Step 4: Verify test runner executes with empty palette placeholder**
  Run: `python src/test_pipeline_local.py --name "Underground" --genre "Trap"`
  Expected: Success without crashes.

- [ ] **Step 5: Commit changes**
  ```bash
  git add src/pipeline.py src/cover_generator.py src/mockup_generator.py
  git commit -m "feat: integrate randomized color palette in pipeline"
  ```

---

### Task 2: 3D Mockup Box Coordinates & Proportions Fix

**Files:**
- Modify: `src/mockup_generator.py`

**Interfaces:**
- Produces: Precise 3D Mockup rendering matching the DareToDream PSD proportions.

- [ ] **Step 1: Implement new box coordinates in mockup_generator.py**
  Replace destination projection coordinates in `src/mockup_generator.py` with the measured vertices (scaled to a `736x736` canvas size):
  ```python
  # Coordinates matching 736x736 PSD Mockup exactly:
  A = (241, 87)
  B = (169, 172)
  C = (243, 198)
  D = (568, 195)
  E = (169, 620)
  F = (243, 643)
  G = (568, 595)

  spine_dest = [B, E, F, C]
  front_dest = [C, F, G, D]
  top_dest = [B, C, D, A]
  ```

- [ ] **Step 2: Update source image transformation sizes and transforms**
  Ensure the canvas size created for the final composite is exactly `736x736`.
  ```python
  canvas = Image.new("RGBA", (736, 736), (0, 0, 0, 0))
  ```

- [ ] **Step 3: Run local mockup generation test**
  Run: `python src/test_pipeline_local.py --name "Underground" --genre "Trap"`
  Verify that the generated `rebranded_mockup.png` matches the shape of the mockup template.

- [ ] **Step 4: Commit changes**
  ```bash
  git add src/mockup_generator.py
  git commit -m "fix: adjust mockup box projection to match PSD dimensions"
  ```

---

### Task 3: 16:9 Landscape Video Upgrades

**Files:**
- Modify: `src/video_generator.py`

**Interfaces:**
- Produces: 
  - `create_tracklist_overlay(pack_name, genre, markers, output_img_path, color_palette)`
  - `compile_video_16_9(audio_path, mockup_path, overlay_path, video_path, genre, markers, srt_path, color_palette)`

- [ ] **Step 1: Design Option A category badges in create_tracklist_overlay**
  In `src/video_generator.py`, style the categories as solid block tags using the genre text color:
  ```python
  # Draw solid tag rectangle for category
  tag_text = m["category"].upper()
  tw, th = draw.textsize(tag_text, font=font_tag) # or getbbox
  draw.rectangle([x, y, x + tw + 12, y + th + 6], fill=gconfig["text_color"])
  draw.text((x + 6, y + 3), tag_text, fill=(6, 6, 12), font=font_tag)
  ```

- [ ] **Step 2: Implement dynamic panning gradient fallback in compile_video_16_9**
  If no background loop exists, generate a `2000x2000` gradient and apply the slow panning crop complex:
  ```python
  # Generate temp_bg_gradient.png (2000x2000)
  bg_input = "-loop 1 -i temp_bg_gradient.png"
  bg_filter = "crop=w=1920:h=1080:x='(in_w-1920)/2 + (in_w-1920)/2*sin(t*0.1)':y='(in_h-1080)/2 + (in_h-1080)/2*cos(t*0.1)',setsar=1"
  ```

- [ ] **Step 3: Run 16:9 compilation test**
  Run: `python src/test_pipeline_local.py --name "Underground" --genre "Trap"`
  Verify the landscape video has the glass card layout, Option A badges, and panning background.

- [ ] **Step 4: Commit changes**
  ```bash
  git add src/video_generator.py
  git commit -m "feat: add panned gradient background and tag badges to 16:9"
  ```

---

### Task 4: 9:16 portrait Shorts Video Upgrades

**Files:**
- Modify: `src/video_generator.py`

**Interfaces:**
- Produces: `compile_video_9_16_shorts(audio_path, mockup_path, shorts_path, genre, rebranded_name, markers, color_palette)`

- [ ] **Step 1: Update scrolling lyrics font size and spacing in render_scrolling_lyric_frame**
  Increase active size to `56`, prev/next to `32`, and gap to `80` pixels.

- [ ] **Step 2: Implement dynamic panning gradient in compile_video_9_16_shorts**
  Apply the panning crop filter complex with `1080x1920` size on the `2000x2000` gradient canvas:
  ```python
  bg_filter = "crop=w=1080:h=1920:x='(in_w-1080)/2 + (in_w-1080)/2*sin(t*0.1)':y='(in_h-1920)/2 + (in_h-1920)/2*cos(t*0.1)',setsar=1"
  ```

- [ ] **Step 3: Run Shorts compilation test**
  Run: `python src/test_pipeline_local.py --name "Underground" --genre "Trap"`
  Verify vertical video text sizes, spacing, and background motion.

- [ ] **Step 4: Commit changes**
  ```bash
  git add src/video_generator.py
  git commit -m "feat: increase active lyric size and narrow gap in Shorts"
  ```

---

### Task 5: End-to-End Test and Verification

**Files:**
- Test: `src/test_pipeline_local.py`

- [ ] **Step 1: Run comprehensive local test pipeline**
  Run: `python src/test_pipeline_local.py --name "Vortex 24" --genre "Trap"`
  Expected: Successful completion, producing cover, mockup, overlay, audio, SRT, landscape, shorts, and packaged ZIPs.

- [ ] **Step 2: Commit final changes**
  ```bash
  git commit -am "feat: finish visual assets upgrade and validation"
  ```
