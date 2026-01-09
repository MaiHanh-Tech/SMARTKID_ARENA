"""
Dashboard phân tích điểm yếu học sinh
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.blocks.weakness_analyzer import WeaknessAnalyzer

def render_weakness_dashboard(analyzer: 'WeaknessAnalyzer'):
    """
    Dashboard hiển thị phân tích điểm yếu
    
    Args:
        analyzer: Instance của WeaknessAnalyzer
    """
    
    st.markdown("## 📊 Phân Tích Điểm Yếu & Tiến Bộ")
    
    # Tab navigation
    tab1, tab2, tab3 = st.tabs(["📈 Tổng Quan", "🔍 Lỗi Lặp Lại", "💡 Khuyến Nghị"])
    
    # ===== TAB 1: TỔNG QUAN =====
    with tab1:
        # 1. Topic Analysis
        topic_stats = analyzer.analyze_by_topic()
        
        if topic_stats:
            # Chuyển sang DataFrame
            df = pd.DataFrame.from_dict(topic_stats, orient='index')
            df = df.reset_index().rename(columns={'index': 'Topic'})
            
            # Metrics tổng quan
            col1, col2, col3, col4 = st.columns(4)
            
            total_attempts = df['total_attempts'].sum()
            total_correct = df['correct'].sum()
            overall_accuracy = total_correct / total_attempts if total_attempts > 0 else 0
            mastered_topics = len(df[df['weakness_level'] == 'mastered'])
            
            with col1:
                st.metric("📝 Tổng câu đã làm", total_attempts)
            with col2:
                st.metric("✅ Tổng câu đúng", total_correct)
            with col3:
                st.metric("🎯 Độ chính xác", f"{overall_accuracy:.1%}")
            with col4:
                st.metric("🌟 Chủ đề thành thạo", mastered_topics)
            
            st.markdown("---")
            
            # Biểu đồ cột: Accuracy theo topic
            fig = px.bar(
                df.sort_values('accuracy'),
                x='accuracy',
                y='Topic',
                color='weakness_level',
                color_discrete_map={
                    'critical': '#FF6B6B',
                    'needs_practice': '#FFD93D',
                    'good': '#6BCF7F',
                    'mastered': '#4ECDC4'
                },
                orientation='h',
                title="📊 Độ Chính Xác Theo Chủ Đề",
                labels={'accuracy': 'Accuracy', 'Topic': 'Chủ đề'},
                text='accuracy'
            )
            fig.update_traces(texttemplate='%{text:.1%}', textposition='outside')
            fig.update_xaxis(tickformat=".0%", range=[0, 1.1])
            fig.update_layout(height=max(400, len(df) * 40))
            st.plotly_chart(fig, use_container_width=True)
            
            # Bảng chi tiết
            with st.expander("📋 Xem Bảng Chi Tiết"):
                df_display = df.copy()
                df_display['accuracy'] = df_display['accuracy'].apply(lambda x: f"{x:.1%}")
                df_display['avg_time'] = df_display['avg_time'].apply(lambda x: f"{x:.1f}s")
                df_display = df_display.rename(columns={
                    'Topic': 'Chủ đề',
                    'total_attempts': 'Số câu',
                    'correct': 'Đúng',
                    'accuracy': 'Độ chính xác',
                    'avg_time': 'Thời gian TB',
                    'weakness_level': 'Mức độ'
                })
                st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        else:
            st.info("📚 Chưa có dữ liệu học tập. Hãy bắt đầu làm quiz!")
    
    # ===== TAB 2: LỖI LẶP LẠI =====
    with tab2:
        st.markdown("### 🔍 Phân Tích Lỗi Lặp Lại")
        errors = analyzer.find_error_patterns()
        
        if errors:
            st.warning(f"⚠️ Tìm thấy **{len(errors)} câu hỏi** bị sai nhiều lần")
            
            # Filter
            filter_col1, filter_col2 = st.columns([2, 1])
            with filter_col1:
                min_errors = st.slider("Hiển thị câu sai tối thiểu:", 2, 10, 2)
            with filter_col2:
                show_top = st.number_input("Hiển thị top:", 5, 20, 10)
            
            filtered_errors = [e for e in errors if e['times_wrong'] >= min_errors][:show_top]
            
            for i, error in enumerate(filtered_errors):
                severity = "🔴" if error['times_wrong'] >= 5 else "🟡" if error['times_wrong'] >= 3 else "🟢"
                
                with st.expander(
                    f"{severity} **{error['topic']}**: {error['question'][:60]}... "
                    f"(Sai {error['times_wrong']} lần)",
                    expanded=(i == 0)
                ):
                    st.markdown(f"**📝 Câu hỏi đầy đủ:**")
                    st.info(error['question'])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**❌ Đáp án sai thường chọn:**")
                        for ans in set(error['wrong_answers']):
                            count = error['wrong_answers'].count(ans)
                            st.write(f"- {ans} ({count} lần)")
                    
                    with col2:
                        st.markdown(f"**✅ Đáp án đúng:**")
                        st.success(error['correct_answer'])
                    
                    if error.get('concept_tags'):
                        st.markdown(f"**🏷️ Concepts:** {', '.join(error['concept_tags'])}")
                    
                    # Action button
                    if st.button(f"🎯 Luyện tập lại câu này", key=f"retry_{i}"):
                        st.session_state.retry_question = error
                        st.info("💡 Tính năng sẽ được thêm trong phiên bản tiếp theo!")
        
        else:
            st.success("🎉 Tuyệt vời! Không có lỗi lặp lại nào!")
    
    # ===== TAB 3: KHUYẾN NGHỊ =====
    with tab3:
        st.markdown("### 💡 Khuyến Nghị Học Tập")
        
        priority_topics = analyzer.get_priority_topics(top_n=5)
        
        if priority_topics:
            st.markdown("#### 🎯 Chủ đề cần ưu tiên:")
            
            for i, topic in enumerate(priority_topics, 1):
                topic_data = topic_stats.get(topic, {})
                accuracy = topic_data.get('accuracy', 0)
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{i}. {topic}** - Accuracy: {accuracy:.1%}")
                    st.progress(accuracy)
                
                with col2:
                    if st.button("📚 Học ngay", key=f"learn_{i}"):
                        st.session_state.focus_topic = topic
                        st.session_state.show_dashboard = False
                        st.session_state.mode = "study"
                        st.rerun()
            
            st.markdown("---")
            
            # Button tạo quiz tập trung
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🎯 TẠO QUIZ TẬP TRUNG VÀO ĐIỂM YẾU", type="primary", use_container_width=True):
                    st.session_state.focus_mode = "review_weak"
                    st.session_state.priority_topics = priority_topics
                    st.session_state.show_dashboard = False
                    st.session_state.mode = "study"
                    st.info("✅ Đã chuyển sang chế độ luyện tập điểm yếu!")
                    st.rerun()
            
            with col2:
                if st.button("🔀 TẠO QUIZ TỔNG HỢP", use_container_width=True):
                    st.session_state.focus_mode = "mixed"
                    st.session_state.show_dashboard = False
                    st.session_state.mode = "study"
                    st.rerun()
        
        else:
            st.success("🌟 Xuất sắc! Bạn đã học tốt ở tất cả chủ đề!")
            st.balloons()
            
            st.markdown("#### 🚀 Gợi ý tiếp theo:")
            st.markdown("""
            - 📈 Thử độ khó cao hơn (Hard/Expert)
            - 📚 Học chương mới
            - ⚔️ Thử chế độ Thách Đấu
            """)
        
        st.markdown("---")
        
        # Learning tips
        with st.expander("💡 Mẹo Học Tập Hiệu Quả"):
            st.markdown("""
            **Nguyên tắc "Spaced Repetition":**
            - Ôn lại kiến thức sau 1 ngày, 3 ngày, 1 tuần
            - Tập trung vào phần yếu trước khi học phần mới
            
            **Kỹ thuật "Active Recall":**
            - Tự hỏi bản thân trước khi xem đáp án
            - Giải thích cho người khác (hoặc gấu bông 🧸)
            
            **Chiến thuật "Pomodoro":**
            - Học 25 phút → Nghỉ 5 phút
            - Sau 4 lần → Nghỉ dài 15-30 phút
            """)
    
    # Back button
    st.markdown("---")
    if st.button("🏠 Quay lại Trang Chủ", use_container_width=True):
        st.session_state.show_dashboard = False
        st.rerun()


def render_progress_timeline(analyzer: 'WeaknessAnalyzer'):
    """
    [Unverified] Biểu đồ timeline tiến bộ theo thời gian
    
    Note: Cần dữ liệu lịch sử đủ dài để vẽ timeline có ý nghĩa
    """
    # TODO: Implement khi có đủ dữ liệu lịch sử
    pass
