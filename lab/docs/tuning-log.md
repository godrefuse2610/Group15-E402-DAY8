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
| Faithfulness | 4.40 /5 |
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

**Ngày:** ___________  
**Biến thay đổi:** ___________  
**Lý do chọn biến này:**
> TODO: Giải thích theo evidence từ baseline results.
> Ví dụ: "Chọn hybrid vì q07 (alias query) và q09 (mã lỗi ERR-403) đều thất bại với dense.
> Corpus có cả ngôn ngữ tự nhiên (policy) lẫn tên riêng/mã lỗi (ticket code, SLA label)."

**Config thay đổi:**
```
retrieval_mode = "hybrid"   # hoặc biến khác
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | ?/5 | ?/5 | +/- |
| Answer Relevance | ?/5 | ?/5 | +/- |
| Context Recall | ?/5 | ?/5 | +/- |
| Completeness | ?/5 | ?/5 | +/- |

**Nhận xét:**
> TODO: Variant 1 cải thiện ở câu nào? Tại sao?
> Có câu nào kém hơn không? Tại sao?

**Kết luận:**
> TODO: Variant 1 có tốt hơn baseline không?
> Bằng chứng là gì? (điểm số, câu hỏi cụ thể)

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
   > _____________

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > _____________

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > _____________
