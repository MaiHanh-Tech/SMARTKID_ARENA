"""
Adaptive Quiz Engine
Sinh quiz thông minh dựa trên điểm yếu và lịch sử học tập
"""
import random
from typing import List, Dict, Optional


class AdaptiveQuizEngine:
    """
    Quiz Engine thích ứng với học sinh:
    - Ưu tiên câu hỏi về chủ đề yếu
    - Tránh lặp lại câu đã làm gần đây
    - Điều chỉnh độ khó dựa trên performance
    - Cân bằng giữa ôn tập và học mới
    """
    
    def __init__(self, weakness_analyzer, base_quiz_engine):
        """
        Args:
            weakness_analyzer: Instance của WeaknessAnalyzer
            base_quiz_engine: Instance của QuizEngine gốc (để gọi AI)
        """
        self.analyzer = weakness_analyzer
        self.base_engine = base_quiz_engine
    
    def generate_adaptive_quiz(
        self,
        content: str,
        subject: str,
        chapter: str = "ALL",
        num_questions: int = 10,
        focus_mode: str = "adaptive"
    ) -> List[dict]:
        """
        [Inference] Sinh quiz thích ứng với học sinh
        
        Args:
            content: Nội dung sách/tài liệu
            subject: Môn học
            chapter: Chương (hoặc "ALL")
            num_questions: Số câu hỏi
            focus_mode:
                - 'adaptive': 70% câu yếu + 30% câu tổng hợp
                - 'review_weak': 100% câu về chủ đề yếu
                - 'mixed': 50-50
                - 'challenge': 100% câu khó ở chủ đề giỏi
        
        Returns:
            List of question dicts
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
        elif focus_mode == "challenge":
            num_weak = 0
            num_general = num_questions
        else:  # mixed
            num_weak = num_questions // 2
            num_general = num_questions - num_weak
        
        all_questions = []
        
        # 3. Sinh câu hỏi cho chủ đề yếu
        if num_weak > 0 and priority_topics:
            weak_questions = self._generate_weakness_focused_quiz(
                content=content,
                subject=subject,
                chapter=chapter,
                priority_topics=priority_topics,
                error_patterns=error_patterns,
                num_questions=num_weak
            )
            all_questions.extend(weak_questions)
        
        # 4. Sinh câu hỏi tổng hợp
        if num_general > 0:
            # Lấy độ khó phù hợp
            if focus_mode == "challenge":
                difficulty = "Hard 😰"
            else:
                # Lấy độ khó trung bình của học sinh
                difficulty = self._get_recommended_difficulty(subject)
            
            general_questions = self.base_engine.generate_quiz(
                content=content,
                subject=subject,
                chapter=chapter,
                difficulty=difficulty,
                num_questions=num_general
            )
            all_questions.extend(general_questions)
        
        # 5. Shuffle (trộn câu hỏi)
        random.shuffle(all_questions)
        
        # 6. Thêm metadata cho tracking
        for i, q in enumerate(all_questions):
            q['question_id'] = f"{subject}_{chapter}_q{i}_{hash(q['question']) % 10000}"
            q['subject'] = subject
            q['chapter'] = chapter
        
        return all_questions
    
    def _generate_weakness_focused_quiz(
        self,
        content: str,
        subject: str,
        chapter: str,
        priority_topics: List[str],
        error_patterns: List[dict],
        num_questions: int
    ) -> List[dict]:
        """
        [Inference] Sinh câu hỏi tập trung vào điểm yếu
        
        Strategy:
        1. 50% câu hỏi về topics yếu nhất (từ priority_topics)
        2. 30% câu hỏi dạng tương tự những câu đã sai (từ error_patterns)
        3. 20% câu hỏi về concepts hay nhầm lẫn
        """
        # Chuẩn bị prompt cho AI
        weak_topics_str = ", ".join(priority_topics[:3])
        
        # Lấy các câu đã sai để tránh trùng lặp
        recent_wrong_questions = [e['question'][:50] for e in error_patterns[:5]]
        
        # Lấy độ khó phù hợp cho topic yếu nhất
        difficulty = self.analyzer.get_recommended_difficulty(priority_topics[0])
        
        # Tạo prompt đặc biệt
        prompt = self._build_weakness_prompt(
            content=content,
            weak_topics=weak_topics_str,
            recent_errors=recent_wrong_questions,
            num_questions=num_questions
        )
        
        # Gọi AI để sinh câu hỏi
        # [Unverified] Cần implement với AI API thực tế
        questions = self.base_engine._call_ai_with_prompt(
            prompt=prompt,
            num_questions=num_questions,
            subject=subject,
            difficulty=difficulty
        )
        
        # Thêm metadata
        for q in questions:
            q['topic'] = priority_topics[0]  # Assign topic chính
            q['difficulty'] = difficulty
            q['is_weakness_focused'] = True
        
        return questions
    
    def _build_weakness_prompt(
        self,
        content: str,
        weak_topics: str,
        recent_errors: List[str],
        num_questions: int
    ) -> str:
        """
        [Inference] Tạo prompt đặc biệt cho AI
        
        Hướng dẫn AI:
        - Tập trung vào topics yếu
        - Tránh trùng câu đã làm
        - Đa dạng góc nhìn (khái niệm, tính toán, ứng dụng)
        """
        prompt = f"""
Sinh {num_questions} câu hỏi trắc nghiệm để rèn luyện học sinh ở các chủ đề đang YẾU:
{weak_topics}

YÊU CẦU QUAN TRỌNG:
1. Câu hỏi phải đa dạng:
   - Khái niệm cơ bản (30%)
   - Tính toán áp dụng (40%)
   - Tư duy phản biện/so sánh (30%)

2. Độ khó: Từ dễ đến trung bình (để học sinh tự tin)

3. TUYỆT ĐỐI TRÁNH trùng với các câu đã sai gần đây:
{chr(10).join(f"   - {q}" for q in recent_errors) if recent_errors else "   (Chưa có lỗi nào)"}

4. Mỗi câu hỏi cần:
   - Gắn tag concept cụ thể (VD: ['phân số', 'so sánh'])
   - Có lời giải ngắn gọn
   - 4 đáp án, chỉ 1 đúng

NỘI DUNG THAM KHẢO (Trích từ sách):
{content[:5000]}

Trả về JSON format:
[
  {{
    "question": "...",
    "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
    "correct_answer": "A. ...",
    "explanation": "...",
    "concept_tags": ["tag1", "tag2"],
    "topic": "tên topic"
  }}
]
"""
        return prompt
    
    def _call_ai_with_prompt(
        self,
        prompt: str,
        num_questions: int,
        subject: str,
        difficulty: str
    ) -> List[dict]:
        """
        [Inference] Gọi AI thông qua base_engine
        
        Note: Hàm này delegate việc gọi AI cho QuizEngine gốc
        """
        try:
            # Check xem base_engine có method generate_adaptive_quiz không
            if hasattr(self.base_engine, 'generate_adaptive_quiz'):
                # Dùng method chuyên biệt cho adaptive (mới nhất)
                return self.base_engine.generate_adaptive_quiz(
                    content=prompt,
                    subject=subject,
                    weak_topics=[],  # Đã có trong prompt
                    recent_errors=[],  # Đã có trong prompt
                    num_questions=num_questions,
                    difficulty=difficulty
                )
            else:
                # Fallback: Dùng generate_quiz thông thường với chapter="ADAPTIVE"
                return self.base_engine.generate_quiz(
                    content=prompt,  # Pass prompt như content
                    subject=subject,
                    chapter="ADAPTIVE",  # Đánh dấu là adaptive mode
                    difficulty=difficulty,
                    num_questions=num_questions
                )
        
        except Exception as e:
            print(f"⚠️ Lỗi gọi AI: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_recommended_difficulty(self, subject: str) -> str:
        """
        [Inference] Đề xuất độ khó cho quiz tổng hợp
        
        Dựa trên accuracy trung bình của tất cả topics trong môn học này
        """
        topic_stats = self.analyzer.analyze_by_topic()
        
        # Lọc topics của môn này
        subject_topics = {
            topic: data 
            for topic, data in topic_stats.items() 
            if data.get('total_attempts', 0) > 0
        }
        
        if not subject_topics:
            return "Medium 🤔"  # Default
        
        # Tính accuracy trung bình
        avg_accuracy = sum(
            data['accuracy'] for data in subject_topics.values()
        ) / len(subject_topics)
        
        # Mapping
        if avg_accuracy >= 0.85:
            return "Hard 😰"
        elif avg_accuracy >= 0.7:
            return "Medium 🤔"
        else:
            return "Easy 😊"
    
    def get_next_question_difficulty(
        self,
        current_streak: int,
        recent_accuracy: float
    ) -> str:
        """
        [Inference] Điều chỉnh độ khó động theo performance real-time
        
        Args:
            current_streak: Số câu đúng liên tiếp
            recent_accuracy: Accuracy của 5 câu gần nhất
        
        Returns:
            Độ khó cho câu tiếp theo
        
        Logic (Flow Theory - Csikszentmihalyi):
        - Đúng nhiều liên tiếp → Tăng độ khó
        - Sai nhiều → Giảm độ khó
        - Giữ trong "flow zone"
        """
        if current_streak >= 5 and recent_accuracy >= 0.8:
            # Đang "on fire" → Thử thách cao hơn
            return "Expert 💀"
        elif current_streak >= 3 and recent_accuracy >= 0.7:
            return "Hard 😰"
        elif recent_accuracy >= 0.5:
            return "Medium 🤔"
        else:
            # Đang struggle → Dễ hơn để tự tin
            return "Easy 😊"
    
    def should_insert_review_question(
        self,
        questions_answered: int,
        interval: int = 5
    ) -> bool:
        """
        [Inference] Quyết định có nên chèn câu ôn tập không
        
        Spaced Repetition: Mỗi N câu, chèn 1 câu ôn lại topic cũ
        
        Args:
            questions_answered: Số câu đã làm
            interval: Chèn mỗi N câu
        
        Returns:
            True nếu nên chèn câu ôn tập
        """
        return questions_answered > 0 and questions_answered % interval == 0
    
    def generate_review_question(
        self,
        content: str,
        subject: str
    ) -> Optional[dict]:
        """
        [Inference] Sinh câu hỏi ôn tập từ topic đã học lâu
        
        Strategy:
        - Lấy topic đã học > 3 ngày
        - Accuracy từng cao (đã thành thạo)
        - Giờ cần ôn lại để không quên
        
        Returns:
            Question dict hoặc None
        """
        # Lấy lịch ôn tập
        topic_stats = self.analyzer.analyze_by_topic()
        
        # Tìm topics đã thành thạo (để ôn)
        mastered_topics = [
            topic for topic, data in topic_stats.items()
            if data['weakness_level'] == 'mastered'
        ]
        
        if not mastered_topics:
            return None
        
        # Random pick 1 topic
        topic = random.choice(mastered_topics)
        
        # Sinh câu hỏi dễ-trung bình
        questions = self.base_engine.generate_quiz(
            content=content,
            subject=subject,
            chapter="ALL",
            difficulty="Easy 😊",
            num_questions=1
        )
        
        if questions:
            q = questions[0]
            q['topic'] = topic
            q['is_review'] = True
            return q
        
        return None
    
    def adjust_quiz_on_the_fly(
        self,
        remaining_questions: List[dict],
        current_performance: Dict
    ) -> List[dict]:
        """
        [Unverified] Điều chỉnh quiz đang làm dở dựa trên performance
        
        VD: Nếu học sinh đang làm quá tốt → Tăng độ khó của các câu còn lại
        
        Args:
            remaining_questions: Các câu chưa làm
            current_performance: {
                'streak': int,
                'accuracy': float,
                'avg_time': float
            }
        
        Returns:
            Adjusted question list
        
        Note: Feature nâng cao, chưa implement đầy đủ
        """
        # TODO: Implement real-time adjustment
        return remaining_questions
