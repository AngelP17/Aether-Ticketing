"""Endpoint tests for /api/tickets/.../attachments and /api/attachments/... routes."""
from __future__ import annotations

from typing import Any

import pytest

import apps.api.routes.attachments as attachments_routes


def _patch(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def _wrap(name: str, is_async: bool = False) -> None:
        if is_async:

            async def _async_impl(self: Any, *args: Any, **kwargs: Any) -> Any:
                calls[name] = {"args": args, "kwargs": kwargs}
                return overrides.get(name)

            monkeypatch.setattr(attachments_routes.AttachmentService, name, _async_impl)
        else:
            def _impl(self: Any, *args: Any, **kwargs: Any) -> Any:
                calls[name] = {"args": args, "kwargs": kwargs}
                return overrides.get(name)

            monkeypatch.setattr(attachments_routes.AttachmentService, name, _impl)

    _wrap("upload_attachment", is_async=True)
    for sync_name in ("list_attachments", "get_attachment", "delete_attachment"):
        _wrap(sync_name)
    return calls


def test_upload_attachment_returns_record(admin_client: Any) -> None:
    record = {"id": 9, "filename": "log.txt", "size_bytes": 1234}
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, upload_attachment=record)
        response = admin_client.post(
            "/api/tickets/IT-1/attachments",
            files={"file": ("log.txt", b"line1\nline2\n", "text/plain")},
        )
    assert response.status_code == 201, response.text
    assert response.json() == record
    assert calls["upload_attachment"]["kwargs"]["ticket_id"] == "IT-1"
    assert calls["upload_attachment"]["kwargs"]["comment_id"] is None
    # The service must receive the actual UploadFile object, not a string.
    uploaded = calls["upload_attachment"]["kwargs"]["file"]
    assert hasattr(uploaded, "filename")
    assert uploaded.filename == "log.txt"


def test_upload_attachment_propagates_comment_id(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, upload_attachment={"id": 9})
        admin_client.post(
            "/api/tickets/IT-1/attachments?comment_id=3",
            files={"file": ("a.txt", b"x", "text/plain")},
        )
    assert calls["upload_attachment"]["kwargs"]["comment_id"] == 3


def test_upload_attachment_404_when_ticket_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, upload_attachment=None)
        response = admin_client.post(
            "/api/tickets/IT-X/attachments",
            files={"file": ("a.txt", b"x", "text/plain")},
        )
    assert response.status_code == 404


def test_upload_attachment_404_on_lookup_error(admin_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> None:
        raise LookupError("not found")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, upload_attachment=None)
        monkeypatch.setattr(
            attachments_routes.AttachmentService, "upload_attachment", _raise
        )
        response = admin_client.post(
            "/api/tickets/IT-1/attachments",
            files={"file": ("a.txt", b"x", "text/plain")},
        )
    assert response.status_code == 404


def test_upload_attachment_400_on_value_error(admin_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> None:
        raise ValueError("bad type")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, upload_attachment=None)
        monkeypatch.setattr(
            attachments_routes.AttachmentService, "upload_attachment", _raise
        )
        response = admin_client.post(
            "/api/tickets/IT-1/attachments",
            files={"file": ("a.txt", b"x", "text/plain")},
        )
    assert response.status_code == 400


def test_list_ticket_attachments_returns_list(agent_client: Any) -> None:
    listing = [{"id": 1, "filename": "a.txt"}, {"id": 2, "filename": "b.png"}]
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, list_attachments=listing)
        response = agent_client.get("/api/tickets/IT-1/attachments")
    assert response.status_code == 200
    assert response.json() == listing


def test_serve_attachment_returns_binary_with_disposition(agent_client: Any) -> None:
    payload = {
        "file_data": b"hello",
        "mime_type": "text/plain",
        "content_disposition": 'attachment; filename="hello.txt"',
    }
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, get_attachment=payload)
        response = agent_client.get("/api/attachments/9")
    assert response.status_code == 200
    assert response.content == b"hello"
    assert response.headers["content-type"].startswith("text/plain")
    assert "hello.txt" in response.headers["content-disposition"]


def test_serve_attachment_404_when_missing(agent_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, get_attachment=None)
        response = agent_client.get("/api/attachments/999")
    assert response.status_code == 404


def test_delete_attachment_returns_success(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, delete_attachment=True)
        response = admin_client.delete("/api/attachments/9")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    assert calls["delete_attachment"]["args"] == (
        9,
        {"username": "admin", "role": "admin", "display_name": "Admin"},
    )


def test_delete_attachment_403_on_permission_error(admin_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> None:
        raise PermissionError("not yours")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, delete_attachment=False)
        monkeypatch.setattr(
            attachments_routes.AttachmentService, "delete_attachment", _raise
        )
        response = admin_client.delete("/api/attachments/9")
    assert response.status_code == 403


def test_delete_attachment_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, delete_attachment=False)
        response = admin_client.delete("/api/attachments/999")
    assert response.status_code == 404


def test_attachment_writes_require_write_role(viewer_client: Any) -> None:
    assert (
        viewer_client.post(
            "/api/tickets/IT-1/attachments",
            files={"file": ("a.txt", b"x", "text/plain")},
        ).status_code
        == 403
    )
    assert viewer_client.delete("/api/attachments/1").status_code == 403


def test_attachment_reads_require_authentication(anon_client: Any) -> None:
    assert anon_client.get("/api/tickets/IT-1/attachments").status_code == 401
    assert anon_client.get("/api/attachments/1").status_code == 401
