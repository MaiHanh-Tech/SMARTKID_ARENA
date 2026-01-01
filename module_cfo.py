import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression
import time
from datetime import datetime, timedelta

# Import các Block dùng chung (để dùng AI)
from ai_core import AI_Core
# (Nếu chị chưa có file ai_core.py thì nó sẽ báo lỗi, đảm bảo chị đã tạo nó ở bước trước)

# --- CÁC HÀM XỬ LÝ DỮ LIỆU (ĐÃ CẬP NHẬT REALISTIC) ---

def tao_data_full_kpi(start_date=None, months=24, seed=None):
    """
    Tạo data KPI với tính realistic cao hơn
    
    Args:
        start_date: Ngày bắt đầu (mặc định: 24 tháng trước)
        months: Số tháng data
        seed: Random seed (để reproduce)
    """
    if seed:
        np.random.seed(seed)
    
    if not start_date:
        start_date = datetime.now() - timedelta(days=months*30)
    
    dates = pd.date_range(start=start_date, periods=months, freq="ME")
    df = pd.DataFrame({"Tháng": dates})
    
    # ✅ Tạo trend realistic (tăng trưởng 5%/năm + seasonal)
    base_revenue = 6000000000  # 6 tỷ
    growth_rate = 0.05 / 12  # 5% năm = 0.4% tháng
    
    revenues = []
    for i in range(months):
        # Trend tăng trưởng
        trend = base_revenue * (1 + growth_rate) ** i
        
        # Seasonal (Q4 cao hơn, Q1-Q2 thấp hơn)
        month = (i % 12) + 1
        if month in [11, 12]:  # Q4
            seasonal = 1.15
        elif month in [1, 2, 3]:  # Q1
            seasonal = 0.95
        else:
            seasonal = 1.0
        
        # Random noise ±10%
        noise = np.random.uniform(0.9, 1.1)
        
        revenues.append(trend * seasonal * noise)
    
    df["Doanh Thu"] = revenues
    
    # ✅ Chi phí biến đổi theo doanh thu (60% ± 2%)
    df["Giá Vốn"] = df["Doanh Thu"] * np.random.uniform(0.58, 0.62, months)
    
    # ✅ Chi phí cố định với noise nhỏ
    base_salary = 700000000
    df["CP Lương"] = base_salary * np.random.uniform(0.95, 1.05, months)
    
    df["CP Marketing"] = df["Doanh Thu"] * np.random.uniform(0.08, 0.12, months)
    df["CP Khác"] = np.random.randint(100, 200, months) * 1000000
    
    df["Chi Phí VH"] = df["CP Lương"] + df["CP Marketing"] + df["CP Khác"]
    
    # ✅ GÀI BẪY REALISTIC HƠN (1-2 tháng bất thường tự nhiên)
    anomaly_months = np.random.choice(range(12, months-2), size=2, replace=False)
    for m in anomaly_months:
        anomaly_type = np.random.choice(['chi_phi_dot_bien', 'mat_khach_hang'])
        
        if anomaly_type == 'chi_phi_dot_bien':
            # Chi phí tăng đột ngột 80%
            df.loc[m, "Chi Phí VH"] *= 1.8
        else:
            # Doanh thu giảm 30%
            df.loc[m, "Doanh Thu"] *= 0.7
    
    # Các chỉ số khác
    df["Lợi Nhuận ST"] = df["Doanh Thu"] - df["Giá Vốn"] - df["Chi Phí VH"]
    df["Dòng Tiền Thực"] = df["Lợi Nhuận ST"] * np.random.uniform(0.75, 0.85, months)
    df["Công Nợ Phải Thu"] = df["Doanh Thu"] * np.random.uniform(0.15, 0.25, months)
    df["Hàng Tồn Kho Tổng"] = df["Giá Vốn"] * np.random.uniform(0.2, 0.3, months)
    
    # Tài sản & Nợ
    df["TS Ngắn Hạn"] = (df["Công Nợ Phải Thu"] + df["Hàng Tồn Kho Tổng"] + 
                         np.random.randint(500, 1000, months) * 1000000)
    df["Nợ Ngắn Hạn"] = df["TS Ngắn Hạn"] * np.random.uniform(0.4, 0.6, months)
    df["Vốn Chủ Sở Hữu"] = np.random.randint(5000, 6000, months) * 1000000
    
    return df

# ✅ THÊM: Hàm validate data upload từ Excel
def validate_uploaded_data(df):
    """Kiểm tra data upload có hợp lệ không"""
    required_columns = ["Tháng", "Doanh Thu", "Chi Phí VH", "Lợi Nhuận ST"]
    
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        return False, f"Thiếu cột: {', '.join(missing)}"
    
    # Kiểm tra số âm bất thường
    if (df["Doanh Thu"] < 0).any():
        return False, "Doanh thu không được âm"
    
    # Kiểm tra outlier quá mức
    for col in ["Doanh Thu", "Chi Phí VH"]:
        if col in df.columns:
            q1, q3 = df[col].quantile([0.25, 0.75])
            iqr = q3 - q1
            outliers = ((df[col] < q1 - 3*iqr) | (df[col] > q3 + 3*iqr)).sum()
            if outliers > len(df) * 0.1:  # Nếu >10% là outlier
                return False, f"Cột {col} có quá nhiều giá trị bất thường ({outliers}/{len(df)})"
    
    return True, "OK"

def tinh_chi_so(df):
    try:
        df["Current Ratio"] = df["TS Ngắn Hạn"] / df["Nợ Ngắn Hạn"].replace(0, 1)
        df["Gross Margin"] = (df["Doanh Thu"] - df["Giá Vốn"]) / df["Doanh Thu"].replace(0, 1) * 100
        df["ROS"] = df["Lợi Nhuận ST"] / df["Doanh Thu"].replace(0, 1) * 100
    except: pass
    return df

def phat_hien_gian_lan(df):
    iso = IsolationForest(contamination=0.05, random_state=42)
    col = "Chi Phí VH" if "Chi Phí VH" in df.columns else df.columns[1]
    # Handle NaN values
    data_clean = df[[col]].fillna(0)
    df['Anomaly'] = iso.fit_predict(data_clean)
    return df[df['Anomaly'] == -1]

# --- HÀM CHÍNH (ĐỂ APP.PY GỌI) ---
def run():
    # Khởi tạo AI
    ai = AI_Core()

    st.header("💰 CFO Controller Dashboard")
    
    # ✅ SIDEBAR MỚI (CHO PHÉP UPLOAD DATA THẬT)
    with st.sidebar:
        st.markdown("---")
        st.write("📊 **Nguồn dữ liệu**")
        data_source = st.radio("Chọn nguồn:", ["Demo (Giả)", "Upload Excel"])
        
        if data_source == "Upload Excel":
            uploaded = st.file_uploader("Upload file Excel", type="xlsx")
            if uploaded:
                try:
                    df_raw = pd.read_excel(uploaded)
                    is_valid, msg = validate_uploaded_data(df_raw)
                    
                    if is_valid:
                        st.session_state.df_fin = df_raw
                        st.success("✅ Tải data thành công!")
                    else:
                        st.error(f"❌ Lỗi data: {msg}")
                except Exception as e:
                    st.error(f"Lỗi đọc file: {e}")
        
        if st.button("🔄 Tạo data demo mới"):
            st.session_state.df_fin = tao_data_full_kpi(seed=int(time.time()))
            st.rerun()
            
    # Init Data (Mặc định Data Demo Realistic)
    if 'df_fin' not in st.session_state:
        st.session_state.df_fin = tao_data_full_kpi(seed=42)
    
    df = tinh_chi_so(st.session_state.df_fin.copy())
    last = df.iloc[-1]

    # Tabs
    t1, t2, t3, t4 = st.tabs(["📊 KPIs & Sức Khỏe", "📉 Phân Tích Chi Phí", "🕵️ Rủi Ro & Check", "🔮 Dự Báo & What-If"])

    # TAB 1: KPI
    with t1:
        st.subheader("Sức khỏe Tài chính Tháng gần nhất")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Doanh Thu", f"{last['Doanh Thu']/1e9:.1f} tỷ")
        k2.metric("Lợi Nhuận ST", f"{last['Lợi Nhuận ST']/1e9:.1f} tỷ")
        k3.metric("ROS", f"{last.get('ROS',0):.1f}%")
        k4.metric("Dòng Tiền", f"{last['Dòng Tiền Thực']/1e9:.1f} tỷ")
        
        st.line_chart(df.set_index("Tháng")[["Doanh Thu", "Lợi Nhuận ST"]])

    # TAB 2: CHI PHÍ & AI
    with t2:
        c1, c2 = st.columns([2, 1])
        with c1:
            if "Giá Vốn" in df.columns and "Chi Phí VH" in df.columns:
                st.plotly_chart(px.bar(df, x="Tháng", y=["Giá Vốn", "Chi Phí VH"], title="Cấu trúc Chi phí"), use_container_width=True)
            else:
                st.info("Chưa có đủ cột dữ liệu chi phí để vẽ biểu đồ.")
        with c2:
            st.write("🤖 **Trợ lý Phân tích:**")
            q = st.text_input("Hỏi về chi phí...")
            if q:
                with st.spinner("AI đang soi số liệu..."):
                    # Gửi data tháng cuối cho AI
                    context = f"Dữ liệu tháng cuối: Doanh thu {last['Doanh Thu']}, Lợi nhuận {last['Lợi Nhuận ST']}."
                    res = ai.generate(q, system_instruction=f"Bạn là Kế toán trưởng. Phân tích dựa trên: {context}")
                    st.write(res)

    # TAB 3: RỦI RO & CROSS-CHECK
    with t3:
        c_risk, c_check = st.columns(2)
        with c_risk:
            st.subheader("Quét Gian Lận (ML)")
            if st.button("🔍 Quét ngay"):
                bad = phat_hien_gian_lan(df)
                if not bad.empty:
                    st.error(f"Phát hiện {len(bad)} tháng bất thường!")
                    st.dataframe(bad)
                else:
                    st.success("Dữ liệu sạch.")
        
        with c_check:
            st.subheader("Cross-Check (Đối chiếu)")
            val_a = st.number_input("Số liệu Thuế (Tờ khai):", value=100.0)
            val_b = st.number_input("Số liệu Sổ cái (ERP):", value=105.0)
            if st.button("So khớp"):
                diff = val_b - val_a
                if diff != 0:
                    st.warning(f"Lệch: {diff}. Rủi ro truy thu thuế!")
                else:
                    st.success("Khớp!")

    # TAB 4: WHAT-IF
    with t4:
        st.subheader("🎛️ What-If Analysis")
        st.caption("Giả lập kịch bản: Nếu thay đổi đầu vào thì Lợi nhuận ra sao?")
        
        base_rev = last['Doanh Thu']
        base_profit = last['Lợi Nhuận ST']
        
        c_s1, c_s2 = st.columns(2)
        with c_s1: delta_price = st.slider("Tăng/Giảm Giá Bán (%)", -20, 20, 0)
        with c_s2: delta_cost = st.slider("Tăng/Giảm Chi Phí (%)", -20, 20, 0)
        
        new_rev = base_rev * (1 + delta_price/100)
        # Giả sử chi phí biến đổi theo doanh thu + chi phí cố định (lấy data last month)
        base_fixed_cost = last.get('Chi Phí VH', 0)
        new_profit = base_profit + (new_rev - base_rev) - (base_fixed_cost * delta_cost/100)
        
        col_res1, col_res2 = st.columns(2)
        col_res1.metric("Lợi Nhuận Gốc", f"{base_profit/1e9:.2f} tỷ")
        col_res2.metric("Lợi Nhuận Mới", f"{new_profit/1e9:.2f} tỷ", delta=f"{(new_profit - base_profit)/1e9:.2f} tỷ")
