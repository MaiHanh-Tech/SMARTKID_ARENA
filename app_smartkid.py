"""
SmartKid Arena - Game-based Learning Platform
Hệ thống học tập thích ứng với AI

ROOT LEVEL VERSION - app_smartkid.py ở ngoài folder services
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
import uuid
import os

# ===== IMPORT CÁC MODULE Ở ROOT LEVEL =====
from quiz_engine import QuizEngine
from game_mechanics import GameMechanics
from player_profile import PlayerProfile
from services.blocks.history_tracker import LearningHistoryTracker
from services.blocks.weakness_analyzer import WeaknessAnalyzer
from services.blocks.adaptive_quiz_engine import AdaptiveQuizEngine
from services.blocks.file_processor import doc_file
from services.report_generator import ReportGenerator
from pages.student_dashboard import render_weakness_dashboard

# ===== CẤU HÌNH TRANG =====
st.set_page_config(
    page_title="SmartKid Arena 🎮",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== CUSTOM CSS (Game-like UI) =====
st.markdown("""
<style>
    /* Background gradient */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Card styling */
    .metric-card {
        background: rgba(255,255,255,0.9);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        text-align: center;
        margin: 10px;
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(45deg, #FF6B6B, #FFD93D);
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 10px;
        padding: 15px 30px;
        font-size: 18px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    
    .stButton>button:hover {
        transform: scale(1.05);
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, #4ECDC4, #44A08D);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
    }
</style>
""", unsafe_allow_html=True)

# ===== KHỞI TẠO SESSION STATE =====
def init_session_state():
    if "player" not in st.session_state:
        # Kiểm tra xem đã có tên trong session chưa
        if "player_name" not in st.session_state:
            # Hiển thị form nhập tên ngay đầu app
            st.title("Chào mừng đến SmartKid Arena! 🎮")
            player_name = st.text_input("Nhập tên của bạn:", placeholder="Ví dụ: Minh, Lan, Bé Bảo...")
            start_button = st.button("Bắt đầu chơi →", type="primary")
            
            if start_button and player_name.strip():
                st.session_state.player_name = player_name.strip()
                st.rerun()  # Reload để tạo player
            elif start_button:
                st.error("Vui lòng nhập tên nhé!")
            # Dừng lại để người dùng nhập tên
            st.stop()
        
        # Khi đã có tên → tạo profile
        st.session_state.player = PlayerProfile(st.session_state.player_name)
    
    # Quiz engine (cũ)
    if "quiz_engine" not in st.session_state:
        st.session_state.quiz_engine = QuizEngine()
    
    # Game mechanics
    if "game" not in st.session_state:
        st.session_state.game = GameMechanics()
    
    # ===== THÊM MỚI: History & Analytics =====
    if "history_tracker" not in st.session_state:
        st.session_state.history_tracker = LearningHistoryTracker(
            student_id=st.session_state.player.name
        )
    
    if "weakness_analyzer" not in st.session_state:
        st.session_state.weakness_analyzer = WeaknessAnalyzer(
            st.session_state.history_tracker
        )
    
    if "adaptive_engine" not in st.session_state:
        st.session_state.adaptive_engine = AdaptiveQuizEngine(
            weakness_analyzer=st.session_state.weakness_analyzer,
            base_quiz_engine=st.session_state.quiz_engine
        )
    
    # Quiz state
    if "current_quiz" not in st.session_state:
        st.session_state.current_quiz = None
    
    if "quiz_active" not in st.session_state:
        st.session_state.quiz_active = False
    
    if "current_question" not in st.session_state:
        st.session_state.current_question = 0
    
    if "score" not in st.session_state:
        st.session_state.score = 0
    
    if "answers" not in st.session_state:
        st.session_state.answers = []
    
    # Book content
    if "book_content" not in st.session_state:
        st.session_state.book_content = None
    
    if "book_name" not in st.session_state:
        st.session_state.book_name = ""
    
    # Session tracking
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    
    if "question_start_time" not in st.session_state:
        st.session_state.question_start_time = None
    
    # UI state
    if "show_dashboard" not in st.session_state:
        st.session_state.show_dashboard = False
    
    if "mode" not in st.session_state:
        st.session_state.mode = None
    
    if "focus_mode" not in st.session_state:
        st.session_state.focus_mode = "adaptive"

# Gọi init
init_session_state()

# ===== HEADER =====
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("<h1 style='text-align: center; color: white;'>🎮 SMARTKID ARENA 🎓</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: white;'>Học mà như chơi game!</p>", unsafe_allow_html=True)

# ===== SIDEBAR: PLAYER STATS =====
with st.sidebar:
    st.markdown("### 👤 Hồ Sơ Chiến Binh")
    
    player = st.session_state.player
    
    # Avatar & Name
    st.markdown(f"<div class='metric-card'><h2>🦸 {player.name}</h2></div>", unsafe_allow_html=True)
    
    # Level & XP
    st.metric("⚡ Level", player.level)
    st.metric("🌟 XP", f"{player.xp}/{player.xp_to_next_level()}")
    st.progress(player.xp / player.xp_to_next_level())
    
    # Streak
    st.metric("🔥 Streak", f"{player.streak} ngày")
    
    # Total Score
    st.metric("💎 Tổng điểm", player.total_score)
    
    st.markdown("---")
    
    # Badges
    st.markdown("### 🏆 Huy Hiệu")
    badges = player.get_badges()
    if badges:
        badge_cols = st.columns(3)
        for i, badge in enumerate(badges[:6]):
            with badge_cols[i % 3]:
                st.markdown(f"<div style='font-size: 30px; text-align: center;'>{badge}</div>", unsafe_allow_html=True)
    else:
        st.info("Chưa có huy hiệu. Làm bài để nhận thưởng!")
    
    st.markdown("---")
    
    # ===== THÊM MỚI: Nút Xem Dashboard =====
    if st.button("📊 XEM PHÂN TÍCH HỌC TẬP", use_container_width=True, type="primary"):
        st.session_state.show_dashboard = True
        st.rerun()
    
    # Stats nhanh
    overall_stats = st.session_state.history_tracker.get_overall_stats()
    if overall_stats['total_questions'] > 0:
        st.markdown("### 📈 Thống Kê Nhanh")
        st.metric("📝 Tổng câu đã làm", overall_stats['total_questions'])
        st.metric("🎯 Độ chính xác", f"{overall_stats['accuracy']:.1%}")


if st.session_state.show_dashboard:
    render_weakness_dashboard(st.session_state.weakness_analyzer)

# ===== NẾU ĐANG LÀM QUIZ =====
elif st.session_state.quiz_active:
    quiz = st.session_state.current_quiz
    q_index = st.session_state.current_question
    
    if q_index < len(quiz):
        question_data = quiz[q_index]
        
        # Progress bar
        progress = (q_index + 1) / len(quiz)
        st.progress(progress)
        st.markdown(f"### Câu {q_index + 1}/{len(quiz)}")
        
        # Question
        st.markdown(f"## {question_data['question']}")
        
        # Start timer nếu chưa có
        if st.session_state.question_start_time is None:
            st.session_state.question_start_time = time.time()
        
        # Options
        selected = st.radio(
            "Chọn đáp án:",
            question_data['options'],
            key=f"q_{q_index}"
        )
        
        # Confidence level
        confidence = st.select_slider(
            "Bạn tự tin bao nhiêu với đáp án này?",
            options=["Không chắc 😕", "Tạm được 😐", "Khá chắc 😊", "Rất chắc 😎"],
            value="Tạm được 😐",
            key=f"conf_{q_index}"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            if st.button("✅ XÁC NHẬN", type="primary", use_container_width=True):
                # Calculate time spent
                time_spent = time.time() - st.session_state.question_start_time
                
                # Check answer
                correct = selected == question_data['correct_answer']
                
                # Map confidence
                confidence_map = {
                    "Không chắc 😕": "low",
                    "Tạm được 😐": "medium",
                    "Khá chắc 😊": "high",
                    "Rất chắc 😎": "high"
                }
                
                # ===== LOG VÀO HISTORY TRACKER =====
                st.session_state.history_tracker.log_answer(
                    session_id=st.session_state.current_session_id,
                    question_data={
                        'question_id': question_data.get('question_id', f"q_{q_index}_{hash(question_data['question']) % 10000}"),
                        'question': question_data['question'],
                        'subject': st.session_state.get('current_subject', 'Unknown'),
                        'chapter': st.session_state.get('current_chapter', 'Unknown'),
                        'topic': question_data.get('topic', 'General'),
                        'difficulty': st.session_state.get('current_difficulty', 'Medium 🤔'),
                        'concept_tags': question_data.get('concept_tags', [])
                    },
                    answer_data={
                        'selected': selected,
                        'correct_answer': question_data['correct_answer'],
                        'is_correct': correct,
                        'time_spent': time_spent,
                        'confidence': confidence_map[confidence]
                    }
                )
                
                # Save to answers list
                st.session_state.answers.append({
                    'question': question_data['question'],
                    'selected': selected,
                    'correct': question_data['correct_answer'],
                    'is_correct': correct,
                    'time_spent': time_spent
                })
                
                # Show feedback
                if correct:
                    st.success("🎉 CHÍNH XÁC!")
                    st.balloons()
                    st.session_state.score += 10
                else:
                    st.error(f"❌ SAI RỒI! Đáp án đúng: {question_data['correct_answer']}")
                    if 'explanation' in question_data:
                        with st.expander("💡 Xem giải thích"):
                            st.info(question_data['explanation'])
                
                # Reset timer
                st.session_state.question_start_time = None
                
                time.sleep(2)
                st.session_state.current_question += 1
                st.rerun()
    
    else:
        # ===== QUIZ FINISHED =====
        st.markdown("## 🎊 HOÀN THÀNH!")
        
        total = len(st.session_state.answers)
        correct = sum(1 for a in st.session_state.answers if a['is_correct'])
        accuracy = (correct / total) * 100 if total > 0 else 0
        
        # End session
        st.session_state.history_tracker.end_session(
            session_id=st.session_state.current_session_id,
            score=st.session_state.score
        )
        
        # Results
        result_col1, result_col2, result_col3, result_col4 = st.columns(4)
        
        with result_col1:
            st.metric("📊 Số câu đúng", f"{correct}/{total}")
        
        with result_col2:
            st.metric("🎯 Độ chính xác", f"{accuracy:.1f}%")
        
        with result_col3:
            xp_earned = correct * 10
            st.metric("⚡ XP kiếm được", xp_earned)
        
        with result_col4:
            avg_time = sum(a['time_spent'] for a in st.session_state.answers) / total
            st.metric("⏱️ Thời gian TB", f"{avg_time:.1f}s")
        
        # Update player profile
        st.session_state.player.add_xp(xp_earned)
        st.session_state.player.update_streak()
        st.session_state.player.total_score += st.session_state.score
        
        # Performance message
        if accuracy >= 90:
            st.success("🌟 XUẤT SẮC! Bạn thật tuyệt vời!")
        elif accuracy >= 70:
            st.info("👍 TỐT LẮM! Tiếp tục phát huy nhé!")
        else:
            st.warning("💪 CỐ GẮNG LÊN! Hãy xem lại phần yếu nhé!")
        
        # Show answers
        with st.expander("📝 Xem lại đáp án chi tiết"):
            for i, ans in enumerate(st.session_state.answers):
                icon = "✅" if ans['is_correct'] else "❌"
                st.markdown(f"{icon} **Câu {i+1}:** {ans['question']}")
                st.markdown(f"   - Bạn chọn: {ans['selected']}")
                if not ans['is_correct']:
                    st.markdown(f"   - Đáp án đúng: {ans['correct']}")
                st.markdown(f"   - Thời gian: {ans['time_spent']:.1f}s")
                st.markdown("---")

        
        
        # ===== THÊM MỚI: Phân tích nhanh =====
        st.markdown("### 🔍 Phân Tích Nhanh")
        
        priority_topics = st.session_state.weakness_analyzer.get_priority_topics(top_n=3)
        
        if priority_topics:
            st.warning(f"💡 **Gợi ý:** Bạn nên tập trung vào: **{', '.join(priority_topics)}**")

        # ── THÊM ĐÂY: NÚT XUẤT BÁO CÁO PDF ────────────────────────────
        st.markdown("---")
        if st.button("📄 Xuất báo cáo PDF", type="primary", use_container_width=True):
            with st.spinner("Đang tạo báo cáo..."):
                from services.report_generator import ReportGenerator  # import ở đây hoặc đầu file
                    
                pdf_file = ReportGenerator.generate_quiz_report(
                    player=st.session_state.player,
                    quiz_results=st.session_state.answers,  # list các câu trả lời
                    weakness_topics=st.session_state.weakness_analyzer.get_priority_topics(5)
                )
                    
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        label="Tải báo cáo PDF về máy",
                        data=f,
                        file_name=pdf_file,
                        mime="application/pdf"
                    )
        
        # Buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 XEM PHÂN TÍCH ĐẦY ĐỦ", use_container_width=True, type="primary"):
                st.session_state.quiz_active = False
                st.session_state.show_dashboard = True
                st.rerun()
        
        with col2:
            if st.button("🔄 CHƠI LẠI", use_container_width=True):
                st.session_state.quiz_active = False
                st.session_state.current_quiz = None
                st.rerun()
        
        with col3:
            if st.button("🏠 VỀ TRANG CHỦ", use_container_width=True):
                st.session_state.quiz_active = False
                st.session_state.current_quiz = None
                st.session_state.mode = None
                st.rerun()

# ===== TRANG CHỦ =====
else:
    if not st.session_state.mode:
        st.markdown("## 🎯 Chọn Nhiệm Vụ")
        
        mode_col1, mode_col2 = st.columns(2)
        
        with mode_col1:
            st.markdown("""
            <div class='metric-card'>
                <h3>📚 Chế Độ Học Tập</h3>
                <p>Upload sách và làm quiz theo chương</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 BẮT ĐẦU HỌC", key="study_mode", use_container_width=True):
                st.session_state.mode = "study"
                st.rerun()
        
        with mode_col2:
            st.markdown("""
            <div class='metric-card'>
                <h3>⚔️ Chế Độ Thử Thách</h3>
                <p>Đấu Boss và leo bảng xếp hạng</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔥 THÁCH ĐẤU", key="challenge_mode", use_container_width=True):
                st.session_state.mode = "challenge"
                st.rerun()
    
    # ===== STUDY MODE =====
    elif st.session_state.mode == "study":
        st.markdown("## 📖 Chọn Sách Giáo Khoa")
        
        # Chọn môn
        subject = st.selectbox(
            "Chọn môn học:",
            ["📐 Toán", "📝 Văn", "🇬🇧 Tiếng Anh", "🔬 Khoa Học Tự Nhiên", "🏛️ Lịch Sử", "🌍 Địa Lý"]
        )
        
        st.session_state.current_subject = subject
        
        # Map môn → folder
        subject_to_folder = {
            "📐 Toán": "toan",
            "📝 Văn": "van",
            "🇬🇧 Tiếng Anh": "tieng_anh",
            "🔬 Khoa Học Tự Nhiên": "khoa_hoc_tu_nhien",
            "🏛️ Lịch Sử": "lich_su",
            "🌍 Địa Lý": "dia_ly"
        }
        
        folder = subject_to_folder.get(subject, "")
        books_path = os.path.join("books", folder)
        
        # Lấy danh sách sách
        available_books = []
        if os.path.exists(books_path):
            available_books = [f for f in os.listdir(books_path) if f.lower().endswith(('.pdf', '.docx'))]
            available_books.sort()
        
        # UI chọn sách
        if available_books:
            st.success(f"📚 Tìm thấy **{len(available_books)} sách sẵn** cho môn {subject}")
            
            choice = st.radio(
                "Chọn nguồn sách:",
                ["📖 Dùng sách sẵn trong repo", "⬆️ Upload sách mới"],
                horizontal=True
            )
            
            if choice == "📖 Dùng sách sẵn trong repo":
                selected_book_name = st.selectbox("Chọn sách:", available_books)
                
                if st.button("📂 MỞ SÁCH NÀY", type="secondary", use_container_width=True):
                    book_path = os.path.join(books_path, selected_book_name)
                    
                    with st.spinner(f"📖 Đang đọc {selected_book_name}..."):
                        try:
                            content = doc_file(book_path)
                            
                            if content and len(content) > 100:
                                st.session_state.book_content = content
                                st.session_state.book_name = selected_book_name
                                st.success(f"✅ Đã đọc xong **{selected_book_name}** ({len(content):,} ký tự)")
                                st.rerun()
                            else:
                                st.error("❌ File rỗng hoặc không đọc được!")
                        except Exception as e:
                            st.error(f"❌ Lỗi đọc file: {e}")
            
            else:
                uploaded_file = st.file_uploader(
                    "Upload sách (PDF/DOCX):",
                    type=["pdf", "docx"],
                    key="upload_with_repo"
                )
                
                if uploaded_file:
                    with st.spinner(f"📖 Đang đọc {uploaded_file.name}..."):
                        content = doc_file(uploaded_file)
                        
                        if content and len(content) > 100:
                            st.session_state.book_content = content
                            st.session_state.book_name = uploaded_file.name
                            st.success(f"✅ Đã đọc xong **{uploaded_file.name}** ({len(content):,} ký tự)")
        
        else:
            st.warning(f"⚠️ Chưa có sách sẵn cho môn {subject}. Hãy upload sách!")
            
            uploaded_file = st.file_uploader(
                "Upload sách (PDF/DOCX):",
                type=["pdf", "docx"],
                key="upload_no_repo"
            )
            
            if uploaded_file:
                with st.spinner(f"📖 Đang đọc {uploaded_file.name}..."):
                    content = doc_file(uploaded_file)
                    
                    if content and len(content) > 100:
                        st.session_state.book_content = content
                        st.session_state.book_name = uploaded_file.name
                        st.success(f"✅ Đã đọc xong **{uploaded_file.name}** ({len(content):,} ký tự)")
        
        # UI tạo quiz
        if st.session_state.book_content and len(st.session_state.book_content) > 100:
            st.markdown("---")
            st.markdown(f"### 📖 Đang làm việc với: **{st.session_state.book_name}**")
            
            # Smart recommendations
            priority_topics = st.session_state.weakness_analyzer.get_priority_topics(top_n=3)
            
            if priority_topics:
                st.info(f"💡 **AI gợi ý:** Bạn nên tập trung vào: **{', '.join(priority_topics)}**")
            
            st.markdown("### ⚙️ Cấu hình Quiz")
            
            # Focus mode
            focus_mode = st.radio(
                "🎯 Chế độ học:",
                [
                    "🤖 Thích ứng (AI tự động)",
                    "💪 Tập trung điểm yếu",
                    "🎲 Tổng hợp ngẫu nhiên",
                    "🔥 Thử thách (Khó)"
                ],
                horizontal=True
            )
            
            focus_mode_map = {
                "🤖 Thích ứng (AI tự động)": "adaptive",
                "💪 Tập trung điểm yếu": "review_weak",
                "🎲 Tổng hợp ngẫu nhiên": "mixed",
                "🔥 Thử thách (Khó)": "challenge"
            }
            st.session_state.focus_mode = focus_mode_map[focus_mode]
            
            col1, col2 = st.columns(2)
            
            with col1:
                chapter = st.text_input("Nhập số chương (VD: 1, 2, 3) hoặc 'ALL':", "1")
                st.session_state.current_chapter = chapter
            
            with col2:
                if st.session_state.focus_mode == "challenge":
                    difficulty = "Hard 😰"
                    st.info("🔥 Độ khó: **Hard 😰** (Chế độ Thử thách)")
                else:
                    difficulty = st.select_slider(
                        "Chọn độ khó:",
                        options=["Easy 😊", "Medium 🤔", "Hard 😰", "Expert 💀"],
                        value="Medium 🤔"
                    )
                st.session_state.current_difficulty = difficulty
            
            num_questions = st.slider("Số câu hỏi:", 5, 20, 10)
            
            col_btn1, col_btn2 = st.columns([3, 1])
            with col_btn1:
                if st.button("🎮 TẠO QUIZ NGAY!", type="primary", use_container_width=True):
                    with st.spinner("🤖 AI đang sinh câu hỏi..."):
                        try:
                            quiz = st.session_state.adaptive_engine.generate_adaptive_quiz(
                                content=st.session_state.book_content,
                                subject=subject,
                                chapter=chapter,
                                num_questions=num_questions,
                                focus_mode=st.session_state.focus_mode
                            )

                            if quiz and len(quiz) > 0:
                                st.session_state.current_quiz = quiz
                                st.session_state.quiz_active = True

                                st.session_state.current_session_id = (
                                    st.session_state.history_tracker.create_session(
                                        subject=subject,
                                        chapter=chapter,
                                        difficulty=difficulty
                                    )
                                )

                                st.rerun()

                            else:
                                st.warning("Không tạo được câu hỏi nào. Vui lòng thử lại hoặc chọn chương khác.")

                        except Exception as e:
                            st.error(f"❌ Lỗi khi tạo quiz: {str(e)}")
                            # Optional: hiện traceback nếu bạn đang debug
                            # import traceback
                            # st.error(traceback.format_exc())

            with col_btn2:
                if st.button("🗑️ Đổi sách", use_container_width=True):
                    st.session_state.book_content = None
                    st.session_state.book_name = ""
                    st.rerun()

    # ===== CHALLENGE MODE =====
    elif st.session_state.mode == "challenge":
        st.markdown("## ⚔️ Đấu Trường Tri Thức")
        st.info("🚧 Coming Soon!")
    
        if st.button("🏠 Quay lại", use_container_width=True):
            st.session_state.mode = None
            st.rerun()
            
# ===== FOOTER =====
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: white; padding: 20px;'>
    <p>🎓 <b>SmartKid Arena</b> - Powered by AI (Gemini, Grok, DeepSeek)</p>
    <p style='font-size: 12px;'>Học mà như chơi game | Adaptive Learning System</p>
</div>
""", unsafe_allow_html=True)
