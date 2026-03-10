"""
Integration tests for the PropertyImage endpoints.

These tests require a live PostgreSQL instance and are skipped automatically
when the database is not reachable.  Run them with:

    pytest -m integration tests/integration/test_property_images_integration.py

Or with a custom DATABASE_URL:

    DATABASE_URL=postgresql://user:pass@host:5432/db pytest -m integration ...
"""

import io
import os
import tempfile
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError


pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image_upload(
    property_id: str = "prop-001",
    uploaded_by: str | None = None,
    caption: str | None = None,
    content_type: str = "image/jpeg",
    size: int = 60,
    filename: str = "test.jpg",
):
    """Build a multipart upload payload for a synthetic image."""
    content = b"\xff\xd8\xff" + b"\x00" * size  # JPEG-like bytes
    data = {"property_id": property_id}
    if uploaded_by:
        data["uploaded_by"] = uploaded_by
    if caption:
        data["caption"] = caption
    files = {"file": (filename, io.BytesIO(content), content_type)}
    return data, files


# ---------------------------------------------------------------------------
# Upload endpoint — correct operation
# ---------------------------------------------------------------------------

class TestPropertyImageUploadIntegration:
    """Validates correct operation of the upload endpoint against PostgreSQL."""

    def test_upload_image_returns_201(self, pg_client):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload()
                response = pg_client.post("/api/property-images", data=data, files=files)
        assert response.status_code == 201

    def test_upload_response_contains_id(self, pg_client):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload()
                body = pg_client.post("/api/property-images", data=data, files=files).json()
        assert "id" in body
        uuid.UUID(body["id"])  # must be a valid UUID

    def test_upload_response_contains_property_id(self, pg_client):
        prop_id = f"prop-{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload(property_id=prop_id)
                body = pg_client.post("/api/property-images", data=data, files=files).json()
        assert body["property_id"] == prop_id

    def test_upload_response_contains_file_size(self, pg_client):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload(size=100)
                body = pg_client.post("/api/property-images", data=data, files=files).json()
        assert body["file_size"] > 0

    def test_upload_persists_caption(self, pg_client):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload(caption="Front door view")
                body = pg_client.post("/api/property-images", data=data, files=files).json()
        assert body["caption"] == "Front door view"

    def test_upload_persists_uploaded_by(self, pg_client):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload(uploaded_by="agent@test.com")
                body = pg_client.post("/api/property-images", data=data, files=files).json()
        assert body["uploaded_by"] == "agent@test.com"

    def test_upload_image_metadata_in_postgres(self, pg_client):
        """Confirms the upload actually persists metadata to PostgreSQL."""
        prop_id = f"prop-{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload(property_id=prop_id)
                created = pg_client.post("/api/property-images", data=data, files=files).json()

        # Re-fetch and confirm the record is in the database
        results = pg_client.get(f"/api/property-images?property_id={prop_id}").json()
        ids = [item["id"] for item in results]
        assert created["id"] in ids

    def test_upload_png_image_accepted(self, pg_client):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload(
                    content_type="image/png",
                    filename="test.png",
                )
                response = pg_client.post("/api/property-images", data=data, files=files)
        assert response.status_code == 201

    def test_upload_webp_image_accepted(self, pg_client):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload(
                    content_type="image/webp",
                    filename="test.webp",
                )
                response = pg_client.post("/api/property-images", data=data, files=files)
        assert response.status_code == 201

    def test_upload_gif_image_accepted(self, pg_client):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload(
                    content_type="image/gif",
                    filename="anim.gif",
                )
                response = pg_client.post("/api/property-images", data=data, files=files)
        assert response.status_code == 201

    def test_upload_creates_file_on_disk(self, pg_client):
        """Verifies the image bytes are written to the upload directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload()
                body = pg_client.post("/api/property-images", data=data, files=files).json()

            # The file_path in the response should have been written to disk
            assert os.path.exists(body["file_path"])

    def test_multiple_images_same_property(self, pg_client):
        """Multiple images can be uploaded for the same property_id."""
        prop_id = f"prop-{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                for i in range(3):
                    data, files = _make_image_upload(property_id=prop_id, caption=f"Image {i}")
                    resp = pg_client.post("/api/property-images", data=data, files=files)
                    assert resp.status_code == 201

        results = pg_client.get(f"/api/property-images?property_id={prop_id}").json()
        assert len(results) >= 3


# ---------------------------------------------------------------------------
# Upload endpoint — size limits and error handling
# ---------------------------------------------------------------------------

class TestPropertyImageSizeLimitsIntegration:
    """Ensures file uploads respect size limits and error handling."""

    def test_file_exceeding_10mb_returns_413(self, pg_client):
        """File above the 10 MB limit must be rejected with HTTP 413."""
        oversized = b"\x00" * (11 * 1024 * 1024)  # 11 MB
        response = pg_client.post(
            "/api/property-images",
            data={"property_id": "prop-size-test"},
            files={"file": ("big.jpg", io.BytesIO(oversized), "image/jpeg")},
        )
        assert response.status_code == 413

    def test_413_error_body_contains_detail(self, pg_client):
        oversized = b"\x00" * (11 * 1024 * 1024)
        response = pg_client.post(
            "/api/property-images",
            data={"property_id": "prop-size-test"},
            files={"file": ("big.jpg", io.BytesIO(oversized), "image/jpeg")},
        )
        body = response.json()
        assert "detail" in body
        assert "large" in body["detail"].lower() or "MB" in body["detail"]

    def test_file_at_exact_10mb_limit_accepted(self, pg_client):
        """A file exactly at 10 MB should be accepted."""
        exact_size = 10 * 1024 * 1024  # exactly 10 MB
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                response = pg_client.post(
                    "/api/property-images",
                    data={"property_id": "prop-size-exact"},
                    files={"file": ("exact.jpg", io.BytesIO(b"\x00" * exact_size), "image/jpeg")},
                )
        assert response.status_code == 201

    def test_unsupported_content_type_returns_415(self, pg_client):
        """PDF files must be rejected with HTTP 415."""
        response = pg_client.post(
            "/api/property-images",
            data={"property_id": "prop-001"},
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        assert response.status_code == 415

    def test_415_error_body_contains_supported_types(self, pg_client):
        response = pg_client.post(
            "/api/property-images",
            data={"property_id": "prop-001"},
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        body = response.json()
        assert "detail" in body
        assert "application/pdf" in body["detail"]

    def test_text_plain_content_type_returns_415(self, pg_client):
        response = pg_client.post(
            "/api/property-images",
            data={"property_id": "prop-001"},
            files={"file": ("note.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert response.status_code == 415

    def test_missing_property_id_returns_422(self, pg_client):
        response = pg_client.post(
            "/api/property-images",
            files={"file": ("img.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")},
        )
        assert response.status_code == 422

    def test_missing_file_returns_422(self, pg_client):
        response = pg_client.post(
            "/api/property-images",
            data={"property_id": "prop-001"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Retrieval endpoint — correct operation
# ---------------------------------------------------------------------------

class TestPropertyImageRetrievalIntegration:
    """Validates correct operation of the retrieval endpoint against PostgreSQL."""

    def test_list_images_returns_200(self, pg_client):
        response = pg_client.get("/api/property-images")
        assert response.status_code == 200

    def test_list_images_is_list(self, pg_client):
        data = pg_client.get("/api/property-images").json()
        assert isinstance(data, list)

    def test_filter_by_property_id_returns_correct_records(self, pg_client):
        prop_id = f"prop-{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload(property_id=prop_id)
                pg_client.post("/api/property-images", data=data, files=files)

        results = pg_client.get(f"/api/property-images?property_id={prop_id}").json()
        assert len(results) >= 1
        for item in results:
            assert item["property_id"] == prop_id

    def test_filter_by_unknown_property_id_returns_empty(self, pg_client):
        results = pg_client.get("/api/property-images?property_id=nonexistent-9999").json()
        assert results == []

    def test_filter_by_uploaded_by(self, pg_client):
        unique_uploader = f"uploader-{uuid.uuid4().hex[:8]}@test.com"
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload(uploaded_by=unique_uploader)
                pg_client.post("/api/property-images", data=data, files=files)

        results = pg_client.get(
            f"/api/property-images?uploaded_by={unique_uploader}"
        ).json()
        assert len(results) >= 1
        for item in results:
            assert item["uploaded_by"] == unique_uploader

    def test_response_schema_has_required_fields(self, pg_client):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                data, files = _make_image_upload()
                pg_client.post("/api/property-images", data=data, files=files)

        items = pg_client.get("/api/property-images").json()
        assert len(items) >= 1
        item = items[0]
        for field in ("id", "property_id", "filename", "content_type", "file_size", "created_at"):
            assert field in item, f"Missing field: {field}"

    def test_no_cross_property_contamination(self, pg_client):
        """Filtering by property_id must not return images from other properties."""
        prop_a = f"prop-A-{uuid.uuid4().hex[:6]}"
        prop_b = f"prop-B-{uuid.uuid4().hex[:6]}"
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                for pid in (prop_a, prop_b):
                    d, f = _make_image_upload(property_id=pid)
                    pg_client.post("/api/property-images", data=d, files=f)

        results_a = pg_client.get(f"/api/property-images?property_id={prop_a}").json()
        for item in results_a:
            assert item["property_id"] == prop_a
            assert item["property_id"] != prop_b


# ---------------------------------------------------------------------------
# Database interaction simulation
# ---------------------------------------------------------------------------

class TestPropertyImageDatabaseInteractionIntegration:
    """Tests simulate database conditions for the PropertyImage service."""

    def test_db_session_rollback_on_error(self, pg_session):
        """
        Simulate a DB error mid-transaction: verify session can roll back cleanly
        without leaving corrupted state.
        """
        from app.models.property_image import PropertyImage

        img = PropertyImage(
            property_id="prop-rollback",
            filename="rollback_test.jpg",
            original_filename="rollback_test.jpg",
            content_type="image/jpeg",
            file_size=512,
            file_path="/tmp/rollback_test.jpg",
        )
        pg_session.add(img)

        # Roll back before commit — record should not persist
        pg_session.rollback()

        count = pg_session.query(PropertyImage).filter(
            PropertyImage.filename == "rollback_test.jpg"
        ).count()
        assert count == 0

    def test_duplicate_upload_creates_separate_records(self, pg_client):
        """Each upload must create a distinct record, even with identical data."""
        prop_id = f"prop-dup-{uuid.uuid4().hex[:6]}"
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                for _ in range(2):
                    d, f = _make_image_upload(property_id=prop_id)
                    r = pg_client.post("/api/property-images", data=d, files=f)
                    assert r.status_code == 201

        results = pg_client.get(f"/api/property-images?property_id={prop_id}").json()
        ids = [item["id"] for item in results]
        assert len(ids) == len(set(ids)), "Duplicate IDs found — records not distinct"

    def test_sequential_uploads_retrievable_individually(self, pg_client):
        """Each uploaded image must be individually identifiable by its UUID."""
        prop_id = f"prop-seq-{uuid.uuid4().hex[:6]}"
        created_ids = []
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                for i in range(3):
                    d, f = _make_image_upload(property_id=prop_id, caption=f"View {i}")
                    body = pg_client.post("/api/property-images", data=d, files=f).json()
                    created_ids.append(body["id"])

        results = pg_client.get(f"/api/property-images?property_id={prop_id}").json()
        result_ids = {item["id"] for item in results}
        for cid in created_ids:
            assert cid in result_ids

    def test_upload_dir_written_correctly(self, pg_client):
        """Validates that file bytes are flushed to the upload directory."""
        content = b"\xff\xd8\xff" + b"\xAB" * 128
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                response = pg_client.post(
                    "/api/property-images",
                    data={"property_id": "prop-dir-test"},
                    files={"file": ("check.jpg", io.BytesIO(content), "image/jpeg")},
                )
                assert response.status_code == 201
                body = response.json()
                assert os.path.isfile(body["file_path"])
                with open(body["file_path"], "rb") as fh:
                    written = fh.read()
                assert written == content


# ---------------------------------------------------------------------------
# Network/database condition simulation
# ---------------------------------------------------------------------------

class TestPropertyImageNetworkConditionsIntegration:
    """
    Tests simulate network and database conditions to ensure robustness.
    These use mocking to simulate conditions that cannot be induced against a
    live database deterministically (e.g., transient failures, connection drops).
    """

    def test_db_write_failure_returns_500(self, pg_client):
        """
        Simulate a database write failure (e.g., disk full, connection lost).
        The endpoint must return 500 and not crash the process.
        """
        from app.main import app
        from app.deps import get_db

        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock(
            side_effect=OperationalError("disk full", None, None)
        )

        def bad_db():
            yield mock_session

        app.dependency_overrides[get_db] = bad_db
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with patch("app.routers.property_images.settings") as ms:
                    ms.upload_dir = tmpdir
                    response = pg_client.post(
                        "/api/property-images",
                        data={"property_id": "prop-db-fail"},
                        files={
                            "file": (
                                "img.jpg",
                                io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 10),
                                "image/jpeg",
                            )
                        },
                    )
            assert response.status_code == 500
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_upload_dir_creation_failure_raises_error(self, pg_client):
        """
        Simulate a filesystem error when creating the upload directory.
        The endpoint should propagate the error as a server error.
        """
        with patch("app.routers.property_images.os.makedirs") as mock_makedirs:
            mock_makedirs.side_effect = OSError("Permission denied")
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = "/nonexistent/restricted/path"
                response = pg_client.post(
                    "/api/property-images",
                    data={"property_id": "prop-fs-fail"},
                    files={
                        "file": (
                            "img.jpg",
                            io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 10),
                            "image/jpeg",
                        )
                    },
                )
        assert response.status_code == 500

    def test_large_valid_upload_near_limit(self, pg_client):
        """
        A file just below the 10 MB size limit should be accepted successfully,
        confirming the boundary condition is correct.
        """
        just_under = b"\x00" * (10 * 1024 * 1024 - 1)  # 10 MB - 1 byte
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.routers.property_images.settings") as ms:
                ms.upload_dir = tmpdir
                response = pg_client.post(
                    "/api/property-images",
                    data={"property_id": "prop-near-limit"},
                    files={"file": ("near.jpg", io.BytesIO(just_under), "image/jpeg")},
                )
        assert response.status_code == 201
