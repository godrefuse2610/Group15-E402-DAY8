import json
from datetime import datetime
from rag_answer import rag_answer
import os

# Đảm bảo thư mục logs luôn tồn tại
os.makedirs("logs", exist_ok=True)

print("Đang nạp bộ đề đánh giá grading_questions.json...")
try:
    with open("data/grading_questions.json", "r", encoding="utf-8") as f:
        questions = json.load(f)

    log = []
    print(f"Bắt đầu làm bài thi ({len(questions)} câu). Vui lòng đợi...")
    
    for q in questions:
        # Chọn cấu hình tốt nhất. Theo báo cáo, Rerank làm giảm điểm ở 1 số câu,
        # Nên chiến lược an toàn là dùng 'dense' hoặc 'hybrid' tùy ý.
        # Chiếu theo code gốc của giảng viên: retrieval_mode="hybrid"
        result = rag_answer(q["question"], retrieval_mode="hybrid", use_rerank=False, verbose=False)
        log.append({
            "id": q["id"],
            "question": q["question"],
            "answer": result["answer"],
            "sources": result["sources"],
            "chunks_retrieved": len(result["chunks_used"]),
            "retrieval_mode": result["config"]["retrieval_mode"],
            "timestamp": datetime.now().isoformat(),
        })

    with open("logs/grading_run.json", "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
        
    print("✅ Hoàn tất! File nộp bài đã được lưu tại: logs/grading_run.json")

except FileNotFoundError:
    print("❌ Lỗi: Chưa tìm thấy file data/grading_questions.json.")
