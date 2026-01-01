"""
Module: module_weaver.py
Clean, robust rewrite of the Cognitive Weaver UI module (Streamlit).
Key points:
- Use services.blocks imports
- Use ServiceLocator to obtain singletons (ai_core, voice)
- Robust AI calls with retry/fallback and logging
- Avoid appending raw API error texts into chat history (prevents false consensus)
- Consensus detection ignores system-error notes
"""
import time
from datetime import datetime
import json
import streamlit as st
import pandas as pd
import numpy as np

# Blocks imports (explicit service paths)
from services.blocks.file_processor import doc_file
from services.blocks.embedding_engine import load_encoder
from services.blocks.html_generator import create_html_block, create_interactive_html_block
from services.blocks.rag_orchestrator import (
    analyze_document_streamlit,
    compute_similarity_with_excel,
    store_history,
    init_knowledge_universe,
    tai_lich_su,
)
from services.blocks.prompts import DEBATE_PERSONAS, BOOK_ANALYSIS_PROMPT
from services.blocks.service_locator import ServiceLocator
from services.blocks.argument_analyzer import ArgumentAnalyzer
from services.blocks.reading_tracker import ReadingProgressTracker

# Optional supabase import (don't fail app if missing)
try:
    from supabase import create_client, Client
except Exception:
    create_client = None

# UI Translations
TRANS = {
    "vi": {
        "lang_select": "Ngôn ngữ / Language / 语言",
        "tab1": "📚 Phân Tích Sách",
        "tab2": "✍️ Dịch Giả",
        "tab3": "🗣️ Tranh Biện",
        "tab4": "🎙️ Phòng Thu AI",
        "tab5": "⏳ Nhật Ký",
        "t1_header": "Trợ lý Nghiên cứu & Knowledge Graph",
        "t1_up_excel": "1. Kết nối Kho Sách (Excel)",
        "t1_up_doc": "2. Tài liệu mới (PDF/Docx)",
        "t1_btn": "🚀 PHÂN TÍCH NGAY",
        "t1_analyzing": "Đang phân tích {name}...",
        "t1_connect_ok": "✅ Đã kết nối {n} cuốn sách.",
        "t1_graph_title": "🪐 Vũ trụ Sách",
        "t2_header": "Dịch Thuật Đa Chiều",
        "t2_input": "Nhập văn bản cần dịch:",
        "t2_btn": "✍️ Dịch Ngay",
        "t3_header": "Đấu Trường Tư Duy",
        "t3_persona_label": "Chọn Đối Thủ:",
        "t3_input": "Nhập chủ đề tranh luận...",
        "t3_clear": "🗑️ Xóa Chat",
        "t4_header": "🎙️ Phòng Thu AI Đa Ngôn Ngữ",
        "t4_btn": "🔊 TẠO AUDIO",
        "t5_header": "Nhật Ký & Lịch Sử",
        "t5_refresh": "🔄 Tải lại Lịch sử",
        "t5_empty": "Chưa có dữ liệu lịch sử.",
    },
    "en": {
        "lang_select": "Language",
        "tab1": "📚 Book Analysis",
        "tab2": "✍️ Translator",
        "tab3": "🗣️ Debater",
        "tab4": "🎙️ AI Studio",
        "tab5": "⏳ History",
    },
    "zh": {
        "lang_select": "语言",
        "tab1": "📚 书籍分析",
        "tab2": "✍️ 翻译专家",
        "tab3": "🗣️ 辩论场",
        "tab4": "🎙️ AI 录音室",
        "tab5": "⏳ 历史记录",
    }
}


def T(key):
    lang = st.session_state.get('weaver_lang', 'vi')
    return TRANS.get(lang, TRANS['vi']).get(key, key)


@st.cache_resource
def load_models():
    try:
        return load_encoder()
    except Exception:
        return None


def get_knowledge_universe():
    ku = st.session_state.get("knowledge_universe", None)
    if ku is not None:
        return ku
    try:
        ku = init_knowledge_universe()
        st.session_state["knowledge_universe"] = ku
        return ku
    except Exception:
        return None


# -----------------------
# Helper: persona generation with retry/fallback
# -----------------------
def _persona_generate_with_retry(ai_instance, prompt, persona_name, initial_model="pro", max_attempts=3, short_context_limit=800):
    """
    Try to generate persona response with retries and fallbacks.
    Returns (ok: bool, response: str, error_summary: str)
    - ok True when we obtained a usable response
    - response: AI text if ok else ""
    - error_summary: final error message (for logging)
    """
    error_markers = ["Hệ thống đang bận", "[System Busy", "⚠️ Hệ thống", "[API Error", "Lỗi", "System Busy", "exhausted"]
    attempt = 0
    last_err = ""
    model_plan = [initial_model, "flash", "flash"]

    while attempt < max_attempts:
        model_choice = model_plan[min(attempt, len(model_plan) - 1)]
        try:
            res = ai_instance.generate(prompt, model_type=model_choice, system_instruction=DEBATE_PERSONAS.get(persona_name))
        except Exception as e:
            res = f"⚠️ Lỗi khi gọi AI: {e}"

        # If response looks like system busy / error -> retry
        if not res or any(marker in res for marker in error_markers):
            last_err = res
            # log attempt if logger available
            try:
                if hasattr(ai_instance, "logger"):
                    ai_instance.logger.log_error("Persona_Generate_Attempt", f"{persona_name} attempt={attempt+1} model={model_choice}", str(res))
            except Exception:
                pass

            time.sleep(0.8 * (attempt + 1))
            # Try to shorten prompt after second failure
            if attempt == 1 and len(prompt) > short_context_limit:
                prompt = prompt[-short_context_limit:]
            attempt += 1
            continue

        return True, res, ""
    return False, "", last_err


# -----------------------
# Helper: consensus detection (ignore system-error notes)
# -----------------------
def _check_consensus_reached(chat_history):
    if len(chat_history) < 4:
        return False
    last_two = [chat_history[-2]['content'], chat_history[-1]['content']]
    error_markers = ["Hệ thống đang bận", "[System Busy", "⚠️ Hệ thống", "[API Error", "Lỗi", "System Busy", "exhausted"]
    if any(any(marker in s for marker in error_markers) for s in last_two):
        return False

    # try to use encoder similarity
    encoder = load_models()
    if encoder is not None:
        try:
            embs = encoder.encode(last_two)
            from sklearn.metrics.pairwise import cosine_similarity
            sim = cosine_similarity([embs[0]], [embs[1]])[0][0]
            if sim > 0.85:
                return True
        except Exception:
            pass

    agreement_keywords = ["đồng ý", "đúng", "thừa nhận", "agree", "correct", "nhất trí", "thống nhất"]
    last_msg = chat_history[-1]['content'].lower()
    if any(kw in last_msg for kw in agreement_keywords):
        return True
    return False


# -----------------------
# Simple KG helper used in UI (kept small)
# -----------------------
def find_related_books_with_decay(ku, query_text, top_k=3):
    if not ku or not hasattr(ku, 'graph'):
        return []
    encoder = load_models()
    if not encoder:
        return []
    try:
        query_emb = encoder.encode([query_text])[0]
    except Exception:
        return []

    scored_nodes = []
    current_time = datetime.now()
    for node_id in ku.graph.nodes:
        node = ku.graph.nodes[node_id]
        if "embedding" not in node:
            continue
        other_emb = node["embedding"]
        # cosine similarity safe
        sim = float(np.dot(query_emb, other_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(other_emb) + 1e-9))
        # time decay
        time_factor = 1.0
        added_at = node.get("added_at")
        if added_at:
            try:
                days_old = (current_time - datetime.fromisoformat(added_at)).days
                if days_old < 0: days_old = 0
                time_factor = np.exp(-0.001 * days_old)
            except Exception:
                pass
        score = sim * time_factor
        scored_nodes.append((node_id, score))
    scored_nodes.sort(key=lambda x: x[1], reverse=True)
    results = []
    for nid, score in scored_nodes[:top_k]:
        title = ku.graph.nodes[nid].get("title", nid)
        explanation = ku.graph.nodes[nid].get("summary", "")[:120] + "..."
        results.append((nid, title, score, explanation))
    return results


# -----------------------
# Main Run (Streamlit)
# -----------------------
def run():
    # Acquire services
    ai = ServiceLocator.get("ai_core")
    voice = ServiceLocator.get("voice_engine")

    # Ensure session state defaults
    if 'weaver_lang' not in st.session_state:
        st.session_state.weaver_lang = 'vi'
    if 'weaver_chat' not in st.session_state:
        st.session_state.weaver_chat = []

    knowledge_universe = get_knowledge_universe()

    # Sidebar
    with st.sidebar:
        st.markdown("---")
        lang_choice = st.selectbox("🌐 " + T("lang_select"), ["Tiếng Việt", "English", "中文"], key="weaver_lang_selector")
        if lang_choice == "Tiếng Việt":
            st.session_state.weaver_lang = 'vi'
        elif lang_choice == "English":
            st.session_state.weaver_lang = 'en'
        else:
            st.session_state.weaver_lang = 'zh'
        st.divider()
        if st.button("🔄 Clear Chat History"):
            st.session_state.weaver_chat = []
            st.experimental_rerun()

    st.header("🧠 The Cognitive Weaver")

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        [T("tab1"), T("tab2"), T("tab3"), T("tab4"), T("tab5"), "📖 Reading Tracker"]
    )

    # ---------------- Tab 1: RAG / Document analysis ----------------
    with tab1:
        st.header(T("t1_header"))
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            file_excel = st.file_uploader(T("t1_up_excel"), type="xlsx", key="t1_excel")
        with c2:
            uploaded_files = st.file_uploader(T("t1_up_doc"), type=["pdf", "docx", "txt", "md", "html"], accept_multiple_files=True)
        with c3:
            st.write("")
            btn_run = st.button(T("t1_btn"), type="primary", use_container_width=True)

        if btn_run and uploaded_files:
            vec = load_models()
            db_df = None
            if file_excel:
                try:
                    db_df = pd.read_excel(file_excel).dropna(subset=["Tên sách"])
                    st.success(T("t1_connect_ok").format(n=len(db_df)))
                except Exception as e:
                    st.error(f"❌ Lỗi đọc Excel: {e}")

            for f in uploaded_files:
                text = doc_file(f)
                if not text:
                    st.warning(f"⚠️ Không đọc được file {f.name}")
                    continue

                # compute similarity to excel DB if available
                link = ""
                if db_df is not None and vec is not None:
                    try:
                        matches = compute_similarity_with_excel(text, db_df, vec)
                        if matches:
                            link = "\n".join([f"- {m[0]} ({m[1]*100:.0f}%)" for m in matches])
                    except Exception:
                        link = ""

                # knowledge graph related
                related = []
                if knowledge_universe:
                    try:
                        related = find_related_books_with_decay(knowledge_universe, text[:2000], top_k=3)
                    except Exception:
                        related = []

                with st.spinner(T("t1_analyzing").format(name=f.name)):
                    res = analyze_document_streamlit(f.name, text, user_lang=st.session_state.get('weaver_lang', 'vi'))
                    if res and "Lỗi" not in res and not str(res).startswith("⚠️ Hệ thống đang bận"):
                        st.markdown(f"### 📄 {f.name}")
                        if link:
                            st.markdown("**Sách có liên quan (từ Excel):**")
                            st.markdown(link)
                        st.markdown(res)
                        if related:
                            st.markdown("**Sách liên quan từ Knowledge Graph:**")
                            for node_id, title, score, explanation in related:
                                st.markdown(f"- **{title}** (Relevance: {score:.3f}) — {explanation}")
                        st.markdown("---")
                        try:
                            store_history("Phân Tích Sách", f.name, str(res)[:500])
                        except Exception:
                            pass
                    else:
                        st.error(f"❌ Không thể phân tích file {f.name}: {res}")

    # ---------------- Tab 2: Simple Translator (fallback) ----------------
    with tab2:
        st.subheader(T("t2_header"))
        txt = st.text_area(T("t2_input"), height=150, key="weaver_trans_inp")
        if st.button(T("t2_btn")) and txt:
            if not ai:
                st.error("AI service chưa sẵn sàng.")
            else:
                style = "Default"
                prompt = f"Translate to Vietnamese. Style: {style}. Text: {txt}"
                try:
                    # simple call with fallback model selection handled inside ai.generate
                    out = ai.generate(prompt, model_type="pro")
                except Exception as e:
                    out = f"⚠️ Lỗi khi gọi AI: {e}"
                st.markdown(out)
                try:
                    store_history("Dịch Thuật", "Translate", txt[:200])
                except Exception:
                    pass

    # ---------------- Tab 3: Debates (Solo & Multi-Agent) ----------------
    with tab3:
        st.subheader(T("t3_header"))
        mode = st.radio("Mode:", ["👤 Solo", "⚔️ Multi-Agent"], horizontal=True, key="weaver_debate_mode")
        # display chat history
        for msg in st.session_state.weaver_chat:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            st.chat_message(role).write(content)

        if mode == "👤 Solo":
            col1, col2 = st.columns([3, 1])
            with col1:
                persona = st.selectbox(T("t3_persona_label"), list(DEBATE_PERSONAS.keys()), key="weaver_solo_persona")
            with col2:
                if st.button(T("t3_clear")):
                    st.session_state.weaver_chat = []
                    st.experimental_rerun()

            if prompt := st.chat_input(T("t3_input")):
                st.chat_message("user").write(prompt)
                st.session_state.weaver_chat.append({"role": "user", "content": prompt})
                recent = st.session_state.weaver_chat[-10:]
                ctx = "\n".join([f"{m.get('role','').upper()}: {m.get('content','')}" for m in recent])
                full_prompt = f"LỊCH SỬ:\n{ctx}\n\nNHIỆM VỤ: Trả lời câu hỏi mới nhất của USER."
                # Use retry helper
                if not ai:
                    st.warning("AI service chưa sẵn sàng.")
                else:
                    ok, res_text, err_text = _persona_generate_with_retry(ai, full_prompt, persona, initial_model="flash", max_attempts=2)
                    if not ok:
                        st.warning(f"AI trả về lỗi cho persona {persona}: {err_text}")
                        note = f"(AI lỗi cho {persona} - đã bỏ qua. {datetime.now().strftime('%H:%M:%S')})"
                        st.session_state.weaver_chat.append({"role": "assistant", "content": note})
                    else:
                        st.chat_message("assistant").write(res_text)
                        st.session_state.weaver_chat.append({"role": "assistant", "content": res_text})
                        try:
                            store_history("Tranh Biện Solo", f"{persona}", f"Q: {prompt}\nA: {res_text}")
                        except Exception:
                            pass

        else:
            participants = st.multiselect("Chọn Hội Đồng:", list(DEBATE_PERSONAS.keys()),
                                          default=list(DEBATE_PERSONAS.keys())[:2], max_selections=3)
            topic = st.text_input("Chủ đề:", key="weaver_multi_topic")
            if st.button("🔥 KHAI CHIẾN", disabled=(len(participants) < 2 or not topic)):
                st.session_state.weaver_chat = []
                start_msg = f"📢 **CHỦ TỌA:** Khai mạc tranh luận về: *'{topic}'*"
                st.session_state.weaver_chat.append({"role": "system", "content": start_msg})
                st.info(start_msg)
                full_transcript = [start_msg]
                MAX_DEBATE_TIME = 600
                start_time = time.time()

                with st.status("🔥 Cuộc chiến đang diễn ra (3 vòng)...") as status:
                    try:
                        for round_num in range(1, 4):
                            if time.time() - start_time > MAX_DEBATE_TIME:
                                st.warning("⏰ Hết giờ! Cuộc tranh luận kết thúc sớm.")
                                break
                            status.update(label=f"🔄 Vòng {round_num}/3 đang diễn ra...")

                            for p_name in participants:
                                # build context
                                recent_msgs = st.session_state.weaver_chat[-6:]
                                context_str = "\n".join([f"{m.get('role','')}: {m.get('content','')}" for m in recent_msgs]) or topic
                                if round_num == 1:
                                    p_prompt = f"CHỦ ĐỀ: {topic}\nNHIỆM VỤ (Vòng 1 - Mở đầu): Nêu quan điểm chính và 2-3 lý lẽ."
                                else:
                                    p_prompt = f"CHỦ ĐỀ: {topic}\nBỐI CẢNH:\n{context_str}\n\nNHIỆM VỤ (Vòng {round_num} - Phản biện): Phản biện sắc bén và củng cố lập trường."

                                if not ai:
                                    short_note = f"(AI không sẵn sàng cho {p_name})"
                                    st.session_state.weaver_chat.append({"role": "assistant", "content": short_note})
                                    full_transcript.append(short_note)
                                    continue

                                ok, res_text, err_text = _persona_generate_with_retry(ai, p_prompt, p_name, initial_model="pro", max_attempts=3)
                                if not ok:
                                    st.warning(f"AI trả về lỗi cho {p_name}: {err_text}")
                                    short_note = f"(AI lỗi cho {p_name} - vòng {round_num} - {datetime.now().strftime('%H:%M:%S')})"
                                    st.session_state.weaver_chat.append({"role": "assistant", "content": short_note})
                                    full_transcript.append(short_note)
                                    # log final failure if logger available
                                    try:
                                        if hasattr(ai, "logger"):
                                            ai.logger.log_error("Persona_Failure", f"{p_name} round={round_num}", err_text)
                                    except Exception:
                                        pass
                                    continue

                                # normal flow
                                clean_res = res_text.replace(f"{p_name}:", "").strip()
                                icon_map = {"Kẻ Phản Biện": "😈", "Shushu": "🎩", "Phật Tổ": "🙏", "Socrates": "🏛️"}
                                icon = icon_map.get(p_name, "🤖")
                                content_fmt = f"### {icon} {p_name}\n\n{clean_res}"
                                st.session_state.weaver_chat.append({"role": "assistant", "content": content_fmt})
                                full_transcript.append(content_fmt)
                                with st.chat_message("assistant", avatar=icon):
                                    st.markdown(content_fmt)
                                time.sleep(0.6)

                            # check consensus after each round
                            if _check_consensus_reached(st.session_state.weaver_chat):
                                status.update(label="✅ Tranh luận đã đạt đồng thuận!", state="complete")
                                st.info("✅ Các bên đã tìm thấy điểm chung (Consensus Reached). Dừng tranh luận.")
                                break

                        status.update(label="✅ Tranh luận kết thúc!", state="complete")
                    except Exception as e:
                        st.error(f"Lỗi trong quá trình tranh luận: {e}")

                # store full transcript
                full_log = "\n\n".join(full_transcript)
                try:
                    store_history("Hội Đồng Tranh Biện", f"Chủ đề: {topic}", full_log)
                except Exception:
                    pass

        # Analysis & fallacy checker area (always visible)
        st.divider()
        st.markdown("### 🧠 Phân Tích Logic & Ngụy Biện")
        arg_text = st.text_area("Nhập đoạn lập luận cần kiểm tra:", height=100, key="weaver_arg_inp")
        if st.button("🔍 Phân tích Lập luận", key="weaver_arg_btn"):
            ana = ArgumentAnalyzer()
            res = ana.analyze_argument(arg_text)
            st.metric("Điểm Logic", f"{res['strength']}/100")
            if res['fallacies']:
                st.error("⚠️ Phát hiện Ngụy biện:")
                for f in res['fallacies']:
                    st.write(f"- **{f['type']}**: {f['explanation']}")
            else:
                st.success("✅ Lập luận vững chắc.")

    # ---------------- Tab 4: Voice / TTS ----------------
    with tab4:
        st.subheader(T("t4_header"))
        text_v = st.text_area("Text for TTS:", height=160)
        if st.button(T("t4_btn")) and text_v:
            if not voice:
                st.error("Voice engine chưa được khởi tạo.")
            else:
                path = voice.speak(text_v)
                if path:
                    st.audio(path)

    # ---------------- Tab 5: History / Bayes ----------------
    with tab5:
        st.subheader("⏳ Nhật Ký & Phản Chiếu Tư Duy")
        if st.button("🔄 Tải lại", key="weaver_hist_refresh"):
            st.session_state.history_cloud = tai_lich_su()
            st.experimental_rerun()
        data = st.session_state.get("history_cloud", tai_lich_su())
        if data:
            df_h = pd.DataFrame(data)
            if "SentimentScore" in df_h.columns:
                try:
                    import plotly.express as px
                    df_h["score"] = pd.to_numeric(df_h.get("SentimentScore", 0), errors='coerce').fillna(0)
                    fig = px.line(df_h, x="Time", y="score", markers=True)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass

            with st.expander("🔮 Phân tích Tư duy theo xác suất Bayes (E.T. Jaynes)", expanded=False):
                st.info("AI sẽ coi nhật ký hoạt động là dữ liệu quan sát để phân tích tư duy.")
                if st.button("🧠 Chạy Mô hình Bayes ngay"):
                    recent_logs = df_h.tail(10).to_dict(orient="records")
                    prompt = f"Phân tích chuỗi nhật ký sau như bài toán Bayes:\n{json.dumps(recent_logs, ensure_ascii=False)}"
                    if ai:
                        try:
                            analysis = ai.generate(prompt, model_type="pro")
                        except Exception as e:
                            analysis = f"⚠️ Lỗi khi gọi AI: {e}"
                        st.markdown(analysis)
                    else:
                        st.error("AI không sẵn sàng.")

            for idx, item in df_h.iterrows():
                t = str(item.get('Time', ''))
                tp = str(item.get('Type', ''))
                ti = str(item.get('Title', ''))
                ct = str(item.get('Content', ''))
                icon = "📝"
                if "Tranh Biện" in tp:
                    icon = "🗣️"
                elif "Dịch" in tp:
                    icon = "✍️"
                with st.expander(f"{icon} {t} | {tp} | {ti}"):
                    st.markdown(ct)
        else:
            st.info(T("t5_empty"))

    # ---------------- Tab 6: Reading Tracker ----------------
    with tab6:
        st.subheader("📊 Tiến độ đọc sách & Spaced Repetition")
        if "current_user" in st.session_state and st.session_state.current_user:
            if create_client:
                try:
                    url = st.secrets["supabase"]["url"]
                    key = st.secrets["supabase"]["key"]
                    db_client = create_client(url, key)
                    tracker = ReadingProgressTracker(db_client, st.session_state.current_user)
                    due = tracker.get_due_reviews()
                    if due:
                        st.warning(f"⏰ {len(due)} sách cần ôn tập!")
                        for rev in due:
                            book_title = "Sách"
                            if isinstance(rev.get('reading_progress'), dict):
                                book_title = rev['reading_progress'].get('book_title', 'Sách')
                            with st.expander(f"📘 {book_title} (Lần {rev.get('repetition',0)})"):
                                q = st.slider("Độ nhớ (0-5):", 0, 5, key=f"q_{rev.get('book_id')}")
                                if st.button("Lưu đánh giá", key=f"b_{rev.get('book_id')}"):
                                    tracker.review_book(rev.get('book_id'), q)
                                    st.success("Đã lưu!")
                                    time.sleep(1)
                                    st.experimental_rerun()
                    else:
                        st.success("✅ Bạn đã hoàn thành bài ôn tập hôm nay.")
                except Exception as e:
                    st.error(f"Lỗi kết nối DB: {e}")
            else:
                st.info("Supabase client chưa cấu hình; không thể truy vấn Reading Tracker.")
        else:
            st.info("Vui lòng đăng nhập để sử dụng tính năng này.")
