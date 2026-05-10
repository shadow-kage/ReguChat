from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    domain_id: str


class QueryResponse(BaseModel):
    answer: str
    domain_id: str
    cached: bool
    is_fallback: bool


class DomainInfo(BaseModel):
    id: str
    name: str
    description: str


class HealthResponse(BaseModel):
    status: str
    domains: list[str]
