import streamlit as st
import sys
import os

# --- CẤU HÌNH ĐƯỜNG DẪN (QUAN TRỌNG) ---
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# 1. IMPORT CÁC MODULE TỪ THƯ MỤC BLOCKS
try:
    from services.blocks import module_weaver
    from services.blocks import module_cfo
    from services.blocks import module_translator
    from services.blocks.auth_block import AuthBlock # Import class AuthBlock trực tiếp
except ImportError as e:
    st.error(f"❌ Lỗi cấu trúc file: Không tìm thấy module trong 'services/blocks/'.\nChi tiết: {e}")
    st.stop()

# 2. CẤU HÌNH TRANG
st.set_page_config(page_title="Cognitive Weaver", layout="wide", page_icon="🏢")

# 3. KHỞI TẠO AUTH
try:
    auth = AuthBlock()
except Exception as e:
    st.error(f"❌ Lỗi khởi tạo Auth: {e}")
    st.stop()

# SIMPLE SAFE WRAPPER
def safe_run_module(module_func, module_name):
    try:
        module_func()
    except Exception as e:
        st.error(f"❌ Module {module_name} gặp lỗi:")
        st.exception(e)
        st.info("💡 Hãy reload trang hoặc chọn module khác")

# 4. LOGIN UI
if 'user_logged_in' not in st.session_state:
    st.session_state.user_logged_in = False

if not st.session_state.user_logged_in:
    st.title("🔐 Đăng Nhập Hệ Thống")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        pwd = st.text_input("Nhập mật khẩu:", type="password", placeholder="Nhập mật khẩu của bạn")
        if st.button("Truy cập", use_container_width=True):
            if auth.login(pwd):
                st.success("✅ Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("❌ Sai mật khẩu!")
                # Logic đếm số lần thử đã có trong auth_block mới, 
                # hiển thị cảnh báo từ đó hoặc xử lý đơn giản ở đây
    st.stop()

# 5. SIDEBAR & NAVIGATION
with st.sidebar:
    st.title("🗂️ DANH MỤC ỨNG DỤNG")
    user_name = st.session_state.get('current_user', 'User')
    st.info(f"👤 Xin chào: **{user_name}**")
    
    app_choice = st.radio("Chọn công việc:", [
        "💰 1. Cognitive Weaver (Sách & Graph)",
        "🌏 2. AI Translator (Dịch thuật)",
        "🧠 3. CFO Controller (Tài chính)"
    ])
    
    st.divider()
    if st.button("Đăng Xuất"):
        st.session_state.user_logged_in = False
        st.rerun()

    # Admin panel (nếu có)
    if st.session_state.get("is_admin"):
        st.divider()
        st.write("👑 **Admin Panel**")
        with st.expander("Quản lý Người dùng"):
            try:
                all_users = auth.get_all_users()
                if all_users:
                    import pandas as pd
                    df_users = pd.DataFrame(all_users)
                    # Lọc cột hiển thị cho gọn
                    cols = [c for c in ['username', 'role', 'created_at'] if c in df_users.columns]
                    st.dataframe(df_users[cols], hide_index=True)
                
                st.write("---")
                new_u = st.text_input("Username mới:")
                new_p = st.text_input("Password mới:", type="password")
                new_role = st.selectbox("Role:", ["user", "admin"])
                if st.button("Tạo User"):
                    if new_u and new_p:
                        ok, msg = auth.create_user(new_u, new_p, new_role)
                        if ok:
                            st.success(msg)
                            time.sleep(1) # Đợi 1s để đọc thông báo
                            st.rerun()
                        else:
                            st.error(msg)
            except Exception as e:
                st.warning(f"Lỗi Admin Panel: {e}")

# 6. LOAD UI MODULES (Sử dụng biến đã import ở trên đầu)
try:
    if app_choice == "💰 1. Cognitive Weaver (Sách & Graph)":
        # Không cần import lại, dùng trực tiếp biến module_weaver đã import ở dòng 10
        safe_run_module(module_weaver.run, "Cognitive Weaver")
        
    elif app_choice == "🌏 2. AI Translator (Dịch thuật)":
        safe_run_module(module_translator.run, "AI Translator")
        
    elif app_choice == "🧠 3. CFO Controller (Tài chính)":
        safe_run_module(module_cfo.run, "CFO Controller")
        
except Exception as e:
    st.error(f"❌ Lỗi chạy module: {e}")
    st.exception(e)
