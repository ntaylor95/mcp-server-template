"""
Milvus Lite "hello world" — embed, store, semantic search.

Pipeline this exercises (the core of the eventual policy KB):
    text  ─encode_documents──►  vector  ─insert──►  Milvus collection
    query ─encode_queries───►  vector  ─search──►  top-k nearest neighbors

In the real project, each "document" here will be one *topic* extracted from a
SharePoint policy doc by an LLM splitter; the search results will be fed back
into an LLM to answer the user's question. This script proves the embed →
store → search core works end-to-end with no external services.
"""

from pymilvus import MilvusClient, model

# ---------------------------------------------------------------------------
# 1. Connect to Milvus Lite.
#    Milvus Lite is a file-backed embedded build — no server, no Docker.
#    The "URI" is just a local file path; it will be created if missing.
# ---------------------------------------------------------------------------
DB_PATH = "./milvus_demo.db"
COLLECTION = "policy_topics"

client = MilvusClient(DB_PATH)

# ---------------------------------------------------------------------------
# 2. Build a local embedding function.
#    An *embedding* is a fixed-length vector of floats that represents the
#    meaning of a piece of text. Texts with similar meaning land near each
#    other in this vector space — that's what makes semantic search work.
#    DefaultEmbeddingFunction is whatever small CPU model pymilvus currently
#    bundles (an ONNX-exported transformer, no torch needed). The exact model
#    and dimension change across pymilvus.model versions, so we read the dim
#    off the function itself rather than hard-coding it. Weights download on
#    first use (~80–300MB) and are cached under ~/.cache/huggingface/.
# ---------------------------------------------------------------------------
embedding_fn = model.DefaultEmbeddingFunction()
DIM = embedding_fn.dim  # whatever the bundled default model outputs
print(f"Embedding dimension: {DIM}")

# ---------------------------------------------------------------------------
# 3. (Re)create the collection.
#    Drop-and-recreate makes the script idempotent — every run starts clean,
#    so you can tweak the sample data and re-run without stale state.
#    The collection's `dimension` MUST match the embedding model's output dim,
#    otherwise inserts will fail.
# ---------------------------------------------------------------------------
if client.has_collection(COLLECTION):
    client.drop_collection(COLLECTION)

client.create_collection(
    collection_name=COLLECTION,
    dimension=DIM,
    # Quickstart mode uses L2 distance by default — the field labeled
    # `distance` in search results is a *distance* metric, so LOWER = closer.
)

# ---------------------------------------------------------------------------
# 4. Sample "policy topics" — stand-ins for what the LLM splitter will produce
#    from real SharePoint docs in the eventual KB.
# ---------------------------------------------------------------------------
topics = [
    {
        "subject": "PTO",
        "text": (
            "Full-time employees accrue 15 paid time-off days per year in their "
            "first three years, increasing to 20 days thereafter. Unused days "
            "may roll over up to a 10-day cap."
        ),
    },
    {
        "subject": "Dental Coverage",
        "text": (
            "The standard dental plan covers two preventive cleanings per year "
            "at 100%, basic procedures at 80%, and major procedures at 50% "
            "after the annual deductible."
        ),
    },
    {
        "subject": "401(k) Matching",
        "text": (
            "The company matches 100% of employee retirement contributions up "
            "to 4% of base salary. Matching contributions vest immediately."
        ),
    },
    {
        "subject": "Remote Work Eligibility",
        "text": (
            "Employees in non-customer-facing roles may work remotely up to "
            "three days per week with manager approval. Fully remote "
            "arrangements require VP-level sign-off."
        ),
    },
    {
        "subject": "Expense Reimbursement",
        "text": (
            "Business meals are reimbursable up to $75 per person per day. "
            "Hotel stays must be booked through the approved travel portal "
            "and may not exceed the GSA per-diem rate for the destination."
        ),
    },
    {
        "subject": "Parental Leave",
        "text": (
            "New parents are eligible for 12 weeks of fully paid parental "
            "leave, available to birthing and non-birthing parents alike, to "
            "be used within 12 months of the child's arrival."
        ),
    },
    {
        "subject": "Security Badge Policy",
        "text": (
            "Building access badges must be worn visibly at all times on "
            "company premises. Lost badges must be reported to facilities "
            "within 24 hours; a $25 replacement fee applies."
        ),
    },
    {
        "subject": "Laptop Refresh Cycle",
        "text": (
            "Standard-issue laptops are refreshed every three years. "
            "Engineers and designers may request an off-cycle upgrade once "
            "per cycle with manager approval."
        ),
    },
    {
        "subject": "Holiday Schedule",
        "text": (
            "The company observes 11 paid holidays per year, including two "
            "floating holidays employees may use at their discretion."
        ),
    },
    {
        "subject": "Tuition Reimbursement",
        "text": (
            "Employees may receive up to $5,250 per calendar year in tuition "
            "reimbursement for accredited coursework related to their role, "
            "subject to manager and HR pre-approval."
        ),
    },
]

# ---------------------------------------------------------------------------
# 5. Embed and insert.
#    encode_documents() is used for the *corpus* side. Some embedding models
#    (notably asymmetric ones like e5 or BGE) prepend different instructions
#    to documents vs. queries; even when symmetric, keeping the two calls
#    separate is the conventional API so your code stays portable across
#    models. Each row gets an integer id, the vector, and the original fields.
# ---------------------------------------------------------------------------
doc_texts = [t["text"] for t in topics]
doc_vectors = embedding_fn.encode_documents(doc_texts)

rows = [
    {
        "id": i,
        "vector": doc_vectors[i],
        "text": topics[i]["text"],
        "subject": topics[i]["subject"],
    }
    for i in range(len(topics))
]
client.insert(collection_name=COLLECTION, data=rows)
print(f"Inserted {len(rows)} topics.\n")

# ---------------------------------------------------------------------------
# 6. Semantic search.
#    For each natural-language question we encode the query into the same
#    vector space and ask Milvus for the `limit` (top-k) nearest neighbors.
#    With the quickstart default (L2 distance), the `distance` field is a
#    true distance — LOWER values mean the stored topic is closer in meaning
#    to the question. Top-k decides recall vs. cost: small k is fast and is
#    typically what you'd feed to a downstream LLM.
# ---------------------------------------------------------------------------
questions = [
    "how many vacation days do I get?",
    "does the company match my retirement contributions?",
    "can I work from home?",
]

query_vectors = embedding_fn.encode_queries(questions)

results = client.search(
    collection_name=COLLECTION,
    data=query_vectors,
    limit=3,  # top-k: how many nearest neighbors to return per query
    output_fields=["text", "subject"],
)

for question, hits in zip(questions, results):
    print(f"Q: {question}")
    for rank, hit in enumerate(hits, start=1):
        subject = hit["entity"]["subject"]
        text = hit["entity"]["text"]
        score = hit["distance"]  # L2 distance — LOWER is a closer match
        print(f"  {rank}. [dist={score:.4f}] {subject}")
        print(f"     {text}")
    print()
