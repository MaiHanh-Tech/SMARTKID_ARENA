import streamlit as st
from datetime import datetime, timedelta
import json

class PlayerProfile:
    """Profile học sinh với XP, level, streak"""
    
    def __init__(self, name="Player"):
        self.name = name
        self.xp = 0
        self.level = 1
        self.total_score = 0
        self.streak = 0
        self.last_play_date = None
        self.badges = []
        
        # Load từ session nếu có
        self._load_from_session()
    
    def _load_from_session(self):
        """Load dữ liệu từ st.session_state"""
        if "player_data" in st.session_state:
            data = st.session_state.player_data
            self.xp = data.get("xp", 0)
            self.level = data.get("level", 1)
            self.total_score = data.get("total_score", 0)
            self.streak = data.get("streak", 0)
            self.last_play_date = data.get("last_play_date")
            self.badges = data.get("badges", [])
    
    def _save_to_session(self):
        """Lưu vào st.session_state"""
        st.session_state.player_data = {
            "xp": self.xp,
            "level": self.level,
            "total_score": self.total_score,
            "streak": self.streak,
            "last_play_date": self.last_play_date,
            "badges": self.badges
        }
    
    def add_xp(self, amount):
        """Thêm XP và tự động tính level"""
        self.xp += amount
        new_level = self._calculate_level()
        
        if new_level > self.level:
            st.success(f"🎊 LEVEL UP! Bạn đã lên Level {new_level}!")
            st.balloons()
            self.level = new_level
        
        self._save_to_session()
    
    def _calculate_level(self):
        """Tính level từ XP"""
        import math
        return int(math.sqrt(self.xp / 100)) + 1
    
    def xp_to_next_level(self):
        """XP cần để lên level kế tiếp"""
        return (self.level ** 2) * 100
    
    def update_streak(self):
        """Cập nhật streak (chuỗi ngày chơi liên tục)"""
        today = datetime.now().date()
        
        if self.last_play_date is None:
            self.streak = 1
        elif self.last_play_date == today:
            pass  # Đã chơi hôm nay rồi
        elif self.last_play_date == today - timedelta(days=1):
            self.streak += 1  # Tiếp tục streak
        else:
            self.streak = 1  # Mất streak
        
        self.last_play_date = today
        self._save_to_session()
    
    def get_badges(self):
        """Lấy danh sách huy hiệu"""
        badges = []
        
        # Huy hiệu XP
        if self.xp >= 500:
            badges.append("🌟")
        if self.xp >= 2000:
            badges.append("💫")
        if self.xp >= 5000:
            badges.append("✨")
        
        # Huy hiệu Streak
        if self.streak >= 3:
            badges.append("🔥")
        if self.streak >= 7:
            badges.append("💪")
        
        # Huy hiệu điểm
        if self.total_score >= 500:
            badges.append("🏆")
        
        return badges
