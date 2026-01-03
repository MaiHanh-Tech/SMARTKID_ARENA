import streamlit as st
from datetime import datetime, timedelta
from supabase_manager import SupabaseManager

class PlayerProfile:
    """Profile học sinh với XP, level, streak - Lưu vào Supabase"""
    
    def __init__(self, name="Player"):
        self.db = SupabaseManager()
        self.name = name
        self.player_id = None
        
        # Giá trị mặc định
        self.xp = 0
        self.level = 1
        self.total_score = 0
        self.streak = 0
        self.last_play_date = None
        self.badges = []
        
        # Load từ DB hoặc tạo mới
        self._load_or_create()
    
    def _load_or_create(self):
        """Load player từ DB, nếu không có thì tạo mới"""
        if not self.db.connected:
            st.warning("⚠️ Không kết nối DB. Dữ liệu sẽ mất khi reload.")
            return
        
        # Thử load
        player_data = self.db.get_player(self.name)
        
        if player_data:
            # Đã có trong DB
            self.player_id = player_data["id"]
            self.xp = player_data.get("xp", 0)
            self.level = player_data.get("level", 1)
            self.total_score = player_data.get("total_score", 0)
            self.streak = player_data.get("streak", 0)
            
            # Parse last_play_date
            if player_data.get("last_play_date"):
                self.last_play_date = datetime.fromisoformat(player_data["last_play_date"]).date()
            
            self.badges = player_data.get("badges", [])
            
            st.success(f"✅ Chào mừng trở lại, **{self.name}**!")
        else:
            # Chưa có → Tạo mới
            new_player = self.db.create_player(self.name)
            if new_player:
                self.player_id = new_player["id"]
                st.success(f"🎉 Tài khoản **{self.name}** đã được tạo!")
            else:
                st.error("❌ Không thể tạo tài khoản. Kiểm tra kết nối DB.")
    
    def _save_to_db(self):
        """Lưu thay đổi lên Supabase"""
        if not self.db.connected or not self.player_id:
            return
        
        updates = {
            "xp": self.xp,
            "level": self.level,
            "total_score": self.total_score,
            "streak": self.streak,
            "last_play_date": self.last_play_date.isoformat() if self.last_play_date else None,
            "badges": self.badges
        }
        
        self.db.update_player(self.player_id, updates)
    
    def add_xp(self, amount):
        """Thêm XP và tự động tính level"""
        self.xp += amount
        new_level = self._calculate_level()
        
        if new_level > self.level:
            st.success(f"🎊 LEVEL UP! Bạn đã lên Level {new_level}!")
            st.balloons()
            self.level = new_level
        
        # Lưu DB
        self._save_to_db()
    
    def _calculate_level(self):
        """Tính level từ XP (công thức: level = sqrt(xp/100))"""
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
            st.info(f"🔥 Streak: {self.streak} ngày liên tục!")
        else:
            self.streak = 1  # Mất streak
            st.warning("💔 Streak bị reset. Hãy chơi đều đặn hơn nhé!")
        
        self.last_play_date = today
        
        # Lưu DB
        self._save_to_db()
    
    def get_badges(self):
        """Lấy danh sách huy hiệu dựa trên thành tích"""
        badges = []
        
        # Huy hiệu XP
        if self.xp >= 100:
            badges.append("🌟")  # Novice
        if self.xp >= 500:
            badges.append("💫")  # Apprentice
        if self.xp >= 1000:
            badges.append("✨")  # Expert
        if self.xp >= 2500:
            badges.append("🏅")  # Master
        if self.xp >= 5000:
            badges.append("👑")  # Legend
        
        # Huy hiệu Streak
        if self.streak >= 3:
            badges.append("🔥")  # 3 Day
        if self.streak >= 7:
            badges.append("💪")  # Week Warrior
        if self.streak >= 30:
            badges.append("🦾")  # Month Master
        
        # Huy hiệu điểm
        if self.total_score >= 200:
            badges.append("🏆")  # High Scorer
        if self.total_score >= 500:
            badges.append("💎")  # Diamond
        
        return badges
