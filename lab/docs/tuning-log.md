# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** ____13/4/2026_____  
**Config:**
```
retrieval_mode = "dense"
chunk_size = _____400 tokens
overlap = _____80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = _____gpt-4o-mini
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.50 /5 |
| Answer Relevance | 4.70 /5 |
| Context Recall | 5 /5 |
| Completeness |3.8 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
Câu [q09]: ERR-403-AUTH là lỗi gì và cách xử lý?

Điểm: Faithful: 5 | Relevant: 5 | Recall: None | Complete: 2
Phân tích vì sao thấp: Đây là câu hỏi mẹo (Out-of-Domain), file tài liệu công ty không hề có mã lỗi này (Context Recall là None do expected_source bị bõ trống). Tuy nhiên, LLM lại không biết nói "Tôi không biết / Không đủ dữ liệu", mà lại bị "ảo giác" (Hallucination) dùng kiến thức lập trình ngoài internet để tự chém gió ra câu trả lời. Câu trả lời đó đi chệch hoàn toàn so với đáp án kỳ vọng của Eval Owner nên Completeness chỉ được 2.

Câu [q07]: Approval Matrix để cấp quyền hệ thống là tài liệu nào?

Điểm: Faithful: 5 | Relevant: 5 | Recall: 5 | Complete: 2
Phân tích vì sao thấp: Hệ thống tìm đúng file, trả lời bám sát file nhưng bị rơi rụng mất các điểm ý chính so với đáp án chuẩn (expected_answer), khiến Completeness rất thấp. Nguyên nhân có thể do Top K = 3 quá ít để gom đủ tất cả các ý nghĩa (context) hoặc thuật toán Dense Retrieval lấy lên 3 đoạn bị rác/trùng lặp nên LLM không có đủ nguyên liệu để soạn ra một câu trả lời đầy đủ ý.


**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [ ] Retrieval: Dense bỏ lỡ exact keyword / alias
- [x] Retrieval: Top-k quá ít → thiếu evidence
- [ ] Generation: Prompt không đủ grounding
- [ ] Generation: Context quá dài → lost in the middle

---

## Variant 1 (Sprint 3)

**Ngày:** ______13/4/2026_____  
**Biến thay đổi:** retrieval_mode = "hybrid"   
**Lý do chọn biến này:**

> Ví dụ: "Chọn hybrid vì q07 (alias query) và q09 (mã lỗi ERR-403) đều thất bại với dense.
> Corpus có cả ngôn ngữ tự nhiên (policy) lẫn tên riêng/mã lỗi (ticket code, SLA label)."

**Config thay đổi:**
```
retrieval_mode = "hybrid"   
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.50/5 | 4.10/5 | -0.4 |
| Answer Relevance | 4.70/5 | 4.30/5 | -0.4 |
| Context Recall | 5/5 | 5/5 | 0 |
| Completeness | 3.8/5 | 3.5/5 | -0.3 |

**Nhận xét:**
Variant 1 cải thiện ở câu nào? Tại sao?

Cải thiện thực chất ở câu [q09] (ERR-403-AUTH).

Bằng chứng: Ở bản Baseline, AI bị ảo giác (hallucinate) và tự bịa ra định nghĩa cho mã lỗi này (được chấm 5 điểm sai quy định). Nhưng sang bản Variant Hybrid, AI đã biết nói "Tôi không biết".
Tại sao: Do Hybrid Search đưa lên các từ khóa nhiễu, làm loãng ngữ cảnh, khiến Generative LLM tự nhận thức được là nó không có đủ dữ kiện để bịa.
Nghịch lý ở đây: Dù hành vi nói "không biết" là chính xác hoàn toàn cho câu hỏi Out-of-Domain này, nhưng prompt chấm điểm tự động của Eval Owner đã chấm cực kỳ gắt (Faithful 1, Relevant 1, Complete 1) vì nó không hiểu "từ chối trả lời" suy ra là Faithful. Đây là lý do chính khiến tổng điểm Variant bị kéo sập xuống.

Kém hơn rõ nhất ở câu [q06] (Escalation sự cố P1 diễn ra như thế nào?)

Bằng chứng: Điểm Completeness của [q06] rớt thẳng từ 5 (Baseline) xuống còn 2 (Variant 1).
Tại sao: Thuật toán Sparse (BM25) của Hybrid cực kỳ nhạy cảm với các keyword ("Escalation", "P1"). Nó đã "kéo" nhầm một số thông báo ngẫu nhiên hoặc tài liệu phụ chứa cụm từ này lên top đầu, vô tình đạp đoạn văn bản gốc chứa sự miêu tả đầy đủ của quy trình Escalation xuống (vì top_k_select chỉ lấy cắt đúng 3 đoạn). Hậu quả là LLM không nhận được đủ mảnh ghép văn bản và trả lời thiếu hụt.

**Kết luận:**
Variant 1 có tốt hơn baseline không?
Bằng chứng là gì? (điểm số, câu hỏi cụ thể)

Variant 1 KHÔNG tốt hơn Baseline.

Bằng chứng: Tổng điểm trung bình của Variant 1 là 3.85/5, thấp hơn Baseline là 4.45/5. Cụ thể, các chỉ số Faithfulness và Answer Relevance giảm 0.4 điểm.

Lý do: Mặc dù Hybrid Search đã giúp AI không bịa chuyện ở câu hỏi OOD (Out-of-Domain) [q09], nhưng nó lại làm giảm chất lượng câu trả lời ở các câu hỏi thông thường (như [q06]) do thuật toán Sparse bị nhiễu bởi từ khóa, dẫn đến việc LLM nhận được context kém chất lượng hơn và trả lời thiếu ý.

---

## Variant 2 (nếu có thời gian)

**Biến thay đổi:** ___________  
**Config:**
```
# TODO
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | ? | ? | ? | ? |
| Answer Relevance | ? | ? | ? | ? |
| Context Recall | ? | ? | ? | ? |
| Completeness | ? | ? | ? | ? |

---

## Tóm tắt học được

> TODO (Sprint 4): Điền sau khi hoàn thành evaluation.

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Lỗi phổ biến nhất là AI bị ảo giác (Hallucination) đối với các truy vấn ngoài miền dữ liệu (Out-of-Domain) và trả lời thiếu ý do Context window bị cắt mỏng. Hệ thống Dense Retrieval đôi khi gom được đúng file nhưng Rerank/Sparse lại đưa các đoạn rác lên đầu, đẩy đoạn chốt chứa ý nghĩa chính xuống dưới ngưỡng top_k_select, làm LLM bị thiếu nguyên liệu tổng hợp.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Cấu trúc System Prompt (Generative) và Top K Select. Khi thuật toán tìm kiếm (Retrieval) thay đổi từ Dense sang Hybrid, nó mang lại kết quả xáo trộn. Dù cố gắng tối ưu thuật toán tìm kiếm thuật toán cỡ nào, nhưng nếu bước sinh ngôn ngữ (LLM Prompt) không được dặn "phải từ chối nếu không thấy" thì điểm số của hệ thống vẫn sẽ bị kéo sụt nhanh chóng bởi lỗi ảo giác.

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Sẽ Tinh chỉnh lại System Prompt kết hợp với thử nghiệm phương pháp Query Transformation (HyDE hoặc Decomposition). Bằng cách chặn đứng hiện tượng ảo giác ngay tại Prompt, chúng ta sẽ bảo vệ được sự tin cậy (Faithfulness) của Scorecard. Đồng thời, áp dụng HyDE có thể giúp tìm tài liệu tốt hơn phương pháp Hybrid thuần túy.
