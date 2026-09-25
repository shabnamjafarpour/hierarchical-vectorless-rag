# Hierarchical Vectorless RAG

A domain-agnostic Retrieval-Augmented Generation system that
preprocesses PDFs into a hierarchical semantic representation and
retrieves relevant document nodes **without query embeddings or a vector
database**.

The project explores a simple question:

> **Can document structure itself serve as a practical retrieval
> index?**

Instead of splitting a document into fixed chunks and relying on vector
similarity at query time, this system discovers document structure,
extracts semantic units, organizes them into a persistent tree, and
performs lightweight local retrieval over that representation.

## Key Results

The final system was evaluated on a 20-question benchmark over a 59-page
Persian document.

  Metric                                    Result
  --------------------------- --------------------
  Retrieval Hit@5               **94.12% (16/17)**
  Answer Correctness            **94.74% (18/19)**
  Unanswerable Accuracy             **100% (3/3)**
  Mean Retrieval Latency             **145.67 ms**
  Median Retrieval Latency           **153.43 ms**
  Mean Generation Latency               **8.08 s**
  Median Generation Latency             **7.86 s**
  Mean End-to-End Latency               **8.23 s**
  Median End-to-End Latency             **8.02 s**

The primary retrieval score excludes document-level questions that do
not have node-level retrieval ground truth and one ambiguous benchmark
item with multiple valid answers.

## Why Vectorless?

A conventional RAG pipeline commonly follows this pattern:

``` text
Document
   ↓
Chunking
   ↓
Embedding Model
   ↓
Vector Database
   ↓
Query Embedding
   ↓
Similarity Search
   ↓
LLM
```

This project takes a different approach:

``` text
Document
   ↓
Semantic + Structural Preprocessing
   ↓
Hierarchical Document Tree
   ↓
Local Vectorless Retrieval
   ↓
Top-K Semantic Nodes
   ↓
LLM
```

At query time, the retriever does **not** require:

-   a query embedding
-   cosine similarity
-   a vector database
-   an LLM call for retrieval

The trade-off is that more computation is moved into offline
preprocessing, while query-time retrieval remains lightweight and
interpretable.

## Architecture

``` mermaid
flowchart TD
    A[PDF] --> B[Document Loader]
    B --> C[Structure Discovery]
    C --> D[Semantic Unit Extraction]
    D --> E[Node Consolidation]
    E --> F[Hierarchical Tree Construction]
    F --> G[Node Summarization]
    G --> H[Persistent Document Cache]

    Q[User Query] --> R[Persian-Aware Query Processing]
    H --> R
    R --> S[Vectorless Node Scoring]
    S --> T[Top-K Relevant Nodes]
    T --> U[Grounded Answer Generation]
    U --> V[Answer]
```

The system is divided into two major stages.

### Offline preprocessing

A new PDF is transformed into a reusable hierarchical representation:

1.  Load the PDF page by page.
2.  Discover the document's structural schema in batches.
3.  Merge partial structure descriptions into a global structure.
4.  Extract semantically meaningful units using overlapping page
    windows.
5.  Consolidate duplicate or overlapping semantic nodes.
6.  Build a hierarchy from the discovered structure.
7.  Generate retrieval-oriented summaries for tree nodes.
8.  Persist the processed document for reuse.

This preprocessing cost is paid once per unique document.

### Online question answering

Once a document has been processed:

1.  Normalize and classify the query.
2.  Load retrievable semantic nodes from the persisted tree.
3.  Score nodes locally.
4.  Rank the candidates.
5.  Select the Top-K relevant nodes.
6.  Build grounded context from those nodes.
7.  Ask the configured language model to answer using only that context.

## Persistent Document Cache

Documents are identified using a SHA-256 hash of their contents.

``` text
PDF
 ↓
SHA-256
 ↓
Document ID
 ↓
Already processed?
 ├── Yes → Load persisted representation
 └── No  → Run preprocessing → Save → Reuse later
```

Processed artifacts are stored under:

``` text
storage/documents/<document_id>/
├── metadata.json
├── structure.json
├── semantic_nodes.json
└── tree.json
```

This avoids paying the expensive preprocessing cost every time the same
document is uploaded.

## Retrieval Strategy

The final retriever is intentionally local and vectorless.

For ordinary specific queries, semantic nodes are ranked using multiple
signals rather than a single raw keyword count.

### Persian-aware normalization

The retriever normalizes common Persian and Arabic orthographic
variations, including:

-   Arabic/Persian character variants such as `ي` / `ی` and `ك` / `ک`
-   Persian, Arabic, and ASCII digit forms
-   diacritics and tatweel
-   zero-width and join-control characters
-   punctuation and spacing differences

A compact representation is also used so forms such as:

``` text
برنامه نویسی
برنامه‌نویسی
برنامهنویسی
```

can still be compared effectively.

### Weighted node fields

Each semantic node exposes several searchable fields:

``` text
title
metadata
hierarchical path
summary
content
```

These fields do not contribute equally. Titles and metadata receive
stronger weights than broad content because they are usually more
discriminative for entity-level questions.

### Corpus-local IDF

The retriever calculates local inverse document frequency over the
current document representation. Rare terms therefore contribute more to
the relevance score than generic terms that appear across many nodes.

### Character n-gram similarity

Compact character trigrams provide additional robustness to Persian
spacing and orthographic variation.

### Top-K retrieval

For specific questions, candidates are ranked deterministically and the
highest-scoring nodes are returned to the answer generator. The
evaluation uses **Top-K = 5**.

The retriever also recognizes two special query classes:

-   **Document-level queries** use document-level context rather than
    ordinary node ranking.
-   **Complete-list queries** retrieve the full relevant collection and
    use deterministic list generation to avoid accidental omissions by
    the LLM.

## Grounded Answer Generation

The generation layer receives only the retrieved document context and is
instructed to:

-   use only information supported by that context
-   avoid external knowledge
-   avoid inventing unsupported facts
-   answer in the same language as the user
-   handle natural Persian spelling and spacing variations

Complete-list queries can bypass LLM generation and produce a
deterministic answer directly from retrieved nodes.

This is particularly useful when completeness matters more than
free-form generation.

## Evaluation

The evaluation suite contains 20 manually designed questions covering
several behaviors:

  Category         Purpose
  ---------------- -----------------------------------------
  Factual          Exact entity and metadata lookup
  Semantic         Retrieval based on descriptive meaning
  Filter           Constraint-based retrieval
  Comparison       Retrieval of multiple relevant entities
  Document-level   Questions about the document as a whole
  Unanswerable     Hallucination-resistance checks

The evaluation records:

``` text
expected identifiers
retrieved identifiers
Hit@5
retrieval latency
generation latency
end-to-end latency
generated answer
```

Answer correctness is manually reviewed rather than calculated with
exact string matching because a correct generated answer does not need
to reproduce the reference wording verbatim.

### Benchmark accounting

The benchmark contains 20 total questions.

-   Two document-level questions have no node-level expected identifier
    and therefore do not participate in Hit@5.
-   One filter question was excluded from the primary aggregated
    benchmark because its original ground truth specified one identifier
    even though multiple document entries legitimately satisfied the
    query.
-   The remaining 17 unambiguous retrieval questions form the primary
    Hit@5 benchmark.

This produces:

``` text
Retrieval Hit@5 = 16 / 17 = 94.12%
```

The excluded item is retained in the evaluation data for transparency.

## Failure Analysis

The benchmark intentionally preserves a genuine retrieval failure.

One semantic question asks about the influence of emotions and past
experiences on human decision-making. The expected semantic node does
not appear in the Top-5 results.

This illustrates an important limitation of the current architecture:
local lexical and character-level similarity can perform well when the
query shares meaningful surface signals with the document, but it can
miss deeper semantic relationships when query wording and document
wording diverge substantially.

This failure is not patched with query-specific synonyms or hard-coded
benchmark rules.

## Trade-offs

### Advantages

-   No vector database is required.
-   No query-time embedding model is required.
-   Retrieval is local and deterministic.
-   Retrieval decisions are easier to inspect.
-   Document hierarchy and semantic units are preserved.
-   Processed documents can be persisted and reused.
-   Persian orthographic variation is handled explicitly.
-   Unsupported questions can be answered conservatively from grounded
    context.

### Limitations

-   Offline preprocessing is significantly heavier than fixed-size
    chunking.
-   Preprocessing currently relies on an LLM for structure discovery,
    semantic extraction, consolidation, and summarization.
-   The lexical retriever is weaker when semantic similarity exists
    without sufficient lexical overlap.
-   Large document collections would require additional indexing and
    scaling strategies.
-   Current evaluation is a small project benchmark, not a
    general-purpose RAG benchmark.
-   The current results should not be interpreted as evidence that
    vectorless retrieval universally outperforms embedding-based RAG.

## Project Structure

``` text
hierarchical-vectorless-rag/
├── app.py
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
│
├── src/
│   ├── config.py
│   ├── pipeline.py
│   ├── document_manager.py
│   ├── ui.py
│   │
│   ├── preprocessing/
│   │   ├── document_loader.py
│   │   ├── structure_extractor.py
│   │   ├── semantic_extractor.py
│   │   └── tree_builder.py
│   │
│   ├── retrieval/
│   │   └── tree_retriever.py
│   │
│   ├── generation/
│   │   └── answer_generator.py
│   │
│   └── utils/
│       ├── json_utils.py
│       └── llm_utils.py
│
├── evaluation/
│   ├── evaluation_dataset.json
│   ├── evaluation_results.json
│   ├── evaluate.py
│   └── metrics.py
│
├── storage/
└── tests/
```

## Tech Stack

-   Python 3.12+
-   LangChain
-   Gradio
-   PyPDF
-   OpenAI-compatible chat model interface
-   `uv` for dependency and environment management

The current configuration uses an OpenAI-compatible provider endpoint
with `claude-sonnet-4-6`. The retrieval architecture itself is
provider-agnostic.

## Installation

Clone the repository and enter the project directory:

``` bash
git clone <your-repository-url>
cd hierarchical-vectorless-rag
```

Install dependencies with `uv`:

``` bash
uv sync
```

Create a local environment file from the example:

``` bash
cp .env.example .env
```

On Windows PowerShell:

``` powershell
Copy-Item .env.example .env
```

Add your API key to `.env`:

``` env
VYCE_API_KEY=your_api_key_here
```

Never commit the real `.env` file.

## Run the Application

Start the Gradio interface:

``` bash
uv run python app.py
```

Then:

1.  Upload a PDF.
2.  Select **Process Document**.
3.  Wait for preprocessing or cached-document loading.
4.  Ask questions about the document.

The chat UI supports Persian right-to-left answers while keeping code
content left-to-right.

## Run the Evaluation

Run the benchmark from the project root:

``` bash
uv run python -m evaluation.evaluate
```

Results are persisted to:

``` text
evaluation/evaluation_results.json
```

Calculate the final aggregate metrics with:

``` bash
uv run python -m evaluation.metrics
```

## Demo

The application includes a Gradio interface designed for a simple
end-to-end demonstration:

``` text
Upload PDF
   ↓
Process / Load Cache
   ↓
Ask Question
   ↓
Vectorless Retrieval
   ↓
Grounded Answer
```

A short demo can showcase three complementary behaviors:

1.  exact factual retrieval
2.  semantic retrieval
3.  refusal to invent information that is absent from the document

> Add the final demo video or GIF here after recording.

## Design Decisions

### Why semantic units instead of fixed-size chunks?

Fixed-size chunking is simple and inexpensive, but it can separate
content according to token boundaries rather than meaning. This project
deliberately moves more computation into offline preprocessing to
construct semantically meaningful retrieval units while preserving
document hierarchy.

### Why cache processed documents?

The preprocessing pipeline is intentionally expensive. Content-addressed
persistence means that cost is paid once for each unique document while
later sessions can reuse the saved representation.

### Why not use an LLM for query-time tree traversal?

An earlier retrieval design used LLM-guided hierarchical traversal. It
was substantially slower at query time. The final implementation
therefore keeps the semantic hierarchy created during preprocessing but
performs retrieval locally using deterministic scoring.

### Why preserve failure cases?

The goal of the evaluation is to characterize the system rather than
optimize against a tiny benchmark. Genuine retrieval failures are kept
visible so the limitations of the approach remain measurable.

## Future Work

Potential extensions include:

-   benchmarking against an embedding-based vector RAG baseline on the
    exact same dataset
-   measuring Hit@1, Hit@3, MRR, and Recall@K
-   hybrid lexical + semantic retrieval
-   lightweight reranking
-   improved multilingual normalization
-   scalable indexing for larger document collections
-   automated regression tests for retrieval behavior

These are intentionally left outside the current implementation so the
repository remains focused on the core hierarchical vectorless retrieval
experiment.

## Status

The current version includes:

-   hierarchical semantic preprocessing
-   SHA-256 document caching
-   persistent processed-document storage
-   Persian-aware vectorless retrieval
-   Top-5 node ranking
-   grounded answer generation
-   deterministic complete-list handling
-   unanswerable-question handling
-   Gradio demo UI
-   a reproducible evaluation dataset
-   benchmark metrics and latency reporting

------------------------------------------------------------------------

**Hierarchical Vectorless RAG** is a portfolio-oriented exploration of
structure-aware retrieval: moving semantic organization into
preprocessing and keeping query-time retrieval lightweight, local, and
interpretable.
