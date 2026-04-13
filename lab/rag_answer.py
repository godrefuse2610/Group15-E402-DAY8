"""
rag_answer.py — Sprint 2 + Sprint 3: Retrieval & Grounded Answer
================================================================
Sprint 2 (60 phút): Baseline RAG
  - Dense retrieval từ ChromaDB
  - Grounded answer function với prompt ép citation
  - Trả lời được ít nhất 3 câu hỏi mẫu, output có source

Sprint 3 (60 phút): Tuning tối thiểu
  - Thêm hybrid retrieval (dense + sparse/BM25)
  - Hoặc thêm rerank (cross-encoder)
  - Hoặc thử query transformation (expansion, decomposition, HyDE)
  - Tạo bảng so sánh baseline vs variant

Definition of Done Sprint 2:
  ✓ rag_answer("SLA ticket P1?") trả về câu trả lời có citation
  ✓ rag_answer("Câu hỏi không có trong docs") trả về "Không đủ dữ liệu"

Definition of Done Sprint 3:
  ✓ Có ít nhất 1 variant (hybrid / rerank / query transform) chạy được
  ✓ Giải thích được tại sao chọn biến đó để tune
"""

import os
import json
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Lazy-initialized singletons — avoid connecting at import time
_openai_client = None
_chroma_collection = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _openai_client


def _get_collection():
    """Return (and cache) the ChromaDB collection built by index.py."""
    global _chroma_collection
    if _chroma_collection is None:
        import chromadb
        from index import CHROMA_DB_DIR
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        _chroma_collection = client.get_collection("rag_lab")
    return _chroma_collection


def _get_embedding(text: str) -> List[float]:
    """Embed text using the same model as index.py (text-embedding-3-small)."""
    client = _get_openai_client()
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small",
    )
    return response.data[0].embedding

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Dense retrieval: tìm kiếm theo embedding similarity trong ChromaDB.

    Args:
        query: Câu hỏi của người dùng
        top_k: Số chunk tối đa trả về

    Returns:
        List các dict, mỗi dict là một chunk với:
          - "text": nội dung chunk
          - "metadata": metadata (source, section, effective_date, ...)
          - "score": cosine similarity score

    TODO Sprint 2:
    1. Embed query bằng cùng model đã dùng khi index (xem index.py)
    2. Query ChromaDB với embedding đó
    3. Trả về kết quả kèm score

    Gợi ý:
        import chromadb
        from index import get_embedding, CHROMA_DB_DIR

        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        collection = client.get_collection("rag_lab")

        query_embedding = get_embedding(query)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        # Lưu ý: distances trong ChromaDB cosine = 1 - similarity
        # Score = 1 - distance
    """
    collection = _get_collection()
    query_embedding = _get_embedding(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "metadata": meta,
            "score": 1.0 - dist,   # ChromaDB cosine distance → similarity
        })
    return chunks


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).

    Mạnh ở: exact term, mã lỗi, tên riêng (ví dụ: "ERR-403", "P1", "refund")
    Hay hụt: câu hỏi paraphrase, đồng nghĩa

    TODO Sprint 3 (nếu chọn hybrid):
    1. Cài rank_bm25: pip install rank-bm25
    2. Load tất cả chunks từ ChromaDB (hoặc rebuild từ docs)
    3. Tokenize và tạo BM25Index
    4. Query và trả về top_k kết quả

    Gợi ý:
        from rank_bm25 import BM25Okapi
        corpus = [chunk["text"] for chunk in all_chunks]
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    """
    from rank_bm25 import BM25Okapi

    collection = _get_collection()
    all_results = collection.get(include=["documents", "metadatas"])
    all_docs: List[str] = all_results["documents"]
    all_metas: List[Dict] = all_results["metadatas"]

    tokenized_corpus = [doc.lower().split() for doc in all_docs]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(query.lower().split())

    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    max_score = scores[top_indices[0]] if top_indices and scores[top_indices[0]] > 0 else 1.0

    return [
        {
            "text": all_docs[i],
            "metadata": all_metas[i],
            "score": float(scores[i] / max_score),  # normalize to [0, 1]
        }
        for i in top_indices
    ]


# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: kết hợp dense và sparse bằng Reciprocal Rank Fusion (RRF).

    Mạnh ở: giữ được cả nghĩa (dense) lẫn keyword chính xác (sparse)
    Phù hợp khi: corpus lẫn lộn ngôn ngữ tự nhiên và tên riêng/mã lỗi/điều khoản

    Args:
        dense_weight: Trọng số cho dense score (0-1)
        sparse_weight: Trọng số cho sparse score (0-1)

    TODO Sprint 3 (nếu chọn hybrid):
    1. Chạy retrieve_dense() → dense_results
    2. Chạy retrieve_sparse() → sparse_results
    3. Merge bằng RRF:
       RRF_score(doc) = dense_weight * (1 / (60 + dense_rank)) +
                        sparse_weight * (1 / (60 + sparse_rank))
       60 là hằng số RRF tiêu chuẩn
    4. Sort theo RRF score giảm dần, trả về top_k

    Khi nào dùng hybrid (từ slide):
    - Corpus có cả câu tự nhiên VÀ tên riêng, mã lỗi, điều khoản
    - Query như "Approval Matrix" khi doc đổi tên thành "Access Control SOP"
    """
    dense_results = retrieve_dense(query, top_k=top_k)
    sparse_results = retrieve_sparse(query, top_k=top_k)

    # Reciprocal Rank Fusion: RRF(doc) = Σ weight * 1/(60 + rank)
    rrf: Dict[str, float] = {}
    doc_map: Dict[str, Dict] = {}

    for rank, chunk in enumerate(dense_results):
        key = chunk["text"]
        rrf[key] = rrf.get(key, 0.0) + dense_weight / (60 + rank + 1)
        doc_map[key] = chunk

    for rank, chunk in enumerate(sparse_results):
        key = chunk["text"]
        rrf[key] = rrf.get(key, 0.0) + sparse_weight / (60 + rank + 1)
        doc_map[key] = chunk

    sorted_keys = sorted(rrf, key=lambda k: rrf[k], reverse=True)[:top_k]
    results = []
    for key in sorted_keys:
        chunk = dict(doc_map[key])
        chunk["score"] = rrf[key]
        results.append(chunk)
    return results


# =============================================================================
# RERANK — Sprint 3 VARIANT: Cross-Encoder (ĐÃ CHỌN)
# Cross-encoder chấm lại relevance sau dense search rộng
# =============================================================================

# Cache cross-encoder model — tránh tải lại ~85MB mỗi lần gọi
_cross_encoder_model = None

def _get_cross_encoder():
    """Lazy-initialize và cache CrossEncoder model."""
    global _cross_encoder_model
    if _cross_encoder_model is None:
        from sentence_transformers import CrossEncoder
        # cross-encoder/ms-marco-MiniLM-L-6-v2:
        # - Lightweight (~85MB), chạy CPU được
        # - Trained trên MS-MARCO passage ranking task
        # - Score range: unbounded logits dùng để rank relative
        _cross_encoder_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder_model


def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Sprint 3 — Variant: Rerank candidates bằng Cross-Encoder.

    LÝ DO CHỌN RERANK (A/B justification theo README):
    - Dense search (bi-encoder) embed query và chunk độc lập → nhanh nhưng có noise
    - Cross-encoder đọc cặp (query, chunk) cùng lúc → chấm relevance chính xác hơn
    - Funnel approach: search rộng top-10 → rerank → chỉ top-3 đi vào prompt
    - Phù hợp với corpus chính sách: query hỏi điều khoản cụ thể cần precision cao
    - A/B Rule: CHỈ thay đổi use_rerank=True, giữ nguyên retrieval_mode="dense"

    Funnel logic (từ slide):
      Dense search rộng (top-10) → Cross-Encoder Rerank → Select top-3 vào prompt

    Implementation (Option A — Cross-encoder):
        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        pairs = [[query, chunk_text] for each candidate]
        scores = model.predict(pairs)  # logit scores
        Sort by score DESC → take top_k

    Args:
        query: Câu hỏi gốc
        candidates: Danh sách chunks từ retrieve_dense() (top-10)
        top_k: Số chunks giữ lại sau rerank (mặc định TOP_K_SELECT=3)

    Returns:
        List chunks được rerank, có thêm field "rerank_score" để debug
    """
    if not candidates:
        return []

    # Nếu candidates ít hơn top_k thì không cần rerank
    if len(candidates) <= top_k:
        return candidates

    model = _get_cross_encoder()

    # Tạo pairs [query, chunk_text] cho cross-encoder
    pairs = [[query, chunk["text"]] for chunk in candidates]

    # Predict trả về logit scores (unbounded) — dùng để rank, không cần normalize
    scores = model.predict(pairs)

    # Sort theo cross-encoder score giảm dần
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)

    results = []
    for chunk, score in ranked[:top_k]:
        chunk = dict(chunk)  # copy để không mutate original
        chunk["rerank_score"] = round(float(score), 4)
        results.append(chunk)
    return results


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query để tăng recall.

    Strategies:
      - "expansion": Thêm từ đồng nghĩa, alias, tên cũ
      - "decomposition": Tách query phức tạp thành 2-3 sub-queries
      - "hyde": Sinh câu trả lời giả (hypothetical document) để embed thay query

    TODO Sprint 3 (nếu chọn query transformation):
    Gọi LLM với prompt phù hợp với từng strategy.

    Ví dụ expansion prompt:
        "Given the query: '{query}'
         Generate 2-3 alternative phrasings or related terms in Vietnamese.
         Output as JSON array of strings."

    Ví dụ decomposition:
        "Break down this complex query into 2-3 simpler sub-queries: '{query}'
         Output as JSON array."

    Khi nào dùng:
    - Expansion: query dùng alias/tên cũ (ví dụ: "Approval Matrix" → "Access Control SOP")
    - Decomposition: query hỏi nhiều thứ một lúc
    - HyDE: query mơ hồ, search theo nghĩa không hiệu quả
    """
    client = _get_openai_client()

    if strategy == "hyde":
        # Hypothetical Document Embedding: generate a fake answer, embed that instead
        prompt = (
            f"Write a short passage (2-3 sentences) that would directly answer "
            f"this question: '{query}'\nOutput only the passage text."
        )
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        return [response.choices[0].message.content.strip()]

    if strategy == "decomposition":
        prompt = (
            f"Break down this complex query into 2-3 simpler sub-queries: '{query}'\n"
            "Output as a JSON array of strings only, no explanation."
        )
    else:  # expansion (default)
        prompt = (
            f"Given the query: '{query}'\n"
            "Generate 2-3 alternative phrasings or related terms in the same language as the query.\n"
            "Output as a JSON array of strings only, no explanation."
        )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )
    try:
        alternatives = json.loads(response.choices[0].message.content.strip())
        return [query] + alternatives   # always keep the original
    except (json.JSONDecodeError, TypeError):
        return [query]


# =============================================================================
# GENERATION — GROUNDED ANSWER FUNCTION
# =============================================================================

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Đóng gói danh sách chunks thành context block để đưa vào prompt.

    Format: structured snippets với source, section, score (từ slide).
    Mỗi chunk có số thứ tự [1], [2], ... để model dễ trích dẫn.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")

        # TODO: Tùy chỉnh format nếu muốn (thêm effective_date, department, ...)
        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        if score > 0:
            header += f" | score={score:.2f}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Xây dựng grounded prompt theo 4 quy tắc từ slide:
    1. Evidence-only: Chỉ trả lời từ retrieved context
    2. Abstain: Thiếu context thì nói không đủ dữ liệu
    3. Citation: Gắn source/section khi có thể
    4. Short, clear, stable: Output ngắn, rõ, nhất quán

    TODO Sprint 2:
    Đây là prompt baseline. Trong Sprint 3, bạn có thể:
    - Thêm hướng dẫn về format output (JSON, bullet points)
    - Thêm ngôn ngữ phản hồi (tiếng Việt vs tiếng Anh)
    - Điều chỉnh tone phù hợp với use case (CS helpdesk, IT support)
    """
    prompt = f"""Answer only from the retrieved context below.
If the context is insufficient to answer the question, say you do not know and do not make up information.
Cite the source field (in brackets like [1]) when possible.
Keep your answer short, clear, and factual.
Respond in the same language as the question.

Question: {query}

Context:
{context_block}

Answer:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM để sinh câu trả lời.

    TODO Sprint 2:
    Chọn một trong hai:

    Option A — OpenAI (cần OPENAI_API_KEY):
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,     # temperature=0 để output ổn định, dễ đánh giá
            max_tokens=512,
        )
        return response.choices[0].message.content

    Option B — Google Gemini (cần GOOGLE_API_KEY):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text

    Lưu ý: Dùng temperature=0 hoặc thấp để output ổn định cho evaluation.
    """
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,      # stable output for evaluation
        max_tokens=512,
    )
    return response.choices[0].message.content


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng cross-encoder rerank không
        verbose: In thêm thông tin debug

    Returns:
        Dict với:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "config": cấu hình pipeline đã dùng

    TODO Sprint 2 — Implement pipeline cơ bản:
    1. Chọn retrieval function dựa theo retrieval_mode
    2. Gọi rerank() nếu use_rerank=True
    3. Truncate về top_k_select chunks
    4. Build context block và grounded prompt
    5. Gọi call_llm() để sinh câu trả lời
    6. Trả về kết quả kèm metadata

    TODO Sprint 3 — Thử các variant:
    - Variant A: đổi retrieval_mode="hybrid"
    - Variant B: bật use_rerank=True
    - Variant C: thêm query transformation trước khi retrieve
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
    }

    # --- Bước 1: Retrieve ---
    if retrieval_mode == "dense":
        candidates = retrieve_dense(query, top_k=top_k_search)
    elif retrieval_mode == "sparse":
        candidates = retrieve_sparse(query, top_k=top_k_search)
    elif retrieval_mode == "hybrid":
        candidates = retrieve_hybrid(query, top_k=top_k_search)
    else:
        raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates (mode={retrieval_mode})")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)

    # --- Bước 5: Extract sources ---
    sources = list({
        c["metadata"].get("source", "unknown")
        for c in candidates
    })

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
    }


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT (A/B Comparison)
# A/B Rule: Chỉ đổi MỘT biến mỗi lần
# Baseline: dense, use_rerank=False
# Variant:  dense, use_rerank=True  (Cross-Encoder Rerank)
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh Baseline (Dense) vs Variant (Dense + Rerank) với cùng một query.

    A/B Rule (từ slide và README): Chỉ đổi MỘT biến mỗi lần.
    → Giữ nguyên retrieval_mode="dense", chỉ bật/tắt use_rerank
    → Điều này giúp biết chắc rerank có tác dụng không (loại trừ ảnh hưởng
       của việc đổi retrieval mode)

    Hiển thị:
    - Top chunks được chọn trước/sau rerank (để thấy thứ tự thay đổi)
    - Câu trả lời cuối cùng từ mỗi variant
    - Sources được sử dụng
    """
    print(f"\n{'='*65}")
    print(f"Query: {query}")
    print('='*65)

    configs = [
        {
            "label":    "Baseline — Dense (no rerank)",
            "mode":     "dense",
            "rerank":   False,
        },
        {
            "label":    "Variant  — Dense + Cross-Encoder Rerank",
            "mode":     "dense",
            "rerank":   True,
        },
    ]

    for cfg in configs:
        print(f"\n[{cfg['label']}]")
        try:
            result = rag_answer(
                query,
                retrieval_mode=cfg["mode"],
                use_rerank=cfg["rerank"],
                verbose=False,
            )
            # Hiển thị chunks đã dùng kèm score
            print(f"  Chunks used ({len(result['chunks_used'])}/{TOP_K_SELECT}):")
            for i, c in enumerate(result["chunks_used"]):
                score_key = "rerank_score" if "rerank_score" in c else "score"
                score_val = c.get(score_key, 0)
                print(f"    [{i+1}] {score_key}={score_val:.4f} | "
                      f"{c['metadata'].get('source','?')} | "
                      f"{c['metadata'].get('section','')[:35]}")
            print(f"  Answer:  {result['answer']}")
            print(f"  Sources: {result['sources']}")
        except Exception as e:
            print(f"  Lỗi: {e}")


# =============================================================================
# MAIN — Sprint 2 Demo + Sprint 3 A/B Comparison
# =============================================================================

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("=" * 65)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 65)

    # -----------------------------------------------------------------------
    # Sprint 2: Baseline Dense Retrieval
    # -----------------------------------------------------------------------
    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",  # abstain test
    ]

    print("\n--- Sprint 2: Baseline Dense (no rerank) ---")
    for query in test_queries:
        print(f"\nQ: {query}")
        result = rag_answer(query, retrieval_mode="dense", use_rerank=False)
        print(f"A: {result['answer']}")
        print(f"Sources: {result['sources']}")

    # -----------------------------------------------------------------------
    # Sprint 3: A/B Comparison — Baseline vs Rerank Variant
    # A/B Rule: chỉ đổi use_rerank, giữ nguyên retrieval_mode
    # -----------------------------------------------------------------------
    print("\n\n" + "="*65)
    print("Sprint 3: A/B Comparison — Dense vs Dense+Rerank")
    print("Variant đã chọn: RERANK (Cross-Encoder ms-marco-MiniLM-L-6-v2)")
    print("Lý do:")
    print("  - Dense top-10 có noise: chunks liên quan chủ đề nhưng không trả lời câu hỏi")
    print("  - Cross-encoder chấm lại (query, chunk) pairs → chính xác hơn bi-encoder")
    print("  - Funnel: top-10 search → rerank → top-3 vào prompt")
    print("  - A/B Rule: CHỈ đổi use_rerank=True, không đổi retrieval_mode")
    print("="*65)

    comparison_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "Khách hàng hoàn tiền trong bao nhiêu ngày?",
    ]

    for q in comparison_queries:
        compare_retrieval_strategies(q)

    print("\n\n✓ Sprint 3 hoàn thành!")
    print("Xem docs/tuning-log.md để biết kết quả A/B comparison đầy đủ.")
