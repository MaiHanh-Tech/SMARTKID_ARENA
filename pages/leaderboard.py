# pages/leaderboard.py
import streamlit as st
import pandas as pd
from datetime import datetime
from supabase_manager import SupabaseManager

st.set_page_config(
    page_title="Bảng Xếp Hạng - SmartKid Arena",
    page_icon="🏆",
    layout="wide"
)

st.title("🏆 Bảng Xếp Hạng Chiến Binh")
st.markdown("Ai là người chơi xuất sắc nhất hôm nay? Kiểm tra vị trí của bạn ngay!")

# Khởi tạo Supabase (nếu chưa có trong session)
if "supabase" not in st.session_state:
    st.session_state.supabase = SupabaseManager()

supabase = st.session_state.supabase

# Lấy dữ liệu leaderboard
@st.cache_data(ttl=300)  # cache 5 phút để đỡ query nhiều
def load_leaderboard():
    data = supabase.get_leaderboard(limit=50)  # lấy top 50
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    # Đảm bảo các cột cần thiết
    df = df[['name', 'xp', 'level', 'total_score']]
    df = df.sort_values(by='xp', ascending=False).reset_index(drop=True)
    df['rank'] = df.index + 1
    return df

df = load_leaderboard()

if df.empty:
    st.info("Chưa có dữ liệu xếp hạng nào. Hãy là người đầu tiên lên bảng!")
else:
    # Hiển thị top 3 đặc biệt
    col1, col2, col3 = st.columns(3)
    
    if len(df) >= 1:
        with col1:
            st.metric("🥇 Top 1", df.iloc[0]['name'])
            st.caption(f"XP: {df.iloc[0]['xp']:,} | Level {df.iloc[0]['level']}")
    
    if len(df) >= 2:
        with col2:
            st.metric("🥈 Top 2", df.iloc[1]['name'])
            st.caption(f"XP: {df.iloc[1]['xp']:,} | Level {df.iloc[1]['level']}")
    
    if len(df) >= 3:
        with col3:
            st.metric("🥉 Top 3", df.iloc[2]['name'])
            st.caption(f"XP: {df.iloc[2]['xp']:,} | Level {df.iloc[2]['level']}")

    # Bảng đầy đủ
    st.markdown("### Top 50 Người Chơi")
    
    # Thêm cột huy hiệu (tùy chọn)
    def get_rank_emoji(rank):
        if rank == 1: return "🥇"
        if rank == 2: return "🥈"
        if rank == 3: return "🥉"
        return f"{rank}."

    df_display = df[['rank', 'name', 'xp', 'level', 'total_score']].copy()
    df_display['rank'] = df_display['rank'].apply(get_rank_emoji)
    
    st.dataframe(
        df_display.style.format({
            'xp': '{:,}',
            'total_score': '{:,}'
        }),
        hide_index=True,
        use_container_width=True
    )

    # Tìm vị trí của người chơi hiện tại (nếu có)
    if 'player' in st.session_state and st.session_state.player:
        current_name = st.session_state.player.name
        current_rank = df[df['name'] == current_name]
        if not current_rank.empty:
            rank = current_rank.iloc[0]['rank']
            st.success(f"🎯 Bạn đang ở vị trí **{rank}** trên bảng xếp hạng!")
        else:
            st.info("Bạn chưa có trong top 50. Chơi nhiều hơn để lên bảng nhé!")

st.markdown("---")
st.caption(f"Cập nhật lần cuối: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
