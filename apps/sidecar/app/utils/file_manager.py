"""
File Manager Utility for Sclip
Handles file saving, loading, deletion, and session directory management.
"""
from pathlib import Path
from typing import Optional, List

# TODO: Add quota management, file validation, cleanup jobs, etc.

def save_file(path: Path, content: bytes) -> None:
    """Save bytes to a file at the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)

def load_file(path: Path) -> Optional[bytes]:
    """Load bytes from a file, or return None if not found."""
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return f.read()

def delete_file(path: Path) -> bool:
    """Delete a file if it exists. Returns True if deleted."""
    if path.exists():
        path.unlink()
        return True
    return False

def list_files(directory: Path, pattern: str = "*") -> List[Path]:
    """List files in a directory matching a pattern."""
    if not directory.exists():
        return []
    return list(directory.glob(pattern))

def ensure_session_directory(session_id: str) -> Path:
    """Ensure a session-specific directory exists and return its Path."""
    session_dir = Path("sessions") / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir 