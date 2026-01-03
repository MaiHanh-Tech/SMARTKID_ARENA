import streamlit as st
import pandas as pd
import time
from datetime import datetime

# Import các module con
from quiz_engine import QuizEngine
from game_mechanics import GameMechanics
from player_profile import PlayerProfile

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
</style>
""", unsafe_allow_html=True)

# ===== KHỞI TẠO SESSION STATE =====
if "player" not in st.session_state:
    st.session_state.player = PlayerProfile("NHIMXU")

if "quiz_engine" not in st.session_state:
    st.session_state.quiz_engine = QuizEngine()

if "game" not in st.session_state:
    st.session_state.game = GameMechanics()

if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None

if "quiz_active" not in st.session_state:
    st.session_state.quiz_active = False

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
    
    # Settings
    if st.button("⚙️ Cài đặt"):
        st.session_state.show_settings = True

# ===== MAIN CONTENT =====
if not st.session_state.quiz_active:
    # ===== MODE SELECT =====
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
    
    with mode_col2:
        st.markdown("""
        <div class='metric-card'>
            <h3>⚔️ Chế Độ Thử Thách</h3>
            <p>Đấu Boss và leo bảng xếp hạng</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔥 THÁCH ĐẤU", key="challenge_mode", use_container_width=True):
            st.session_state.mode = "challenge"
    
    st.markdown("---")
    
    # ===== STUDY MODE =====
    if st.session_state.get("mode") == "study":
        st.markdown("## 📖 Chọn Sách Giáo Khoa")
        
        # Chọn môn
        subject = st.selectbox(
            "Chọn môn học:",
            ["📐 Toán", "📝 Văn", "🇬🇧 Tiếng Anh", "🔬 Khoa Học Tự Nhiên", "🏛️ Lịch Sử", "🌍 Địa Lý"]
        )
        
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
        
        import os
        books_path = os.path.join("books", folder)
        
        # Lấy danh sách sách sẵn
        available_books = []
        if os.path.exists(books_path):
            available_books = [f for f in os.listdir(books_path) if f.lower().endswith(('.pdf', '.docx'))]
            available_books.sort()
        
        # ===== KHỞI TẠO BIẾN =====
        content = None
        file_name = ""
        
        # ===== UI: CHỌN NGUỒN SÁCH =====
        if available_books:
            st.success(f"📚 Tìm thấy **{len(available_books)} sách sẵn** cho môn {subject}")
            
            # Radio: Chọn sách sẵn hay upload mới
            choice = st.radio(
                "Chọn nguồn sách:",
                ["📖 Dùng sách sẵn trong repo", "⬆️ Upload sách mới"],
                horizontal=True
            )
            
            if choice == "📖 Dùng sách sẵn trong repo":
                # Chọn sách từ dropdown
                selected_book_name = st.selectbox("Chọn sách:", available_books)
                
                if st.button("📂 MỞ SÁCH NÀY", type="secondary", use_container_width=True):
                    book_path = os.path.join(books_path, selected_book_name)
                    file_name = selected_book_name
    
                    # ✅ DEBUG: Hiện path
                    st.info(f"🔍 Debug: Đang thử đọc file từ: `{book_path}`")
    
                    # ✅ DEBUG: Kiểm tra file có tồn tại không
                    if not os.path.exists(book_path):
                        st.error(f"❌ File không tồn tại tại path: {book_path}")
                    else:
                        st.success(f"✅ File tồn tại! Size: {os.path.getsize(book_path):,} bytes")
    
                    with st.spinner(f"📖 Đang đọc {file_name}..."):
                        try:
                            from services.blocks.file_processor import doc_file
            
                            # Tạo fake UploadedFile để tương thích với doc_file
                            class FakeUploadedFile:
                                def __init__(self, path):
                                    self.name = os.path.basename(path)
                                    self._path = path
                
                                def read(self):
                                    with open(self._path, 'rb') as f:
                                        return f.read()
            
                            fake_file = FakeUploadedFile(book_path)
            
                            # ✅ DEBUG: Log trước khi gọi doc_file
                            st.info("🔧 Đang gọi hàm doc_file()...")
            
                            content = doc_file(fake_file)
            
                            # ✅ DEBUG: Hiện kết quả
                            if content:
                                st.success(f"✅ Đọc thành công! Độ dài: {len(content):,} ký tự")
                            else:
                                st.error("❌ doc_file() trả về rỗng!")
            
                        except Exception as e:
                            st.error(f"❌ Lỗi đọc file: {type(e).__name__}: {e}")
            
                            # ✅ DEBUG: Hiện full traceback
                            import traceback
                            st.code(traceback.format_exc())
            
                            content = None
            
            else:  # Upload mới
                uploaded_file = st.file_uploader(
                    "Upload sách (PDF/DOCX):",
                    type=["pdf", "docx"],
                    help="Tải lên sách giáo khoa hoặc sách bài tập",
                    key="upload_with_repo"
                )
                
                if uploaded_file:
                    file_name = uploaded_file.name
                    
                    with st.spinner(f"📖 Đang đọc {file_name}..."):
                        from services.blocks.file_processor import doc_file
                        content = doc_file(uploaded_file)
                        
                        if not content:
                            st.error("❌ Không đọc được file. Hãy thử file khác!")
        
        else:
            # Không có sách sẵn → Chỉ có option upload
            st.warning(f"⚠️ Chưa có sách sẵn cho môn {subject}. Hãy upload sách!")
            
            uploaded_file = st.file_uploader(
                "Upload sách (PDF/DOCX):",
                type=["pdf", "docx"],
                help="Tải lên sách giáo khoa hoặc sách bài tập",
                key="upload_no_repo"
            )
            
            if uploaded_file:
                file_name = uploaded_file.name
                
                with st.spinner(f"📖 Đang đọc {file_name}..."):
                    from services.blocks.file_processor import doc_file
                    content = doc_file(uploaded_file)
                    
                    if not content:
                        st.error("❌ Không đọc được file. Hãy thử file khác!")
        
        # ===== NẾU ĐÃ CÓ NỘI DUNG → TẠO QUIZ =====
        if content and len(content) > 100:
            st.success(f"✅ Đã đọc xong **{file_name}** ({len(content):,} ký tự)")
            
            st.markdown("---")
            st.markdown("### ⚙️ Cấu hình Quiz")
            
            col1, col2 = st.columns(2)
            
            with col1:
                chapter = st.text_input(
                    "Nhập số chương (VD: 1, 2, 3) hoặc 'ALL' để ôn toàn môn:",
                    "1",
                    help="Nhập số chương bạn muốn ôn tập"
                )
            
            with col2:
                difficulty = st.select_slider(
                    "Chọn độ khó:",
                    options=["Easy 😊", "Medium 🤔", "Hard 😰", "Expert 💀"],
                    value="Medium 🤔"
                )
            
            num_questions = st.slider("Số câu hỏi:", 5, 20, 10)
            
            if st.button("🎮 TẠO QUIZ NGAY!", type="primary", use_container_width=True):
                with st.spinner("🤖 AI đang sinh câu hỏi... (Có thể mất 10-30 giây)"):
                    quiz = st.session_state.quiz_engine.generate_quiz(
                        content=content,
                        subject=subject,
                        chapter=chapter,
                        difficulty=difficulty,
                        num_questions=num_questions
                    )
                    
                    if quiz:
                        st.session_state.current_quiz = quiz
                        st.session_state.quiz_active = True
                        st.session_state.current_question = 0
                        st.session_state.score = 0
                        st.session_state.answers = []
                        st.rerun()
                    else:
                        st.error("❌ Không thể tạo quiz. Hãy thử lại!")
    
    # ===== CHALLENGE MODE =====
    elif st.session_state.get("mode") == "challenge":
        st.markdown("## ⚔️ Đấu Trường Tri Thức")
        st.info("🚧 Chức năng đang phát triển. Coming soon!")

else:
    # ===== QUIZ PLAYING =====
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
        
        # Options
        selected = st.radio(
            "Chọn đáp án:",
            question_data['options'],
            key=f"q_{q_index}"
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            if st.button("✅ XÁC NHẬN", type="primary", use_container_width=True):
                # Check answer
                correct = selected == question_data['correct_answer']
                st.session_state.answers.append({
                    'question': question_data['question'],
                    'selected': selected,
                    'correct': question_data['correct_answer'],
                    'is_correct': correct
                })
                
                if correct:
                    st.success("🎉 CHÍNH XÁC!")
                    st.balloons()
                    st.session_state.score += 10
                else:
                    st.error(f"❌ SAI RỒI! Đáp án đúng: {question_data['correct_answer']}")
                
                time.sleep(2)
                st.session_state.current_question += 1
                st.rerun()
    
    else:
        # ===== QUIZ FINISHED =====
        st.markdown("## 🎊 HOÀN THÀNH!")
        
        total = len(st.session_state.answers)
        correct = sum(1 for a in st.session_state.answers if a['is_correct'])
        accuracy = (correct / total) * 100 if total > 0 else 0
        
        # Results
        result_col1, result_col2, result_col3 = st.columns(3)
        
        with result_col1:
            st.metric("📊 Số câu đúng", f"{correct}/{total}")
        
        with result_col2:
            st.metric("🎯 Độ chính xác", f"{accuracy:.1f}%")
        
        with result_col3:
            xp_earned = correct * 10
            st.metric("⚡ XP kiếm được", xp_earned)
        
        # Update player profile
        st.session_state.player.add_xp(xp_earned)
        st.session_state.player.update_streak()
        st.session_state.player.total_score += st.session_state.score
        
        # Show answers
        with st.expander("📝 Xem lại đáp án"):
            for i, ans in enumerate(st.session_state.answers):
                icon = "✅" if ans['is_correct'] else "❌"
                st.markdown(f"{icon} **Câu {i+1}:** {ans['question']}")
                st.markdown(f"   - Bạn chọn: {ans['selected']}")
                if not ans['is_correct']:
                    st.markdown(f"   - Đáp án đúng: {ans['correct']}")
        
        # Buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 CHƠI LẠI", use_container_width=True):
                st.session_state.quiz_active = False
                st.session_state.current_quiz = None
                st.rerun()
        
        with col2:
            if st.button("🏠 VỀ TRANG CHỦ", use_container_width=True):
                st.session_state.quiz_active = False
                st.session_state.current_quiz = None
                st.session_state.mode = None
                st.rerun()
