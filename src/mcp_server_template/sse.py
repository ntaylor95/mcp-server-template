"""SSE transport for production deployment."""

import asyncio
import json
import logging
import multiprocessing as mp
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor

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


# ---------------------------------------------------------------------------
# Embedding provider — matches whatever built the Milvus DB
# ---------------------------------------------------------------------------

def _make_embedding_fn():
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


# ---------------------------------------------------------------------------
# Document helpers
# Copied from milvus-document-ingestion/docling_splitter.py — keep in sync
# until these repos are consolidated.
# ---------------------------------------------------------------------------

def convert_pdf(path: str, converter) -> str:
    """Convert a PDF or DOCX to markdown using Docling."""
    result = converter.convert(path)
    return result.document.export_to_markdown()


def _check_access(url: str, user_token: str | None) -> bool:
    """Return True if the current user can read this document.

    Local paths (POC test data): check the file exists on disk.
    SharePoint URLs: placeholder — always grants access for now.
    TODO: attempt a HEAD request with user_token; return False on 403/401.
    """
    if url.startswith("/"):
        return os.path.exists(url)
    return True  # placeholder


async def _fetch_document(url: str, document_id: str) -> bytes:
    """Return raw document bytes.

    Local path (POC test data): read from disk.
    SharePoint URL: download via the Graph API using the caller's SSO token.
    """
    if url.startswith("/"):
        with open(url, "rb") as f:
            return f.read()
    from mcp_server_template import sharepoint  # noqa: PLC0415
    return await sharepoint.download_file(document_id)


# ---------------------------------------------------------------------------
# Docling subprocess worker
# Runs in a spawned process to avoid gRPC fork conflicts on macOS.
# Module-level functions are required for pickling by ProcessPoolExecutor.
# ---------------------------------------------------------------------------

_docling_converter = None  # lives only in the worker process


def _init_docling_worker():
    """Initialiser — runs once per worker process when the pool starts."""
    global _docling_converter
    from docling.document_converter import DocumentConverter  # noqa: PLC0415
    _docling_converter = DocumentConverter()


def _docling_worker(doc_bytes: bytes, filename: str) -> str:
    """Convert document bytes to markdown. Runs in the spawned worker process."""
    suffix = os.path.splitext(filename)[-1] or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(doc_bytes)
        tmp_path = f.name
    try:
        return convert_pdf(tmp_path, _docling_converter)
    finally:
        os.unlink(tmp_path)


def _ask_llm(markdown: str, question: str, client, deployment: str, max_tokens: int) -> str:
    """Send document markdown + question to the LLM and return the answer."""
    # gpt-4.1-nano has a 1M token context window; 300k chars (~75k tokens) is
    # a safe practical limit that leaves headroom for the prompt and output.
    MAX_CHARS = 300_000
    if len(markdown) > MAX_CHARS:
        logger.warning("Document truncated from %d to %d chars for LLM", len(markdown), MAX_CHARS)
        markdown = markdown[:MAX_CHARS]

    resp = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful policy assistant for Tricentis employees. "
                    "Answer the question using only the document provided. "
                    "Be specific and concise. Cite specific values, dates, or section names "
                    "when they are relevant to the answer. "
                    "If the document does not contain the answer, say so clearly."
                ),
            },
            {
                "role": "user",
                "content": f"Document:\n\n{markdown}\n\nQuestion: {question}",
            },
        ],
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

def run_sse_server(server: Server, host: str = "0.0.0.0", port: int = 8000):
    sse = SseServerTransport("/messages/")

    # Initialise once at startup
    db_path = os.environ.get("MILVUS_DB_PATH", "")
    collection = os.environ.get("MILVUS_COLLECTION", "hr")
    embedding_fn = _make_embedding_fn()
    milvus_client = MilvusClient(db_path) if db_path else None

    # Spawn a dedicated worker process for Docling so it never forks while
    # Milvus Lite's gRPC threads are active (fork + gRPC = crash on macOS).
    logger.info("Starting Docling worker process...")
    docling_pool = ProcessPoolExecutor(
        max_workers=1,
        mp_context=mp.get_context("spawn"),
        initializer=_init_docling_worker,
    )
    # Eagerly warm up the worker so the first request isn't slow.
    docling_pool.submit(lambda: None)
    logger.info("Docling worker started.")

    from openai import AzureOpenAI  # noqa: PLC0415
    chat_client = AzureOpenAI(
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_CHAT_API_VERSION", "2024-12-01-preview"),
    )
    chat_deployment = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"]
    chat_max_tokens = int(os.environ.get("AZURE_OPENAI_CHAT_MAX_TOKENS", "1000"))

    async def handle_sse(request: Request):
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
        user_token = auth._user_token_var.get(None)

        # 1. Embed and search Milvus
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

        # 2. Try each candidate: access check → fetch → Docling → LLM
        for candidate in merged:
            url = candidate["entity"].get("sharepoint_url", "")
            document_id = candidate["entity"].get("document_id", "")
            subject = candidate["entity"].get("subject", "")

            if not _check_access(url, user_token):
                logger.info("access denied for document '%s', trying next", subject)
                continue

            try:
                doc_bytes = await _fetch_document(url, document_id)
            except PermissionError:
                logger.info("permission denied fetching '%s', trying next", subject)
                continue
            except Exception as e:
                logger.warning("failed to fetch '%s': %s", subject, e)
                continue

            try:
                loop = asyncio.get_running_loop()
                markdown = await loop.run_in_executor(
                    docling_pool, _docling_worker, doc_bytes, url
                )
            except Exception as e:
                logger.warning("Docling failed for '%s': %s", subject, e)
                continue

            logger.info(
                "answering from '%s' (dist=%.4f, %d markdown chars)",
                subject, candidate["distance"], len(markdown),
            )

            answer = await asyncio.to_thread(
                _ask_llm, markdown, question, chat_client, chat_deployment, chat_max_tokens
            )

            return JSONResponse({
                "answer": answer,
                "source": {"name": subject, "url": url} if url else None,
            })

        return JSONResponse({
            "answer": "No accessible policy document was found for your question.",
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
