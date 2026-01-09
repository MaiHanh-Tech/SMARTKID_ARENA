# services/weakness_analyzer.py
from collections import defaultdict
from typing import Dict, List
import pandas as pd

class WeaknessAnalyzer:
    """
    Phân tích điểm yếu dựa trên:
    1. Accuracy per topic/concept
    2. Error patterns (lỗi lặp lại)
    3. Time efficiency
    4. Confidence vs correctness gap
    """
    
    def __init__(self, history_tracker: LearningHistoryTracker):
        self.tracker = history_tracker
    
    def analyze_by_topic(self) -> Dict[str, dict]:
        """
        [Inference] Phân tích theo chủ đề
        
        Returns:
            {
                'topic_name': {
                    'total_attempts': int,
                    'correct': int,
                    'accuracy': float,
                    'avg_time': float,
                    'weakness_level': str  # 'critical', 'needs_practice', 'good', 'mastered'
                }
            }
        """
        topic_stats = defaultdict(lambda: {
            'total': 0,
            'correct': 0,
            'times': []
        })
        
        # Duyệt qua tất cả attempts
        for session in self.tracker.data['sessions']:
            for attempt in session['attempts']:
                topic = attempt.get('topic', 'Unknown')
                topic_stats[topic]['total'] += 1
                if attempt['is_correct']:
                    topic_stats[topic]['correct'] += 1
                topic_stats[topic]['times'].append(attempt.get('time_spent', 0))
        
        # Tính toán metrics
        result = {}
        for topic, stats in topic_stats.items():
            accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
            avg_time = sum(stats['times']) / len(stats['times']) if stats['times'] else 0
            
            # Phân loại weakness level
            if accuracy < 0.5:
                weakness_level = 'critical'  # Cần tập trung ngay
            elif accuracy < 0.7:
                weakness_level = 'needs_practice'  # Cần luyện tập thêm
            elif accuracy < 0.9:
                weakness_level = 'good'  # Khá tốt
            else:
                weakness_level = 'mastered'  # Đã thành thạo
            
            result[topic] = {
                'total_attempts': stats['total'],
                'correct': stats['correct'],
                'accuracy': accuracy,
                'avg_time': avg_time,
                'weakness_level': weakness_level
            }
        
        return result
    
    def find_error_patterns(self) -> List[dict]:
        """
        [Inference] Tìm lỗi lặp lại
        
        VD: Bé hay nhầm phân số 2/3 với 3/2, hay quên dấu trong phép nhân...
        """
        # Phân tích các câu sai nhiều lần
        repeated_errors = []
        
        for q_id, attempts in self.tracker.data['question_bank'].items():
            wrong_attempts = [a for a in attempts if not a['is_correct']]
            
            if len(wrong_attempts) >= 2:  # Sai >= 2 lần
                # Phân tích pattern
                wrong_answers = [a['selected'] for a in wrong_attempts]
                
                repeated_errors.append({
                    'question_id': q_id,
                    'question': attempts[0]['question'],
                    'topic': attempts[0].get('topic', 'Unknown'),
                    'concept_tags': attempts[0].get('concept_tags', []),
                    'times_wrong': len(wrong_attempts),
                    'wrong_answers': wrong_answers,
                    'correct_answer': attempts[0]['correct_answer']
                })
        
        # Sắp xếp theo độ nghiêm trọng
        repeated_errors.sort(key=lambda x: x['times_wrong'], reverse=True)
        
        return repeated_errors
    
    def get_priority_topics(self, top_n: int = 5) -> List[str]:
        """
        [Inference] Trả về top N chủ đề cần ưu tiên
        
        Dựa trên:
        - Accuracy thấp
        - Số lần sai nhiều
        - Lỗi lặp lại
        """
        topic_analysis = self.analyze_by_topic()
        
        # Lọc các topic yếu (critical + needs_practice)
        weak_topics = [
            (topic, data) 
            for topic, data in topic_analysis.items() 
            if data['weakness_level'] in ['critical', 'needs_practice']
        ]
        
        # Sắp xếp theo accuracy tăng dần (yếu nhất trước)
        weak_topics.sort(key=lambda x: x[1]['accuracy'])
        
        return [topic for topic, _ in weak_topics[:top_n]]
