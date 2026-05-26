"""SSE transport for production deployment."""

import json
import logging
import os

import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from pymilvus import MilvusClient
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp_server_template import auth

logger = logging.getLogger(__name__)

_CONTENT_VECTOR_FIELD = "vector"
_QUESTIONS_SUFFIX = "_questions"
_OUTPUT_FIELDS = [
    "document_id", "sharepoint_url", "subject",
    "jurisdiction", "policy_type", "country_code", "language", "document_category",
]


def _make_embedding_fn():
    """Return an embedding provider that matches whatever built the Milvus DB.

    Set EMBEDDING_PROVIDER=azure_openai (requires AZURE_OPENAI_* vars) or
    leave unset for the local pymilvus ONNX model (dim=768).
    """
    provider = os.environ.get("EMBEDDING_PROVIDER", "pymilvus").lower()

    if provider == "azure_openai":
        from openai import AzureOpenAI  # noqa: PLC0415

        _client = AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )
        _deployment = os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]

        class _AzureEmbeddings:
            def encode_queries(self, texts: list[str]) -> list[list[float]]:
                resp = _client.embeddings.create(model=_deployment, input=texts)
                return [item.embedding for item in resp.data]

        logger.info("Embedding provider: Azure OpenAI (%s)", _deployment)
        return _AzureEmbeddings()

    from pymilvus import model as milvus_model  # noqa: PLC0415

    logger.info("Embedding provider: pymilvus ONNX (dim=768)")
    return milvus_model.DefaultEmbeddingFunction()


def run_sse_server(server: Server, host: str = "0.0.0.0", port: int = 8000):
    sse = SseServerTransport("/messages/")

    # Initialise once at startup — MilvusClient holds the file lock for the
    # lifetime of the process; embedding client is created once and reused.
    db_path = os.environ.get("MILVUS_DB_PATH", "")
    collection = os.environ.get("MILVUS_COLLECTION", "hr")
    embedding_fn = _make_embedding_fn()
    milvus_client = MilvusClient(db_path) if db_path else None

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
        """
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        question = (body.get("question") or "").strip()
        if not question:
            return JSONResponse({"error": "question is required"}, status_code=400)

        if milvus_client is None:
            return JSONResponse({"error": "MILVUS_DB_PATH is not configured"}, status_code=503)

        logger.info("ask: %s", question)

        vector = embedding_fn.encode_queries([question])[0]
        ann_params = {"metric_type": "L2", "params": {}}

        milvus_client.load_collection(collection)
        topic_hits = milvus_client.search(
            collection_name=collection,
            data=[vector],
            anns_field=_CONTENT_VECTOR_FIELD,
            search_params=ann_params,
            limit=10,
            output_fields=_OUTPUT_FIELDS,
        )
        topic_hits = topic_hits[0] if topic_hits else []

        question_hits = []
        questions_collection = collection + _QUESTIONS_SUFFIX
        if milvus_client.has_collection(questions_collection):
            milvus_client.load_collection(questions_collection)
            q_results = milvus_client.search(
                collection_name=questions_collection,
                data=[vector],
                anns_field=_CONTENT_VECTOR_FIELD,
                search_params=ann_params,
                limit=15,
                output_fields=_OUTPUT_FIELDS + ["question_text"],
            )
            question_hits = q_results[0] if q_results else []

        # Merge: best (lowest L2) per unique (document_id, subject)
        seen: dict[tuple, dict] = {}
        for hit, src in [(h, "topic") for h in topic_hits] + [(h, "question") for h in question_hits]:
            key = (hit["entity"].get("document_id", ""), hit["entity"].get("subject", ""))
            if key not in seen or hit["distance"] < seen[key]["distance"]:
                seen[key] = {**hit, "_source": src}
        merged = sorted(seen.values(), key=lambda h: h["distance"])[:3]

        if not merged:
            return JSONResponse({"answer": "No relevant policy found.", "source": None})

        top = merged[0]
        subject = top["entity"].get("subject", "")
        url = top["entity"].get("sharepoint_url", "")
        logger.info("top result: %s  dist=%.4f  url=%s", subject, top["distance"], url)

        return JSONResponse({
            "answer": subject,
            "source": {"name": subject, "url": url} if url else None,
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
