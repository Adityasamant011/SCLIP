import pytest
import os
from pathlib import Path
import importlib

# Root of backend
BACKEND_ROOT = Path("apps/sidecar/app")

@pytest.mark.parametrize("rel_path", [
    "main.py",
    "orchestrator/sclip_brain.py",
    "orchestrator/message_handler.py",
    "orchestrator/state_machine.py",
    "tools/base_tool.py",
    "tools/script_writer.py",
    "tools/broll_finder.py",
    "tools/voiceover_generator.py",
    "tools/video_processor.py",
    "models/session.py",
    "models/user.py",
    "models/preferences.py",
    "api/__init__.py",
    "database/models.py",
    "database/connection.py",
    "services/google_search.py",
    "services/pexels_api.py",
    "services/media_downloader.py",
    "utils/file_manager.py",
    "utils/validators.py",
    "__init__.py",
])
def test_core_files_exist(rel_path):
    path = BACKEND_ROOT / rel_path
    assert path.exists(), f"Missing: {rel_path}"

@pytest.mark.parametrize("rel_dir", [
    "orchestrator",
    "tools",
    "models",
    "api",
    "database",
    "services",
    "utils",
])
def test_core_directories_exist(rel_dir):
    path = BACKEND_ROOT / rel_dir
    assert path.exists() and path.is_dir(), f"Missing directory: {rel_dir}"

def test_config_and_requirements():
    assert Path("apps/sidecar/config.py").exists()
    assert Path("apps/sidecar/requirements.txt").exists()
    assert Path("apps/sidecar/.env.example").exists() or Path(".env.example").exists()
    assert Path("apps/sidecar/README.md").exists() or Path("README.md").exists()

@pytest.mark.parametrize("pkg,mod,should_exist", [
    ("apps.sidecar.app.orchestrator.sclip_brain", "SclipBrain", True),
    ("apps.sidecar.app.tools.base_tool", "BaseTool", True),
])
def test_key_classes_exist(pkg, mod, should_exist):
    try:
        module = importlib.import_module(pkg)
        assert hasattr(module, mod) == should_exist, f"{mod} missing in {pkg}"
    except ImportError:
        assert not should_exist, f"Module {pkg} should exist" 