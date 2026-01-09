# services/adaptive_quiz_engine.py
from quiz_engine import QuizEngine
from weakness_analyzer import WeaknessAnalyzer
import random

class AdaptiveQuizEngine(QuizEngine):
    """
    Quiz Engine thông minh:
    - Ưu tiên câu hỏi về chủ đề yếu
    - Tránh lặp lại câu đã làm gần đây
    - Điều chỉnh độ khó dựa trên hiệu suất
    """
    
    def __init__(self, weakness_analyzer: WeaknessAnalyzer):
        super().__init__()
        self.analyzer = weakness_analyzer
    
    def generate_adaptive_quiz(
        self,
        content: str,
        subject: str,
        num_questions: int = 10,
        focus_mode: str = "adaptive"  # 'adaptive', 'review_weak', 'mixed'
    ) -> List[dict]:
        """
        [Inference] Sinh quiz thích ứng
        
        Args:
            focus_mode:
                - 'adaptive': 70% câu yếu + 30% câu tổng hợp
                - 'review_weak': 100% câu về chủ đề yếu
                - 'mixed': 50-50
        """
        # 1. Phân tích điểm yếu
        priority_topics = self.analyzer.get_priority_topics(top_n=5)
        error_patterns = self.analyzer.find_error_patterns()
        
        # 2. Xác định tỉ lệ câu hỏi
        if focus_mode == "adaptive":
            num_weak = int(num_questions * 0.7)
            num_general = num_questions - num_weak
        elif focus_mode == "review_weak":
            num_weak = num_questions
            num_general = 0
        else:  # mixed
            num_weak = num_questions // 2
            num_general = num_questions - num_weak
        
        # 3. Sinh câu hỏi cho chủ đề yếu
        weak_questions = []
        if num_weak > 0 and priority_topics:
            # Prompt đặc biệt cho AI
            weak_topics_str = ", ".join(priority_topics)
            
            prompt = f"""
Sinh {num_weak} câu hỏi tập trung vào các chủ đề học sinh đang YẾU:
{weak_topics_str}

Lưu ý:
- Câu hỏi phải đa dạng góc nhìn (so sánh, tính toán, ứng dụng thực tế)
- Độ khó: Medium-Hard (để rèn luyện)
- Tránh trùng với các câu đã sai gần đây: {[e['question'] for e in error_patterns[:3]]}

Nội dung tham khảo:
{content[:3000]}  # Giới hạn token
"""
            
            weak_questions = self._call_ai_to_generate(prompt, num_weak)
        
        # 4. Sinh câu hỏi tổng hợp
        general_questions = []
        if num_general > 0:
            general_questions = self.generate_quiz(
                content=content,
                subject=subject,
                chapter="ALL",
                difficulty="Medium 🤔",
                num_questions=num_general
            )
        
        # 5. Trộn và shuffle
        all_questions = weak_questions + general_questions
        random.shuffle(all_questions)
        
        return all_questions
    
    def _call_ai_to_generate(self, prompt: str, num_questions: int) -> List[dict]:
        """
        [Unverified] Gọi AI để sinh câu hỏi (cần implement với Claude API)
        
        Note: Hàm này cần được implement với Claude API thực tế
        """
        # TODO: Implement với Claude API
        # Tạm thời return empty list
        return []
