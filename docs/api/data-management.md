# Data Management Microservice — API Documentation

This document describes the REST API endpoints provided by the Data Management microservice, covering **AuditLog** and **PropertyImage** resources.

---

## Base URL

```
http://localhost:8000
```

---

## Authentication

All endpoints currently rely on network-level trust (internal service communication). No JWT or API-key header is required in Phase 2. A future hardening phase will add `Authorization: Bearer <token>` headers.

---

## Common Headers

| Header         | Value              | Required |
|----------------|--------------------|----------|
| `Content-Type` | `application/json` | Yes (for JSON endpoints) |
| `Accept`       | `application/json` | Recommended |

---

## AuditLog Endpoints

### POST `/api/audit-logs`

Store a new audit log entry.

**Request Body** (`application/json`):

| Field        | Type     | Required | Constraints               | Description                          |
|--------------|----------|----------|---------------------------|--------------------------------------|
| `action`     | string   | ✅       | 1–100 chars               | Action performed (e.g. `CREATE`)     |
| `entity_type`| string   | ✅       | 1–100 chars               | Entity affected (e.g. `Property`)    |
| `entity_id`  | string   | ❌       | max 255 chars             | ID of the affected entity            |
| `user_id`    | string   | ❌       | max 255 chars             | ID of the acting user                |
| `user_email` | string   | ❌       | max 255 chars             | Email of the acting user             |
| `description`| string   | ❌       | —                         | Human-readable description           |
| `ip_address` | string   | ❌       | max 45 chars (IPv4/IPv6)  | Originating IP address               |
| `user_agent` | string   | ❌       | max 500 chars             | Client user-agent string             |

**Example Request:**
```json
{
  "action": "CREATE",
  "entity_type": "Property",
  "entity_id": "prop-123",
  "user_id": "user-456",
  "user_email": "agent@example.com",
  "description": "New property listing created",
  "ip_address": "192.168.1.10"
}
```

**Success Response** `201 Created`:
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "action": "CREATE",
  "entity_type": "Property",
  "entity_id": "prop-123",
  "user_id": "user-456",
  "user_email": "agent@example.com",
  "description": "New property listing created",
  "ip_address": "192.168.1.10",
  "user_agent": null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Responses:**

| Status | Condition                          |
|--------|------------------------------------|
| `422`  | Validation error (missing/invalid fields) |

---

### GET `/api/audit-logs`

Retrieve a paginated list of audit logs.

**Query Parameters:**

| Parameter     | Type    | Default | Constraints    | Description                                  |
|---------------|---------|---------|----------------|----------------------------------------------|
| `page`        | integer | `1`     | ≥ 1            | Page number (1-based)                        |
| `size`        | integer | `20`    | 1–100          | Number of items per page                     |
| `action`      | string  | —       | —              | Filter by exact action value                 |
| `entity_type` | string  | —       | —              | Filter by exact entity type                  |
| `user_id`     | string  | —       | —              | Filter by exact user ID                      |

**Success Response** `200 OK`:
```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "action": "CREATE",
      "entity_type": "Property",
      "entity_id": "prop-123",
      "user_id": "user-456",
      "user_email": "agent@example.com",
      "description": "New property listing created",
      "ip_address": "192.168.1.10",
      "user_agent": null,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20,
  "pages": 1
}
```

**Error Responses:**

| Status | Condition                                          |
|--------|----------------------------------------------------|
| `422`  | Invalid query parameters (e.g. `page=0`, `size=200`) |

---

## PropertyImage Endpoints

### POST `/api/property-images`

Upload a property image file and store its metadata.

**Request** (`multipart/form-data`):

| Field           | Type    | Required | Constraints                              | Description                            |
|-----------------|---------|----------|------------------------------------------|----------------------------------------|
| `file`          | file    | ✅       | ≤ 10 MB, JPEG/PNG/GIF/WebP               | Image file to upload                   |
| `property_id`   | string  | ✅       | —                                        | ID of the property this image belongs to |
| `caption`       | string  | ❌       | max 500 chars                            | Optional image caption                 |
| `display_order` | integer | ❌       | default `0`                              | Sort order for display                 |
| `uploaded_by`   | string  | ❌       | max 255 chars                            | Identifier of the uploader             |

**Allowed Content Types:** `image/jpeg`, `image/png`, `image/gif`, `image/webp`

**Example curl:**
```bash
curl -X POST http://localhost:8000/api/property-images \
  -F "file=@/path/to/image.jpg;type=image/jpeg" \
  -F "property_id=prop-123" \
  -F "caption=Front view" \
  -F "uploaded_by=agent@example.com"
```

**Success Response** `201 Created`:
```json
{
  "id": "7b3e6d2a-1234-5678-abcd-ef0123456789",
  "property_id": "prop-123",
  "filename": "a1b2c3d4-uuid_image.jpg",
  "original_filename": "image.jpg",
  "content_type": "image/jpeg",
  "file_size": 204800,
  "file_path": "/app/uploads/a1b2c3d4-uuid_image.jpg",
  "caption": "Front view",
  "display_order": 0,
  "uploaded_by": "agent@example.com",
  "created_at": "2024-01-15T10:35:00Z"
}
```

**Error Responses:**

| Status | Condition                                   |
|--------|---------------------------------------------|
| `413`  | File size exceeds 10 MB limit               |
| `415`  | Unsupported media type (non-image file)     |
| `422`  | Missing required fields (`file`, `property_id`) |

---

### GET `/api/property-images`

Retrieve a list of property images with optional filtering.

**Query Parameters:**

| Parameter     | Type   | Default | Description                              |
|---------------|--------|---------|------------------------------------------|
| `property_id` | string | —       | Filter images by property ID             |
| `uploaded_by` | string | —       | Filter images by uploader identifier     |

**Success Response** `200 OK`:
```json
[
  {
    "id": "7b3e6d2a-1234-5678-abcd-ef0123456789",
    "property_id": "prop-123",
    "filename": "a1b2c3d4-uuid_image.jpg",
    "original_filename": "image.jpg",
    "content_type": "image/jpeg",
    "file_size": 204800,
    "file_path": "/app/uploads/a1b2c3d4-uuid_image.jpg",
    "caption": "Front view",
    "display_order": 0,
    "uploaded_by": "agent@example.com",
    "created_at": "2024-01-15T10:35:00Z"
  }
]
```

Results are ordered by `display_order` ascending, then `created_at` ascending.

---

## Health Check

### GET `/health`

Returns the operational status of the service and database.

**Success Response** `200 OK`:
```json
{
  "status": "ok",
  "database": "ok",
  "last_checked": "2024-01-15T10:00:00Z"
}
```

---

## Changes from Java System

See [CHANGELOG.md](../../CHANGELOG.md) for a full list of changes from the Java monolith to this FastAPI microservice.

Key differences:
- `AuditLog` and `PropertyImage` are now exposed as dedicated REST endpoints (previously embedded in the Java monolith's `MasterService`)
- Pagination on `GET /api/audit-logs` uses `page`/`size` query parameters and returns a `{ items, total, page, size, pages }` envelope
- File uploads enforce a 10 MB size limit and restrict to image MIME types
- All timestamps are returned in ISO 8601 format with timezone (`Z` suffix)
- UUIDs are used as primary keys (matching the Java JPA UUID strategy)
