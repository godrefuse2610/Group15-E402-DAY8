# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyễn Công Nhật Tân - 2A202600141
**Vai trò trong nhóm:** Eval Owner
**Ngày nộp:** 13/4/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong đồ án này, với vai trò là Eval Owner, nhiệm vụ trọng tâm của tôi thuộc về Sprint 4: Thiết kế hệ thống đo lường và đánh giá chất lượng (Scorecard) cho RAG pipeline. Cụ thể, tôi đã đảm nhận việc lập trình các hàm chấm điểm trong `eval.py`. Thay vì phải ngồi chấm thủ công cảm tính cho 10 câu hỏi kiểm thử mỗi lần đổi cấu hình, tôi đã hiện thực hoá kỹ thuật "LLM-as-a-Judge", sử dụng mô hình `gpt-4o-mini` qua API OpenAI để tự động đánh giá 4 chỉ số (Metrics) cốt lõi: Faithfulness, Answer Relevance, Context Recall và Completeness. Tôi trực tiếp định nghĩa các System Prompt với thang điểm phân bổ rõ ràng để ép LLM làm giám khảo một cách khách quan. Kết quả công việc của tôi là trạm kiểm định cuối cùng, tiếp nhận đoạn trích xuất từ pipeline của Tech Lead, từ đó sinh ra các báo cáo Scorecard tự động phục vụ công tác đối chiếu A/B Testing.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau khi trực tiếp cấu hình và quan sát kết quả sinh ra từ hệ thống, tôi hiểu sâu sắc hơn về khái niệm "Evaluation Loop" và rủi ro của "Hallucination" trong RAG. Ban đầu, tôi lầm tưởng sơ đẳng rằng chỉ cần hệ thống Retriever đi tìm ra đúng văn bản mang về là hệ thống sẽ dĩ nhiên trả lời đúng. Tuy nhiên, việc tự tay bóc tách cấu hình chỉ số `Completeness` và `Faithfulness` giúp tôi ngộ ra rằng: khả năng thu thập văn bản (Retrieval) và khả năng suy luận/đọc hiểu để trả lời (Generation) là hai tầng lỗi riêng biệt. Đặc biệt là thông qua kỹ thuật LLM-as-a-Judge, tôi hiểu được phương pháp "ép" một AI làm việc như một công cụ đo lường thay vì một trợ lý ảo (thông qua ràng buộc output JSON nghiêm ngặt và đối chiếu trực tiếp ground truth trong prompt).

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều khiến tôi ngạc nhiên nhất là nghịch lý kết quả trong quá trình A/B Testing: Bản nâng cấp Variant 1 (sử dụng Hybrid Search kết hợp BM25) lại cho ra điểm số trung bình "thấp hơn" khá nhiều so với bản Baseline Vanilla (chỉ dùng Dense Search). Giả thuyết ban đầu của tôi là khi ghép thêm thuật toán Sparse, độ bắt keyword mã lỗi nội bộ sẽ giúp hệ thống nhạy bén hơn. Ngược lại, thực tế debug các câu hỏi điểm thấp lại phơi bày việc thuật toán Sparse vơ vét quá nhiều đoạn văn bản chứa "từ khóa rác", đánh bật cả tài liệu mang ngữ cảnh trọng tâm ra khỏi quỹ đạo `top_3` nạp vào bước Gen. Quá trình loay hoay xử lý việc môi trường Windows báo lỗi `rank_bm25` chưa nạp và lần mò độ mâu thuẫn điểm số mang lại cho tôi bài học bẻ gãy mọi giả thuyết màu hồng về "Model càng thêm nhiều layer càng thông minh".

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** [q09] ERR-403-AUTH là lỗi gì và cách xử lý?

**Phân tích:** 
Đây là một câu hỏi dạng Out-of-Domain (OOD) - cố tình hỏi một mã lỗi không hề tồn tại trong kho tài liệu để thử thách độ an ninh của pipeline. 
Ở bản Baseline, AI đã bị "ảo giác" (Hallucination) nặng và bịa ra cách giải quyết lỗi y hệt như tài liệu kỹ thuật trên Internet (chúng tôi nhận được một câu trả lời dù trôi chảy nhưng vi phạm nguyên tắc Data Grounding). 
Bất ngờ thay, khi chạy bản Variant (sử dụng Hybrid Search), do các từ khóa rác làm nhiễu loạn thông tin, Generative LLM tự nhận thức được giới hạn và phản hồi "Tôi không biết / Không có dữ liệu". Đây là một hành vi hoàn toàn chính xác và an toàn. Tuy nhiên, lỗi đánh giá lại nằm chính ở hệ thống của tôi: Prompt của Eval Judge không được dạy cách chấm điểm ưu tiên cho câu trả lời "từ chối". Do đó, thuật toán đánh giá đã thẳng tay phạt câu phản hồi này 1/5 điểm Faithfulness và 1/5 điểm Completeness vì không giống mong đợi. Câu [q09] này đã trở thành ví dụ kinh điển minh hoạ cho sai lệch cấu trúc đo lường nội bộ.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm một buổi làm việc, mục tiêu ưu tiên số một của tôi sẽ là tối ưu lại logic các Prompt làm giám khảo trong `eval.py`. Cụ thể, tôi sẽ bổ sung một vòng nhánh điều kiện kiểm tra (Decision Tree Root) để LLM-as-a-Judge phân biệt được câu trả lời "bỏ qua an toàn" (Abstaining) đối chiếu với các câu OOD, từ đó thưởng điểm tối đa thay vì phạt lỗi. Thêm vào đó, tôi muốn áp dụng thực tiễn công nghệ Query Transform ở vòng lấy source để giúp Context trở nên giàu ngữ nghĩa hơn.

---
