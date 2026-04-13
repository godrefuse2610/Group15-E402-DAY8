"""
index.py — Sprint 1: Build RAG Index
====================================
Mục tiêu Sprint 1 (60 phút):
  - Đọc và preprocess tài liệu từ data/docs/ (định dạng .pdf)
  - Chunk tài liệu theo cấu trúc tự nhiên (heading/section)
  - Gắn metadata: source, section, department, effective_date, access
  - Embed và lưu vào vector store (ChromaDB)

Definition of Done Sprint 1:
  ✓ Script chạy được và index đủ docs
  ✓ Có ít nhất 3 metadata fields hữu ích cho retrieval
  ✓ Có thể kiểm tra chunk bằng list_chunks()
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

DOCS_DIR = Path(__file__).parent / "data" / "docs"
CHROMA_DB_DIR = Path(__file__).parent / "chroma_db"

# Chunk size và overlap (theo token ≈ ký tự / 4)
# Slide gợi ý: chunk 300-500 tokens, overlap 50-80 tokens
CHUNK_SIZE = 400       # tokens (ước lượng bằng số ký tự / 4)
CHUNK_OVERLAP = 80     # tokens overlap giữa các chunk


# =============================================================================
# PDF READER
# Đọc nội dung từ file .pdf bằng pypdf
# =============================================================================

def read_pdf(filepath: Path) -> str:
    """
    Đọc toàn bộ text từ file PDF bằng pypdf.

    Returns:
        str: Nội dung text của toàn bộ file PDF
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(filepath))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        return "\n".join(pages_text)
    except Exception as e:
        print(f"  [WARN] Không đọc được PDF {filepath.name}: {e}")
        return ""


# =============================================================================
# STEP 1: PREPROCESS
# Làm sạch text trước khi chunk và embed
# =============================================================================

def preprocess_document(raw_text: str, filepath: str) -> Dict[str, Any]:
    """
    Preprocess một tài liệu: extract metadata từ header và làm sạch nội dung.

    Args:
        raw_text: Toàn bộ nội dung file text (đã extract từ PDF)
        filepath: Đường dẫn file để làm source mặc định

    Returns:
        Dict chứa:
          - "text": nội dung đã clean
          - "metadata": dict với source, department, effective_date, access

    Logic:
    - Extract metadata từ dòng đầu file (Source, Department, Effective Date, Access)
    - Bỏ các dòng header metadata khỏi nội dung chính
    - Normalize khoảng trắng, xóa ký tự rác
    - Dùng regex để parse dòng "Key: Value" ở đầu file
    """
    lines = raw_text.strip().split("\n")
    metadata = {
        "source": Path(filepath).stem,   # fallback: tên file không có extension
        "section": "",
        "department": "unknown",
        "effective_date": "unknown",
        "access": "internal",
    }
    content_lines = []
    header_done = False

    for line in lines:
        # Bỏ ký tự Unicode đặc biệt từ PDF (BOM, soft-hyphen, v.v.)
        line = line.replace("\ufeff", "").replace("\u00ad", "").strip()

        if not header_done:
            # Parse metadata từ các dòng "Key: Value"
            if re.match(r"^Source\s*:", line, re.IGNORECASE):
                metadata["source"] = re.sub(r"^Source\s*:\s*", "", line, flags=re.IGNORECASE).strip()
            elif re.match(r"^Department\s*:", line, re.IGNORECASE):
                metadata["department"] = re.sub(r"^Department\s*:\s*", "", line, flags=re.IGNORECASE).strip()
            elif re.match(r"^Effective Date\s*:", line, re.IGNORECASE):
                metadata["effective_date"] = re.sub(r"^Effective Date\s*:\s*", "", line, flags=re.IGNORECASE).strip()
            elif re.match(r"^Access\s*:", line, re.IGNORECASE):
                metadata["access"] = re.sub(r"^Access\s*:\s*", "", line, flags=re.IGNORECASE).strip()
            elif re.match(r"^={3,}", line):
                # Gặp section heading đầu tiên → kết thúc header
                header_done = True
                content_lines.append(line)
            elif not line or line.isupper():
                # Dòng tên tài liệu (toàn chữ hoa) hoặc dòng trống trong header
                continue
        else:
            content_lines.append(line)

    cleaned_text = "\n".join(content_lines)

    # Normalize: bỏ dòng trống thừa (max 2 dòng trống liên tiếp)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    # Bỏ khoảng trắng cuối dòng
    cleaned_text = re.sub(r"[ \t]+\n", "\n", cleaned_text)

    return {
        "text": cleaned_text.strip(),
        "metadata": metadata,
    }


# =============================================================================
# STEP 2: CHUNK
# Chia tài liệu thành các đoạn nhỏ theo cấu trúc tự nhiên
# =============================================================================

def chunk_document(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Chunk một tài liệu đã preprocess thành danh sách các chunk nhỏ.

    Args:
        doc: Dict với "text" và "metadata" (output của preprocess_document)

    Returns:
        List các Dict, mỗi dict là một chunk với:
          - "text": nội dung chunk
          - "metadata": metadata gốc + "section" của chunk đó

    Strategy (Retrieval Owner):
    1. Split theo heading "=== Section ... ===" trước
    2. Nếu section quá dài (> CHUNK_SIZE * 4 ký tự), split tiếp theo paragraph
    3. Thêm overlap: lấy đoạn cuối của chunk trước vào đầu chunk tiếp theo
    4. Mỗi chunk PHẢI giữ metadata đầy đủ từ tài liệu gốc
    """
    text = doc["text"]
    base_metadata = doc["metadata"].copy()
    chunks = []

    # Bước 1: Split theo heading pattern "=== ... ==="
    # Pattern này match cả "=== Section Name ===" hoặc "=== Phần X: ... ==="
    sections = re.split(r"(={3,}[^=\n]+={3,})", text)

    current_section = "General"
    current_section_text = ""

    for part in sections:
        if re.match(r"={3,}[^=\n]+={3,}", part):
            # Lưu section trước (nếu có nội dung thực sự)
            if current_section_text.strip():
                section_chunks = _split_by_size(
                    current_section_text.strip(),
                    base_metadata=base_metadata,
                    section=current_section,
                )
                chunks.extend(section_chunks)
            # Bắt đầu section mới: bóc tên section sạch
            current_section = re.sub(r"=+", "", part).strip()
            current_section_text = ""
        else:
            current_section_text += part

    # Lưu section cuối cùng
    if current_section_text.strip():
        section_chunks = _split_by_size(
            current_section_text.strip(),
            base_metadata=base_metadata,
            section=current_section,
        )
        chunks.extend(section_chunks)

    return chunks


def _split_by_size(
    text: str,
    base_metadata: Dict,
    section: str,
    chunk_chars: int = CHUNK_SIZE * 4,
    overlap_chars: int = CHUNK_OVERLAP * 4,
) -> List[Dict[str, Any]]:
    """
    Helper: Split text dài thành chunks theo paragraph với overlap.

    Strategy (Retrieval Owner):
    - Ưu tiên ranh giới tự nhiên: paragraph (\\n\\n), rồi câu (. / ! / ?)
    - Ghép paragraphs cho đến khi gần đủ chunk_chars
    - Lấy overlap từ đoạn cuối chunk trước để đảm bảo context liên tục
    - Không cắt giữa câu hoặc điều khoản
    """
    if len(text) <= chunk_chars:
        return [{
            "text": text,
            "metadata": {**base_metadata, "section": section},
        }]

    # Tách theo paragraph (2+ dòng trống hoặc dòng trống đơn)
    paragraphs = re.split(r"\n\n+", text)
    # Lọc paragraph rỗng
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks = []
    current_chunk_parts = []
    current_len = 0
    overlap_buffer = ""  # Đoạn cuối của chunk trước để overlap

    for para in paragraphs:
        para_len = len(para)

        if current_len + para_len + 1 > chunk_chars and current_chunk_parts:
            # Chunk đã đủ kích thước → xuất ra
            chunk_text = "\n\n".join(current_chunk_parts)
            if overlap_buffer:
                chunk_text = overlap_buffer + "\n\n" + chunk_text
            chunks.append({
                "text": chunk_text.strip(),
                "metadata": {**base_metadata, "section": section},
            })
            # Tính overlap: lấy đoạn cuối (tối đa overlap_chars ký tự)
            overlap_buffer = _get_overlap(current_chunk_parts, overlap_chars)
            current_chunk_parts = []
            current_len = 0

        # Nếu một paragraph đơn lẻ đã vượt chunk_chars, cắt theo câu
        if para_len > chunk_chars:
            sentence_chunks = _split_by_sentence(para, chunk_chars, overlap_chars)
            for sc in sentence_chunks:
                chunks.append({
                    "text": sc.strip(),
                    "metadata": {**base_metadata, "section": section},
                })
            overlap_buffer = _get_overlap([sentence_chunks[-1]], overlap_chars) if sentence_chunks else ""
        else:
            current_chunk_parts.append(para)
            current_len += para_len + 2  # +2 cho "\n\n"

    # Xử lý phần còn lại
    if current_chunk_parts:
        chunk_text = "\n\n".join(current_chunk_parts)
        if overlap_buffer and len(overlap_buffer) < overlap_chars:
            chunk_text = overlap_buffer + "\n\n" + chunk_text
        chunks.append({
            "text": chunk_text.strip(),
            "metadata": {**base_metadata, "section": section},
        })

    return chunks if chunks else [{
        "text": text[:chunk_chars].strip(),
        "metadata": {**base_metadata, "section": section},
    }]


def _get_overlap(parts: List[str], overlap_chars: int) -> str:
    """Lấy đoạn cuối của danh sách parts không vượt quá overlap_chars ký tự."""
    if not parts:
        return ""
    last = parts[-1]
    if len(last) <= overlap_chars:
        return last
    # Cắt từ đầu câu gần nhất với vị trí (len - overlap_chars)
    start = len(last) - overlap_chars
    # Tìm điểm bắt đầu câu gần nhất
    match = re.search(r"[.!?]\s+", last[start:])
    if match:
        return last[start + match.end():]
    return last[start:]


def _split_by_sentence(text: str, chunk_chars: int, overlap_chars: int) -> List[str]:
    """Fallback: cắt paragraph dài theo câu."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 > chunk_chars and current:
            chunks.append(current.strip())
            # Overlap: giữ lại câu cuối
            overlap = current.split(". ")[-1] if ". " in current else ""
            current = overlap + " " + sent if overlap else sent
        else:
            current = current + " " + sent if current else sent
    if current.strip():
        chunks.append(current.strip())
    return chunks


# =============================================================================
# STEP 3: EMBED + STORE
# Embed các chunk và lưu vào ChromaDB
# =============================================================================

# Cache OpenAI client để tránh khởi tạo nhiều lần
_openai_client = None

def _get_openai_client():
    """Lazy-initialize OpenAI client."""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY chưa được set trong .env")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def get_embedding(text: str) -> List[float]:
    """
    Tạo embedding vector cho một đoạn text.

    Sử dụng OpenAI text-embedding-3-small (Option A từ TODO comment gốc).
    Model này hỗ trợ tiếng Việt tốt, 1536 dimensions, cost-effective.

    Lý do chọn OpenAI thay vì Sentence Transformers:
    - Cùng provider với LLM (OpenAI) → nhất quán về tokenization
    - text-embedding-3-small có chất lượng cao cho multilingual
    - Không cần tải model local (~500MB)
    """
    client = _get_openai_client()
    # Truncate text nếu quá dài (giới hạn 8192 tokens của API)
    text = text[:8000]
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


def build_index(docs_dir: Path = DOCS_DIR, db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Pipeline hoàn chỉnh: đọc PDF docs → preprocess → chunk → embed → store vào ChromaDB.

    Flow:
    1. Khởi tạo ChromaDB PersistentClient
    2. Get-or-create collection "rag_lab" với cosine similarity
    3. Với mỗi .pdf trong docs_dir:
       a. Đọc PDF bằng pypdf
       b. Preprocess (extract metadata, clean text)
       c. Chunk theo section + paragraph với overlap
       d. Embed từng chunk với OpenAI
       e. Upsert vào ChromaDB với đầy đủ metadata
    4. In thống kê

    Metadata mỗi chunk (≥ 3 fields theo DoD):
      - source: tên tài liệu gốc (ví dụ: "policy/refund-v4.pdf")
      - section: tên section trong tài liệu
      - department: phòng ban sở hữu tài liệu
      - effective_date: ngày hiệu lực
      - access: mức độ truy cập (internal/public/confidential)
    """
    import chromadb
    from tqdm import tqdm

    print(f"Đang build index từ: {docs_dir}")
    db_dir.mkdir(parents=True, exist_ok=True)

    # Khởi tạo ChromaDB với cosine similarity space
    client = chromadb.PersistentClient(path=str(db_dir))
    collection = client.get_or_create_collection(
        name="rag_lab",
        metadata={"hnsw:space": "cosine"}
    )

    # Xóa collection cũ nếu muốn rebuild sạch (upsert sẽ update nếu id đã tồn tại)
    print(f"Collection 'rag_lab' hiện có: {collection.count()} chunks")

    total_chunks = 0
    # Xử lý tất cả file .pdf trong docs_dir
    doc_files = sorted(docs_dir.glob("*.pdf"))

    if not doc_files:
        print(f"Không tìm thấy file .pdf trong {docs_dir}")
        return

    print(f"Tìm thấy {len(doc_files)} file PDF\n")

    for filepath in doc_files:
        print(f"Processing: {filepath.name}")

        # Bước a: Đọc PDF
        raw_text = read_pdf(filepath)
        if not raw_text.strip():
            print(f"  [WARN] File rỗng hoặc không đọc được: {filepath.name}")
            continue

        # Bước b: Preprocess
        doc = preprocess_document(raw_text, str(filepath))
        print(f"  Metadata: source={doc['metadata']['source']}, "
              f"department={doc['metadata']['department']}, "
              f"effective_date={doc['metadata']['effective_date']}")

        # Bước c: Chunk
        chunks = chunk_document(doc)
        print(f"  Chunks: {len(chunks)}")

        # Bước d + e: Embed và upsert vào ChromaDB
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(tqdm(chunks, desc=f"  Embedding {filepath.stem}", leave=False)):
            chunk_id = f"{filepath.stem}_{i:04d}"
            embedding = get_embedding(chunk["text"])

            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk["text"])
            metadatas.append(chunk["metadata"])

        # Upsert theo batch cho hiệu quả
        BATCH_SIZE = 50
        for batch_start in range(0, len(ids), BATCH_SIZE):
            batch_end = batch_start + BATCH_SIZE
            collection.upsert(
                ids=ids[batch_start:batch_end],
                embeddings=embeddings[batch_start:batch_end],
                documents=documents[batch_start:batch_end],
                metadatas=metadatas[batch_start:batch_end],
            )

        total_chunks += len(chunks)
        print(f"  ✓ Indexed {len(chunks)} chunks từ {filepath.name}\n")

    print(f"{'='*50}")
    print(f"Hoàn thành! Tổng chunks đã index: {total_chunks}")
    print(f"ChromaDB stored tại: {db_dir}")
    print(f"Collection count: {collection.count()}")


# =============================================================================
# STEP 4: INSPECT / KIỂM TRA
# Dùng để debug và kiểm tra chất lượng index
# =============================================================================

def list_chunks(db_dir: Path = CHROMA_DB_DIR, n: int = 5) -> None:
    """
    In ra n chunk đầu tiên trong ChromaDB để kiểm tra chất lượng index.

    Kiểm tra:
    - Chunk có giữ đủ metadata không? (source, section, effective_date)
    - Chunk có bị cắt giữa điều khoản không?
    - Metadata effective_date có đúng không?
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(limit=n, include=["documents", "metadatas"])

        print(f"\n=== Top {n} chunks trong index ===\n")
        print(f"Tổng chunks trong collection: {collection.count()}\n")
        for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"])):
            print(f"[Chunk {i+1}]")
            print(f"  Source:         {meta.get('source', 'N/A')}")
            print(f"  Section:        {meta.get('section', 'N/A')}")
            print(f"  Department:     {meta.get('department', 'N/A')}")
            print(f"  Effective Date: {meta.get('effective_date', 'N/A')}")
            print(f"  Access:         {meta.get('access', 'N/A')}")
            print(f"  Text length:    {len(doc)} chars")
            print(f"  Text preview:   {doc[:150].replace(chr(10), ' ')}...")
            print()
    except Exception as e:
        print(f"Lỗi khi đọc index: {e}")
        print("Hãy chạy build_index() trước.")


def inspect_metadata_coverage(db_dir: Path = CHROMA_DB_DIR) -> None:
    """
    Kiểm tra phân phối metadata trong toàn bộ index.

    Checklist Sprint 1:
    - Mọi chunk đều có source?
    - Có bao nhiêu chunk từ mỗi department?
    - Chunk nào thiếu effective_date?
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(db_dir))
        collection = client.get_collection("rag_lab")
        results = collection.get(include=["metadatas"])

        total = len(results['metadatas'])
        print(f"\n=== Metadata Coverage Report ===\n")
        print(f"Tổng chunks: {total}")

        # Phân tích metadata
        departments = {}
        sources = {}
        access_levels = {}
        missing_date = 0
        missing_source = 0

        for meta in results["metadatas"]:
            dept = meta.get("department", "unknown")
            departments[dept] = departments.get(dept, 0) + 1

            src = meta.get("source", "")
            sources[src] = sources.get(src, 0) + 1
            if not src:
                missing_source += 1

            access = meta.get("access", "unknown")
            access_levels[access] = access_levels.get(access, 0) + 1

            if meta.get("effective_date") in ("unknown", "", None):
                missing_date += 1

        print(f"\nPhân bố theo Department:")
        for dept, count in sorted(departments.items()):
            print(f"  {dept}: {count} chunks")

        print(f"\nPhân bố theo Source:")
        for src, count in sorted(sources.items()):
            print(f"  {src}: {count} chunks")

        print(f"\nPhân bố theo Access Level:")
        for access, count in sorted(access_levels.items()):
            print(f"  {access}: {count} chunks")

        print(f"\nChất lượng metadata:")
        print(f"  Chunks thiếu source:         {missing_source}/{total}")
        print(f"  Chunks thiếu effective_date: {missing_date}/{total}")

    except Exception as e:
        print(f"Lỗi: {e}. Hãy chạy build_index() trước.")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 1: Build RAG Index")
    print("=" * 60)

    # Bước 1: Kiểm tra docs
    doc_files = sorted(DOCS_DIR.glob("*.pdf"))
    print(f"\nTìm thấy {len(doc_files)} tài liệu PDF:")
    for f in doc_files:
        print(f"  - {f.name} ({f.stat().st_size // 1024} KB)")

    if not doc_files:
        print(f"\n[ERROR] Không tìm thấy file .pdf trong {DOCS_DIR}")
        exit(1)

    # Bước 2: Test preprocess và chunking (không cần API key)
    print("\n--- Test preprocess + chunking (không cần API key) ---")
    for filepath in doc_files[:1]:  # Test với 1 file đầu
        raw = read_pdf(filepath)
        doc = preprocess_document(raw, str(filepath))
        chunks = chunk_document(doc)
        print(f"\nFile: {filepath.name}")
        print(f"  Metadata: {doc['metadata']}")
        print(f"  Số chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n  [Chunk {i+1}] Section: {chunk['metadata']['section']}")
            print(f"  Chars: {len(chunk['text'])}")
            print(f"  Text: {chunk['text'][:200].replace(chr(10), ' ')}...")

    # Bước 3: Build index (yêu cầu OPENAI_API_KEY)
    print("\n--- Build Full Index ---")
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_key or openai_key == "...":
        print("[SKIP] OPENAI_API_KEY chưa được set. Set key trong .env để build index.")
        print("Việc cần làm:")
        print("  1. Set OPENAI_API_KEY trong .env")
        print("  2. Chạy lại: python index.py")
    else:
        build_index()

        # Bước 4: Kiểm tra index
        print("\n--- Kiểm tra Index ---")
        list_chunks(n=5)
        inspect_metadata_coverage()

    print("\n✓ Sprint 1 hoàn thành!")
