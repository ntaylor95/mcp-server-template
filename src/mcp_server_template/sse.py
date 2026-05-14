"""SSE transport for production deployment."""

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route


def run_sse_server(server: Server, host: str = "0.0.0.0", port: int = 8000):
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    app = Starlette(
        routes=[
            Route("/health", endpoint=health, methods=["GET"]),
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )

    uvicorn.run(app, host=host, port=port)
