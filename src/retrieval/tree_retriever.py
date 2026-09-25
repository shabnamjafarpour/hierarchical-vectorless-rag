import math
import re
import unicodedata
from collections import Counter


# =========================================================
# Persian-aware text normalization
# =========================================================

_ARABIC_TO_PERSIAN = str.maketrans({
    "ي": "ی", "ى": "ی", "ئ": "ی",
    "ك": "ک",
    "ة": "ه", "ۀ": "ه",
    "ؤ": "و",
})

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_ASCII_DIGITS = "0123456789"
_DIGIT_TRANS = str.maketrans(
    _PERSIAN_DIGITS + _ARABIC_DIGITS,
    _ASCII_DIGITS + _ASCII_DIGITS,
)

# Arabic/Persian combining marks + Quranic marks + tatweel.
_DIACRITICS_RE = re.compile(
    r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]"
)
_NON_WORD_RE = re.compile(r"[^\u0600-\u06FFa-z0-9]+", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[\u0600-\u06FFa-z0-9]+", re.IGNORECASE)

# Deliberately small: aggressive stop-word removal hurts Persian retrieval.
_STOP_WORDS = {
    "چه", "چی", "چیه", "چیست", "کی", "کیه", "کیست", "کدام",
    "را", "رو", "از", "به", "در", "و", "برای", "با",
    "این", "آن", "یک", "است", "هست", "هستند",
    "بگو", "بده", "لطفا", "میشه", "میتونی", "میتوانی",
}


def normalize_text(text: str) -> str:
    """Canonical normalization for Persian/Arabic/English retrieval text."""
    text = unicodedata.normalize("NFKC", str(text or "")).lower()
    text = text.translate(_ARABIC_TO_PERSIAN).translate(_DIGIT_TRANS)
    text = _DIACRITICS_RE.sub("", text)

    # Join-control characters are orthographic variants for retrieval purposes.
    text = re.sub(r"[\u200c\u200d\u200e\u200f\ufeff]", " ", text)
    text = _NON_WORD_RE.sub(" ", text)
    return " ".join(text.split())


def compact_text(text: str) -> str:
    """
    Space-insensitive representation.

    This makes forms such as «برنامه نویسی», «برنامه‌نویسی» and
    «برنامهنویسی» comparable without changing persisted document data.
    """
    return normalize_text(text).replace(" ", "")


def tokenize(text: str) -> set[str]:
    """Return useful normalized lexical tokens."""
    tokens = _TOKEN_RE.findall(normalize_text(text))
    return {t for t in tokens if len(t) > 1 and t not in _STOP_WORDS}


def char_ngrams(text: str, n: int = 3) -> set[str]:
    """Character n-grams over compact text; useful for Persian spacing variants."""
    value = compact_text(text)
    if not value:
        return set()
    if len(value) <= n:
        return {value}
    return {value[i:i + n] for i in range(len(value) - n + 1)}


# =========================================================
# Tree traversal
# =========================================================


def collect_semantic_nodes(node: dict, path: list[str] | None = None) -> list[dict]:
    """Collect retrievable content nodes without mutating the persisted tree."""
    if path is None:
        path = []

    current_path = path + [str(node.get("title", "") or "")]
    semantic_nodes = []

    if node.get("content"):
        semantic_nodes.append({
            "title": node.get("title", ""),
            "type": node.get("type", ""),
            "content": node.get("content", ""),
            "summary": node.get("summary", ""),
            "metadata": node.get("metadata", {}) or {},
            "path": current_path,
        })

    for child in node.get("children", []) or []:
        semantic_nodes.extend(collect_semantic_nodes(child, current_path))

    return semantic_nodes


# =========================================================
# Query classification
# =========================================================

_DOCUMENT_TERMS = (
    "داکیومنت", "سند", "فایل", "پی دی اف", "pdf", "متن", "مدرک",
)

_DOCUMENT_PATTERNS = (
    "درباره چیست", "درباره چیه", "موضوع چیست", "موضوع چیه",
    "محتوای کلی", "خلاصه سند", "خلاصه فایل", "خلاصه داکیومنت",
    "به طور کلی", "بطور کلی",
    "چه نوع اطلاعاتی", "چه اطلاعاتی", "چه داده هایی", "چه داده ای",
    "چه فیلدهایی", "چه فیلد هایی", "ساختار اطلاعات", "ساختار سند",
    "ساختار فایل", "ساختار داکیومنت",
)


def is_document_level_query(query: str) -> bool:
    """
    Detect questions about the document as a whole rather than an entity in it.

    Requiring a document-reference term prevents broad words such as «اطلاعات»
    from turning ordinary entity questions into DOCUMENT queries.
    """
    q = normalize_text(query)
    has_document_reference = any(term in q for term in _DOCUMENT_TERMS)
    if not has_document_reference:
        return False

    if any(pattern in q for pattern in _DOCUMENT_PATTERNS):
        return True

    intent_terms = (
        "درباره", "راجع", "موضوع", "محتوا", "خلاصه", "کلی",
        "اطلاعات", "داده", "فیلد", "ساختار", "شامل",
    )
    return any(term in q for term in intent_terms)


_COMPLETE_LIST_PATTERNS = (
    "لیست کامل", "فهرست کامل", "همه موارد", "تمام موارد", "کل موارد",
    "همه آیتم", "تمام آیتم", "همه را بگو", "همه رو بگو",
    "همه را نام ببر", "همه رو نام ببر", "تمام را نام ببر",
    "لیستشون رو بده", "لیستشون را بده", "فهرستشون رو بده",
    "فهرستشون را بده", "لیست همه", "فهرست همه",
)


def is_complete_list_query(query: str) -> bool:
    """Detect explicit requests for the complete collection, not title words."""
    q = normalize_text(query)
    if any(pattern in q for pattern in _COMPLETE_LIST_PATTERNS):
        return True


    request_verbs = ("بده", "بگو", "نمایش", "نشون", "نشان", "نام ببر")
    return (
        any(word in q.split() for word in ("لیست", "فهرست"))
        and any(verb in q for verb in request_verbs)
    )


# =========================================================
# Lexical scoring
# =========================================================


def _metadata_text(node: dict) -> str:
    """Flatten node metadata into searchable text without changing the persisted representation."""
    metadata = node.get("metadata", {}) or {}
    return " ".join(f"{key} {value}" for key, value in metadata.items())


def _field_texts(node: dict) -> dict[str, str]:
    """Build weighted searchable fields from a semantic node."""
    return {
        "title": str(node.get("title", "") or ""),
        "metadata": _metadata_text(node),
        "path": " ".join(str(x) for x in (node.get("path", []) or [])),
        "summary": str(node.get("summary", "") or ""),
        "content": str(node.get("content", "") or ""),
    }


def _build_idf(nodes: list[dict]) -> dict[str, float]:
    """Corpus-local IDF so rare query terms matter more than generic terms."""
    n_docs = max(len(nodes), 1)
    df = Counter()

    for node in nodes:
        fields = _field_texts(node)
        node_tokens = set()
        for text in fields.values():
            node_tokens.update(tokenize(text))
        df.update(node_tokens)

    return {
        token: math.log((n_docs + 1) / (freq + 1)) + 1.0
        for token, freq in df.items()
    }


def _weighted_overlap(query_tokens: set[str], field_tokens: set[str], idf: dict[str, float]) -> float:
    """Compute IDF-weighted token overlap between query tokens and a document field."""
    return sum(idf.get(token, 1.0) for token in query_tokens & field_tokens)


def _char_similarity(query: str, text: str) -> float:
    """Jaccard similarity of compact character trigrams."""
    q = char_ngrams(query)
    t = char_ngrams(text)
    if not q or not t:
        return 0.0
    return len(q & t) / len(q | t)


def score_node(
    query: str,
    query_tokens: set[str],
    node: dict,
    idf: dict[str, float] | None = None,
) -> float:
    """
    Persian-aware field-weighted lexical score.

    Signals:
    - token overlap with corpus-local IDF
    - compact exact containment for spacing/ZWNJ variants
    - character n-gram similarity for near lexical matches

    It remains fully local and vectorless: no embeddings and no query-time LLM.
    """
    idf = idf or {}
    fields = _field_texts(node)

    weights = {
        "title": 6.0,
        "metadata": 4.0,
        "path": 3.0,
        "summary": 2.0,
        "content": 1.0,
    }

    score = 0.0
    for name, text in fields.items():
        score += weights[name] * _weighted_overlap(
            query_tokens, tokenize(text), idf
        )

    q_compact = compact_text(query)
    title_compact = compact_text(fields["title"])

    # Strong generic signal for exact/near-exact entity titles despite Persian
    # whitespace or ZWNJ inconsistencies. Minimum length avoids tiny matches.
    if title_compact and len(title_compact) >= 4 and title_compact in q_compact:
        score += 18.0
    elif q_compact and len(q_compact) >= 4 and q_compact in title_compact:
        score += 10.0

    # Character similarity is deliberately limited to high-value short fields;
    # applying it to long content would reward generic prose.
    title_sim = _char_similarity(query, fields["title"])
    metadata_sim = _char_similarity(query, fields["metadata"])
    score += 10.0 * title_sim
    score += 2.0 * metadata_sim

    return score


# =========================================================
# Main retrieval
# =========================================================


def _document_context(tree: dict) -> list[dict]:
    """Build one synthetic context node describing the document as a whole."""
    root_summary = str(tree.get("summary", "") or "").strip()
    document_type = str(tree.get("document_type", "") or "").strip()
    semantic_unit = str(tree.get("semantic_unit", "") or "").strip()
    root_title = str(tree.get("title", "") or "").strip()

    if normalize_text(root_title) in {"document", "داکیومنت", "سند"}:
        root_title = ""

    parts = []
    if root_title:
        parts.append(f"Document title: {root_title}")
    if document_type:
        parts.append(f"Document type: {document_type}")
    if semantic_unit:
        parts.append(f"Semantic unit: {semantic_unit}")
    if root_summary:
        parts.append(f"Document summary:\n{root_summary}")

    content = "\n\n".join(parts)
    if not content:
        return []

    return [{
        "title": root_title,
        "type": "document",
        "content": content,
        "summary": root_summary,
        "metadata": {
            "document_type": document_type,
            "semantic_unit": semantic_unit,
        },
        "path": [],
    }]


def retrieve_from_tree(
    tree: dict,
    query: str,
    llm=None,
    top_k: int = 5,
) -> list[dict]:
    """
    Fast hierarchical vectorless retrieval for Persian-heavy documents.

    Modes:
      DOCUMENT      -> root/document summary context
      COMPLETE_LIST -> all semantic nodes
      SPECIFIC      -> Persian-aware lexical Top-K

    `llm` is retained only for backward compatibility. Retrieval itself makes
    no LLM call and uses no embeddings/vector database.
    """
    semantic_nodes = collect_semantic_nodes(tree)
    print(f">>> Total semantic nodes: {len(semantic_nodes)}")

    if not semantic_nodes:
        print(">>> No semantic nodes found.")
        return []

    if is_document_level_query(query):
        print(">>> Retrieval mode: DOCUMENT")
        return _document_context(tree)

    if is_complete_list_query(query):
        print(">>> Retrieval mode: COMPLETE_LIST")
        return semantic_nodes

    print(">>> Retrieval mode: SPECIFIC")
    query_tokens = tokenize(query)
    if not query_tokens:
        print(">>> Query contains no useful tokens.")
        return []

    idf = _build_idf(semantic_nodes)
    scored_nodes = []

    for node in semantic_nodes:
        score = score_node(
            query=query,
            query_tokens=query_tokens,
            node=node,
            idf=idf,
        )
        if score > 0:
            scored_nodes.append((score, node))

    # Stable deterministic tie-breakers improve reproducibility.
    scored_nodes.sort(
        key=lambda item: (
            item[0],
            compact_text(item[1].get("title", "")),
        ),
        reverse=True,
    )

    print(f">>> Matching semantic nodes: {len(scored_nodes)}")
    if not scored_nodes:
        return []

    return [node for _, node in scored_nodes[:top_k]]
