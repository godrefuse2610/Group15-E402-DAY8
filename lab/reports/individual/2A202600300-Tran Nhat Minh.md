# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Tran Nhat Minh  
**Vai trò trong nhóm:** Tech Lead
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Em đã làm gì trong lab này? (100-150 từ)

> Mô tả cụ thể phần bạn đóng góp vào pipeline:
> - Sprint nào bạn chủ yếu làm?
> - Cụ thể bạn implement hoặc quyết định điều gì?
> - Công việc của bạn kết nối với phần của người khác như thế nào?

Trong lab này em phụ trách toàn bộ Sprint 2 — xây dựng baseline RAG pipeline hoàn chỉnh. Cụ thể, em implement ba hàm cốt lõi trong `rag_answer.py`: `retrieve_dense()` nhúng query bằng `text-embedding-3-small` rồi truy vấn ChromaDB, chuyển cosine distance thành similarity score (`1 - distance`); `call_llm()` gọi GPT-4o-mini với `temperature=0` để output ổn định cho evaluation; và `build_grounded_prompt()` với 4 ràng buộc — chỉ trả lời từ context, abstain khi thiếu thông tin, gắn citation `[1][2]`, ngắn gọn và rõ ràng.

Ngoài ra em kết nối pipeline hoàn chỉnh trong `rag_answer()`: chọn retrieval mode → truncate về `top_k_select` chunk → build context block → generate. Em cũng chạy thủ công 4 test query từ `test_questions.json` để verify Definition of Done Sprint 2: câu có đáp án trả về đúng với citation, câu `ERR-403-AUTH` (không có trong docs) phải abstain. Phần index ChromaDB (Sprint 1) do thành viên khác build; Em dùng lại `CHROMA_DB_DIR` và collection schema của họ.

---

## 2. Điều Em hiểu rõ hơn sau lab này (100-150 từ)

> Chọn 1-2 concept từ bài học mà bạn thực sự hiểu rõ hơn sau khi làm lab.
> Ví dụ: chunking, hybrid retrieval, grounded prompt, evaluation loop.
> Giải thích bằng ngôn ngữ của bạn — không copy từ slide.

**Grounded prompt và hành vi abstain.** Trước lab, em nghĩ chỉ cần viết "answer from context only" là model sẽ tự abstain khi thiếu thông tin. Thực tế phức tạp hơn — nếu prompt không nói rõ phải nói "không biết", model có xu hướng suy luận thêm từ kiến thức nền thay vì từ chối. Em phải thêm câu tường minh *"If the context is insufficient, say you do not know and do not make up information"* thì abstain mới hoạt động đúng với câu `ERR-403-AUTH`.

**Dense retrieval và vai trò của score.** Khi implement `retrieve_dense()`, em hiểu rõ hơn sự khác biệt giữa distance và similarity trong ChromaDB: với cosine space, `distance = 1 - similarity`, nên phải đảo lại khi hiển thị score. Điều này quan trọng khi debug — nếu dùng thẳng distance để so sánh, chunk "tốt nhất" lại có số nhỏ nhất, rất dễ nhầm khi đọc log.

---

## 3. Điều Em ngạc nhiên hoặc gặp khó khăn (100-150 từ)

> Điều gì xảy ra không đúng kỳ vọng?
> Lỗi nào mất nhiều thời gian debug nhất?
> Giả thuyết ban đầu của bạn là gì và thực tế ra sao?

Điều ngạc nhiên nhất là `temperature=0` không đảm bảo output hoàn toàn giống nhau giữa các lần chạy — với cùng một prompt, câu trả lời đôi khi khác nhau ở cách đặt câu dù nội dung tương đương. em tưởng `temperature=0` sẽ cho output deterministic hoàn toàn, nhưng thực tế vẫn có biến động nhỏ do floating-point ở phía OpenAI server.

Khó khăn lớn nhất là debug khi `retrieve_dense()` trả về kết quả nhưng câu trả lời vẫn sai. em mất khá nhiều thời gian mới nhận ra vấn đề nằm ở phía index (Sprint 1) — chunk bị cắt giữa điều khoản nên context gửi vào prompt thiếu thông tin quan trọng, không phải lỗi của retrieval hay generation. Đây là lúc em thực sự hiểu tại sao cần kiểm tra từng tầng riêng lẻ (indexing → retrieval → generation) thay vì debug end-to-end ngay.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

> Chọn 1 câu hỏi trong test_questions.json mà nhóm bạn thấy thú vị.
> Phân tích:
> - Baseline trả lời đúng hay sai? Điểm như thế nào?
> - Lỗi nằm ở đâu: indexing / retrieval / generation?
> - Variant có cải thiện không? Tại sao có/không?

**Câu hỏi:** SLA xử lý ticket P1 là bao lâu?

**Phân tích:**

**Baseline trả lời như thế nào?** Dense retrieval lấy đúng chunk từ `Phần 2` của `sla-p1-2026.pdf`, nơi ghi rõ first response 15 phút và resolution 4 giờ. Model trả lời đúng và gắn citation `[1]` vào source. Tuy nhiên, trong một lần chạy, model chỉ đề cập "4 giờ" mà bỏ qua mốc "15 phút first response" — đây là lỗi ở tầng **generation**: prompt không yêu cầu liệt kê đầy đủ các mốc thời gian, nên model tự chọn thông tin nổi bật nhất thay vì trả lời toàn diện.

**Bẫy ở tầng indexing.** Tài liệu có `Phần 5: Lịch sử phiên bản` ghi rõ *"v2026.1: cập nhật SLA P1 resolution từ 6 giờ xuống 4 giờ"*. Nếu chunk này lọt vào top-3 context (xảy ra khi chunking cắt không khéo và chunk Phần 2 bị đẩy xuống rank thấp hơn), model có thể trả lời "6 giờ" — đây là thông tin cũ, không còn hiệu lực. Lỗi nằm ở **indexing**: cần đảm bảo chunk chứa Phần 2 (SLA hiện hành) có score cao hơn chunk chứa lịch sử phiên bản.

**Kết luận:** Câu dễ nhưng cho thấy hai rủi ro thực tế — generation thiếu toàn diện và indexing có thể đưa thông tin lỗi thời vào context.

---

## 5. Nếu có thêm thời gian, Em sẽ làm gì? (50-100 từ)

> 1-2 cải tiến cụ thể bạn muốn thử.
> Không phải "làm tốt hơn chung chung" mà phải là:
> "Em sẽ thử X vì kết quả eval cho thấy Y."

Em sẽ thêm **metadata filter** vào `retrieve_dense()` — cụ thể lọc theo `effective_date` mới nhất khi có nhiều phiên bản tài liệu cùng chủ đề. Kết quả eval câu `q01` cho thấy chunk từ `Phần 5: Lịch sử phiên bản` có thể lọt vào context và đưa thông tin cũ ("6 giờ") vào câu trả lời; filter theo metadata sẽ loại bỏ rủi ro này mà không cần thay đổi chunking hay prompt.

Ngoài ra Em muốn thử **prompt thêm yêu cầu liệt kê đầy đủ** cho các câu hỏi dạng SLA — thêm một dòng *"If the answer contains multiple time values, list all of them"* — vì eval cho thấy generation hay tự chọn con số nổi bật nhất thay vì trả lời toàn diện (bỏ sót "15 phút first response" dù chunk đã có đủ thông tin).

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
