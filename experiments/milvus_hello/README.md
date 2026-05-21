# Milvus Lite — Hello World

A self-contained POC that exercises the embed → store → semantic-search core
of the eventual enterprise policy knowledge base. It uses Milvus Lite (a
file-backed embedded build of Milvus — no server, no Docker) and the local
embedding model bundled by `pymilvus.model.DefaultEmbeddingFunction()` (an
ONNX-exported transformer that runs on CPU, no API key, no cost). The exact
model — and therefore the embedding dimension — depends on your installed
`pymilvus.model` version; the script prints the dim at startup so you can
see what you actually got. Nothing here touches the MCP server template; it
lives in `experiments/` and is throwaway exploration code.

> **Python version:** pin to **3.11 or 3.12**. Python 3.14 is too new — pip
> silently downgrades `pymilvus` to an ancient version that doesn't have
> `MilvusClient`, and the ML extras refuse to install.

## Run it

From this directory (`experiments/milvus_hello/`):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python hello_milvus.py
```

The script drops and recreates the collection on each run, so it's safe to
re-run while you tweak the sample data or queries.

**First run is slower** — the embedding model weights (~80MB) download from
Hugging Face and are cached under `~/.cache/huggingface/`. Subsequent runs
start in a few seconds.

## What to notice

- The printed embedding dimension matches the collection's `dimension` arg.
  If those ever disagree, inserts fail — the collection's dim is a hard
  contract with whatever model you use to encode. The current bundled
  default outputs **768** dims; older docs/tutorials mention 384 because
  earlier `pymilvus.model` versions bundled MiniLM-L6-v2.
- The query `"how many vacation days do I get?"` returns the **PTO** topic as
  the top hit even though the word *"vacation"* never appears in the stored
  text. That's the whole point of semantic search vs. keyword search: the
  model maps *vacation* and *paid time off* to nearby points in vector space
  because they mean similar things, not because they share letters.
- The score in each row is **L2 distance** — lower is closer. (Switch the
  collection's metric to `IP` or `COSINE` if you want a similarity-style
  score where higher = closer.)
- `encode_documents()` and `encode_queries()` are kept as separate calls even
  when the underlying model is symmetric — asymmetric models (e5, BGE,
  instruction-tuned ones) prepend different prompts to docs vs. queries, and
  using the right side keeps your code portable across embedding models.

### Warnings you can ignore

- `None of PyTorch, TensorFlow >= 2.0, or Flax have been found.` — `pymilvus.model`
  uses `onnxruntime` directly, so it doesn't need torch. The line is just
  `transformers` grumbling that it can't load `.bin` checkpoints; tokenizer-only
  usage still works.
- Hugging Face "unauthenticated requests" notice — fine for this POC.
