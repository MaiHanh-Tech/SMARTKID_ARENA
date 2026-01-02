import streamlit as st
from datetime import datetime, timedelta

class GameMechanics:
    """Quản lý điểm, level, achievements"""
    
    @staticmethod
    def calculate_level(xp):
        """Tính level từ XP (công thức: level = sqrt(xp/100))"""
        import math
        return int(math.sqrt(xp / 100)) + 1
    
    @staticmethod
    def xp_for_next_level(current_level):
        """XP cần để lên level tiếp theo"""
        return (current_level ** 2) * 100
    
    @staticmethod
    def check_achievements(player):
        """Kiểm tra và trao huy hiệu"""
        badges = []
        
        # Huy hiệu XP
        if player.xp >= 1000:
            badges.append("🌟")  # Novice
        if player.xp >= 5000:
            badges.append("💫")  # Expert
        if player.xp >= 10000:
            badges.append("✨")  # Master
        
        # Huy hiệu Streak
        if player.streak >= 7:
            badges.append("🔥")  # Week Warrior
        if player.streak >= 30:
            badges.append("💪")  # Month Master
        
        # Huy hiệu điểm
        if player.total_score >= 1000:
            badges.append("🏆")  # High Scorer
        
        return badges
    
    @staticmethod
    def get_rank(level):
        """Lấy rank title theo level"""
        if level < 5:
            return "🥉 Tân Binh"
        elif level < 10:
            return "🥈 Chiến Binh"
        elif level < 20:
            return "🥇 Cao Thủ"
        elif level < 50:
            return "💎 Đại Cao Thủ"
        else:
            return "👑 Huyền Thoại"
