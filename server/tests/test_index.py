import time
import pytest
from second_brain.models import Document


def make_doc(i: int, namespace_prefix: str = "test") -> dict:
    return {
        "global_id": f"test_source:{namespace_prefix}_doc_{i}",
        "title": f"Test Document {i}",
        "domain": "test.example.com",
        "snippet": f"This is snippet number {i} about testing",
        "last_seen": int(time.time() * 1000),
    }


@pytest.mark.asyncio
async def test_index_single_document(test_client):
    doc = make_doc(1)
    response = await test_client.post("/api/v1/documents", json={"documents": [doc]})
    assert response.status_code == 200
    data = response.json()
    assert data["indexed"] == 1
    assert data["errors"] == 0


@pytest.mark.asyncio
async def test_index_batch(test_client):
    docs = [make_doc(i, "batch") for i in range(5)]
    response = await test_client.post("/api/v1/documents", json={"documents": docs})
    assert response.status_code == 200
    data = response.json()
    assert data["indexed"] == 5
    assert data["errors"] == 0


@pytest.mark.asyncio
async def test_index_optional_fields_missing(test_client):
    doc = {
        "global_id": "test_source:no_optional_fields",
        "title": "No Optional Fields",
        "domain": "test.example.com",
        "snippet": "Document without url or content",
        "last_seen": int(time.time() * 1000),
    }
    response = await test_client.post("/api/v1/documents", json={"documents": [doc]})
    assert response.status_code == 200
    data = response.json()
    assert data["indexed"] == 1


@pytest.mark.asyncio
async def test_index_upsert(test_client):
    doc = {
        "global_id": "test_source:upsert_doc",
        "title": "Original Title",
        "domain": "test.example.com",
        "snippet": "Original snippet",
        "last_seen": int(time.time() * 1000),
    }
    response = await test_client.post("/api/v1/documents", json={"documents": [doc]})
    assert response.status_code == 200

    doc["title"] = "Updated Title"
    response = await test_client.post("/api/v1/documents", json={"documents": [doc]})
    assert response.status_code == 200
    data = response.json()
    assert data["indexed"] == 1
    assert data["errors"] == 0
