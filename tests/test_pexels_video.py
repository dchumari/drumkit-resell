import os
import sys
import json
from unittest.mock import patch, MagicMock

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
import config
from video_generator import get_pexels_background_video

def test_pexels_video_unconfigured():
    # If API key is empty, it should immediately return None without crashing
    old_key = getattr(config, "PEXELS_API_KEY", "")
    config.PEXELS_API_KEY = ""
    
    bg = get_pexels_background_video()
    assert bg is None
    
    config.PEXELS_API_KEY = old_key

def test_pexels_video_registry():
    # If API key is set, check that get_pexels_background_video updates the registry
    registry_path = "test_output/test_used_videos.json"
    if os.path.exists(registry_path):
        os.remove(registry_path)
        
    old_key = getattr(config, "PEXELS_API_KEY", "")
    config.PEXELS_API_KEY = "dummy_key"
    
    mock_payload = {
        "videos": [
            {
                "id": 12345,
                "video_files": [
                    {"quality": "hd", "file_type": "video/mp4", "link": "http://example.com/video1.mp4"}
                ]
            }
        ]
    }
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        # Mock API response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        
        mock_video_data = MagicMock()
        mock_video_data.read.return_value = b"video_data"
        mock_video_data.__enter__.return_value = mock_video_data
        
        # We mock twice: once for search query, second for image download
        mock_urlopen.side_effect = [mock_response, mock_video_data]
        
        video_path = get_pexels_background_video(cache_dir="test_output/cache", registry_path=registry_path)
        assert video_path == os.path.join("test_output/cache", "video_12345.mp4")
        
        # Verify it was added to registry
        assert os.path.exists(registry_path)
        with open(registry_path, "r") as f:
            used_ids = json.load(f)
            assert 12345 in used_ids
            
    # Clean up
    if os.path.exists(registry_path):
        os.remove(registry_path)
    config.PEXELS_API_KEY = old_key

def test_detect_pack_type_logic():
    from pipeline import detect_pack_type
    # 1. Test by title keywords
    assert detect_pack_type("Nova Pack", "Exclusive Loopkit 2026") == "Loopkit"
    assert detect_pack_type("Apex Drums", "Best 808s") == "Drumkit"
    assert detect_pack_type("Starlight One Shots", "Clean synths") == "One-shot"
    
    # 2. Test by extracted categories fallback
    cats_loop = {"LOOPS": ["melody.wav"], "MELODIES": ["piano.wav"]}
    assert detect_pack_type("Nova Pack", "No keywords", cats_loop) == "Loopkit"
    
    cats_drum = {"808S": ["sub.wav"], "KICKS": ["kick.wav"], "SNARES": ["snare.wav"]}
    assert detect_pack_type("Nova Pack", "No keywords", cats_drum) == "Drumkit"
