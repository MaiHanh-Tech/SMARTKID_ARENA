import streamlit as st
from supabase import create_client, Client
from datetime import datetime, date

class SupabaseManager:
    """Quản lý kết nối và thao tác với Supabase"""
    
    def __init__(self):
        self.connected = False
        self.client = None
        
        try:
            if "supabase" in st.secrets:
                url = st.secrets["supabase"]["url"]
                key = st.secrets["supabase"]["key"]
                self.client: Client = create_client(url, key)
                self.connected = True
            else:
                st.warning("⚠️ Chưa cấu hình Supabase trong secrets.toml")
        except Exception as e:
            st.error(f"❌ Lỗi kết nối Supabase: {e}")
    
    def get_player(self, name):
        """Lấy thông tin player theo tên"""
        if not self.connected:
            return None
        
        try:
            response = self.client.table("players").select("*").eq("name", name).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            st.error(f"❌ Lỗi lấy player: {e}")
            return None
    
    def create_player(self, name):
        """Tạo player mới"""
        if not self.connected:
            return None
        
        try:
            data = {
                "name": name,
                "xp": 0,
                "level": 1,
                "total_score": 0,
                "streak": 0,
                "last_play_date": None,
                "badges": []
            }
            response = self.client.table("players").insert(data).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            st.error(f"❌ Lỗi tạo player: {e}")
            return None
    
    def update_player(self, player_id, updates):
        """Cập nhật thông tin player"""
        if not self.connected:
            return False
        
        try:
            # Cập nhật updated_at
            updates["updated_at"] = datetime.now().isoformat()
            
            # Convert date object to string
            if "last_play_date" in updates and isinstance(updates["last_play_date"], date):
                updates["last_play_date"] = updates["last_play_date"].isoformat()
            
            response = self.client.table("players").update(updates).eq("id", player_id).execute()
            return True
        except Exception as e:
            st.error(f"❌ Lỗi update player: {e}")
            return False
    
    def get_leaderboard(self, limit=10):
        """Lấy bảng xếp hạng top players"""
        if not self.connected:
            return []
        
        try:
            response = self.client.table("players").select("name, xp, level, total_score").order("xp", desc=True).limit(limit).execute()
            return response.data or []
        except Exception:
            return []
