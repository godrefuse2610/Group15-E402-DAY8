# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phan Anh Ly Ly
**Vai trò trong nhóm:** Nhóm 15 - Research Owner
**Ngày nộp:** 2026-04-13  
**Độ dài:** ~750 từ

---

## 1. Tôi đã làm gì trong lab này?

Trong lab này, tôi đảm nhận vai trò **Tech Lead**, với đóng góp cốt lõi là xây dựng **lớp research tools** — tầng trung gian bọc RAG retrieval thành các callable tools — đây là bước chuyển đổi quyết định từ RAG pipeline tĩnh sang agent có khả năng suy luận động.

Ở **Sprint 1**, tôi implement `get_embedding()` sử dụng OpenAI `text-embedding-3-small` và hoàn thiện `build_index()` trong `index.py`. Pipeline bao gồm: đọc PDF bằng `pypdf`, preprocess (extract metadata từ header `Key: Value`, normalize whitespace), chunk theo cấu trúc heading tự nhiên (`=== Section ===`) rồi sub-chunk theo paragraph với overlap 80 tokens, embed và upsert vào ChromaDB `PersistentClient`. Kết quả: **29 chunks từ 5 tài liệu** với đủ 5 metadata fields, không có chunk nào thiếu `effective_date`.

Ở **Sprint 2**, tôi implement `retrieve_dense()` (embedding similarity với ChromaDB), `call_llm()`, và thiết kế **grounded prompt** theo 4 nguyên tắc từ slide: evidence-only, abstain, citation, và short/clear. Pipeline RAG end-to-end hoạt động: trả lời đúng 8/10 câu và abstain đúng ở câu hỏi không có nguồn.

Ở **Sprint 3**, phần quan trọng nhất trong lab của tôi: tôi thiết kế và implement **`tools.py`** — thư viện 5 research tools bọc các retrieval function thành interface mà LLM có thể gọi qua OpenAI Function Calling:
- `search_knowledge_base()` — bọc `retrieve_dense()`, dùng cho câu hỏi tự nhiên về policy, SLA
- `search_keyword()` — BM25 index với `rank_bm25` cho mã lỗi/tên riêng chính xác (ERR-403, P1)
- `get_current_date()` — cung cấp thời gian thực để tính deadline SLA
- `get_ticket_info()` — tra cứu ticket theo ID (mock Jira/ServiceNow)
- `escalate_to_human()` — fallback khi không đủ thông tin, thay vì để model bịa

Mỗi tool đều trả về JSON string chuẩn hoá để LLM dễ parse, và đi kèm `TOOL_DEFINITIONS` (JSON schema) cho OpenAI Function Calling. Đây chính là **điểm chuyển đổi**: từ RAG pipeline gọi retrieval cứng → agent tự quyết định gọi tool nào, khi nào, theo thứ tự gì.

Ở **Sprint 4**, tôi implement `agent.py` (ReAct loop với `MAX_TURNS=6`, dispatch qua `execute_tool()`) và `eval.py` với **LLM-as-Judge** (4 metrics: Faithfulness, Relevance, Context Recall, Completeness), `run_scorecard()`, `run_agent_scorecard()`, và `compare_ab()` xuất CSV.

Công việc của tôi kết nối trực tiếp với phần của Retrieval Owner (các retrieval functions trong `rag_answer.py` được tôi bọc lại thành tools) và Eval Owner (scorecard chạy được vì pipeline đã end-to-end).

---

## 2. Điều tôi hiểu rõ hơn sau lab này

**Chunking quyết định chất lượng retrieval nhiều hơn tôi nghĩ.** Trước lab, tôi cho rằng embedding model là yếu tố chính. Sau khi implement và chạy `list_chunks()`, tôi nhận ra: nếu cắt giữa điều khoản, embedding của chunk đó sẽ thiếu context dù model hoàn toàn bình thường. Heading-based chunking (tôn trọng cấu trúc `=== Section ===`) + paragraph overlap cho kết quả nhất quán hơn nhiều so với split cứng theo số ký tự. Điều này giải thích tại sao **Context Recall = 5.00/5** trên cả baseline và variant — không có câu hỏi nào bị miss source vì retrieval đã tìm đúng chunk.

**Eval framework phải được thiết kế song song với pipeline, không phải sau.** Khi implement `run_agent_scorecard()`, tôi phát hiện ra vấn đề: agent không trả về `chunks_used` (vì dùng Function Calling thay vì RAG pipeline thẳng), nên `chunks_used = []` được truyền vào LLM judge. Judge phán "không được grounded" dù agent đã query ChromaDB thành công. Hệ quả: **Faithfulness của variant = 4.10/5 thấp hơn baseline = 4.50/5** — không phải vì pipeline kém hơn mà vì measurement artifact. Bài học: metric phải đo đúng cái cần đo, không phải cái dễ đo.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn

Điều ngạc nhiên nhất là **agent tự gọi 2 tools theo đúng thứ tự logic mà không cần hướng dẫn cụ thể.** Với test case "Ticket IT-0001 tạo lúc 9h sáng, đến giờ có vi phạm SLA chưa?", agent gọi `get_ticket_info("IT-0001")` → lấy priority P1 và created_at → sau đó tự gọi `get_current_date()` → tính ra đã qua 6h20 > 4h SLA → kết luận "đã vi phạm". Không có gì trong system prompt chỉ định phải làm theo thứ tự đó. Đây là emergent multi-step reasoning từ Function Calling.

Khó khăn lớn nhất là **Unicode encoding trên Windows PowerShell** khi script dùng tiếng Việt. PowerShell mặc định dùng `cp1252`, gây `UnicodeEncodeError` ngay ở dòng `print()` đầu tiên. Fix là thêm `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")` vào mỗi `__main__` block và đặt `$env:PYTHONIOENCODING="utf-8"` trong shell. Mất thời gian debug vì error message không rõ nguyên nhân.

Bất ngờ tiêu cực: **q10 (VIP refund) bị Faithfulness=1 ở cả baseline và variant.** Tôi điều tra và thấy đây là câu hỏi không có thông tin trong docs (`expected_answer` nói rõ "không đề cập"), nhưng baseline lại trả về "tôi không biết" đúng — LLM judge vẫn chấm 1 vì `chunks_used` có chunks về refund policy (retrieved do semantic similarity) và judge cho rằng "không trả lời khi có context" là fabrication. Đây là false negative của eval: abstain đúng bị phạt.

---

## 4. Phân tích một câu hỏi trong scorecard

**Câu hỏi:** `q09 — "ERR-403-AUTH là lỗi gì và cách xử lý?"`

**Phân tích:**

Đây là câu hỏi thiết kế để kiểm tra khả năng **abstain** — tài liệu nội bộ không có thông tin về mã lỗi `ERR-403-AUTH`. `expected_sources = []` xác nhận không có source nào phù hợp, và `expected_answer` chỉ đơn giản là "hãy liên hệ IT Helpdesk."

Ở **baseline (Dense RAG)**: `retrieve_dense()` tìm được top-3 chunks với similarity score thấp (khoảng 0.35–0.37, gần noise). Vì grounded prompt có quy tắc abstain, model đọc context → nhận ra không có thông tin về `ERR-403-AUTH` → tuy nhiên lại **không abstain hoàn toàn**: thay vào đó, model suy diễn từ chunks access control rằng đây có thể là lỗi "không có quyền truy cập" và gợi ý tạo Jira ticket. LLM judge chấm Faithfulness=5 (câu trả lời grounded theo chunks), Relevance=5 (trả lời câu hỏi), nhưng Completeness=2 (thiếu gợi ý liên hệ IT Helpdesk cụ thể). **Lỗi ở generation**: grounded prompt không đủ strict để ép model abstain khi context chỉ là noise.

Ở **variant (Hybrid RAG)**: `retrieve_hybrid()` với BM25 chạy keyword search "ERR-403-AUTH" → BM25 score = 0 (exact term không có trong corpus) → hybrid vẫn dùng dense results → model trả về "Tôi không biết." Judge chấm Faithfulness=1, Relevance=1, Completeness=1 — đây là measurement artifact như đã phân tích: abstain đúng nhưng bị penalize vì context (dù noise) được coi là "đủ để trả lời."

**Kết luận**: câu q09 cho thấy need thiết kế **abstain metric riêng** (did the system correctly *not answer* when there's no relevant context?), thay vì dùng faithfulness/relevance vốn assume luôn phải có câu trả lời.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì?

**Thứ nhất**, tôi sẽ fix agent eval để expose `chunks_retrieved` từ mỗi tool call vào `chunks_used`. Kết quả scorecard cho thấy variant Faithfulness = 4.10/5 thấp hơn baseline 4.50/5 — không phải vì agent kém hơn mà vì `chunks_used = []` được truyền vào judge. Fix này sẽ cho so sánh fair hơn và có thể đảo ngược kết quả A/B trên metric faithfulness.

**Thứ hai**, tôi sẽ thêm **abstain metric chuyên biệt** vào eval framework: với câu hỏi có `expected_sources = []`, metric duy nhất nên là "system có từ chối trả lời không?" (binary: 1 hoặc 0), thay vì dùng faithfulness/completeness vốn penalize abstain. Kết quả eval q09 và q10 cho thấy rõ nhu cầu này.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
