from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.domain import DomainRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\nReguChat — starting up")
    print("─" * 60)
    registry = DomainRegistry.get_instance()
    registry.load_all(settings.domains_dir)
    print("─" * 60)
    yield
    print("\nReguChat — shutting down")


app = FastAPI(
    title="ReguChat",
    description="A compliance-aware domain-specific conversational AI system.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
