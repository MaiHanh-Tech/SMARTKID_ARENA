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
    "explanation": "Giải thích ngắn gọn tại sao đây là đáp án đúng"
  }}
]

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
