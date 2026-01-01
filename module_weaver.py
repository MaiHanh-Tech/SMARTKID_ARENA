import streamlit as st
import pandas as pd
import numpy as np
from services.blocks.file_processor import doc_file, clean_pdf_text
from services.blocks.embedding_engine import load_encoder, encode_texts
from services.blocks.html_generator import load_template, create_html_block, create_interactive_html_block
from services.blocks.rag_orchestrator import analyze_document_streamlit, compute_similarity_with_excel, store_history, init_knowledge_universe, create_personal_rag
from ai_core import AI_Core
from voice_block import Voice_Engine
from prompts import DEBATE_PERSONAS, BOOK_ANALYSIS_PROMPT
import time

# ✅ IMPORT SUPABASE
try:
    from supabase import create_client, Client
except ImportError:
    # Không raise error trực tiếp để app vẫn chạy các phần khác
    st.error("⚠️ Thiếu thư viện supabase. Hãy thêm 'supabase' vào requirements.txt")

# ==========================================
# 🌍 BỘ TỪ ĐIỂN ĐA NGÔN NGỮ (giữ nguyên)
# ==========================================
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
        "t1_graph_title": "🪐 Vũ Trụ Sách",
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

# --- CÁC HÀM PHỤ TRỢ (giữ nguyên, nhẹ) ---
@st.cache_resource
def load_models():
    try:
        model = load_encoder()
        return model
    except Exception as e:
        return None

def check_model_available():
    model = load_models()
    if model is None:
        st.warning("⚠️ Chức năng Knowledge Graph tạm thời không khả dụng (thiếu RAM)")
        return False
    return True

def doc_file_safe(uploaded_file):
    return doc_file(uploaded_file)

# --- RUN ---
def run():
    ai = AI_Core()
    voice = Voice_Engine()

    with st.sidebar:
        st.markdown("---")
        lang_choice = st.selectbox("🌐 " + TRANS['vi']['lang_select'], ["Tiếng Việt", "English", "中文"], key="weaver_lang_selector")
        if lang_choice == "Tiếng Việt":
            st.session_state.weaver_lang = 'vi'
        elif lang_choice == "English":
            st.session_state.weaver_lang = 'en'
        else:
            st.session_state.weaver_lang = 'zh'

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

                # --- SAFE INIT: Knowledge Graph (tránh UnboundLocalError) ---
                kg = st.session_state.get("knowledge_universe", None)
                if kg is None:
                    try:
                        kg = init_knowledge_universe()
                        st.session_state["knowledge_universe"] = kg
                    except Exception as e:
                        st.warning(f"Knowledge Graph chưa khởi tạo: {e}")
                        kg = None

                # Lấy sách liên quan nếu KG khả dụng
                try:
                    related = kg.find_related_books(text[:2000], top_k=3) if kg else []
                except Exception as e:
                    st.warning(f"Lỗi khi tìm sách liên quan: {e}")
                    related = []

                with st.spinner(T("t1_analyzing").format(name=f.name)):
                    res = analyze_document_streamlit(f.name, text, user_lang=st.session_state.get('weaver_lang', 'vi'))
                    if res and "Lỗi" not in res:
                        st.markdown(f"### 📄 {f.name}")
                        # Hiển thị link sách liên quan (nếu có)
                        if link:
                            st.markdown("**Sách có liên quan (từ Excel):**")
                            st.markdown(link)
                        # Hiển thị kết quả phân tích
                        st.markdown(res)
                        # Nếu có KG liên quan, hiển thị tóm tắt
                        if related:
                            st.markdown("**Sách liên quan từ Knowledge Graph:**")
                            for node_id, title, score, explanation in related:
                                st.markdown(f"- **{title}** ({score:.2f}) — {explanation}")
                        st.markdown("---")
                        store_history("Phân Tích Sách", f.name, res[:500])
                    else:
                        st.error(f"❌ Không thể phân tích file {f.name}: {res}")

    # === TAB 2: DỊCH GIẢ ===
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

    # === TAB 3: ĐẤU TRƯỜNG ===
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
                    st.rerun()
            for msg in st.session_state.weaver_chat:
                st.chat_message(msg["role"]).write(msg["content"])
            if prompt := st.chat_input(T("t3_input")):
                st.chat_message("user").write(prompt)
                st.session_state.weaver_chat.append({"role": "user", "content": prompt})
                recent_history = st.session_state.weaver_chat[-10:]
                context_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in recent_history])
                full_prompt = f"LỊCH SỬ:\n{context_text}\n\nNHIỆM VỤ: Trả lời câu hỏi mới nhất của USER."
                with st.chat_message("assistant"):
                    with st.spinner("..."):
                        res = ai.generate(full_prompt, model_type="flash", system_instruction=DEBATE_PERSONAS[persona])
                        if res:
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
                                    context_str = "\n".join([f"{m['role']}: {m['content']}" for m in recent_msgs])

                                length_instruction = " (BẮT BUỘC: Trả lời ngắn gọn khoảng 150-200 từ. Đi thẳng vào trọng tâm, không lan man.)"

                                if round_num == 1:
                                    p_prompt = f"CHỦ ĐỀ: {topic}\nNHIỆM VỤ (Vòng 1 - Mở đầu): Nêu quan điểm chính và 2-3 lý lẽ. {length_instruction}"
                                else:
                                    p_prompt = f"CHỦ ĐỀ: {topic}\nBỐI CẢNH MỚI NHẤT:\n{context_str}\n\nNHIỆM VỤ (Vòng {round_num} - Phản biện): Phản biện sắc bén quan điểm đối thủ và củng cố lập trường của mình. {length_instruction}"

                                try:
                                    res = ai.generate(
                                        p_prompt,
                                        model_type="pro",
                                        system_instruction=DEBATE_PERSONAS[p_name]
                                    )

                                    if res:
                                        clean_res = res.replace(f"{p_name}:", "").strip()
                                        clean_res = clean_res.replace(f"**{p_name}:**", "").strip()
                                        icons = {"Kẻ Phản Biện": "😈", "Shushu": "🎩", "Phật Tổ": "🙏", "Socrates": "🏛️"}
                                        icon = icons.get(p_name, "🤖")
                                        content_fmt = f"### {icon} {p_name}\n\n{clean_res}"
                                        st.session_state.weaver_chat.append({"role": "assistant", "content": content_fmt})
                                        full_transcript.append(content_fmt)
                                        with st.chat_message("assistant", avatar=icon):
                                            st.markdown(content_fmt)
                                        time.sleep(1)
                                except Exception as e:
                                    st.error(f"Lỗi khi gọi AI cho {p_name}: {e}")
                                    continue
                        status.update(label="✅ Tranh luận kết thúc!", state="complete")
                    except Exception as e:
                        st.error(f"Lỗi trong quá trình tranh luận: {e}")

                full_log = "\n\n".join(full_transcript)
                store_history("Hội Đồng Tranh Biện", f"Chủ đề: {topic}", full_log)

    # === TAB 4: PHÒNG THU ===
    with tab4:
        st.subheader(T("t4_header"))
        inp_v = st.text_area("Text:", height=200)
        btn_v = st.button(T("t4_btn"))
        if btn_v and inp_v:
            path = voice.speak(inp_v)
            if path:
                st.audio(path)

    # === TAB 5: NHẬT KÝ (CÓ PHẦN BAYES) ===
    with tab5:
        st.subheader("⏳ Nhật Ký & Phản Chiếu Tư Duy")
        if st.button("🔄 Tải lại", key="w_t5_refresh"):
            from services.blocks.rag_orchestrator import DBBlock, tai_lich_su
            db = DBBlock()
            st.session_state.history_cloud = tai_lich_su()
            st.rerun()

        data = st.session_state.get("history_cloud", [])
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
