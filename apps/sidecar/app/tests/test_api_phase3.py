import pytest
import httpx
import asyncio
import websockets
import json
from pathlib import Path

API_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001"

@pytest.mark.asyncio
async def test_cors_and_health_check():
    # Test CORS preflight
    async with httpx.AsyncClient() as client:
        resp = await client.options(f"{API_URL}/api/prompt")
        assert resp.status_code in (200, 204)
    # Test health check endpoint
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_URL}/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "script_writer" in data["services"]

@pytest.mark.asyncio
async def test_prompt_and_session_flow():
    # Submit a prompt
    prompt_data = {
        "prompt": "Test video about climate change",
        "style": "documentary",
        "length": "short",
        "tone": "informative",
        "approval_mode": "every_step",
        "quality_setting": "standard"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}/api/prompt", json=prompt_data)
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        session_id = data["session_id"]
        # List sessions
        resp2 = await client.get(f"{API_URL}/api/sessions")
        assert resp2.status_code == 200
        sessions = resp2.json()["sessions"]
        assert any(s["session_id"] == session_id for s in sessions)
        # Get session info
        resp3 = await client.get(f"{API_URL}/api/sessions/{session_id}")
        assert resp3.status_code == 200
        info = resp3.json()
        assert info["session_id"] == session_id

@pytest.mark.asyncio
async def test_websocket_streaming_and_message_types():
    # Start a session
    prompt_data = {
        "prompt": "Test video about AI",
        "style": "cinematic",
        "length": "medium",
        "tone": "exciting",
        "approval_mode": "auto_approve",
        "quality_setting": "draft"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}/api/prompt", json=prompt_data)
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]
    # Connect to WebSocket
    uri = f"{WS_URL}/api/stream/{session_id}"
    async with websockets.connect(uri) as ws:
        # First message should be connection_established
        msg = await ws.recv()
        data = json.loads(msg)
        assert data["type"] == "connection_established"
        # Receive a few more messages (ai_message, tool_call, tool_result, progress, etc.)
        received_types = set()
        for _ in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                received_types.add(data.get("type"))
                if received_types >= {"ai_message", "tool_call", "tool_result", "progress"}:
                    break
            except asyncio.TimeoutError:
                break
        assert "ai_message" in received_types
        assert "tool_call" in received_types
        assert "tool_result" in received_types
        if "progress" not in received_types:
            print("[WARN] 'progress' message not received in first 10 messages. This may be normal if backend does not emit progress early.")

@pytest.mark.asyncio
async def test_user_approval_and_error_handling():
    # Start a session
    prompt_data = {
        "prompt": "Test approval flow",
        "style": "social_media",
        "length": "short",
        "tone": "casual",
        "approval_mode": "every_step",
        "quality_setting": "standard"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}/api/prompt", json=prompt_data)
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]
        # Send approval with missing fields (should error)
        resp2 = await client.post(f"{API_URL}/api/approve/{session_id}", json={})
        assert resp2.status_code == 422
        # Send valid approval
        approval = {"step": "script_generation", "action": "approve", "modifications": {}}
        resp3 = await client.post(f"{API_URL}/api/approve/{session_id}", json=approval)
        assert resp3.status_code == 200
        data = resp3.json()
        assert data["status"] == "approved"
    # Try approval for non-existent session
    async with httpx.AsyncClient() as client:
        resp4 = await client.post(f"{API_URL}/api/approve/fake_session", json=approval)
        assert resp4.status_code == 404

@pytest.mark.asyncio
async def test_file_upload_download_list():
    # Start a session
    prompt_data = {
        "prompt": "Test file upload",
        "style": "documentary",
        "length": "short",
        "tone": "neutral",
        "approval_mode": "auto_approve",
        "quality_setting": "draft"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}/api/prompt", json=prompt_data)
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]
        # Upload a file (create a temp file)
        file_content = b"test file content"
        file_path = Path("test_upload.txt")
        file_path.write_bytes(file_content)
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "text/plain")}
            resp2 = await client.post(f"{API_URL}/api/files/upload?session_id={session_id}", files=files)
            assert resp2.status_code == 200
            data = resp2.json()
            assert data["status"] == "uploaded"
        # List files
        resp3 = await client.get(f"{API_URL}/api/files/list/{session_id}")
        assert resp3.status_code == 200
        files_list = resp3.json()["files"]
        assert any(f["filename"] == file_path.name for f in files_list)
        # Clean up temp file
        file_path.unlink(missing_ok=True)

# Additional tests for error handling, message queuing, and file preview/compression endpoints can be added similarly. 