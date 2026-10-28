"""Marine intelligence query API endpoint."""

from fastapi import APIRouter
from app.schemas.query import MarineQueryRequest, MarineQueryResponse
from app.services.query_workflow import QueryWorkflowEngine

router = APIRouter(tags=["Marine Query"])

_engine = QueryWorkflowEngine()


@router.post("/query", response_model=MarineQueryResponse)
async def marine_query(request: MarineQueryRequest) -> MarineQueryResponse:
    """Submit a natural language marine intelligence query.

    The engine classifies intent, audits upstream data sources, validates
    evidence provenance, and returns a fully grounded response.

    Strict safety rules are enforced:
    - No expired advisories are returned as active PFZ guidance.
    - No onshore landing center coordinates are returned as offshore hotspots.
    - No fabricated or synthetic coordinates are generated.

    Example request body:
    ```json
    {
        "query": "Where can I fish near Malpe today?",
        "user_location": {"latitude": 13.36, "longitude": 74.7},
        "departure_port": "Malpe"
    }
    ```
    """
    return await _engine.run(request)
