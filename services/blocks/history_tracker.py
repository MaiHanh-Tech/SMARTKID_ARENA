# services/history_tracker.py
import json
from datetime import datetime
from pathlib import Path

class LearningHistoryTracker:
    """
    Lưu trữ mọi hành vi học tập:
    - Mỗi câu hỏi được trả lời
    - Thời gian suy nghĩ
    - Độ tin cậy khi chọn đáp án
    - Lỗi lặp lại
    """
    
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.history_file = Path(f"data/students/{student_id}/history.json")
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_history()
    
    def load_history(self):
        """[Inference] Đọc lịch sử từ file JSON"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {
                "student_id": self.student_id,
                "sessions": [],
                "question_bank": {}  # question_id -> attempts list
            }
    
    def log_answer(self, session_id: str, question_data: dict, answer_data: dict):
        """
        Ghi lại 1 lần trả lời
        
        Args:
            session_id: ID của buổi học
            question_data: {
                'question_id': str,
                'question': str,
                'subject': str,
                'chapter': str,
                'topic': str,  # Thêm phân loại chi tiết
                'difficulty': str,
                'concept_tags': list  # VD: ['phân số', 'so sánh', 'bài toán thực tế']
            }
            answer_data: {
                'selected': str,
                'correct_answer': str,
                'is_correct': bool,
                'time_spent': float,  # seconds
                'confidence': str  # 'high', 'medium', 'low' (từ UI)
            }
        """
        attempt = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            **question_data,
            **answer_data
        }
        
        # Thêm vào session hiện tại
        session = next((s for s in self.data['sessions'] if s['id'] == session_id), None)
        if not session:
            session = {
                "id": session_id,
                "start_time": datetime.now().isoformat(),
                "attempts": []
            }
            self.data['sessions'].append(session)
        
        session['attempts'].append(attempt)
        
        # Thêm vào question bank (để track lịch sử của từng câu hỏi)
        q_id = question_data['question_id']
        if q_id not in self.data['question_bank']:
            self.data['question_bank'][q_id] = []
        self.data['question_bank'][q_id].append(attempt)
        
        self.save_history()
    
    def save_history(self):
        """Lưu lịch sử vào file"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)


    def get_overall_stats(self):
        total_questions = 0
        correct_count = 0

        # Duyệt qua tất cả các session
        for session in self.data.get("sessions", []):
            for attempt in session.get("attempts", []):
                total_questions += 1
                if attempt.get("is_correct", False):
                    correct_count += 1

        accuracy = (correct_count / total_questions * 100) if total_questions > 0 else 0.0

        return {
            "total_questions": total_questions,
            "correct_count": correct_count,    # optional, có thể thêm
            "accuracy": accuracy
        }
