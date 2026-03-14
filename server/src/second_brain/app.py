import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from second_brain.config import Settings
from second_brain.storage.vespa import VespaStorage
from second_brain.routes import index, search, status, ui


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    storage = VespaStorage(settings.vespa_url)
    app.state.storage = storage
    app.state.settings = settings
    yield


app = FastAPI(
    title="Second Brain",
    description="Search your personal knowledge base",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(index.router)
app.include_router(search.router)
app.include_router(status.router)
app.include_router(ui.router)
