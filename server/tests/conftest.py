import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from second_brain.app import app
from second_brain.config import Settings
from second_brain.storage.vespa import VespaStorage

VESPA_TEST_URL = "http://vespa-01:8080"


@pytest.fixture(scope="session")
def test_namespace():
    return f"test_{uuid.uuid4().hex[:12]}"


@pytest.fixture(scope="session")
def vespa_storage():
    return VespaStorage(VESPA_TEST_URL)


@pytest_asyncio.fixture(scope="session")
async def cleanup_namespace(test_namespace, vespa_storage, request):
    yield
    try:
        await vespa_storage.delete_all_in_namespace(test_namespace)
    except Exception as e:
        print(f"Cleanup warning: {e}")


@pytest.fixture(scope="session")
def test_settings(test_namespace):
    settings = Settings()
    settings.vespa_url = VESPA_TEST_URL
    settings.default_namespace = test_namespace
    return settings


@pytest_asyncio.fixture(scope="session")
async def test_client(test_settings, cleanup_namespace):
    app.state.storage = VespaStorage(test_settings.vespa_url)
    app.state.settings = test_settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
