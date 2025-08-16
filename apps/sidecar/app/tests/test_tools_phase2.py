import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path

from apps.sidecar.app.tools.script_writer import ScriptWriterTool
from apps.sidecar.app.tools.broll_finder import BrollFinderTool
from apps.sidecar.app.tools.voiceover_generator import VoiceoverGeneratorTool
from apps.sidecar.app.tools.video_processor import VideoProcessorTool

@pytest.mark.asyncio
async def test_script_writer_tool():
    tool = ScriptWriterTool()
    input_data = {
        "topic": "Climate Change Solutions",
        "style": "documentary",
        "length": "short",
        "tone": "informative"
    }
    output = await tool.run(input_data)
    assert isinstance(output, dict)
    assert "script_text" in output
    assert "file_path" in output
    assert "duration" in output
    # Check deterministic output
    output2 = await tool.run(input_data)
    assert output["script_text"] == output2["script_text"]
    # Check file was created
    assert Path(output["file_path"]).exists()
    # Clean up
    Path(output["file_path"]).unlink(missing_ok=True)

@pytest.mark.asyncio
async def test_broll_finder_tool():
    # Check for at least 2 local image files
    preview_dir = Path("resources/preview_cache")
    local_images = list(preview_dir.glob("*.jpg")) + list(preview_dir.glob("*.png"))
    if len(local_images) < 2:
        pytest.skip("Not enough local image files in resources/preview_cache for broll test")
    tool = BrollFinderTool()
    input_data = {
        "topic": "Nature",
        "count": 2,
        "style": "cinematic",
        "duration": "short",
        "search_type": "images",
        "sources": ["local"],
        "ai_generation": False,
        "session_id": "test_broll"
    }
    output = await tool.run(input_data)
    assert output["success"]
    assert isinstance(output["clips"], list)
    assert isinstance(output["file_paths"], list)
    assert len(output["clips"]) == 2
    assert len(output["file_paths"]) == 2
    # Check file paths exist
    for fp in output["file_paths"]:
        assert Path(fp).exists()

@pytest.mark.asyncio
async def test_voiceover_generator_tool():
    tool = VoiceoverGeneratorTool()
    script_text = "This is a test script for voiceover generation."
    input_data = {
        "script_text": script_text,
        "voice": "en-US-Neural2-A",
        "speed": 1.0,
        "style": "professional",
        "session_id": "test_voiceover"
    }
    output = await tool.run(input_data)
    assert isinstance(output, dict)
    assert "audio_path" in output
    assert "duration" in output
    assert "format" in output
    # Check file exists
    assert Path(output["audio_path"]).exists()
    # Clean up
    Path(output["audio_path"]).unlink(missing_ok=True)

@pytest.mark.asyncio
async def test_video_processor_tool():
    tool = VideoProcessorTool()
    # Create temp script file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as script_file:
        script_file.write(b"Test script for video processor.")
        script_path = script_file.name
    # Use dummy broll and audio files (must exist for test to pass)
    broll_paths = []
    audio_path = None
    # Try to find at least one image/video in resources/preview_cache
    preview_dir = Path("resources/preview_cache")
    for f in preview_dir.glob("*.jpg"):
        broll_paths.append(str(f))
        break
    for f in preview_dir.glob("*.mp3"):
        audio_path = str(f)
        break
    if not broll_paths or not audio_path:
        pytest.skip("No test broll or audio files available in resources/preview_cache")
    input_data = {
        "script_path": script_path,
        "broll_paths": broll_paths,
        "audio_path": audio_path,
        "style": "cinematic",
        "session_id": "test_video"
    }
    output = await tool.run(input_data)
    assert isinstance(output, dict)
    assert "video_path" in output
    assert "duration" in output
    assert "thumbnail_path" in output
    assert "format" in output
    # Check video file exists
    assert Path(output["video_path"]).exists()
    # Clean up
    Path(output["video_path"]).unlink(missing_ok=True)
    Path(script_path).unlink(missing_ok=True)
    if Path(output["thumbnail_path"]).exists():
        Path(output["thumbnail_path"]).unlink(missing_ok=True) 