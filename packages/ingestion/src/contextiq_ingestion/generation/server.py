"""Starlette SSE API for grounded chat + observability (Phase 6–8, 17 security)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from contextiq_ingestion.generation.pipeline import GroundedChatPipeline, build_chat_pipeline
from contextiq_ingestion.observability.trace import get_trace_store
from contextiq_ingestion.query.rewriter import Turn
from contextiq_ingestion.security.auth import (
    check_api_key,
    load_auth_config,
    path_requires_auth,
)
from contextiq_ingestion.security.rate_limit import RATE_LIMITED_PATHS, RateLimiter
from contextiq_ingestion.security.validation import ValidationError, validate_query_body

logger = logging.getLogger(__name__)

_pipeline: GroundedChatPipeline | None = None
_rate_limiter = RateLimiter()


def get_pipeline() -> GroundedChatPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = build_chat_pipeline()
    return _pipeline


def create_app(
    *,
    strategy: str = "structural",
    embed_provider: str | None = None,
    generator: str | None = None,
    cors_origins: list[str] | None = None,
):
    try:
        from starlette.applications import Starlette
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.middleware.cors import CORSMiddleware
        from starlette.requests import Request
        from starlette.responses import JSONResponse, Response, StreamingResponse
        from starlette.routing import Route
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install serve extras: pip install 'contextiq-ingestion[serve]'"
        ) from exc

    global _pipeline
    _pipeline = build_chat_pipeline(
        strategy=strategy,
        embed_provider=embed_provider,
        generator=generator,
    )
    origins = cors_origins or _cors_origins_from_env()
    auth_cfg = load_auth_config()

    class SecurityMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            path = request.url.path
            if path_requires_auth(path, auth_cfg):
                headers = {k: v for k, v in request.headers.items()}
                if not check_api_key(headers, auth_cfg):
                    return JSONResponse(
                        {
                            "error": "unauthorized",
                            "detail": "Provide X-API-Key or Authorization: Bearer",
                        },
                        status_code=401,
                    )
            if path in RATE_LIMITED_PATHS and request.method == "POST":
                client = request.client.host if request.client else "unknown"
                key_hdr = request.headers.get("x-api-key") or ""
                bucket = f"{client}:{key_hdr[:8]}"
                allowed, retry_after = _rate_limiter.allow(bucket)
                if not allowed:
                    return JSONResponse(
                        {
                            "error": "rate_limited",
                            "detail": f"Try again in {retry_after}s",
                            "retry_after": retry_after,
                        },
                        status_code=429,
                        headers={"Retry-After": str(retry_after)},
                    )
            return await call_next(request)

    async def health(_: Request) -> JSONResponse:
        return JSONResponse(
            {
                "ok": True,
                "service": "contextiq-generate",
                "ready": True,
                "auth_mode": auth_cfg.mode,
                "rate_limit_per_minute": _rate_limiter.config.per_minute
                if _rate_limiter.config.enabled
                else 0,
            }
        )

    async def query(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return JSONResponse({"error": "invalid JSON body"}, status_code=400)
        try:
            cleaned = validate_query_body(body)
            result = _run_ask(cleaned)
            return JSONResponse(result.to_dict())
        except ValidationError as exc:
            return JSONResponse({"error": str(exc)}, status_code=exc.status_code)
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)

    async def query_stream(request: Request) -> Response:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return JSONResponse({"error": "invalid JSON body"}, status_code=400)
        try:
            cleaned = validate_query_body(body)
        except ValidationError as exc:
            return JSONResponse({"error": str(exc)}, status_code=exc.status_code)

        history = _history_from_body({"history": cleaned["history"]})
        query_text = cleaned["query"]

        def event_gen():
            pipe = get_pipeline()
            for ev in pipe.ask_stream_events(
                query_text,
                history=history,
                family=cleaned.get("family"),
                top_k=cleaned["top_k"],
            ):
                yield _sse(ev["event"], ev["data"])

        return StreamingResponse(
            event_gen(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def list_traces(request: Request) -> JSONResponse:
        limit = min(int(request.query_params.get("limit") or 40), 200)
        return JSONResponse({"traces": get_trace_store().list(limit=limit)})

    async def trace_stats(_: Request) -> JSONResponse:
        return JSONResponse(get_trace_store().stats())

    async def get_trace(request: Request) -> JSONResponse:
        tid = request.path_params["trace_id"]
        row = get_trace_store().get(tid)
        if not row:
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(row)

    async def feedback(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return JSONResponse({"error": "invalid JSON body"}, status_code=400)
        tid = str(body.get("trace_id") or "").strip()
        fb = str(body.get("feedback") or "").strip()
        if not tid or fb not in {"up", "down"}:
            return JSONResponse(
                {"error": "trace_id and feedback (up|down) required"}, status_code=400
            )
        if len(tid) > 128:
            return JSONResponse({"error": "trace_id too long"}, status_code=400)
        ok = get_trace_store().set_feedback(tid, fb)
        if not ok:
            return JSONResponse({"error": "trace not found"}, status_code=404)
        return JSONResponse({"ok": True, "trace_id": tid, "feedback": fb})

    async def eval_dashboard(_: Request) -> JSONResponse:
        from contextiq_ingestion.evaluation.workspace import assemble_workspace

        data = assemble_workspace()
        if not data.get("metrics_pct") and not data.get("comparison"):
            return JSONResponse(
                {"error": "No eval artifacts. Run contextiq-eval run first."},
                status_code=404,
            )
        return JSONResponse(data)

    async def eval_failures(_: Request) -> JSONResponse:
        from contextiq_ingestion.evaluation.failures import load_failure_cases

        return JSONResponse(load_failure_cases())

    async def eval_cost_tradeoffs(_: Request) -> JSONResponse:
        from contextiq_ingestion.evaluation.cost_tradeoffs import load_cost_tradeoffs

        return JSONResponse(load_cost_tradeoffs())

    app = Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Route("/query", query, methods=["POST"]),
            Route("/query/stream", query_stream, methods=["POST"]),
            Route("/traces", list_traces, methods=["GET"]),
            Route("/traces/stats", trace_stats, methods=["GET"]),
            Route("/traces/{trace_id}", get_trace, methods=["GET"]),
            Route("/feedback", feedback, methods=["POST"]),
            Route("/eval/dashboard", eval_dashboard, methods=["GET"]),
            Route("/eval/failures", eval_failures, methods=["GET"]),
            Route("/eval/cost-tradeoffs", eval_cost_tradeoffs, methods=["GET"]),
        ]
    )
    # Middleware order: last added runs first. Security then CORS.
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def _cors_origins_from_env() -> list[str]:
    raw = (os.getenv("CONTEXTIQ_CORS_ORIGINS") or "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def _run_ask(body: dict[str, Any]):
    """body is already validated via validate_query_body."""
    return get_pipeline().ask(
        body["query"],
        history=_history_from_body(body),
        family=body.get("family"),
        top_k=int(body.get("top_k") or 6),
    )


def _history_from_body(body: dict[str, Any]) -> list[Turn]:
    raw = body.get("history") or []
    turns: list[Turn] = []
    for item in raw:
        if isinstance(item, str):
            turns.append(Turn(role="user", content=item))
        elif isinstance(item, dict):
            turns.append(
                Turn(
                    role=str(item.get("role") or "user"),
                    content=str(item.get("content") or ""),
                )
            )
    return turns


def _sse(event: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="contextiq-serve")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--strategy", default="structural")
    parser.add_argument("--generator", default=None)
    parser.add_argument("--embed-provider", default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Install serve extras: pip install 'contextiq-ingestion[serve]'"
        ) from exc

    app = create_app(
        strategy=args.strategy,
        embed_provider=args.embed_provider,
        generator=args.generator,
    )
    auth = load_auth_config()
    logger.info(
        "Serving on http://%s:%s (auth_mode=%s, rate_limit=%s/min)",
        args.host,
        args.port,
        auth.mode,
        _rate_limiter.config.per_minute if _rate_limiter.config.enabled else 0,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
