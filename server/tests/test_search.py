import asyncio
import time
import pytest


SEARCH_DOCS = [
    {
        "global_id": "test_source:python_doc",
        "title": "Python Programming",
        "domain": "docs.python.org",
        "snippet": "Python is a high-level programming language",
        "last_seen": int(time.time() * 1000),
        "url": "https://docs.python.org",
    },
    {
        "global_id": "test_source:golang_doc",
        "title": "Go Programming Language",
        "domain": "go.dev",
        "snippet": "Go is an open source programming language",
        "last_seen": int(time.time() * 1000),
        "url": "https://go.dev",
    },
    {
        "global_id": "test_source:vespa_doc",
        "title": "Vespa Search Engine",
        "domain": "vespa.ai",
        "snippet": "Vespa is a platform for applications combining data and AI",
        "last_seen": int(time.time() * 1000),
        "url": "https://vespa.ai",
    },
]


@pytest.fixture(scope="module", autouse=True)
async def index_search_docs(test_client):
    response = await test_client.post("/api/v1/documents", json={"documents": SEARCH_DOCS})
    assert response.status_code == 200
    # Give Vespa time to index
    await asyncio.sleep(2)
    yield


@pytest.mark.asyncio
async def test_search_returns_results(test_client):
    response = await test_client.get("/api/v1/search?q=programming&hits=10")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "programming"
    assert data["count"] >= 1
    assert len(data["results"]) >= 1


@pytest.mark.asyncio
async def test_search_result_fields(test_client):
    response = await test_client.get("/api/v1/search?q=Python&hits=10")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    result = data["results"][0]
    assert "global_id" in result
    assert "title" in result
    assert "domain" in result
    assert "snippet" in result
    assert "relevance" in result


@pytest.mark.asyncio
async def test_search_namespace_isolation(test_client, vespa_storage):
    other_ns = f"other_ns_{int(time.time())}"
    doc = {
        "global_id": "test_source:isolation_doc",
        "title": "Isolation Test Document",
        "domain": "isolation.test",
        "snippet": "uniquetoken12345 isolation test",
        "last_seen": int(time.time() * 1000),
    }
    from second_brain.models import Document
    await vespa_storage.index_document(Document(**doc), namespace=other_ns)
    await asyncio.sleep(1)

    response = await test_client.get("/api/v1/search?q=uniquetoken12345&hits=10")
    assert response.status_code == 200
    data = response.json()
    global_ids = [r["global_id"] for r in data["results"]]
    assert "test_source:isolation_doc" not in global_ids

    await vespa_storage.delete_all_in_namespace(other_ns)
