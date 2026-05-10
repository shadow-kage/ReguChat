import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas import DomainInfo, HealthResponse, QueryRequest, QueryResponse
from app.domain import DomainRegistry
from app.services.answer import run_query, stream_query

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    registry = DomainRegistry.get_instance()
    return HealthResponse(status="ok", domains=registry.ids())


@router.get("/domains", response_model=list[DomainInfo])
async def list_domains():
    registry = DomainRegistry.get_instance()
    return [
        DomainInfo(id=d.id, name=d.name, description=d.description)
        for d in registry.list_all()
    ]


@router.get("/domains/{domain_id}", response_model=DomainInfo)
async def get_domain(domain_id: str):
    domain = DomainRegistry.get_instance().get(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_id}' not found.")
    return DomainInfo(id=domain.id, name=domain.name, description=domain.description)


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")
    result, cached = await run_query(request.domain_id, request.query)
    return QueryResponse(
        answer=result.text,
        domain_id=request.domain_id,
        cached=cached,
        is_fallback=result.is_fallback,
    )


@router.post("/query/stream")
async def query_stream(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    async def event_generator():
        async for event in stream_query(request.domain_id, request.query):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
