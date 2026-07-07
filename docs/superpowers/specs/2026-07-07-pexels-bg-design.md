# Design Spec: Pexels API Background Video Sourcing

This document specifies the integration of the Pexels Videos API to fetch abstract background videos for the Landscape and Shorts video compilation showreels.

---

## 1. API Configuration & Request Setup
- **Config Key**: `PEXELS_API_KEY` defined in `src/config.py`.
- **Search Query**: `"abstract background"`.
- **Endpoint**: `GET https://api.pexels.com/v1/videos/search?query=abstract+background&per_page=80`.
- **Authorization**: Added via standard HTTP Header: `"Authorization": PEXELS_API_KEY`.

---

## 2. Selection & De-duplication Strategy
- **Used Registry**: Maintain a list of already used video IDs in `data/used_background_videos.json`.
- **Selection**:
  1. Filter the search results to exclude any video IDs present in `used_background_videos.json`.
  2. Select a video from the remaining candidates.
  3. Once selected, save its Pexels ID to `data/used_background_videos.json`.
- **Quality Selection**: Choose a video file from the `video_files` array where `quality == "hd"` and size is close to `1920x1080` (or the highest quality available).

---

## 3. Caching & Fallback Behavior
- **Local Cache**: Downloaded videos are cached in `assets/cache/video_{video_id}.mp4` for the run.
- **Fail-safe Fallback**: If the API key is not configured, if there is no internet, or if Pexels API limits are hit, the system seamlessly falls back to:
  1. Local loop videos `assets/bg_loop_*.mp4` (if present).
  2. Dynamically generated panning/scrolling gradients.
This ensures the pipeline is 100% reliable and never crashes during offline tests or when API limits are reached.
