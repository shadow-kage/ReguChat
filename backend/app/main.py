from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)
