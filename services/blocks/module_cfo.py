import streamlit as st
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from services.blocks.cfo_data_manager import tao_data_full_kpi, validate_uploaded_data, tinh_chi_so
from services.blocks.ai_core import AI_Core

# --- CÁC HÀM XỬ LÝ NÂNG CAO (NEW) ---

def phat_hien_gian_lan_nang_cao(df):
    """
    Phát hiện gian lận đa chiều: Benford's Law + Multi-feature IsolationForest
    """
    # 1. Feature engineering
    # Tránh chia cho 0
    df_check = df.copy()
    df_check['GrossMargin'] = (df_check['Doanh Thu'] - df_check['Giá Vốn']) / df_check['Doanh Thu'].replace(0, 1)
    df_check['ExpenseRatio'] = df_check['Chi Phí VH'] / df_check['Doanh Thu'].replace(0, 1)
    df_check['CashflowRatio'] = df_check['Dòng Tiền Thực'] / df_check['Lợi Nhuận ST'].replace(0, 1)
    
    # 2. Benford's Law check (Cho Doanh Thu)
    def check_benfords_law(numbers):
        # Lấy chữ số đầu tiên (1-9)
        first_digits = [int(str(abs(int(x)))[0]) for x in numbers if x != 0]
        if not first_digits: return False
        
        observed = np.bincount(first_digits, minlength=10)[1:]
        
        # Kỳ vọng theo Benford
        expected_probs = np.log10(1 + 1/np.arange(1, 10))
        expected = expected_probs * len(first_digits)
        
        # Chi-square approximation (đơn giản)
        # Tránh chia cho 0 trong công thức chi2
        with np.errstate(divide='ignore', invalid='ignore'):
            chi2 = np.sum((observed - expected)**2 / expected)
        
        # Ngưỡng (Threshold) ước lượng cho mức ý nghĩa 5%
        return chi2 > 15.5
    
    benford_suspicious = check_benfords_law(df_check['Doanh Thu'].values)
    
    # 3. Multi-feature IsolationForest
    features = ['GrossMargin', 'ExpenseRatio', 'CashflowRatio']
    # Fill NaN bằng 0 để model chạy được
    X = StandardScaler().fit_transform(df_check[features].fillna(0))
    
    iso = IsolationForest(contamination=0.05, random_state=42)
    df_check['AnomalyScore'] = iso.fit_predict(X) # -1 là bất thường
    
    # 4. Combine signals
    df_check['FraudRisk'] = 'Low'
    
    # Nếu IsolationForest báo bất thường -> Medium
    df_check.loc[df_check['AnomalyScore'] == -1, 'FraudRisk'] = 'Medium'
    
    # Nếu Benford báo động VÀ có bất thường số liệu -> High
    if benford_suspicious:
        df_check.loc[df_check['AnomalyScore'] == -1, 'FraudRisk'] = 'High'
        
    # Trả về các dòng có rủi ro
    return df_check[df_check['FraudRisk'].isin(['Medium', 'High'])], benford_suspicious

def forecast_next_quarter(df, target_col='Doanh Thu'):
    """
    Dự báo 3 tháng tới bằng Ensemble (Linear Regression + Random Forest)
    """
    try:
        # Prepare data
        df_forecast = df.copy()
        df_forecast['Month_Num'] = range(len(df_forecast))
        
        X = df_forecast[['Month_Num']].values
        y = df_forecast[target_col].values
        
        # Model 1: Linear Regression (Trend)
        lr = LinearRegression()
        lr.fit(X, y)
        
        # Model 2: Random Forest (Seasonality/Non-linear)
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(X, y)
        
        # Predict next 3 months
        last_idx = len(df_forecast)
        future_months = np.array([[last_idx], [last_idx+1], [last_idx+2]])
        
        pred_lr = lr.predict(future_months)
        pred_rf = rf.predict(future_months)
        
        # Ensemble (70% RF, 30% LR - ưu tiên phi tuyến tính)
        pred_final = 0.7 * pred_rf + 0.3 * pred_lr
        
        return pred_final
    except Exception as e:
        return [0, 0, 0]

# --- MAIN RUN ---

def run():
    ai = AI_Core()
    st.header("💰 CFO Controller Dashboard")
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
            st.session_state.df_fin = tao_data_full_kpi(seed=int(st.time()))
            st.rerun()

    if 'df_fin' not in st.session_state:
        st.session_state.df_fin = tao_data_full_kpi(seed=42)

    df = tinh_chi_so(st.session_state.df_fin.copy())
    last = df.iloc[-1]

    t1, t2, t3, t4 = st.tabs(["📊 KPIs & Sức Khỏe", "📉 Phân Tích Chi Phí", "🕵️ Rủi Ro & Check", "🔮 Dự Báo & What-If"])

    with t1:
        st.subheader("Sức khỏe Tài chính Tháng gần nhất")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Doanh Thu", f"{last['Doanh Thu']/1e9:.1f} tỷ")
        k2.metric("Lợi Nhuận ST", f"{last['Lợi Nhuận ST']/1e9:.1f} tỷ")
        k3.metric("ROS", f"{last.get('ROS',0):.1f}%")
        k4.metric("Dòng Tiền", f"{last['Dòng Tiền Thực']/1e9:.1f} tỷ")
        st.line_chart(df.set_index("Tháng")[["Doanh Thu", "Lợi Nhuận ST"]])

    with t2:
        c1, c2 = st.columns([2,1])
        with c1:
            if "Giá Vốn" in df.columns and "Chi Phí VH" in df.columns:
                st.bar_chart(df.set_index("Tháng")[["Giá Vốn", "Chi Phí VH"]])
            else:
                st.info("Chưa có đủ cột dữ liệu chi phí để vẽ biểu đồ.")
        with c2:
            st.write("🤖 **Trợ lý Phân tích:**")
            q = st.text_input("Hỏi về chi phí...")
            if q:
                with st.spinner("AI đang soi số liệu..."):
                    context = f"Dữ liệu tháng cuối: Doanh thu {last['Doanh Thu']}, Lợi nhuận {last['Lợi Nhuận ST']}."
                    res = ai.generate(q, system_instruction=f"Bạn là Kế toán trưởng. Phân tích dựa trên: {context}")
                    st.write(res)

    with t3:
        c_risk, c_check = st.columns(2)
        with c_risk:
            st.subheader("Quét Gian Lận Đa Chiều (ML)")
            st.caption("Sử dụng Benford's Law & Isolation Forest trên 3 chỉ số.")
            
            if st.button("🔍 Quét ngay"):
                bad, benford_fail = phat_hien_gian_lan_nang_cao(df)
                
                if benford_fail:
                    st.warning("⚠️ **Cảnh báo Benford:** Phân bố chữ số đầu của Doanh thu bất thường (Khả năng số liệu bị 'xào nấu').")
                else:
                    st.info("✅ Kiểm tra Benford: Bình thường.")

                if not bad.empty:
                    st.error(f"Phát hiện {len(bad)} tháng có dấu hiệu bất thường!")
                    # Highlight colors
                    def highlight_risk(val):
                        color = '#ffcccc' if val == 'High' else '#fff4cc'
                        return f'background-color: {color}'
                    
                    st.dataframe(bad[['Tháng', 'Doanh Thu', 'GrossMargin', 'FraudRisk']].style.applymap(highlight_risk, subset=['FraudRisk']))
                else:
                    st.success("Dữ liệu sạch. Không phát hiện bất thường đáng kể.")
                    
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

    with t4:
        # --- FORECAST SECTION ---
        st.subheader("🔮 Dự báo Doanh Thu (Quý tới)")
        st.caption("AI Ensemble Model (Linear Regression + Random Forest)")
        
        forecast_vals = forecast_next_quarter(df, target_col='Doanh Thu')
        
        fc1, fc2, fc3 = st.columns(3)
        fc1.metric("Tháng tới (M+1)", f"{forecast_vals[0]/1e9:.2f} tỷ")
        fc2.metric("Tháng M+2", f"{forecast_vals[1]/1e9:.2f} tỷ")
        fc3.metric("Tháng M+3", f"{forecast_vals[2]/1e9:.2f} tỷ")
        
        # --- WHAT-IF SECTION ---
        st.divider()
        st.subheader("🎛️ What-If Analysis")
        base_rev = last['Doanh Thu']
        base_profit = last['Lợi Nhuận ST']
        c_s1, c_s2 = st.columns(2)
        with c_s1:
            delta_price = st.slider("Tăng/Giảm Giá Bán (%)", -20, 20, 0)
        with c_s2:
            delta_cost = st.slider("Tăng/Giảm Chi Phí (%)", -20, 20, 0)
        new_rev = base_rev * (1 + delta_price/100)
        base_fixed_cost = last.get('Chi Phí VH', 0)
        new_profit = base_profit + (new_rev - base_rev) - (base_fixed_cost * delta_cost/100)
        col_res1, col_res2 = st.columns(2)
        col_res1.metric("Lợi Nhuận Gốc", f"{base_profit/1e9:.2f} tỷ")
        col_res2.metric("Lợi Nhuận Mới", f"{new_profit/1e9:.2f} tỷ", delta=f"{(new_profit - base_profit)/1e9:.2f} tỷ")
