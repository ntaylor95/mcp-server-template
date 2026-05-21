"""SSE transport for production deployment."""

import json
import logging

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp_server_template import auth

logger = logging.getLogger(__name__)


def run_sse_server(server: Server, host: str = "0.0.0.0", port: int = 8000):
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        # Extract the caller's Bearer token and place it in the request context
        # so that tool handlers can use it for the OBO exchange when AUTH_MODE=obo.
        raw = request.headers.get("Authorization", "")
        token = raw[len("Bearer "):].strip() if raw.startswith("Bearer ") else None
        auth.set_user_token(token)

        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def ask(request: Request) -> JSONResponse:
        """Query endpoint for the chat UI.

        Request body:  { "question": string }
        Response body: { "answer": string, "source": { "name": string, "url": string } | null }

        TODO: replace stub with real pipeline —
              Milvus search → SharePoint fetch → Docling → LLM answer
        """
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        question = (body.get("question") or "").strip()
        if not question:
            return JSONResponse({"error": "question is required"}, status_code=400)

        logger.info("ask: %s", question)

        # --- STUB: replace with the real query pipeline ---
        return JSONResponse({
            "answer": (
                f"This is a placeholder response for: \"{question}\"\n\n"
                "The query pipeline (Milvus → SharePoint → LLM) is not wired up yet."
            ),
            "source": None,
        })

    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],  # Vite dev server
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    ]

    app = Starlette(
        middleware=middleware,
        routes=[
            Route("/health", endpoint=health, methods=["GET"]),
            Route("/api/ask", endpoint=ask, methods=["POST"]),
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    uvicorn.run(app, host=host, port=port)
