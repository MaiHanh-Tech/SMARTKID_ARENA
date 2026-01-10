import streamlit as st
from ai_core import AI_Core
import json
import re

class QuizEngine:
    def __init__(self):
        self.ai = AI_Core()
    
    def generate_quiz(self, content, subject, chapter, difficulty, num_questions):
        """Sinh câu hỏi trắc nghiệm từ nội dung sách"""
        
        # Cắt nội dung nếu quá dài (để tránh quá tải token)
        max_chars = 12000
        if len(content) > max_chars:
            content = content[:max_chars]
            st.info(f"ℹ️ Nội dung quá dài, chỉ phân tích {max_chars:,} ký tự đầu")
        
        # Map difficulty
        difficulty_map = {
            "Easy 😊": "dễ (kiến thức cơ bản, ghi nhớ)",
            "Medium 🤔": "trung bình (vận dụng, hiểu bản chất)",
            "Hard 😰": "khó (tư duy cao, phân tích sâu)",
            "Expert 💀": "nâng cao (Olympic, sáng tạo)"
        }
        
        difficulty_text = difficulty_map.get(difficulty, "trung bình")
        
        # Prompt cho AI
        chapter_text = f"Chương {chapter}" if chapter != "ALL" else "toàn bộ môn học"
        
        # ===== THÊM MỚI: Phát hiện nếu là ADAPTIVE mode =====
        is_adaptive = chapter == "ADAPTIVE"
        
        if is_adaptive:
            # Nếu là adaptive mode, content chính là custom prompt
            # Dùng trực tiếp prompt đó
            prompt = content
        else:
            # Prompt thông thường
            prompt = f"""Bạn là giáo viên giỏi môn {subject} lớp 8.

NỘI DUNG SÁCH (Chương {chapter}):
{content}

NHIỆM VỤ:
Tạo {num_questions} câu hỏi trắc nghiệm 4 đáp án về {chapter_text}.

YÊU CẦU:
- Độ khó: {difficulty_text}
- Mỗi câu có 4 đáp án: A, B, C, D
- CHỈ có 1 đáp án đúng
- Câu hỏi phải dựa trên nội dung sách
- Không hỏi chi tiết quá nhỏ
- Câu hỏi rõ ràng, dễ hiểu với học sinh lớp 8

ĐỊNH DẠNG OUTPUT (CHỈ TRẢ VỀ JSON):
[
  {{
    "question": "Câu hỏi 1?",
    "options": ["A. Đáp án A", "B. Đáp án B", "C. Đáp án C", "D. Đáp án D"],
    "correct_answer": "A. Đáp án A",
    "explanation": "Giải thích ngắn gọn tại sao đây là đáp án đúng",
    "topic": "Tên chủ đề CỤ THỂ (VD: 'Phép cộng phân số', 'Đọc hiểu văn bản', 'Thì hiện tại đơn')",
    "concept_tags": ["khái niệm 1", "khái niệm 2"]
  }}
]

⚠️ QUAN TRỌNG:
- "topic" PHẢI là tên chủ đề CỤ THỂ trong chương (VD: "Phép cộng phân số", KHÔNG phải "Toán học")
- "concept_tags" PHẢI là list các khái niệm/kỹ năng liên quan (VD: ["cộng", "phân số", "quy đồng"])
- TUYỆT ĐỐI không bỏ qua 2 fields này!

BẮT BUỘC: 
- Chỉ trả về JSON hợp lệ
- Không thêm text giải thích nào khác
- Không dùng markdown code block
"""
        
        try:
            # Gọi AI
            with st.spinner("🤖 AI đang nghĩ..."):
                response = self.ai.generate(
                    prompt,
                    model_type="flash",
                    system_instruction="Bạn là hệ thống sinh câu hỏi tự động. CHỈ trả về JSON hợp lệ, không thêm text nào khác."
                )
            
            if not response or "⚠️" in response:
                st.error(f"❌ AI trả về lỗi: {response}")
                return None
            
            # Parse JSON (loại bỏ markdown nếu có)
            response = response.strip()
            
            # Loại bỏ markdown code block
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            # Parse JSON
            quiz_data = json.loads(response)
            
            # Validate
            if not isinstance(quiz_data, list) or len(quiz_data) == 0:
                st.error("❌ AI trả về format sai (không phải list)")
                return None
            
            # Validate từng câu hỏi
            valid_quiz = []
            for item in quiz_data:
                if all(k in item for k in ["question", "options", "correct_answer"]):
                    # Kiểm tra số đáp án
                    if len(item["options"]) == 4:
                        # ===== THÊM MỚI: Đảm bảo có topic và concept_tags =====
                        if "topic" not in item or not item["topic"]:
                            # Fallback: Tạo topic từ subject
                            item["topic"] = f"{subject} - Chương {chapter}" if chapter != "ALL" else subject
                        
                        if "concept_tags" not in item:
                            # Fallback: Tạo tags rỗng
                            item["concept_tags"] = []
                        
                        # Đảm bảo concept_tags là list
                        if not isinstance(item["concept_tags"], list):
                            item["concept_tags"] = []
                        
                        valid_quiz.append(item)
            
            if len(valid_quiz) == 0:
                st.error("❌ Không có câu hỏi nào hợp lệ")
                return None
            
            st.success(f"✅ Đã tạo {len(valid_quiz)} câu hỏi!")
            return valid_quiz
                
        except json.JSONDecodeError as e:
            st.error(f"❌ Lỗi parse JSON: {e}")
            with st.expander("🐛 Debug: Xem response từ AI"):
                st.code(response)
            return None
            
        except Exception as e:
            st.error(f"❌ Lỗi tạo quiz: {e}")
            return None
    
    def generate_adaptive_quiz(
        self,
        content: str,
        subject: str,
        weak_topics: list,
        recent_errors: list,
        num_questions: int,
        difficulty: str = "Medium 🤔"
    ):
        """
        [Inference] Sinh quiz tập trung vào điểm yếu
        
        Wrapper method cho adaptive mode
        """
        # Map difficulty
        difficulty_map = {
            "Easy 😊": "dễ (kiến thức cơ bản, ghi nhớ)",
            "Medium 🤔": "trung bình (vận dụng, hiểu bản chất)",
            "Hard 😰": "khó (tư duy cao, phân tích sâu)",
            "Expert 💀": "nâng cao (Olympic, sáng tạo)"
        }
        difficulty_text = difficulty_map.get(difficulty, "trung bình")
        
        weak_topics_str = ", ".join(weak_topics[:3]) if weak_topics else "các chủ đề cần cải thiện"
        
        # Custom prompt for adaptive mode
        adaptive_prompt = f"""Bạn là giáo viên giỏi môn {subject} lớp 8, đang tạo bài tập ÔN TẬP ĐIỂM YẾU cho học sinh.

NỘI DUNG SÁCH (Tham khảo):
{content[:8000]}

HỌC SINH ĐANG YẾU Ở CÁC CHỦ ĐỀ:
{weak_topics_str}

CÁC CÂU ĐÃ SAI GẦN ĐÂY (TRÁNH LẶP LẠI):
{chr(10).join(f"- {e[:80]}..." for e in recent_errors[:5]) if recent_errors else "(Chưa có)"}

NHIỆM VỤ:
Tạo {num_questions} câu hỏi trắc nghiệm 4 đáp án để rèn luyện các chủ đề yếu.

YÊU CẦU:
- Độ khó: {difficulty_text} (PHÙ HỢP để học sinh tự tin)
- Mỗi câu có 4 đáp án: A, B, C, D
- CHỈ có 1 đáp án đúng
- 60% câu hỏi về {weak_topics_str}
- 40% câu hỏi liên quan để củng cố nền tảng
- TUYỆT ĐỐI KHÔNG trùng với các câu đã sai ở trên
- Câu hỏi ĐA DẠNG: khái niệm, tính toán, ứng dụng thực tế

ĐỊNH DẠNG OUTPUT (CHỈ TRẢ VỀ JSON):
[
  {{
    "question": "Câu hỏi 1?",
    "options": ["A. Đáp án A", "B. Đáp án B", "C. Đáp án C", "D. Đáp án D"],
    "correct_answer": "A. Đáp án A",
    "explanation": "Giải thích ngắn gọn tại sao đây là đáp án đúng",
    "topic": "Tên chủ đề CỤ THỂ (VD: 'Phép cộng phân số')",
    "concept_tags": ["khái niệm 1", "khái niệm 2"]
  }}
]

⚠️ QUAN TRỌNG:
- "topic" PHẢI khớp với các chủ đề yếu đã nêu
- "concept_tags" PHẢI là list các khái niệm/kỹ năng cụ thể
- Câu hỏi phải GIÚP học sinh cải thiện, KHÔNG để "bẫy"

BẮT BUỘC: 
- Chỉ trả về JSON hợp lệ
- Không thêm text giải thích nào khác
- Không dùng markdown code block
"""
        
        # Gọi generate với ADAPTIVE flag
        return self.generate_quiz(
            content=adaptive_prompt,
            subject=subject,
            chapter="ADAPTIVE",  # Đánh dấu là adaptive mode
            difficulty=difficulty,
            num_questions=num_questions
        )
