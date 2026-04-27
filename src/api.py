import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.config import Settings, get_settings
from src.guards import PromptGuard
from src.ingest import ingest as ingest_dir
from src.llm import ClaudeClient
from src.rag import Retriever, format_context
from src.tracing import trace_query

logger = logging.getLogger("llmops_rag")


class IngestRequest(BaseModel):
    path: str = Field(..., description="Local directory containing .md documents.")


class IngestResponse(BaseModel):
    chunks_indexed: int


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    user_id: str = "anonymous"
    session_id: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=get_settings().log_level)
    app.state.guard = PromptGuard()
    app.state.llm = ClaudeClient()
    app.state.retriever = None
    yield


app = FastAPI(title="llmops-rag-pipeline", version="0.1.0", lifespan=lifespan)


def _get_retriever(settings: Settings = Depends(get_settings)) -> Retriever:
    if app.state.retriever is None:
        app.state.retriever = Retriever(settings)
    return app.state.retriever


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(req: IngestRequest) -> IngestResponse:
    target = Path(req.path)
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {req.path}")
    n = ingest_dir(target)
    return IngestResponse(chunks_indexed=n)


@app.post("/query")
async def query_endpoint(req: QueryRequest, retriever: Retriever = Depends(_get_retriever)):
    guard: PromptGuard = app.state.guard
    check = guard.check_input(req.question)
    if not check.safe:
        raise HTTPException(status_code=400, detail=check.reason or "blocked")

    chunks = retriever.retrieve(check.sanitized)
    context = format_context(chunks)
    session_id = req.session_id or str(uuid.uuid4())

    async def event_stream() -> AsyncIterator[dict]:
        llm: ClaudeClient = app.state.llm
        started = time.perf_counter()
        accumulated: list[str] = []
        with trace_query(req.user_id, session_id, check.sanitized) as generation:
            try:
                async for token in llm.stream(check.sanitized, context):
                    accumulated.append(token)
                    yield {"event": "token", "data": token}
            except Exception as exc:  # surface to client without leaking internals
                logger.exception("LLM stream failed")
                generation.update(level="ERROR", status_message=str(exc))
                yield {"event": "error", "data": "stream_failed"}
                return
            full = "".join(accumulated)
            redacted = guard.redact_output(check.sanitized, full)
            generation.update(
                output=redacted.sanitized,
                metadata={
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                    "n_chunks": len(chunks),
                    "pii_redacted": not redacted.safe,
                },
            )
            yield {"event": "done", "data": redacted.sanitized}

    return EventSourceResponse(event_stream())


@app.post("/eval")
async def eval_endpoint() -> dict[str, str]:
    return {"status": "use the eval.yml CI workflow or `python evals/ragas_eval.py`"}
