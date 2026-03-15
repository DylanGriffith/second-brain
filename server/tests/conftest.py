import io
import os
import time
import uuid
import zipfile
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from second_brain.app import app
from second_brain.config import Settings
from second_brain.storage.vespa import VespaStorage

VESPA_TEST_URL = os.getenv("VESPA_TEST_URL", "http://vespa-01:8080")
VESPA_CONFIG_URL = os.getenv("VESPA_CONFIG_URL", "http://vespa-01:19071")
APP_DIR = Path(__file__).parent.parent / "vespa" / "app"


def _build_deploy_zip() -> bytes:
    """Zip the vespa app directory, skipping any local .onnx files (model is URL-referenced)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(APP_DIR.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix == ".onnx":
                continue  # referenced by URL in services.xml
            arcname = str(path.relative_to(APP_DIR))
            zf.write(path, arcname)
    return buf.getvalue()


def deploy_vespa_app() -> None:
    """Deploy the Vespa application via the config server HTTP API and wait for convergence."""
    zip_bytes = _build_deploy_zip()
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            f"{VESPA_CONFIG_URL}/application/v2/tenant/default/prepareandactivate",
            content=zip_bytes,
            headers={"Content-Type": "application/zip"},
        )
        if resp.status_code not in (200, 202):
            raise RuntimeError(f"Vespa deploy failed ({resp.status_code}): {resp.text[:500]}")

        # Wait for schema to be active by polling a sentinel document index.
        # The namespace field is new - once indexing succeeds, the schema is live.
        sentinel_id = "convergence_check%3Asentinel"
        sentinel_body = {
            "fields": {
                "global_id": "convergence_check:sentinel",
                "namespace": "_deploy_check",
                "title": "deploy check",
                "domain": "deploy",
                "snippet": "deploy check",
                "last_seen": 0,
            }
        }
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            r = client.post(
                f"{VESPA_TEST_URL}/document/v1/_deploy_check/items/docid/{sentinel_id}",
                json=sentinel_body,
                timeout=10.0,
            )
            if r.status_code == 200:
                # Clean up sentinel
                client.delete(f"{VESPA_TEST_URL}/document/v1/_deploy_check/items/docid/{sentinel_id}")
                return
            time.sleep(2)
        raise RuntimeError("Vespa schema did not become active within 120s")


@pytest.fixture(scope="session", autouse=True)
def vespa_schema_deployed():
    """Deploy the Vespa schema before any tests run."""
    deploy_vespa_app()


@pytest.fixture(scope="session")
def test_namespace():
    return f"test_{uuid.uuid4().hex[:12]}"


@pytest.fixture(scope="session")
def vespa_storage():
    return VespaStorage(VESPA_TEST_URL)


@pytest_asyncio.fixture(scope="session")
async def cleanup_namespace(test_namespace, vespa_storage):
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
