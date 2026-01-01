import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import time
import json
import hashlib

# === BLOCKS IMPORTS (use services.blocks.* to avoid relative path issues) ===
from services.blocks.file_processor import doc_file
from services.blocks.embedding_engine import load_encoder
from services.blocks.html_generator import load_template, create_html_block, create_interactive_html_block
from services.blocks.rag_orchestrator import (
    analyze_document_streamlit,
    compute_similarity_with_excel,
    store_history,
    init_knowledge_universe,
    create_personal_rag,
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

# TRANSLATIONS / UI TEXT (kept as original)
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
        "t2_target": "Dịch sang:",
        "t2_style": "Phong cách:",
        "t2_btn": "✍️ Dịch Ngay",
        "t3_header": "Đấu Trường Tư Duy",
        "t3_persona_label": "Chọn Đối Thủ:",
        "t3_input": "Nhập chủ đề tranh luận...",
        "t3_clear": "🗑️ Xóa Chat",
        "t4_header": "🎙️ Phòng Thu AI Đa Ngôn Ngữ",
        "t4_voice": "Chọn Giọng:",
        "t4_speed": "Tốc độ:",
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
        "t1_header": "Research Assistant & Knowledge Graph",
        "t1_up_excel": "1. Connect Book Database (Excel)",
        "t1_btn": "🚀 ANALYZE NOW",
        "t1_analyzing": "Analyzing {name}...",
        "t1_connect_ok": "✅ Connected {n} books.",
        "t1_graph_title": "🪐 Book Universe",
        "t2_header": "Multidimensional Translator",
        "t2_input": "Enter text to translate:",
        "t2_target": "Translate to:",
        "t2_style": "Style:",
        "t2_btn": "✍️ Translate",
        "t3_header": "Thinking Arena",
        "t3_persona_label": "Choose Opponent:",
        "t3_input": "Enter debate topic...",
        "t3_clear": "🗑️ Clear Chat",
        "t4_header": "🎙️ Multilingual AI Studio",
        "t4_voice": "Select Voice:",
        "t4_speed": "Speed:",
        "t4_btn": "🔊 GENERATE AUDIO",
        "t5_header": "Logs & History",
        "t5_refresh": "🔄 Refresh History",
        "t5_empty": "No history data found.",
    },
    "zh": {
        "lang_select": "语言",
        "tab1": "📚 书籍分析",
        "tab2": "✍️ 翻译专家",
        "tab3": "🗣️ 辩论场",
        "tab4": "🎙️ AI 录音室",
        "tab5": "⏳ 历史记录",
        "t1_header": "研究助手 & 知识图谱",
        "t1_up_excel": "1. 连接书库 (Excel)",
        "t1_up_doc": "2. 上传新文档 (PDF/Docx)",
        "t1_btn": "🚀 立即分析",
        "t1_analyzing": "正在分析 {name}...",
        "t1_connect_ok": "✅ 已连接 {n} 本书。",
        "t1_graph_title": "🪐 书籍宇宙",
        "t2_header": "多维翻译",
        "t2_input": "输入文本:",
        "t2_target": "翻译成:",
        "t2_style": "风格:",
        "t2_btn": "✍️ 翻译",
        "t3_header": "思维竞技场",
        "t3_persona_label": "选择对手:",
        "t3_input": "输入辩论主题...",
        "t3_clear": "🗑️ 清除聊天",
        "t4_header": "🎙️ AI 多语言录音室",
        "t4_voice": "选择声音:",
        "t4_speed": "语速:",
        "t4_btn": "🔊 生成音频",
        "t5_header": "日志 & 历史",
        "t5_refresh": "🔄 刷新历史",
        "t5_empty": "暂无历史数据。",
    }
}

def T(key):
    lang = st.session_state.get('weaver_lang', 'vi')
    return TRANS.get(lang, TRANS['vi']).get(key, key)

@st.cache_resource
def load_models():
    try:
        model = load_encoder()
        return model
    except Exception:
        return None

def check_model_available():
    model = load_models()
    if model is None:
        st.warning("⚠️ Chức năng Knowledge Graph tạm thời không khả dụng (thiếu RAM)")
        return False
    return True

def doc_file_safe(uploaded_file):
    return doc_file(uploaded_file)

# Helper to get or init KnowledgeUniverse without local-name conflicts
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

# Compatibility wrapper for rerun across Streamlit versions — minimal fix
def safe_rerun():
    try:
        st.experimental_rerun()
        return
    except Exception:
        pass
    try:
        if hasattr(st, "rerun"):
            st.rerun()
            return
    except Exception:
        pass
    st.session_state["_forced_rerun_flag"] = not st.session_state.get("_forced_rerun_flag", False)
    try:
        st.stop()
    except Exception:
        raise

# ---- Helper: detect consensus but ignore system-error messages ----
def _check_consensus_reached(chat_history):
    if len(chat_history) < 4:
        return False

    last_two = [chat_history[-2]['content'], chat_history[-1]['content']]

    # Ignore if either of last two messages looks like a system / API error
    error_markers = ["Hệ thống đang bận", "[System Busy", "⚠️ Hệ thống", "[API Error", "Lỗi", "System Busy", "exhausted"]
    if any(any(marker in s for marker in error_markers) for s in last_two):
        return False

    encoder = load_models()
    if encoder is not None:
        try:
            embs = encoder.encode(last_two)
            from sklearn.metrics.pairwise import cosine_similarity
            sim = cosine_similarity([embs[0]], [embs[1]])[0][0]
            if sim > 0.85:
                return True
        except Exception:
            # fallback to keyword matching
            pass

    agreement_keywords = ["đồng ý", "đúng", "thừa nhận", "agree", "correct", "nhất trí", "thống nhất"]
    last_msg = chat_history[-1]['content'].lower()
    if any(kw in last_msg for kw in agreement_keywords):
        return True
    return False

# ---- Helper: persona generation with retry/fallback (module level, not inside loops) ----
def _persona_generate_with_retry(ai_instance, prompt, persona_name, initial_model="pro", max_attempts=3, short_context_limit=800):
    """
    Try to generate persona response with retries and fallbacks.
    Returns tuple (ok:bool, response:str, error_summary:str)
    - ok True when valid response (not system-busy text)
    - response contains AI text when ok, otherwise empty
    - error_summary contains last error string for logging when not ok
    """
    error_markers = ["Hệ thống đang bận", "[System Busy", "⚠️ Hệ thống", "[API Error", "Lỗi", "System Busy", "exhausted"]
    attempt = 0
    last_err = ""

    model_plan = [initial_model, "flash", "flash"]  # fallback sequence
    while attempt < max_attempts:
        model_choice = model_plan[min(attempt, len(model_plan)-1)]
        try:
            res = ai_instance.generate(prompt, model_type=model_choice, system_instruction=DEBATE_PERSONAS.get(persona_name))
        except Exception as e:
            res = f"⚠️ Lỗi khi gọi AI: {e}"

        # If response looks like system busy / error -> retry
        if not res or any(marker in res for marker in error_markers):
            last_err = res
            try:
                if hasattr(ai_instance, "logger"):
                    ai_instance.logger.log_error("Persona_Generate_Attempt", f"{persona_name} attempt={attempt+1} model={model_choice}", str(res))
            except Exception:
                pass

            time.sleep(0.8 * (attempt + 1))
            # If still failing and we have long prompt, try to shorten context then retry
            if attempt == 1 and len(prompt) > short_context_limit:
                prompt = prompt[-short_context_limit:]  # keep tail (recent context)
            attempt += 1
            continue

        # success; return
        return True, res, ""
    # exhausted attempts
    return False, "", last_err

def detect_contradictions(ku, threshold=0.8):
    if not hasattr(ku, 'episteme_layers') or not hasattr(ku, 'graph'):
        return []

    contradictions = []
    contradiction_pairs = [
        ("Vật lý & Sinh học", "Ý thức & Giải phóng"),
        ("Toán học & Logic", "Văn hóa & Quyền lực")
    ]
    from sklearn.metrics.pairwise import cosine_similarity
    for layer_a, layer_b in contradiction_pairs:
        books_a = ku.episteme_layers.get(layer_a, [])
        books_b = ku.episteme_layers.get(layer_b, [])
        for node_a in books_a:
            for node_b in books_b:
                if node_a not in ku.graph.nodes or node_b not in ku.graph.nodes:
                    continue
                emb_a = ku.graph.nodes[node_a].get("embedding")
                emb_b = ku.graph.nodes[node_b].get("embedding")
                if emb_a is None or emb_b is None:
                    continue
                sim = cosine_similarity([emb_a], [emb_b])[0][0]
                if sim > threshold:
                    contradictions.append({
                        "book_1": ku.graph.nodes[node_a].get("title", node_a),
                        "book_2": ku.graph.nodes[node_b].get("title", node_b),
                        "similarity": float(sim),
                        "tension": f"{layer_a} ⚡ {layer_b}",
                        "explanation": "[Inference] Hai sách này cùng đề cập một chủ đề nhưng từ hai episteme khác nhau."
                    })
    return contradictions

def find_related_books_with_decay(ku, query_text, top_k=3):
    if not hasattr(ku, 'graph'):
        return []
    encoder = load_models()
    if not encoder:
        return []
    query_emb = encoder.encode([query_text])[0]
    current_time = datetime.now()

    scored_nodes = []
    for node_id in ku.graph.nodes:
        node = ku.graph.nodes[node_id]
        if "embedding" not in node:
            continue
        base_sim = np.dot(query_emb, node["embedding"]) / (np.linalg.norm(query_emb) * np.linalg.norm(node["embedding"]) + 1e-9)
        added_at_str = node.get("added_at")
        time_factor = 1.0
        if added_at_str:
            try:
                added_time = datetime.fromisoformat(added_at_str)
                days_old = (current_time - added_time).days
                if days_old < 0:
                    days_old = 0
                decay_rate = 0.001
                time_factor = np.exp(-decay_rate * days_old)
            except:
                pass
        score = base_sim * time_factor
        scored_nodes.append((node_id, score))

    scored_nodes.sort(key=lambda x: x[1], reverse=True)
    results = []
    for node_id, score in scored_nodes[:top_k]:
        title = ku.graph.nodes[node_id].get("title", node_id)
        explanation = ku.graph.nodes[node_id].get("summary", "")[:100] + "..."
        results.append((node_id, title, score, explanation))
    return results

# --- RUN ---
def run():
    ai = ServiceLocator.get("ai_core") or ServiceLocator.get("ai_core")
    voice = ServiceLocator.get("voice_engine")

    # initialize knowledge_universe early to avoid UnboundLocalError
    knowledge_universe = get_knowledge_universe()

    with st.sidebar:
        st.markdown("---")
        lang_choice = st.selectbox("🌐 " + TRANS['vi']['lang_select'], ["Tiếng Việt", "English", "中文"], key="weaver_lang_selector")
        if lang_choice == "Tiếng Việt":
            st.session_state.weaver_lang = 'vi'
        elif lang_choice == "English":
            st.session_state.weaver_lang = 'en'
        else:
            st.session_state.weaver_lang = 'zh'

        st.divider()
        if st.button("🔄 Clear Chat History"):
            st.session_state.weaver_chat = []
            safe_rerun()

    st.header(f"🧠 The Cognitive Weaver")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([T("tab1"), T("tab2"), T("tab3"), T("tab4"), T("tab5")])

    # TAB 1: RAG
    with tab1:
        st.header(T("t1_header"))
        with st.container():
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                file_excel = st.file_uploader(T("t1_up_excel"), type="xlsx", key="t1")
            with c2:
                uploaded_files = st.file_uploader(T("t1_up_doc"), type=["pdf", "docx", "txt", "md", "html"], accept_multiple_files=True)
            with c3:
                st.write("")
                st.write("")
                btn_run = st.button(T("t1_btn"), type="primary", use_container_width=True)

        if btn_run and uploaded_files:
            vec = load_encoder()
            db_df = None
            has_db_excel = False

            if file_excel:
                try:
                    db_df = pd.read_excel(file_excel).dropna(subset=["Tên sách"])
                    has_db_excel = True
                    st.success(T("t1_connect_ok").format(n=len(db_df)))
                except Exception as e:
                    st.error(f"❌ Lỗi đọc Excel: {e}")

            for f in uploaded_files:
                text = doc_file_safe(f)
                if not text:
                    st.warning(f"⚠️ Không đọc được file {f.name}")
                    continue

                link = ""
                if has_db_excel and db_df is not None and vec is not None:
                    try:
                        matches = compute_similarity_with_excel(text, db_df, vec)
                        if matches:
                            link = "\n".join([f"- {m[0]} ({m[1]*100:.0f}%)" for m in matches])
                    except Exception as e:
                        st.warning(f"Không thể tính similarity: {e}")

                # Re-check knowledge_universe via helper (safe, no UnboundLocalError)
                knowledge_universe = get_knowledge_universe()

                # Safe call: only call methods on knowledge_universe if available
                try:
                    related = knowledge_universe.find_related_books(text[:2000], top_k=3) if knowledge_universe else []
                except Exception as e:
                    st.warning(f"Lỗi khi tìm sách liên quan: {e}")
                    related = []

                with st.spinner(T("t1_analyzing").format(name=f.name)):
                    res = analyze_document_streamlit(f.name, text, user_lang=st.session_state.get('weaver_lang', 'vi'))
                    if res and "Lỗi" not in res:
                        st.markdown(f"### 📄 {f.name}")
                        if link:
                            st.markdown("**Sách có liên quan (từ Excel):**")
                            st.markdown(link)
                        st.markdown(res)
                        if related:
                            st.markdown("**Sách liên quan từ Knowledge Graph:**")
                            for node_id, title, score, explanation in related:
                                st.markdown(f"- **{title}** ({score:.2f}) — {explanation}")
                        st.markdown("---")
                        store_history("Phân Tích Sách", f.name, res[:500])
                    else:
                        st.error(f"❌ Không thể phân tích file {f.name}: {res}")

        # Graph visualization when Excel provided
        if file_excel:
            try:
                if "df_viz" not in st.session_state:
                    st.session_state.df_viz = pd.read_excel(file_excel).dropna(subset=["Tên sách"])
                df_v = st.session_state.df_viz

                with st.expander(T("t1_graph_title"), expanded=False):
                    vec_local = load_models()
                    if vec_local is None:
                        st.warning("⚠️ Encoder không tải được, bỏ qua đồ thị.")
                    else:
                        if "book_embs" not in st.session_state:
                            with st.spinner("Đang số hóa sách..."):
                                st.session_state.book_embs = vec_local.encode(df_v["Tên sách"].tolist())
                        embs = st.session_state.book_embs
                        sim = np.array([])  # fallback
                        try:
                            from sklearn.metrics.pairwise import cosine_similarity
                            sim = cosine_similarity(embs)
                        except Exception:
                            sim = np.zeros((len(embs), len(embs)))
                        nodes, edges = [], []
                        total_books = len(df_v)
                        c_slider1, c_slider2 = st.columns(2)
                        with c_slider1:
                            max_nodes = st.slider("Số lượng sách hiển thị:", 5, total_books, min(50, total_books))
                        with c_slider2:
                            threshold = st.slider("Độ tương đồng nối dây:", 0.0, 1.0, 0.45)
                        from streamlit_agraph import agraph, Node, Edge, Config
                        for i in range(min(max_nodes, total_books)):
                            nodes.append(Node(id=str(i), label=df_v.iloc[i]["Tên sách"], size=20, color="#FFD166"))
                            for j in range(i+1, min(max_nodes, total_books)):
                                if sim.size and sim[i, j] > threshold:
                                    edges.append(Edge(source=str(i), target=str(j), color="#118AB2"))
                        config = Config(width=900, height=600, directed=False, physics=True, collapsible=False)
                        agraph(nodes, edges, config)

                        knowledge_universe = get_knowledge_universe()
                        if knowledge_universe:
                            contras = detect_contradictions(knowledge_universe, threshold=0.8)
                            if contras:
                                st.error("⚡ PHÁT HIỆN MÂU THUẪN NHẬN THỨC (Episteme Conflict)")
                                for c in contras:
                                    st.write(f"- **{c['book_1']}** vs **{c['book_2']}** ({c['tension']}): {c['explanation']}")

            except Exception:
                pass

    # TAB 2: Dịch giả
    with tab2:
        st.subheader(T("t2_header"))
        txt = st.text_area(T("t2_input"), height=150, key="w_t2_inp")
        c_l, c_s, c_b = st.columns([1, 1, 1])
        with c_l:
            target_lang = st.selectbox(T("t2_target"), ["Tiếng Việt", "English", "Chinese", "French", "Japanese"], key="w_t2_lang")
        with c_s:
            style = st.selectbox(T("t2_style"), ["Default", "Academic", "Literary", "Business"], key="w_t2_style")
        if st.button(T("t2_btn"), key="w_t2_btn") and txt:
            with st.spinner("AI Translating..."):
                p = f"Translate to {target_lang}. Style: {style}. Text: {txt}"
                res = ai.generate(p, model_type="pro")
                st.markdown(res)
                store_history("Dịch Thuật", f"{target_lang}", txt[:50])

    # TAB 3: Đấu trường
    with tab3:
        st.subheader(T("t3_header"))
        mode = st.radio("Mode:", ["👤 Solo", "⚔️ Multi-Agent"], horizontal=True, key="w_t3_mode")
        if "weaver_chat" not in st.session_state:
            st.session_state.weaver_chat = []

        if mode == "👤 Solo":
            c1, c2 = st.columns([3, 1])
            with c1:
                persona = st.selectbox(T("t3_persona_label"), list(DEBATE_PERSONAS.keys()), key="w_t3_solo_p")
            with c2:
                if st.button(T("t3_clear"), key="w_t3_clr"):
                    st.session_state.weaver_chat = []
                    safe_rerun()
            for msg in st.session_state.weaver_chat:
                st.chat_message(msg.get("role", "user")).write(msg.get("content", ""))
            if prompt := st.chat_input(T("t3_input")):
                st.chat_message("user").write(prompt)
                st.session_state.weaver_chat.append({"role": "user", "content": prompt})
                recent_history = st.session_state.weaver_chat[-10:]
                context_text = "\n".join([f"{m.get('role','').upper()}: {m.get('content','')}" for m in recent_history])
                full_prompt = f"LỊCH SỬ:\n{context_text}\n\nNHIỆM VỤ: Trả lời câu hỏi mới nhất của USER."
                with st.chat_message("assistant"):
                    with st.spinner("..."):
                        res = ai.generate(full_prompt, model_type="flash", system_instruction=DEBATE_PERSONAS[persona])
                        error_markers = ["Hệ thống đang bận", "[System Busy", "⚠️ Hệ thống", "[API Error", "Lỗi", "System Busy"]
                        if not res or any(marker in res for marker in error_markers):
                            st.warning(f"AI trả về lỗi cho persona {persona}: {res}")
                            note = f"(AI lỗi cho {persona} - đã bỏ qua. {datetime.now().strftime('%H:%M:%S')})"
                            st.session_state.weaver_chat.append({"role": "assistant", "content": note})
                        else:
                            st.write(res)
                            st.session_state.weaver_chat.append({"role": "assistant", "content": res})
                            store_history("Tranh Biện Solo", f"{persona} - {prompt[:50]}...", f"Q: {prompt}\nA: {res}")
        else:
            participants = st.multiselect("Chọn Hội Đồng:", list(DEBATE_PERSONAS.keys()),
                                          default=[list(DEBATE_PERSONAS.keys())[0], list(DEBATE_PERSONAS.keys())[1]],
                                          max_selections=3)
            topic = st.text_input("Chủ đề:", key="w_t3_topic")
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

                            for i, p_name in enumerate(participants):
                                if time.time() - start_time > MAX_DEBATE_TIME:
                                    break

                                context_str = topic
                                if len(st.session_state.weaver_chat) > 1:
                                    recent_msgs = st.session_state.weaver_chat[-4:]
                                    context_str = "\n".join([f"{m.get('role','')}: {m.get('content','')}" for m in recent_msgs])

                                length_instruction = " (BẮT BUỘC: Trả lời ngắn gọn khoảng 150-200 từ. Đi thẳng vào trọng tâm, không lan man.)"

                                if round_num == 1:
                                    p_prompt = f"CHỦ ĐỀ: {topic}\nNHIỆM VỤ (Vòng 1 - Mở đầu): Nêu quan điểm chính và 2-3 lý lẽ. {length_instruction}"
                                else:
                                    p_prompt = f"CHỦ ĐỀ: {topic}\nBỐI CẢNH MỚI NHẤT:\n{context_str}\n\nNHIỆM VỤ (Vòng {round_num} - Phản biện): Phản biện sắc bén quan điểm đối thủ và củng cố lập trường của mình. {length_instruction}"

                                try:
                                    ok, res_text, err_text = _persona_generate_with_retry(ai, p_prompt, p_name, initial_model="pro", max_attempts=3)
                                except Exception as e:
                                    ok, res_text, err_text = False, "", f"⚠️ Exception: {e}"

                                # If failed after retries -> append short unique note and continue
                                if not ok:
                                    st.warning(f"AI trả về lỗi cho {p_name}: {err_text}")
                                    short_note = f"(AI lỗi cho {p_name} - vòng {round_num} - {datetime.now().strftime('%H:%M:%S')})"
                                    st.session_state.weaver_chat.append({"role": "assistant", "content": short_note})
                                    full_transcript.append(short_note)
                                    try:
                                        if hasattr(ai, "logger"):
                                            ai.logger.log_error("Persona_Failure", f"{p_name} round={round_num}", err_text)
                                    except Exception:
                                        pass
                                    continue

                                # Normal flow when response OK
                                clean_res = res_text.replace(f"{p_name}:", "").strip()
                                clean_res = clean_res.replace(f"**{p_name}:**", "").strip()
                                icons = {"Kẻ Phản Biện": "😈", "Shushu": "🎩", "Phật Tổ": "🙏", "Socrates": "🏛️"}
                                icon = icons.get(p_name, "🤖")
                                content_fmt = f"### {icon} {p_name}\n\n{clean_res}"
                                st.session_state.weaver_chat.append({"role": "assistant", "content": content_fmt})
                                full_transcript.append(content_fmt)
                                with st.chat_message("assistant", avatar=icon):
                                    st.markdown(content_fmt)
                                time.sleep(1)

                            # After each round check if consensus reached (but ignore system-error notes)
                            if _check_consensus_reached(st.session_state.weaver_chat):
                                status.update(label="✅ Tranh luận đã đạt đồng thuận!", state="complete")
                                st.info("✅ Các bên đã tìm thấy điểm chung (Consensus Reached). Dừng tranh luận.")
                                break

                        status.update(label="✅ Tranh luận kết thúc!", state="complete")
                    except Exception as e:
                        st.error(f"Lỗi trong quá trình tranh luận: {e}")

                full_log = "\n\n".join(full_transcript)
                store_history("Hội Đồng Tranh Biện", f"Chủ đề: {topic}", full_log)

    # TAB 4: PHÒNG THU
    with tab4:
        st.subheader(T("t4_header"))
        inp_v = st.text_area("Text:", height=200)
        btn_v = st.button(T("t4_btn"))
        if btn_v and inp_v and voice:
            path = voice.speak(inp_v)
            if path:
                st.audio(path)

    # TAB 5: NHẬT KÝ (CÓ PHẦN BAYES)
    with tab5:
        st.subheader("⏳ Nhật Ký & Phản Chiếu Tư Duy")
        if st.button("🔄 Tải lại", key="w_t5_refresh"):
            st.session_state.history_cloud = tai_lich_su()
            safe_rerun()

        data = st.session_state.get("history_cloud", tai_lich_su())

        if data:
            df_h = pd.DataFrame(data)

            if "SentimentScore" in df_h.columns:
                try:
                    df_h["score"] = pd.to_numeric(df_h["SentimentScore"], errors='coerce').fillna(0)
                    import plotly.express as px
                    fig = px.line(df_h, x="Time", y="score", markers=True, color_discrete_sequence=["#76FF03"])
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    pass

            with st.expander("🔮 Phân tích Tư duy theo xác suất Bayes (E.T. Jaynes)", expanded=False):
                st.info("AI sẽ coi Lịch sử hoạt động của chị là 'Dữ liệu quan sát' (Evidence) để suy luận ra 'Hàm mục tiêu' (Objective Function) và sự dịch chuyển niềm tin của chị.")

                if st.button("🧠 Chạy Mô hình Bayes ngay"):
                    with st.spinner("Đang tính toán xác suất hậu nghiệm (Posterior)..."):
                        recent_logs = df_h.tail(10).to_dict(orient="records")
                        logs_text = pd.io.json.dumps(recent_logs, ensure_ascii=False)

                        bayes_prompt = f"""
                        Đóng vai một nhà khoa học tư duy theo trường phái E.T. Jaynes (sách 'Probability Theory: The Logic of Science').

                        DỮ LIỆU QUAN SÁT (EVIDENCE):
                        Đây là nhật ký hoạt động của tôi:
                        {logs_text}

                        NHIỆM VỤ:
                        Hãy phân tích chuỗi hành động này như một bài toán suy luận Bayes.
                        1. **Xác định Priors (Niềm tin tiên nghiệm):** Dựa trên các hành động đầu, tôi đang quan tâm/tin tưởng điều gì?
                        2. **Cập nhật Likelihood (Khả năng):** Các hành động tiếp theo củng cố hay làm yếu đi niềm tin đó?
                        3. **Kết luận Posterior (Hậu nghiệm):** Trạng thái tư duy hiện tại của tôi đang hội tụ về đâu? Có mâu thuẫn (Inconsistency) nào trong logic hành động không?

                        Trả lời ngắn gọn, sâu sắc, dùng thuật ngữ xác suất nhưng dễ hiểu.
                        """

                        analysis = ai.generate(bayes_prompt, model_type="pro")
                        st.markdown(analysis)

            st.divider()
            for index, item in df_h.iterrows():
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

    # TAB 6: READING TRACKER
    with tab6:
        st.subheader("📊 Tiến độ đọc sách & Spaced Repetition")
        if "current_user" in st.session_state and st.session_state.current_user:
            try:
                if create_client:
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
                            with st.expander(f"📘 {book_title} (Lần {rev['repetition']})"):
                                q = st.slider("Độ nhớ (0-5):", 0, 5, key=f"q_{rev['book_id']}")
                                if st.button("Lưu đánh giá", key=f"b_{rev['book_id']}"):
                                    tracker.review_book(rev['book_id'], q)
                                    st.success("Đã lưu!")
                                    time.sleep(1)
                                    safe_rerun()
                    else:
                        st.success("✅ Bạn đã hoàn thành bài ôn tập hôm nay.")
                else:
                    st.info("Supabase client chưa cấu hình; không thể truy vấn Reading Tracker.")
            except Exception as e:
                st.error(f"Lỗi kết nối DB: {e}")
        else:
            st.info("Vui lòng đăng nhập để sử dụng tính năng này.")
