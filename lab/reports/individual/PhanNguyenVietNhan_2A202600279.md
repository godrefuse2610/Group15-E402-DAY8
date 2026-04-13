# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Phan Nguyễn Việt NhNh
**Vai trò trong nhóm:** Retrieval Owner
**Ngày nộp:** 13/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Với vai trò là **Retrieval Owner**, tôi chịu trách nhiệm chính thiết kế và xây dựng luồng Indexing (Sprint 1) và Retrieval (Sprint 2 & 3). Cụ thể, tôi đã:
- **Indexing:** Xây dựng module đọc PDF bằng thư viện `pypdf`, áp dụng chiến lược hierarchical chunking (tách theo từng section trước, sau đó tách nhỏ theo paragraph với overlap 80 tokens) để giữ nguyên văn cảnh đứt gãy. Tôi viết logic trích xuất 5 trường dạng metadata (Source, Department, Effective Date, Access) giúp làm giàu thông tin cho từng chunk, rồi lưu vào ChromaDB dùng embedding model `text-embedding-3-small`.
- **Retrieval & Tuning:** Trong `rag_answer.py`, tôi đã implement Dense retrieval (baseline). Để cải thiện độ chính xác ở Sprint 3, tôi đã lập trình bổ sung Sparse (BM25), Hybrid (RRF) và **hoàn thiện Cross-Encoder Reranking**. Tôi setup quy trình "funnel": lấy Top 10 chunks bằng vector search, sau đó dùng mô hình phân loại `cross-encoder/ms-marco-MiniLM-L-6-v2` chấm điểm lại mức độ liên quan, rốt cuộc chắt lọc lại thành Top 3 chunks tinh túy nhất để đưa cho LLM. Nhờ đó, Prompt & Generation có context sạch và có căn cứ để trích dẫn nguồn chuẩn xác.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Hai khái niệm tôi thực sự hiểu rõ hơn sau Lab này là **Reranking Funnel** và **Metadata Filtering**.

Trước đây, tôi có quan niệm sai lầm rằng cứ search Vector (Bi-encoder) lấy top cao nhất đưa cho LLM là đủ. Nhưng thực tế Baseline cho thấy Vector Search bị "nhiễu" rất nặng (ví dụ: query về SLA P1 lại lấy cả policy về hoàn tiền). Áp dụng **Cross-encoder Reranking** giúp tôi hiểu nguyên lý chấm điểm chéo sâu sát của nó bằng cách gộp chung (Query, Chunk) - tuy chậm nhưng cho độ chuẩn xác cao hơn nhiều so với việc tra cứu khoảng cách Cosine đơn thuần. Kiến trúc phễu lọc (tìm rộng top 10 -> chọn tinh top 3) cân bằng hoàn hảo giữa hiệu năng của Dense và sự cẩn trọng của Cross-Encoder. Khái niệm trích xuất metadata (Effective Date, Department) cũng giúp tôi hiểu cách một RAG system thực tế xử lý permission cũng như data tagging.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

**Lỗi mất thời gian và ngạc nhiên nhất** cản bước tôi là xung đột dependency giữa `Keras 3` và thư viện `sentence-transformers` khi load mô hình Cross-encoder. Ngay khi chuẩn bị test A/B Sprint 3, hàm `model.predict()` ném ra lỗi vì transformers không hỗ trợ Keras 3. Ban đầu tôi nghĩ do chọn sai bộ model hoặc sai model path, debug hồi lâu mới biết giải pháp đơn giản là cài thư viện tương thích ngược `tf-keras`. Thật bất ngờ khi một lỗi tương tích ngầm lại làm vỡ cả pipeline.

Một khó khăn khác là đánh giá trường hợp **Abstain** (Không đủ dữ liệu). Với câu hỏi `"ERR-403-AUTH là lỗi gì?"`, mô hình sinh ra một câu Tiếng Việt xuất sắc là `"Tôi không biết."` nhưng hàm test tự động của chúng tôi lại đánh trượt kết quả đó vì chỉ khớp keyword cố định ("khong du du lieu", "insufficient"). Việc chỉnh sửa keyword giúp pass test nhưng cũng làm tôi nhận thấy Rule-based evaluation thực ra quá mỏng manh, củng cố việc nhóm làm thêm cơ chế chấm điểm bằng LLM (LLM-as-a-Judge) ở Sprint 4.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** SLA xử lý ticket P1 là bao lâu?

**Phân tích:**
- **Baseline (Dense - No Rerank):** Trả lời đúng, tuy nhiên ở phần Retrieval kéo theo nhiều kết quả ngoài luồng (noise). Lệnh Dense retrieval nhặt ra Top 3 chunks, và chunk thứ 3 lại thuộc về file `policy/refund-v4.pdf` (Chính sách hoàn tiền) dù câu hỏi không hề mang hàm ý đó. Trả lời được nhưng "evidence" bị lẫn tạp.
- **Lỗi nằm ở Retrieval:** Mô hình Bi-encoder dễ nhầm lẫn giữa Vector biểu diễn khái niệm "thời gian xử lý/giải quyết" (giữa tài liệu hoàn tiền và tài liệu SLA) vì chúng ở chung cụm Semantic context. 
- **Variant (Dense + Cross-Encoder Rerank):** Mô hình Cross-encoder nhận thấy cặp câu giữa (Ticket P1, Hoàn Tiền) chẳng hề tương đồng, nên đã đánh tụt giảm điểm của thẻ Chunk đó và đẩy 3 chunks từ file đúng `support/sla-p1-2026.pdf` lên Top 3. Nhờ đó Context Recall cũng như Answer Relevance tăng lên rõ rệt. Retrieval tạo ra ngõ vào sạch nhiễu, hạn chế tối đa rủi ro Model tự bịa hoặc chắp nối bối cảnh không liên quan.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Tôi muốn thử nghiệm **Query Transformation specifically HyDE (Hypothetical Document Embeddings)**. Do nhiều tài liệu công ty hoặc log lỗi có từ ngữ dạng "bí danh" hoặc mã chuyên biệt, một số retrieval query sẽ bỏ lỡ dữ liệu nếu từ khóa khớp cực thấp. Nếu dùng HyDE tạo ra một câu trả lời khả dĩ trước rồi mới search, recall sẽ tăng nhiều so với vector search khô khan ban đầu. Ngoài ra, tôi muốn thiết kế hàm kết hợp cả RRF (Dense + BM25) sau đó mới đưa qua Cross-encoder để có một pipeline tối tân nhất.
