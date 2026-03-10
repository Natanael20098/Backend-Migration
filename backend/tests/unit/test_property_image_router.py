"""
Unit tests for app/routers/property_images.py

Covers:
  - POST /api/property-images  (upload)
  - GET  /api/property-images  (list with filtering)

Edge cases:
  - File too large → 413
  - Unsupported content type → 415
  - Missing required form fields → 422
  - Filtering by property_id and uploaded_by
  - Response shape validation
"""

import io
import os
import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_image_file(size: int = 100, content_type: str = "image/jpeg") -> tuple:
    """Return (filename, file-like, content_type) for a synthetic image upload."""
    content = b"\xff\xd8\xff" + b"\x00" * size  # minimal JPEG-like bytes
    return ("test_image.jpg", io.BytesIO(content), content_type)


def _upload_image(
    client: TestClient,
    property_id: str = "prop-001",
    size: int = 100,
    content_type: str = "image/jpeg",
    **extra_data,
) -> dict:
    """POST a property image and return the response JSON."""
    filename, file_obj, ct = _make_image_file(size, content_type)
    data = {"property_id": property_id, **extra_data}
    response = client.post(
        "/api/property-images",
        data=data,
        files={"file": (filename, file_obj, ct)},
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------

class TestPropertyImageModel:
    """ORM model maps to the expected table and columns."""

    def test_tablename(self):
        from app.models.property_image import PropertyImage
        assert PropertyImage.__tablename__ == "property_images"

    def test_has_id(self):
        from app.models.property_image import PropertyImage
        assert hasattr(PropertyImage, "id")

    def test_has_property_id(self):
        from app.models.property_image import PropertyImage
        assert hasattr(PropertyImage, "property_id")

    def test_has_filename(self):
        from app.models.property_image import PropertyImage
        assert hasattr(PropertyImage, "filename")

    def test_has_original_filename(self):
        from app.models.property_image import PropertyImage
        assert hasattr(PropertyImage, "original_filename")

    def test_has_content_type(self):
        from app.models.property_image import PropertyImage
        assert hasattr(PropertyImage, "content_type")

    def test_has_file_size(self):
        from app.models.property_image import PropertyImage
        assert hasattr(PropertyImage, "file_size")

    def test_has_file_path(self):
        from app.models.property_image import PropertyImage
        assert hasattr(PropertyImage, "file_path")

    def test_has_created_at(self):
        from app.models.property_image import PropertyImage
        assert hasattr(PropertyImage, "created_at")

    def test_db_persistence(self, db_session, tmp_path):
        """PropertyImage can be persisted and retrieved from SQLite."""
        from app.models.property_image import PropertyImage

        img = PropertyImage(
            property_id="prop-999",
            filename="stored_name.jpg",
            original_filename="original.jpg",
            content_type="image/jpeg",
            file_size=1024,
            file_path=str(tmp_path / "stored_name.jpg"),
        )
        db_session.add(img)
        db_session.commit()
        db_session.refresh(img)

        fetched = db_session.get(PropertyImage, img.id)
        assert fetched is not None
        assert fetched.property_id == "prop-999"
        assert fetched.file_size == 1024


# ---------------------------------------------------------------------------
# Schema unit tests
# ---------------------------------------------------------------------------

class TestPropertyImageSchemas:
    """Pydantic schema validates from ORM correctly."""

    def test_read_schema_from_orm(self, db_session, tmp_path):
        from app.models.property_image import PropertyImage
        from app.schemas.property_image import PropertyImageRead

        img = PropertyImage(
            property_id="prop-111",
            filename="f.jpg",
            original_filename="orig.jpg",
            content_type="image/jpeg",
            file_size=512,
            file_path=str(tmp_path / "f.jpg"),
        )
        db_session.add(img)
        db_session.commit()
        db_session.refresh(img)

        schema = PropertyImageRead.model_validate(img)
        assert schema.property_id == "prop-111"
        assert schema.file_size == 512


# ---------------------------------------------------------------------------
# POST /api/property-images
# ---------------------------------------------------------------------------

class TestUploadPropertyImage:
    """POST /api/property-images — upload endpoint."""

    def test_returns_201(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            response = app_client.post(
                "/api/property-images",
                data={"property_id": "prop-001"},
                files={"file": ("img.jpg", io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 10), "image/jpeg")},
            )
        assert response.status_code == 201

    def test_response_contains_id(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            data = _upload_image(app_client, property_id="prop-001")
        assert "id" in data
        uuid.UUID(data["id"])

    def test_response_contains_property_id(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            data = _upload_image(app_client, property_id="prop-XYZ")
        assert data["property_id"] == "prop-XYZ"

    def test_response_contains_file_size(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            data = _upload_image(app_client, property_id="prop-001", size=50)
        assert data["file_size"] > 0

    def test_response_contains_created_at(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            data = _upload_image(app_client, property_id="prop-001")
        assert "created_at" in data
        datetime.fromisoformat(data["created_at"])

    def test_caption_persisted(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            data = _upload_image(app_client, property_id="prop-001", caption="Front view")
        assert data["caption"] == "Front view"

    def test_uploaded_by_persisted(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            data = _upload_image(app_client, property_id="prop-001", uploaded_by="agent@example.com")
        assert data["uploaded_by"] == "agent@example.com"

    def test_unsupported_content_type_returns_415(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            response = app_client.post(
                "/api/property-images",
                data={"property_id": "prop-001"},
                files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            )
        assert response.status_code == 415

    def test_file_too_large_returns_413(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            oversized = b"\x00" * (11 * 1024 * 1024)  # 11 MB
            response = app_client.post(
                "/api/property-images",
                data={"property_id": "prop-001"},
                files={"file": ("big.jpg", io.BytesIO(oversized), "image/jpeg")},
            )
        assert response.status_code == 413

    def test_missing_property_id_returns_422(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            response = app_client.post(
                "/api/property-images",
                files={"file": ("img.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")},
            )
        assert response.status_code == 422

    def test_missing_file_returns_422(self, app_client: TestClient, tmp_path):
        response = app_client.post(
            "/api/property-images",
            data={"property_id": "prop-001"},
        )
        assert response.status_code == 422

    def test_png_upload_accepted(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            response = app_client.post(
                "/api/property-images",
                data={"property_id": "prop-001"},
                files={"file": ("img.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10), "image/png")},
            )
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# GET /api/property-images
# ---------------------------------------------------------------------------

class TestListPropertyImages:
    """GET /api/property-images — list endpoint with filtering."""

    def test_returns_200(self, app_client: TestClient):
        response = app_client.get("/api/property-images")
        assert response.status_code == 200

    def test_empty_list(self, app_client: TestClient):
        response = app_client.get("/api/property-images")
        assert response.json() == []

    def test_returns_uploaded_images(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            _upload_image(app_client, property_id="prop-001")
            _upload_image(app_client, property_id="prop-002")
        results = app_client.get("/api/property-images").json()
        assert len(results) == 2

    def test_filter_by_property_id(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            _upload_image(app_client, property_id="prop-A")
            _upload_image(app_client, property_id="prop-B")
        results = app_client.get("/api/property-images?property_id=prop-A").json()
        assert len(results) == 1
        assert results[0]["property_id"] == "prop-A"

    def test_filter_by_uploaded_by(self, app_client: TestClient, tmp_path):
        with patch("app.routers.property_images.settings") as mock_settings:
            mock_settings.upload_dir = str(tmp_path)
            _upload_image(app_client, property_id="prop-001", uploaded_by="alice@example.com")
            _upload_image(app_client, property_id="prop-002", uploaded_by="bob@example.com")
        results = app_client.get(
            "/api/property-images?uploaded_by=alice@example.com"
        ).json()
        assert len(results) == 1
        assert results[0]["uploaded_by"] == "alice@example.com"

    def test_response_is_list(self, app_client: TestClient):
        response = app_client.get("/api/property-images")
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

class TestPropertyImageRouterRegistration:
    """PropertyImage router is mounted on the FastAPI app."""

    def test_post_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/property-images" in paths

    def test_get_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/property-images" in paths
