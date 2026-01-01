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

def run():
    ai = AI_Core()
    voice = Voice_Engine()
    st.header("🧠 The Cognitive Weaver")

    with st.sidebar:
        st.markdown("---")
        lang_choice = st.selectbox("🌐 Ngôn ngữ", ["Tiếng Việt", "English", "中文"], key="weaver_lang_selector")
        if lang_choice == "Tiếng Việt": st.session_state.weaver_lang = 'vi'
        elif lang_choice == "English": st.session_state.weaver_lang = 'en'
        else: st.session_state.weaver_lang = 'zh'

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📚 Book Analysis", "✍️ Translator", "🗣️ Debater", "🎙️ AI Studio", "⏳ History"])

    # TAB 1: RAG / Book analysis
    with tab1:
        st.header("Research Assistant & Knowledge Graph")
        c1, c2, c3 = st.columns([1,1,1])
        with c1:
            file_excel = st.file_uploader("1. Connect Book Database (Excel)", type="xlsx", key="t1")
        with c2:
            uploaded_files = st.file_uploader("2. New Documents (PDF/Docx)", type=["pdf","docx","txt","md","html"], accept_multiple_files=True)
        with c3:
            btn_run = st.button("🚀 ANALYZE NOW", type="primary", use_container_width=True)

        if btn_run and uploaded_files:
            vec = load_encoder()
            db_df = None
            if file_excel:
                try:
                    db_df = pd.read_excel(file_excel).dropna(subset=["Tên sách"])
                    st.success(f"✅ Connected {len(db_df)} books.")
                except Exception as e:
                    st.error(f"❌ Lỗi đọc Excel: {e}")

            for f in uploaded_files:
                text = doc_file(f)
                if not text:
                    st.warning(f"⚠️ Không đọc được file {f.name}")
                    continue

                # similarity check
                link = ""
                if db_df is not None and vec is not None:
                    try:
                        matches = compute_similarity_with_excel(text, db_df, vec)
                        if matches:
                            link = "\n".join([f"- {m[0]} ({m[1]*100:.0f}%)" for m in matches])
                    except Exception as e:
                        st.warning(f"Không thể tính similarity: {e}")

                with st.spinner(f"Analyzing {f.name}..."):
                    res = analyze_document_streamlit(f.name, text, user_lang=st.session_state.get('weaver_lang','vi'))
                    if res and "Lỗi" not in res:
                        st.markdown(f"### 📄 {f.name}")
                        st.markdown(res)
                        st.markdown("---")
                        store_history("Phân Tích Sách", f.name, res[:500])
                    else:
                        st.error(f"❌ Không thể phân tích file {f.name}: {res}")

    # TAB 2: Translator (delegated to module_translator UI) - keep simple link / integration
    with tab2:
        st.subheader("Translator (Use dedicated module)")
        st.info("Chọn 'AI Translator' từ sidebar để mở chức năng dịch chuyên sâu.")

    # TAB 3: Debater (Solo)
    with tab3:
        st.subheader("Thinking Arena (Solo)")
        if "weaver_chat" not in st.session_state: st.session_state.weaver_chat = []
        persona = st.selectbox("Chọn nhân cách:", list(DEBATE_PERSONAS.keys()))
        if st.button("🗑️ Clear Chat"):
            st.session_state.weaver_chat = []; st.rerun()
        for msg in st.session_state.weaver_chat:
            st.chat_message(msg["role"]).write(msg["content"])
        if prompt := st.chat_input("Enter debate topic..."):
            st.chat_message("user").write(prompt)
            st.session_state.weaver_chat.append({"role":"user","content":prompt})
            context_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.weaver_chat[-10:]])
            full_prompt = f"LỊCH SỬ:\n{context_text}\n\nNHIỆM VỤ: Trả lời câu hỏi mới nhất của USER."
            with st.chat_message("assistant"):
                with st.spinner("..."):
                    res = ai.generate(full_prompt, model_type="flash", system_instruction=DEBATE_PERSONAS[persona])
                    if res:
                        st.write(res)
                        st.session_state.weaver_chat.append({"role":"assistant","content":res})
                        store_history("Tranh Biện Solo", f"{persona} - {prompt[:50]}...", f"Q:{prompt}\nA:{res}")

    # TAB 4: AI Studio (Voice)
    with tab4:
        st.subheader("AI Studio")
        inp_v = st.text_area("Text:", height=200)
        if st.button("🔊 GENERATE AUDIO") and inp_v:
            path = voice.speak(inp_v)
            if path: st.audio(path)

    # TAB 5: History + Personal RAG demo
    with tab5:
        st.subheader("Logs & History")
        if st.button("🔄 Refresh History"):
            # load via rag_orchestrator db helper
            from services.blocks.db_block import DBBlock
            db = DBBlock()
            st.session_state.history_cloud = db.get_history()
            st.rerun()
        data = st.session_state.get("history_cloud", [])
        if data:
            df_h = pd.DataFrame(data)
            st.dataframe(df_h.head(50))
        else:
            st.info("No history data found.")

        st.divider()
        # Personal RAG demo (if supabase configured)
        try:
            from services.blocks.db_block import DBBlock
            db = DBBlock()
            if db.connected:
                user_id = st.session_state.get("current_user", "Unknown")
                pr = create_personal_rag(db.client, user_id)
                if st.button("🔄 Cập nhật Profile (phân tích lại lịch sử)"):
                    pr.update_profile(force=True)
                st.expander("📊 Profile hiện tại").write(pr.profile)
                st.markdown("🎭 Try AI mimic me:")
                test_query = st.text_area("Đặt một câu hỏi", height=100)
                if st.button("🚀 Chạy (Mô phỏng bạn)") and test_query:
                    context = pr.get_personalized_context(test_query, top_k=3)
                    persona_prompt = pr.generate_persona_prompt()
                    full_prompt = f"{context}\n=== NHIỆM VỤ ===\nCâu hỏi: {test_query}"
                    response = ai.generate(full_prompt, model_type="pro", system_instruction=persona_prompt)
                    st.markdown("### 🤖 AI mô phỏng bạn:")
                    st.markdown(response)
                    pr.record_interaction("query", test_query, {"ai_response": response})
            else:
                st.info("Cần kết nối Supabase để dùng tính năng này")
        except Exception:
            st.info("Personal RAG không khả dụng (Supabase API missing).")
