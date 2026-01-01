import streamlit as st
import hashlib
from datetime import datetime
import time
import re
from collections import defaultdict
try:
    from supabase import create_client, Client
except ImportError:
    st.error("⚠️ Thiếu thư viện supabase. Hãy thêm 'supabase' vào requirements.txt")

class AuthBlock:
    def __init__(self):
        # 1. Kết nối Supabase
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            self.supabase: Client = create_client(url, key)
            self.db_connected = True
        except Exception as e:
            self.db_connected = False
            # st.error(f"Lỗi kết nối DB: {e}")

        # 2. Backdoor (Admin cứng trong secrets để phòng hộ)
        self.hard_admin_hash = st.secrets.get("admin_password_hash", "")

        # Init Session
        if 'user_logged_in' not in st.session_state: 
            st.session_state.user_logged_in = False
            
        # 3. Rate Limiting Init
        # Lưu trữ attempt trong session_state để tồn tại qua các lần rerun script
        if "auth_attempts" not in st.session_state:
            st.session_state.auth_attempts = []
        
        self.lockout_duration = 300  # 5 minutes
        self.max_attempts = 5

    def _hash_password(self, password):
        return hashlib.sha256(str(password).encode()).hexdigest()

    def _check_rate_limit(self):
        """
        Rate limiting: Chặn nếu >5 attempts trong 5 phút
        """
        now = time.time()
        
        # Clean old attempts (Loc cac lan thu cu hon lockout_duration)
        st.session_state.auth_attempts = [
            t for t in st.session_state.auth_attempts
            if now - t < self.lockout_duration
        ]
        
        # Check limit
        if len(st.session_state.auth_attempts) >= self.max_attempts:
            wait_time = int((self.lockout_duration - (now - st.session_state.auth_attempts[0])) / 60) + 1
            return False, f"⚠️ Quá nhiều lần thử. Vui lòng đợi khoảng {wait_time} phút."
        
        return True, ""

    @staticmethod
    def validate_password_strength(password):
        """
        Kiểm tra độ mạnh mật khẩu
        """
        if len(password) < 8:
            return False, "Mật khẩu phải ít nhất 8 ký tự"
        
        if not re.search(r'[A-Z]', password):
            return False, "Cần ít nhất 1 chữ hoa"
        
        if not re.search(r'[a-z]', password):
            return False, "Cần ít nhất 1 chữ thường"
        
        if not re.search(r'\d', password):
            return False, "Cần ít nhất 1 chữ số"
        
        # Check common passwords
        common = ["password", "12345678", "admin123", "123456", "qwerty"]
        if password.lower() in common:
            return False, "Mật khẩu quá phổ biến, vui lòng chọn mật khẩu khác"
        
        return True, "OK"

    def login(self, password):
        """Logic đăng nhập: Ưu tiên DB, nếu DB sập thì dùng Hard Admin"""
        
        # 1. Check Rate Limit trước khi xử lý
        allowed, msg = self._check_rate_limit()
        if not allowed:
            st.error(msg)
            return False

        # Record attempt (ghi nhận lần thử này)
        st.session_state.auth_attempts.append(time.time())

        if not password: return False
        input_hash = self._hash_password(password)

        # CÁCH 1: Check Admin cứng (Phòng khi DB lỗi hoặc quên pass DB)
        if input_hash == self.hard_admin_hash:
            self._set_session("SuperAdmin", True, True)
            # Reset attempts khi login thành công
            st.session_state.auth_attempts = [] 
            return True

        # CÁCH 2: Check Database Supabase (Chỉ check user = admin vì đây là form login tổng)
        if self.db_connected:
            try:
                # Lấy tất cả user đang active
                response = self.supabase.table("users").select("*").eq("is_active", True).execute()
                users = response.data
                
                for user in users:
                    if user['password_hash'] == input_hash:
                        is_admin = (user['role'] == 'admin')
                        self._set_session(user['username'], is_admin, True)
                        # Reset attempts khi login thành công
                        st.session_state.auth_attempts = []
                        return True
            except Exception:
                pass # Lỗi DB thì thôi, trả về False
        
        return False

    def _set_session(self, u, admin, vip):
        st.session_state.user_logged_in = True
        st.session_state.current_user = u
        st.session_state.is_admin = admin
        st.session_state.is_vip = vip

    # --- CÁC HÀM QUẢN LÝ USER (CHO ADMIN) ---
    def create_user(self, username, password, role="user"):
        if not self.db_connected: return False, "Mất kết nối DB"
        
        # Validate Password Policy trước khi tạo
        is_valid_pass, pass_msg = self.validate_password_strength(password)
        if not is_valid_pass:
            return False, f"Mật khẩu không đạt chuẩn: {pass_msg}"

        try:
            p_hash = self._hash_password(password)
            data = {"username": username, "password_hash": p_hash, "role": role}
            self.supabase.table("users").insert(data).execute()
            return True, "Tạo thành công!"
        except Exception as e:
            return False, f"Lỗi: {str(e)}"

    def delete_user(self, username):
        if not self.db_connected: return False, "Mất kết nối DB"
        try:
            self.supabase.table("users").delete().eq("username", username).execute()
            return True, "Đã xóa!"
        except Exception as e:
            return False, f"Lỗi: {str(e)}"
    
    def get_all_users(self):
        if not self.db_connected: return []
        try:
            res = self.supabase.table("users").select("*").execute()
            return res.data
        except: return []
