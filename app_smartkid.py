"""
SmartKid Arena - Game-based Learning Platform
BEAUTIFUL EDITION - Designed for Gen Alpha 🌈
"""

import streamlit as st
import pandas as pd
import time
from datetime import datetime
import uuid
import os

# ===== IMPORTS =====
from quiz_engine import QuizEngine
from game_mechanics import GameMechanics
from player_profile import PlayerProfile
from services.blocks.history_tracker import LearningHistoryTracker
from services.blocks.weakness_analyzer import WeaknessAnalyzer
from services.blocks.adaptive_quiz_engine import AdaptiveQuizEngine
from services.blocks.file_processor import doc_file
from pages.student_dashboard import render_weakness_dashboard

# ===== CẤU HÌNH TRANG =====
st.set_page_config(
    page_title="SmartKid Arena 🎮",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== SUPER BEAUTIFUL CSS 🎨 =====
st.markdown("""
<style>
    /* === BACKGROUND ANIMATED === */
    @import url('https://fonts.googleapis.com/css2?family=Fredoka+One&family=Poppins:wght@400;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(-45deg, #ee7752, #e73c7e, #23a6d5, #23d5ab);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* === GLASSMORPHISM CARDS === */
    .glass-card {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 2px solid rgba(255, 255, 255, 0.3);
        padding: 25px;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        transition: all 0.3s ease;
        animation: float 3s ease-in-out infinite;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.5);
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    
    /* === NEON TEXT === */
    .neon-title {
        font-family: 'Fredoka One', cursive;
        font-size: 3.5rem;
        text-align: center;
        color: #fff;
        text-shadow: 
            0 0 10px #fff,
            0 0 20px #fff,
            0 0 30px #fff,
            0 0 40px #ff00de,
            0 0 70px #ff00de,
            0 0 80px #ff00de,
            0 0 100px #ff00de,
            0 0 150px #ff00de;
        animation: flicker 1.5s infinite alternate;
    }
    
    @keyframes flicker {
        0%, 18%, 22%, 25%, 53%, 57%, 100% {
            text-shadow: 
                0 0 10px #fff,
                0 0 20px #fff,
                0 0 30px #fff,
                0 0 40px #ff00de,
                0 0 70px #ff00de;
        }
        20%, 24%, 55% {        
            text-shadow: none;
        }
    }
    
    /* === MODERN BUTTONS === */
    .stButton>button {
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 1.1rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 18px 40px;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        transition: all 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        position: relative;
        overflow: hidden;
    }
    
    .stButton>button:before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.5s;
    }
    
    .stButton>button:hover {
        transform: scale(1.05);
        box-shadow: 0 15px 40px rgba(102, 126, 234, 0.6);
    }
    
    .stButton>button:hover:before {
        left: 100%;
    }
    
    /* === METRIC CARDS === */
    .metric-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.7) 100%);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        border: 3px solid rgba(255,255,255,0.5);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px) rotate(2deg);
    }
    
    /* === PROGRESS BAR RAINBOW === */
    .stProgress > div > div {
        background: linear-gradient(90deg, 
            #ff0000, #ff7f00, #ffff00, #00ff00, 
            #0000ff, #4b0082, #9400d3);
        background-size: 200% 200%;
        animation: rainbow 2s linear infinite;
    }
    
    @keyframes rainbow {
        0% { background-position: 0% 50%; }
        100% { background-position: 100% 50%; }
    }
    
    /* === SIDEBAR GRADIENT === */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, 
            rgba(102, 126, 234, 0.9) 0%, 
            rgba(118, 75, 162, 0.9) 100%);
        backdrop-filter: blur(10px);
    }
    
    [data-testid="stSidebar"] .metric-card {
        background: rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
        color: white;
    }
    
    /* === EMOJI ANIMATION === */
    .emoji-bounce {
        display: inline-block;
        animation: bounce 1s ease infinite;
    }
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-20px); }
    }
    
    /* === MODE CARDS === */
    .mode-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.2) 0%, rgba(255,255,255,0.1) 100%);
        backdrop-filter: blur(10px);
        border-radius: 25px;
        padding: 30px;
        border: 3px solid rgba(255,255,255,0.4);
        text-align: center;
        transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        cursor: pointer;
    }
    
    .mode-card:hover {
        transform: scale(1.05) rotate(-2deg);
        border-color: #fff;
        background: linear-gradient(135deg, rgba(255,255,255,0.3) 0%, rgba(255,255,255,0.2) 100%);
    }
    
    /* === PARTICLE BACKGROUND (Optional) === */
    .particles {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: -1;
    }
    
    /* === CUSTOM FONTS === */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Fredoka One', cursive !important;
        color: white !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    p, div, span, .stMarkdown p {
        font-family: 'Poppins', sans-serif !important;
    }
    
    /* === BADGES GLOW === */
    .badge-glow {
        filter: drop-shadow(0 0 10px #ffd700);
        animation: glow 1.5s ease-in-out infinite;
    }
    
    @keyframes glow {
        0%, 100% { filter: drop-shadow(0 0 10px #ffd700); }
        50% { filter: drop-shadow(0 0 20px #ffd700); }
    }
    
    /* === CONFETTI EFFECT (when correct answer) === */
    @keyframes confetti-fall {
        0% { transform: translateY(-100vh) rotate(0deg); opacity: 1; }
        100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
    }
</style>
""", unsafe_allow_html=True)

# ===== KHỞI TẠO SESSION STATE =====
def init_session_state():
    if "player" not in st.session_state:
        if "player_name" not in st.session_state:
            # === BEAUTIFUL WELCOME SCREEN ===
            st.markdown("""
            <div style='text-align: center; padding: 50px;'>
                <h1 class='neon-title'>🌟 SMARTKID ARENA 🌟</h1>
                <p style='font-size: 1.5rem; color: white; font-weight: 600; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>
                    Học mà như chơi game! 🎮✨
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
                st.markdown("### 👋 Chào mừng chiến binh nhỏ!")
                player_name = st.text_input(
                    "Nhập tên của bạn:", 
                    placeholder="Ví dụ: Minh, Lan, Bé Bảo...",
                    label_visibility="collapsed"
                )
                
                if st.button("🚀 BẮT ĐẦU PHIÊU LƯU!", type="primary", use_container_width=True):
                    if player_name.strip():
                        st.session_state.player_name = player_name.strip()
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Vui lòng nhập tên nhé!")
                st.markdown("</div>", unsafe_allow_html=True)
            st.stop()
        
        player_name = st.session_state.player_name
        st.session_state.player = PlayerProfile(player_name)
    
    # Quiz engine
    if "quiz_engine" not in st.session_state:
        st.session_state.quiz_engine = QuizEngine()
    
    if "game" not in st.session_state:
        st.session_state.game = GameMechanics()
    
    # History & Analytics
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
    for key, default in [
        ("current_quiz", None),
        ("quiz_active", False),
        ("current_question", 0),
        ("score", 0),
        ("answers", []),
        ("book_content", None),
        ("book_name", ""),
        ("current_session_id", None),
        ("question_start_time", None),
        ("show_dashboard", False),
        ("mode", None),
        ("focus_mode", "adaptive")
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()

# ===== BEAUTIFUL HEADER =====
st.markdown("""
<div style='text-align: center; padding: 20px;'>
    <h1 class='neon-title'>
        <span class='emoji-bounce'>🎮</span> 
        SMARTKID ARENA 
        <span class='emoji-bounce'>🎯</span>
    </h1>
    <p style='font-size: 1.2rem; color: white; font-weight: 600; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>
        Học mà như chơi game! ✨🚀
    </p>
</div>
""", unsafe_allow_html=True)

# ===== BEAUTIFUL SIDEBAR =====
with st.sidebar:
    player = st.session_state.player
    
    # Avatar (can add custom avatars later)
    st.markdown(f"""
    <div class='metric-card' style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;'>
        <div style='font-size: 4rem; margin-bottom: 10px;'>🦸</div>
        <h2 style='color: white; margin: 0;'>{player.name}</h2>
        <p style='color: rgba(255,255,255,0.8); margin: 5px 0;'>Level {player.level} Warrior</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Stats with icons
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size: 2.5rem;'>⚡</div>
            <p style='font-size: 0.9rem; color: #666; margin: 5px 0;'>XP</p>
            <h3 style='color: #667eea; margin: 0;'>{player.xp}/{player.xp_to_next_level()}</h3>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size: 2.5rem;'>🔥</div>
            <p style='font-size: 0.9rem; color: #666; margin: 5px 0;'>Streak</p>
            <h3 style='color: #ff6b6b; margin: 0;'>{player.streak} ngày</h3>
        </div>
        """, unsafe_allow_html=True)
    
    st.progress(player.xp / player.xp_to_next_level())
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class='metric-card'>
        <div style='font-size: 2.5rem;'>💎</div>
        <p style='font-size: 0.9rem; color: #666; margin: 5px 0;'>Total Score</p>
        <h3 style='color: #4ecdc4; margin: 0;'>{player.total_score:,}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Badges with glow effect
    st.markdown("### 🏆 Huy Hiệu")
    badges = player.get_badges()
    if badges:
        badge_html = "<div style='display: flex; flex-wrap: wrap; justify-content: center; gap: 10px;'>"
        for badge in badges[:6]:
            badge_html += f"<div class='badge-glow' style='font-size: 3rem;'>{badge}</div>"
        badge_html += "</div>"
        st.markdown(badge_html, unsafe_allow_html=True)
    else:
        st.info("Chưa có huy hiệu. Làm bài để nhận thưởng!")
    
    st.markdown("---")
    
    # Dashboard button with gradient
    if st.button("📊 XEM PHÂN TÍCH", use_container_width=True, type="primary"):
        st.session_state.show_dashboard = True
        st.rerun()
    
    # Quick stats
    overall_stats = st.session_state.history_tracker.get_overall_stats()
    if overall_stats['total_questions'] > 0:
        st.markdown(f"""
        <div class='glass-card' style='margin-top: 20px; color: white;'>
            <p style='font-size: 0.9rem; margin: 5px 0;'>📝 Tổng câu: <b>{overall_stats['total_questions']}</b></p>
            <p style='font-size: 0.9rem; margin: 5px 0;'>🎯 Độ chính xác: <b>{overall_stats['accuracy']:.1%}</b></p>
        </div>
        """, unsafe_allow_html=True)

# ===== MAIN CONTENT =====

if st.session_state.show_dashboard:
    render_weakness_dashboard(st.session_state.weakness_analyzer)

elif st.session_state.quiz_active:
    # === QUIZ UI ===
    quiz = st.session_state.current_quiz
    q_index = st.session_state.current_question
    
    if q_index < len(quiz):
        question_data = quiz[q_index]
        
        # Beautiful progress
        progress = (q_index + 1) / len(quiz)
        st.progress(progress)
        
        st.markdown(f"""
        <div class='glass-card' style='text-align: center; margin: 20px 0;'>
            <h2 style='color: white; margin: 0;'>Câu {q_index + 1} / {len(quiz)}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Question card
        st.markdown(f"""
        <div class='glass-card' style='margin: 30px 0;'>
            <h2 style='color: white; font-size: 1.8rem;'>{question_data['question']}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Timer
        if st.session_state.question_start_time is None:
            st.session_state.question_start_time = time.time()
        
        # Options with custom styling
        selected = st.radio(
            "Chọn đáp án:",
            question_data['options'],
            key=f"q_{q_index}",
            label_visibility="collapsed"
        )
        
        # Confidence slider
        confidence = st.select_slider(
            "Độ tự tin:",
            options=["😕 Không chắc", "😐 Tạm được", "😊 Khá chắc", "😎 Rất chắc"],
            value="😐 Tạm được",
            key=f"conf_{q_index}"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("✅ XÁC NHẬN", type="primary", use_container_width=True):
                time_spent = time.time() - st.session_state.question_start_time
                correct = selected == question_data['correct_answer']
                
                confidence_map = {
                    "😕 Không chắc": "low",
                    "😐 Tạm được": "medium",
                    "😊 Khá chắc": "high",
                    "😎 Rất chắc": "high"
                }
                
                # Log answer
                st.session_state.history_tracker.log_answer(
                    session_id=st.session_state.current_session_id,
                    question_data={
                        'question_id': question_data.get('question_id', f"q_{q_index}_{hash(question_data['question']) % 10000}"),
                        'question': question_data['question'],
                        'subject': st.session_state.get('current_subject', 'Unknown'),
                        'chapter': st.session_state.get('current_chapter', 'Unknown'),
                        'topic': question_data.get('topic', 'General'),
                        'difficulty': st.session_state.get('current_difficulty', 'Medium'),
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
                
                st.session_state.answers.append({
                    'question': question_data['question'],
                    'selected': selected,
                    'correct': question_data['correct_answer'],
                    'is_correct': correct,
                    'time_spent': time_spent
                })
                
                # Feedback
                if correct:
                    st.success("🎉 CHÍNH XÁC! TUYỆT VỜI!")
                    st.balloons()
                    st.session_state.score += 10
                else:
                    st.error(f"❌ Chưa đúng! Đáp án: {question_data['correct_answer']}")
                    if 'explanation' in question_data:
                        with st.expander("💡 Xem giải thích"):
                            st.info(question_data['explanation'])
                
                st.session_state.question_start_time = None
                time.sleep(2)
                st.session_state.current_question += 1
                st.rerun()
    
    else:
        # === QUIZ FINISHED ===
        st.markdown("<h1 style='text-align: center;'>🎊 HOÀN THÀNH! 🎊</h1>", unsafe_allow_html=True)
        
        total = len(st.session_state.answers)
        correct = sum(1 for a in st.session_state.answers if a['is_correct'])
        accuracy = (correct / total) * 100 if total > 0 else 0
        
        st.session_state.history_tracker.end_session(
            session_id=st.session_state.current_session_id,
            score=st.session_state.score
        )
        
        # Beautiful results
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class='glass-card' style='text-align: center;'>
                <div style='font-size: 3rem;'>📊</div>
                <h3 style='color: white;'>{correct}/{total}</h3>
                <p style='color: rgba(255,255,255,0.8);'>Câu đúng</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class='glass-card' style='text-align: center;'>
                <div style='font-size: 3rem;'>🎯</div>
                <h3 style='color: white;'>{accuracy:.1f}%</h3>
                <p style='color: rgba(255,255,255,0.8);'>Chính xác</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            xp_earned = correct * 10
            st.markdown(f"""
            <div class='glass-card' style='text-align: center;'>
                <div style='font-size: 3rem;'>⚡</div>
                <h3 style='color: white;'>+{xp_earned}</h3>
                <p style='color: rgba(255,255,255,0.8);'>XP</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            avg_time = sum(a['time_spent'] for a in st.session_state.answers) / total
            st.markdown(f"""
            <div class='glass-card' style='text-align: center;'>
                <div style='font-size: 3rem;'>⏱️</div>
                <h3 style='color: white;'>{avg_time:.1f}s</h3>
                <p style='color: rgba(255,255,255,0.8);'>Trung bình</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Update player
        st.session_state.player.add_xp(xp_earned)
        st.session_state.player.update_streak()
        st.session_state.player.total_score += st.session_state.score
        
        # Performance message
        if accuracy >= 90:
            st.success("🌟 XUẤT SẮC! Bạn thật tuyệt vời!")
            st.balloons()
        elif accuracy >= 70:
            st.info("👍 TỐT LẮM! Tiếp tục phát huy nhé!")
        else:
            st.warning("💪 CỐ GẮNG LÊN! Hãy xem lại phần yếu nhé!")
        
        # Buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 XEM PHÂN TÍCH", use_container_width=True, type="primary"):
                st.session_state.quiz_active = False
                st.session_state.show_dashboard = True
                st.rerun()
        
        with col2:
            if st.button("🔄 CHƠI LẠI", use_container_width=True):
                st.session_state.quiz_active = False
                st.session_state.current_quiz = None
                st.rerun()
        
        with col3:
            if st.button("🏠 TRANG CHỦ", use_container_width=True):
                st.session_state.quiz_active = False
                st.session_state.current_quiz = None
                st.session_state.mode = None
                st.rerun()

else:
    if not st.session_state.mode:
        # === BEAUTIFUL MODE SELECT ===
        st.markdown("<h2 style='text-align: center; color: white;'>🎯 Chọn Nhiệm Vụ</h2>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class='mode-card'>
                <div style='font-size: 5rem; margin-bottom: 20px;'>📚</div>
                <h2 style='color: white; margin: 10px 0;'>Chế Độ Học Tập</h2>
                <p style='color: rgba(255,255,255,0.9); font-size: 1.1rem;'>Upload sách và làm quiz theo chương</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 BẮT ĐẦU HỌC", key="study", use_container_width=True):
                st.session_state.mode = "study"
                st.rerun()
        
        with col2:
            st.markdown("""
            <div class='mode-card'>
                <div style='font-size: 5rem; margin-bottom: 20px;'>⚔️</div>
                <h2 style='color: white; margin: 10px 0;'>Chế Độ Thử Thách</h2>
                <p style='color: rgba(255,255,255,0.9); font-size: 1.1rem;'>Đấu Boss và leo bảng xếp hạng</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔥 THÁCH ĐẤU", key="challenge", use_container_width=True):
                st.session_state.mode = "challenge"
                st.rerun()
    
    # === STUDY MODE ===
    elif st.session_state.mode == "study":
        st.markdown("<h2 style='text-align: center; color: white;'>📖 Chọn Sách Giáo Khoa</h2>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # === SUBJECT SELECTOR WITH ICONS ===
        st.markdown("""
        <div class='glass-card' style='margin: 20px auto; max-width: 800px;'>
            <h3 style='color: white; text-align: center; margin-bottom: 20px;'>Chọn môn học của bạn</h3>
        """, unsafe_allow_html=True)
        
        subject_options = {
            "📐 Toán": {"icon": "🔢", "color": "#667eea", "folder": "toan"},
            "📝 Văn": {"icon": "✍️", "color": "#ff6b6b", "folder": "van"},
            "🇬🇧 Tiếng Anh": {"icon": "🗣️", "color": "#4ecdc4", "folder": "tieng_anh"},
            "🔬 Khoa Học": {"icon": "🧪", "color": "#95e1d3", "folder": "khoa_hoc_tu_nhien"},
            "🏛️ Sử Địa": {"icon": "🗺️", "color": "#f38181", "folder": "su_dia"},
            "🌐 Công Nghệ": {"icon": "💻", "color": "#aa96da", "folder": "cong_nghe"}
        }
        
        # Create subject buttons
        cols = st.columns(3)
        selected_subject = None
        
        for idx, (subject, info) in enumerate(subject_options.items()):
            with cols[idx % 3]:
                if st.button(
                    f"{info['icon']} {subject.split(' ', 1)[1]}", 
                    key=f"subj_{idx}",
                    use_container_width=True
                ):
                    selected_subject = subject
                    st.session_state.current_subject = subject
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Get current subject
        if not selected_subject and "current_subject" in st.session_state:
            selected_subject = st.session_state.current_subject
        
        if selected_subject:
            folder = subject_options[selected_subject]["folder"]
            books_path = os.path.join("books", folder)
            
            # Get available books
            available_books = []
            if os.path.exists(books_path):
                available_books = [f for f in os.listdir(books_path) 
                                 if f.lower().endswith(('.pdf', '.docx'))]
                available_books.sort()
            
            # === BOOK SELECTION UI ===
            if available_books:
                st.markdown(f"""
                <div class='glass-card' style='margin: 30px auto; max-width: 900px;'>
                    <div style='text-align: center; margin-bottom: 20px;'>
                        <div style='font-size: 3rem;'>📚</div>
                        <h3 style='color: white;'>Tìm thấy {len(available_books)} sách sẵn!</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                # Radio choice with beautiful styling
                choice = st.radio(
                    "Chọn nguồn sách:",
                    ["📖 Dùng sách có sẵn", "⬆️ Upload sách mới"],
                    horizontal=True
                )
                
                if choice == "📖 Dùng sách có sẵn":
                    # Book grid display
                    st.markdown("<div style='margin: 20px 0;'>", unsafe_allow_html=True)
                    
                    # Display books in grid
                    book_cols = st.columns(2)
                    for idx, book in enumerate(available_books):
                        with book_cols[idx % 2]:
                            if st.button(
                                f"📕 {book}", 
                                key=f"book_{idx}",
                                use_container_width=True
                            ):
                                book_path = os.path.join(books_path, book)
                                
                                with st.spinner(f"📖 Đang đọc {book}..."):
                                    try:
                                        content = doc_file(book_path)
                                        
                                        if content and len(content) > 100:
                                            st.session_state.book_content = content
                                            st.session_state.book_name = book
                                            st.success(f"✅ Đã đọc xong **{book}**!")
                                            st.balloons()
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("❌ File rỗng!")
                                    except Exception as e:
                                        st.error(f"❌ Lỗi: {e}")
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                else:
                    # Upload UI
                    uploaded_file = st.file_uploader(
                        "Chọn file sách (PDF/DOCX):",
                        type=["pdf", "docx"],
                        key="upload_file"
                    )
                    
                    if uploaded_file:
                        with st.spinner("📖 Đang xử lý..."):
                            content = doc_file(uploaded_file)
                            
                            if content and len(content) > 100:
                                st.session_state.book_content = content
                                st.session_state.book_name = uploaded_file.name
                                st.success(f"✅ Upload thành công!")
                                st.balloons()
                
                st.markdown("</div>", unsafe_allow_html=True)
            
            else:
                # No books available - upload only
                st.markdown("""
                <div class='glass-card' style='margin: 30px auto; max-width: 700px; text-align: center;'>
                    <div style='font-size: 4rem; margin-bottom: 20px;'>📤</div>
                    <h3 style='color: white;'>Chưa có sách cho môn này</h3>
                    <p style='color: rgba(255,255,255,0.8); font-size: 1.1rem;'>
                        Hãy upload sách của bạn nhé!
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                uploaded_file = st.file_uploader(
                    "Chọn file sách (PDF/DOCX):",
                    type=["pdf", "docx"],
                    key="upload_only"
                )
                
                if uploaded_file:
                    with st.spinner("📖 Đang xử lý..."):
                        content = doc_file(uploaded_file)
                        
                        if content and len(content) > 100:
                            st.session_state.book_content = content
                            st.session_state.book_name = uploaded_file.name
                            st.success(f"✅ Upload thành công!")
                            st.balloons()
            
            # === QUIZ CONFIGURATION (when book is loaded) ===
            if st.session_state.book_content and len(st.session_state.book_content) > 100:
                st.markdown("<br><br>", unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class='glass-card' style='margin: 30px auto; max-width: 900px;'>
                    <div style='text-align: center; margin-bottom: 20px;'>
                        <div style='font-size: 3rem;'>📖</div>
                        <h3 style='color: white;'>{st.session_state.book_name}</h3>
                        <p style='color: rgba(255,255,255,0.8);'>{len(st.session_state.book_content):,} ký tự</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # === AI RECOMMENDATIONS ===
                priority_topics = st.session_state.weakness_analyzer.get_priority_topics(top_n=3)
                
                if priority_topics:
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, rgba(255,193,7,0.3), rgba(255,152,0,0.3)); 
                                padding: 15px; border-radius: 15px; margin: 20px 0; border: 2px solid rgba(255,193,7,0.5);'>
                        <div style='text-align: center;'>
                            <span style='font-size: 2rem;'>💡</span>
                            <p style='color: white; font-weight: 600; margin: 10px 0;'>
                                AI gợi ý: Tập trung vào <b>{', '.join(priority_topics)}</b>
                            </p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<h3 style='color: white; text-align: center;'>⚙️ Cấu hình Quiz</h3>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
                # === FOCUS MODE SELECTOR ===
                st.markdown("<p style='color: white; font-weight: 600; text-align: center;'>🎯 Chọn chế độ học:</p>", unsafe_allow_html=True)
                
                focus_modes = [
                    {"name": "🤖 Thích ứng", "desc": "AI tự động", "mode": "adaptive", "color": "#667eea"},
                    {"name": "💪 Điểm yếu", "desc": "Tập trung luyện", "mode": "review_weak", "color": "#ff6b6b"},
                    {"name": "🎲 Tổng hợp", "desc": "Ngẫu nhiên", "mode": "mixed", "color": "#4ecdc4"},
                    {"name": "🔥 Thử thách", "desc": "Siêu khó", "mode": "challenge", "color": "#f38181"}
                ]
                
                mode_cols = st.columns(4)
                for idx, mode_info in enumerate(focus_modes):
                    with mode_cols[idx]:
                        if st.button(
                            f"{mode_info['name']}\n{mode_info['desc']}", 
                            key=f"mode_{idx}",
                            use_container_width=True
                        ):
                            st.session_state.focus_mode = mode_info['mode']
                
                # Get current focus mode
                current_mode_name = next(
                    (m['name'] for m in focus_modes if m['mode'] == st.session_state.focus_mode),
                    "🤖 Thích ứng"
                )
                
                st.markdown(f"""
                <div style='text-align: center; margin: 15px 0;'>
                    <p style='color: white; font-size: 1.1rem;'>
                        Đã chọn: <b>{current_mode_name}</b>
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # === CHAPTER & DIFFICULTY ===
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("""
                    <div style='background: rgba(255,255,255,0.1); padding: 15px; 
                                border-radius: 15px; border: 2px solid rgba(255,255,255,0.3);'>
                        <p style='color: white; font-weight: 600; text-align: center; margin-bottom: 10px;'>
                            📚 Chương
                        </p>
                    """, unsafe_allow_html=True)
                    
                    chapter = st.text_input(
                        "Nhập số chương (1, 2, 3) hoặc 'ALL':",
                        value="1",
                        key="chapter_input",
                        label_visibility="collapsed"
                    )
                    st.session_state.current_chapter = chapter
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with col2:
                    st.markdown("""
                    <div style='background: rgba(255,255,255,0.1); padding: 15px; 
                                border-radius: 15px; border: 2px solid rgba(255,255,255,0.3);'>
                        <p style='color: white; font-weight: 600; text-align: center; margin-bottom: 10px;'>
                            ⚡ Độ khó
                        </p>
                    """, unsafe_allow_html=True)
                    
                    if st.session_state.focus_mode == "challenge":
                        st.markdown("""
                        <div style='text-align: center; padding: 10px;'>
                            <p style='color: #ff6b6b; font-size: 1.2rem; font-weight: 700;'>
                                🔥 Hard (Chế độ Thử thách)
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                        difficulty = "Hard 😰"
                    else:
                        difficulty = st.select_slider(
                            "Chọn độ khó:",
                            options=["Easy 😊", "Medium 🤔", "Hard 😰", "Expert 💀"],
                            value="Medium 🤔",
                            label_visibility="collapsed"
                        )
                    
                    st.session_state.current_difficulty = difficulty
                    st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # === NUMBER OF QUESTIONS ===
                st.markdown("""
                <div style='background: rgba(255,255,255,0.1); padding: 20px; 
                            border-radius: 15px; border: 2px solid rgba(255,255,255,0.3); margin: 20px 0;'>
                    <p style='color: white; font-weight: 600; text-align: center; margin-bottom: 15px;'>
                        🎯 Số câu hỏi
                    </p>
                """, unsafe_allow_html=True)
                
                num_questions = st.slider(
                    "Chọn số câu:",
                    min_value=5,
                    max_value=20,
                    value=10,
                    key="num_q",
                    label_visibility="collapsed"
                )
                
                st.markdown(f"""
                <div style='text-align: center;'>
                    <p style='color: white; font-size: 1.5rem; font-weight: 700;'>
                        {num_questions} câu hỏi
                    </p>
                </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # === ACTION BUTTONS ===
                btn_col1, btn_col2 = st.columns([3, 1])
                
                with btn_col1:
                    if st.button("🎮 TẠO QUIZ NGAY!", type="primary", use_container_width=True):
                        with st.spinner("🤖 AI đang sinh câu hỏi... ✨"):
                            # Add progress animation
                            progress_bar = st.progress(0)
                            for i in range(100):
                                time.sleep(0.01)
                                progress_bar.progress(i + 1)
                            
                            try:
                                quiz = st.session_state.adaptive_engine.generate_adaptive_quiz(
                                    content=st.session_state.book_content,
                                    subject=selected_subject,
                                    chapter=chapter,
                                    num_questions=num_questions,
                                    focus_mode=st.session_state.focus_mode
                                )
                                
                                if quiz and len(quiz) > 0:
                                    st.session_state.current_quiz = quiz
                                    st.session_state.quiz_active = True
                                    st.session_state.current_question = 0
                                    st.session_state.score = 0
                                    st.session_state.answers = []
                                    
                                    st.session_state.current_session_id = (
                                        st.session_state.history_tracker.create_session(
                                            subject=selected_subject,
                                            chapter=chapter,
                                            difficulty=difficulty
                                        )
                                    )
                                    
                                    st.success("✅ Quiz đã sẵn sàng!")
                                    st.balloons()
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.warning("⚠️ Không tạo được câu hỏi. Thử lại nhé!")
                            
                            except Exception as e:
                                st.error(f"❌ Lỗi: {str(e)}")
                                
                                # Fallback
                                st.warning("🔄 Đang dùng chế độ dự phòng...")
                                quiz = st.session_state.quiz_engine.generate_quiz(
                                    content=st.session_state.book_content,
                                    subject=selected_subject,
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
                                    
                                    # Thay thế đoạn code cũ bằng:
                                    tracker = st.session_state.get('history_tracker')  # an toàn, không raise error nếu không tồn tại

                                    if tracker is not None:
                                        st.session_state.current_session_id = tracker.create_session(
                                            subject=selected_subject,
                                            chapter=chapter,
                                            difficulty=difficulty
                                        )
                                    else:
                                        st.warning("⚠️ Bộ theo dõi lịch sử chưa được khởi tạo. Quiz vẫn chạy nhưng không lưu lịch sử.")
                                        st.session_state.current_session_id = f"temp_{uuid.uuid4().hex[:8]}"  # fake tạm thời
    
                
                with btn_col2:
                    if st.button("🗑️ Đổi sách", use_container_width=True):
                        st.session_state.book_content = None
                        st.session_state.book_name = ""
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
    
    # === CHALLENGE MODE ===
    elif st.session_state.mode == "challenge":
        st.markdown("""
        <div class='glass-card' style='margin: 50px auto; max-width: 800px; text-align: center;'>
            <div style='font-size: 5rem; margin-bottom: 20px;'>⚔️</div>
            <h2 style='color: white;'>Đấu Trường Tri Thức</h2>
            <p style='color: rgba(255,255,255,0.8); font-size: 1.2rem; margin: 20px 0;'>
                🚧 Tính năng đang được phát triển...
            </p>
            <p style='color: rgba(255,255,255,0.7);'>
                Sắp có: Boss Battles, Leaderboard, Multiplayer! 🎮
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🏠 Quay lại", use_container_width=True):
            st.session_state.mode = None
            st.rerun()

# ===== BEAUTIFUL FOOTER =====
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; padding: 30px; margin-top: 50px;'>
    <div style='font-size: 2rem; margin-bottom: 10px;'>
        <span class='emoji-bounce'>🎓</span>
    </div>
    <p style='color: white; font-weight: 700; font-size: 1.2rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);'>
        SmartKid Arena
    </p>
    <p style='color: rgba(255,255,255,0.8); font-size: 0.9rem;'>
        Powered by AI • Học mà như chơi game ✨
    </p>
</div>
""", unsafe_allow_html=True)
