import streamlit as st
from ai_core import AI_Core
import json
import re

class QuizEngine:
    def __init__(self):
        self.ai = AI_Core()
    
    def generate_quiz(self, content, subject, chapter, difficulty, num_questions):
        """Sinh câu hỏi trắc nghiệm từ nội dung sách"""
        
        # Cắt nội dung nếu quá dài
        max_chars = 15000
        if len(content) > max_chars:
            content = content[:max_chars]
        
        # Map difficulty
        difficulty_map = {
            "Easy 😊": "dễ (kiến thức cơ bản)",
            "Medium 🤔": "trung bình (vận dụng)",
            "Hard 😰": "khó (tư duy cao)",
            "Expert 💀": "nâng cao (Olympic)"
        }
        
        difficulty_text = difficulty_map.get(difficulty, "trung bình")
        
        # Prompt cho AI
        prompt = f"""
Bạn là giáo viên giỏi môn {subject} lớp 8.

NỘI DUNG SÁCH:
{content}

NHIỆM VỤ:
Tạo {num_questions} câu hỏi trắc nghiệm 4 đáp án về {"Chương " + chapter if chapter != "ALL" else "toàn bộ môn học"}.

YÊU CẦU:
- Độ khó: {difficulty_text}
- Mỗi câu có 4 đáp án A, B, C, D
- CHỈ có 1 đáp án đúng
- Câu hỏi phải dựa trên nội dung sách
- Không hỏi chi tiết quá nhỏ

ĐỊNH DẠNG OUTPUT (JSON):
```json
[
  {{
    "question": "Câu hỏi 1?",
    "options": ["A. Đáp án A", "B. Đáp án B", "C. Đáp án C", "D. Đáp án D"],
    "correct_answer": "A. Đáp án A",
    "explanation": "Giải thích ngắn gọn"
  }},
  ...
]
```

BẮT BUỘC: Chỉ trả về JSON, không thêm text nào khác.
"""
        
        try:
            # Gọi AI
            response = self.ai.generate(
                prompt,
                model_type="pro",  # Dùng Pro cho chất lượng câu hỏi cao
                system_instruction="Bạn là hệ thống sinh câu hỏi tự động. Chỉ trả về JSON hợp lệ."
            )
            
            # Parse JSON
            # Loại bỏ markdown code block nếu có
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            quiz_data = json.loads(response)
            
            # Validate
            if isinstance(quiz_data, list) and len(quiz_data) > 0:
                return quiz_data
            else:
                st.error("❌ AI trả về format sai")
                return None
                
        except json.JSONDecodeError as e:
            st.error(f"❌ Lỗi parse JSON: {e}")
            st.code(response)  # Debug
            return None
        except Exception as e:
            st.error(f"❌ Lỗi tạo quiz: {e}")
            return None
