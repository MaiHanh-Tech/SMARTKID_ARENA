"""
Weakness Analyzer
Phân tích điểm yếu và pattern lỗi của học sinh
"""
from collections import defaultdict
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


class WeaknessAnalyzer:
    """
    Phân tích điểm yếu dựa trên:
    1. Accuracy theo topic/concept
    2. Error patterns (lỗi lặp lại)
    3. Time efficiency
    4. Confidence vs correctness gap
    5. Forgetting curve (độ quên theo thời gian)
    """
    
    def __init__(self, history_tracker):
        """
        Args:
            history_tracker: Instance của LearningHistoryTracker
        """
        self.tracker = history_tracker
    
    def analyze_by_topic(self) -> Dict[str, dict]:
        """
        [Inference] Phân tích performance theo topic
        
        Returns:
            {
                'topic_name': {
                    'total_attempts': int,
                    'correct': int,
                    'accuracy': float (0-1),
                    'avg_time': float (seconds),
                    'weakness_level': str,  # 'critical', 'needs_practice', 'good', 'mastered'
                    'recent_trend': str  # 'improving', 'declining', 'stable'
                }
            }
        """
        topic_stats = defaultdict(lambda: {
            'total': 0,
            'correct': 0,
            'times': [],
            'attempts_by_date': []  # Để tính trend
        })
        
        # Thu thập data từ tất cả sessions
        for session in self.tracker.data['sessions']:
            for attempt in session['attempts']:
                topic = attempt.get('topic', 'Unknown')
                
                topic_stats[topic]['total'] += 1
                
                if attempt['is_correct']:
                    topic_stats[topic]['correct'] += 1
                
                topic_stats[topic]['times'].append(
                    attempt.get('time_spent', 0)
                )
                
                topic_stats[topic]['attempts_by_date'].append({
                    'timestamp': attempt['timestamp'],
                    'correct': attempt['is_correct']
                })
        
        # Tính toán metrics cho mỗi topic
        result = {}
        
        for topic, stats in topic_stats.items():
            total = stats['total']
            correct = stats['correct']
            accuracy = correct / total if total > 0 else 0
            avg_time = sum(stats['times']) / len(stats['times']) if stats['times'] else 0
            
            # Phân loại weakness level
            weakness_level = self._classify_weakness_level(accuracy, total)
            
            # Phân tích trend (cải thiện/thoái lui)
            recent_trend = self._analyze_trend(stats['attempts_by_date'])
            
            result[topic] = {
                'total_attempts': total,
                'correct': correct,
                'accuracy': accuracy,
                'avg_time': avg_time,
                'weakness_level': weakness_level,
                'recent_trend': recent_trend
            }
        
        return result
    
    def _classify_weakness_level(self, accuracy: float, total_attempts: int) -> str:
        """
        [Inference] Phân loại mức độ yếu/giỏi
        
        Logic:
        - Cần ít nhất 3 câu để đánh giá
        - < 50%: Critical (cần tập trung ngay)
        - 50-70%: Needs practice
        - 70-90%: Good
        - >= 90%: Mastered
        """
        if total_attempts < 3:
            return 'insufficient_data'
        
        if accuracy < 0.5:
            return 'critical'
        elif accuracy < 0.7:
            return 'needs_practice'
        elif accuracy < 0.9:
            return 'good'
        else:
            return 'mastered'
    
    def _analyze_trend(self, attempts_by_date: List[dict]) -> str:
        """
        [Inference] Phân tích xu hướng tiến bộ
        
        So sánh accuracy của 50% attempts đầu vs 50% cuối
        """
        if len(attempts_by_date) < 4:
            return 'insufficient_data'
        
        # Sort theo timestamp
        attempts_by_date.sort(key=lambda x: x['timestamp'])
        
        # Chia đôi
        mid = len(attempts_by_date) // 2
        first_half = attempts_by_date[:mid]
        second_half = attempts_by_date[mid:]
        
        # Tính accuracy
        first_accuracy = sum(1 for a in first_half if a['correct']) / len(first_half)
        second_accuracy = sum(1 for a in second_half if a['correct']) / len(second_half)
        
        # So sánh
        diff = second_accuracy - first_accuracy
        
        if diff > 0.15:  # Tăng > 15%
            return 'improving'
        elif diff < -0.15:  # Giảm > 15%
            return 'declining'
        else:
            return 'stable'
    
    def find_error_patterns(self) -> List[dict]:
        """
        [Inference] Tìm lỗi lặp lại
        
        Phân tích:
        - Câu nào bị sai nhiều lần
        - Đáp án sai nào được chọn nhiều nhất
        - Concept nào hay bị nhầm
        
        Returns:
            List of {
                'question_id': str,
                'question': str,
                'topic': str,
                'concept_tags': list,
                'times_wrong': int,
                'wrong_answers': list,
                'correct_answer': str,
                'last_wrong_date': str
            }
        """
        repeated_errors = []
        
        for q_id, attempts in self.tracker.data['question_bank'].items():
            # Lọc các lần sai
            wrong_attempts = [a for a in attempts if not a['is_correct']]
            
            if len(wrong_attempts) >= 2:  # Sai >= 2 lần
                # Thu thập info
                first_attempt = attempts[0]  # Lấy metadata từ lần đầu
                
                repeated_errors.append({
                    'question_id': q_id,
                    'question': first_attempt['question'],
                    'topic': first_attempt.get('topic', 'Unknown'),
                    'concept_tags': first_attempt.get('concept_tags', []),
                    'times_wrong': len(wrong_attempts),
                    'total_attempts': len(attempts),
                    'wrong_answers': [a['selected'] for a in wrong_attempts],
                    'correct_answer': first_attempt['correct_answer'],
                    'last_wrong_date': wrong_attempts[-1]['timestamp']
                })
        
        # Sắp xếp theo độ nghiêm trọng (sai nhiều nhất trước)
        repeated_errors.sort(key=lambda x: x['times_wrong'], reverse=True)
        
        return repeated_errors
    
    def analyze_concept_confusion(self) -> Dict[str, List[str]]:
        """
        [Inference] Phân tích concept nào hay bị nhầm lẫn
        
        VD: Học sinh hay nhầm "2/3" với "3/2", ">" với "<"
        
        Returns:
            {
                'concept_1': ['concept_2', 'concept_3'],  # Concepts hay bị nhầm
                ...
            }
        """
        # TODO: Cần NLP để extract concepts từ câu hỏi/đáp án
        # Hiện tại chỉ dựa vào concept_tags
        
        confusion_matrix = defaultdict(set)
        
        errors = self.find_error_patterns()
        
        for error in errors:
            concepts = error.get('concept_tags', [])
            
            # Nếu có >= 2 concepts trong 1 câu → Có thể bị nhầm
            if len(concepts) >= 2:
                for i, c1 in enumerate(concepts):
                    for c2 in concepts[i+1:]:
                        confusion_matrix[c1].add(c2)
                        confusion_matrix[c2].add(c1)
        
        # Convert set → list
        return {k: list(v) for k, v in confusion_matrix.items()}
    
    def get_priority_topics(self, top_n: int = 5) -> List[str]:
        """
        [Inference] Trả về top N topics cần ưu tiên
        
        Dựa trên:
        1. Accuracy thấp
        2. Số lần sai nhiều
        3. Trend đang thoái lui
        
        Returns:
            List of topic names (sorted by priority)
        """
        topic_analysis = self.analyze_by_topic()
        
        # Tính priority score cho mỗi topic
        scored_topics = []
        
        for topic, data in topic_analysis.items():
            if data['weakness_level'] == 'insufficient_data':
                continue
            
            # Base score: Càng accuracy thấp càng quan trọng
            priority_score = 1 - data['accuracy']
            
            # Bonus nếu đang thoái lui
            if data['recent_trend'] == 'declining':
                priority_score += 0.3
            
            # Bonus nếu là critical
            if data['weakness_level'] == 'critical':
                priority_score += 0.5
            
            scored_topics.append((topic, priority_score))
        
        # Sắp xếp theo score giảm dần
        scored_topics.sort(key=lambda x: x[1], reverse=True)
        
        # Trả về top N topic names
        return [topic for topic, score in scored_topics[:top_n]]
    
    def get_recommended_difficulty(self, topic: str) -> str:
        """
        [Inference] Đề xuất độ khó phù hợp cho topic
        
        Dựa trên Zone of Proximal Development (Vygotsky):
        - Không quá dễ (boring)
        - Không quá khó (frustrating)
        
        Returns:
            'Easy 😊', 'Medium 🤔', 'Hard 😰', 'Expert 💀'
        """
        topic_stats = self.analyze_by_topic()
        
        if topic not in topic_stats:
            return 'Medium 🤔'  # Default
        
        accuracy = topic_stats[topic]['accuracy']
        
        # Logic mapping
        if accuracy >= 0.9:
            return 'Hard 😰'  # Đã giỏi → Thử khó hơn
        elif accuracy >= 0.7:
            return 'Medium 🤔'  # Khá tốt → Giữ mức vừa
        elif accuracy >= 0.5:
            return 'Easy 😊'  # Còn yếu → Dễ trước
        else:
            return 'Easy 😊'  # Rất yếu → Phải dễ
    
    def get_spaced_repetition_schedule(self, topic: str) -> Dict[str, str]:
        """
        [Inference] Tính lịch ôn tập theo Spaced Repetition
        
        Công thức Ebbinghaus:
        - Lần 1: Sau 1 ngày
        - Lần 2: Sau 3 ngày
        - Lần 3: Sau 7 ngày
        - Lần 4: Sau 14 ngày
        
        Returns:
            {
                'next_review': str (ISO date),
                'review_count': int,
                'mastery_level': str
            }
        """
        # Tìm lần làm gần nhất của topic này
        last_attempt = None
        
        for session in self.tracker.data['sessions']:
            for attempt in session['attempts']:
                if attempt.get('topic') == topic:
                    if not last_attempt or attempt['timestamp'] > last_attempt['timestamp']:
                        last_attempt = attempt
        
        if not last_attempt:
            return {
                'next_review': 'now',
                'review_count': 0,
                'mastery_level': 'not_started'
            }
        
        # Đếm số lần ôn tập (coi mỗi session là 1 lần)
        review_count = sum(
            1 for s in self.tracker.data['sessions']
            if any(a.get('topic') == topic for a in s['attempts'])
        )
        
        # Tính ngày ôn tiếp theo
        last_date = datetime.fromisoformat(last_attempt['timestamp'])
        
        if review_count == 1:
            next_date = last_date + timedelta(days=1)
        elif review_count == 2:
            next_date = last_date + timedelta(days=3)
        elif review_count == 3:
            next_date = last_date + timedelta(days=7)
        else:
            next_date = last_date + timedelta(days=14)
        
        # Check mastery
        topic_stats = self.analyze_by_topic()
        mastery = topic_stats.get(topic, {}).get('weakness_level', 'unknown')
        
        return {
            'next_review': next_date.isoformat(),
            'review_count': review_count,
            'mastery_level': mastery
        }
    
    def get_time_efficiency_analysis(self) -> Dict[str, dict]:
        """
        [Inference] Phân tích hiệu quả thời gian
        
        Tìm những topic nào:
        - Mất thời gian nhiều nhưng accuracy thấp → Cần học lại
        - Mất thời gian ít và accuracy cao → Đã thành thạo
        
        Returns:
            {
                'topic': {
                    'avg_time': float,
                    'accuracy': float,
                    'efficiency_score': float,  # accuracy / time
                    'status': str  # 'efficient', 'struggling', 'needs_practice'
                }
            }
        """
        topic_stats = self.analyze_by_topic()
        
        result = {}
        
        for topic, data in topic_stats.items():
            avg_time = data['avg_time']
            accuracy = data['accuracy']
            
            # Tránh chia cho 0
            if avg_time > 0:
                efficiency = accuracy / avg_time
            else:
                efficiency = 0
            
            # Phân loại status
            if accuracy >= 0.8 and avg_time < 30:  # 30s = baseline
                status = 'efficient'
            elif accuracy < 0.6 and avg_time > 60:
                status = 'struggling'
            else:
                status = 'needs_practice'
            
            result[topic] = {
                'avg_time': avg_time,
                'accuracy': accuracy,
                'efficiency_score': efficiency,
                'status': status
            }
        
        return result
    
    def generate_study_plan(self, days: int = 7) -> List[Dict]:
        """
        [Inference] Sinh kế hoạch học tập cho N ngày tới
        
        Args:
            days: Số ngày lên kế hoạch
        
        Returns:
            List of {
                'date': str,
                'topics': list,
                'focus': str,  # 'review_weak', 'spaced_repetition', 'new_material'
                'recommended_duration': int  # minutes
            }
        """
        priority_topics = self.get_priority_topics(top_n=5)
        
        plan = []
        
        for i in range(days):
            date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            
            if i % 3 == 0:  # Mỗi 3 ngày: Ôn điểm yếu
                plan.append({
                    'date': date,
                    'topics': priority_topics[:2],
                    'focus': 'review_weak',
                    'recommended_duration': 30
                })
            elif i % 3 == 1:  # Spaced repetition
                # TODO: Lấy topics cần ôn theo lịch
                plan.append({
                    'date': date,
                    'topics': ['Review previous lessons'],
                    'focus': 'spaced_repetition',
                    'recommended_duration': 20
                })
            else:  # Học mới
                plan.append({
                    'date': date,
                    'topics': ['New chapter'],
                    'focus': 'new_material',
                    'recommended_duration': 40
                })
        
        return plan
