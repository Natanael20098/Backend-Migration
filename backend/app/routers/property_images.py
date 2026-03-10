"""
PropertyImage API endpoints.

Endpoints:
  POST  /api/property-images            — upload and store image metadata
  GET   /api/property-images            — retrieve images with filtering
"""

import logging
import os
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.deps import get_db
from app.models.property_image import PropertyImage
from app.schemas.property_image import PropertyImageRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/property-images", tags=["property-images"])

# 10 MB maximum file size
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}


@router.post("", response_model=PropertyImageRead, status_code=201)
async def upload_property_image(
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    property_id: str = Form(...),
    caption: Optional[str] = Form(default=None),
    display_order: Optional[int] = Form(default=0),
    uploaded_by: Optional[str] = Form(default=None),
) -> PropertyImage:
    """Upload an image file and store its metadata in the database."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type: {file.content_type}. Allowed: {sorted(ALLOWED_CONTENT_TYPES)}",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    # Persist file to the uploads directory
    upload_dir = settings.upload_dir
    os.makedirs(upload_dir, exist_ok=True)

    stored_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(upload_dir, stored_filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    image = PropertyImage(
        property_id=property_id,
        filename=stored_filename,
        original_filename=file.filename or stored_filename,
        content_type=file.content_type,
        file_size=len(contents),
        file_path=file_path,
        caption=caption,
        display_order=display_order,
        uploaded_by=uploaded_by,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    logger.info(
        "PropertyImage uploaded: id=%s property_id=%s filename=%s size=%d bytes",
        image.id,
        property_id,
        stored_filename,
        len(contents),
    )
    return image


@router.get("", response_model=list[PropertyImageRead])
def list_property_images(
    db: Annotated[Session, Depends(get_db)],
    property_id: Optional[str] = Query(default=None),
    uploaded_by: Optional[str] = Query(default=None),
) -> list[PropertyImage]:
    """Return property images, optionally filtered by property_id or uploaded_by."""
    query = db.query(PropertyImage)
    if property_id is not None:
        query = query.filter(PropertyImage.property_id == property_id)
    if uploaded_by is not None:
        query = query.filter(PropertyImage.uploaded_by == uploaded_by)

    results = query.order_by(PropertyImage.display_order, PropertyImage.created_at).all()
    logger.info(
        "Listed %d property images (property_id=%s)", len(results), property_id
    )
    return results
