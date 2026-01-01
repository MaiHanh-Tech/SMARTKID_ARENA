import streamlit as st
from services.blocks.translation_orchestrator import translate_document
from translator import Translator
import streamlit.components.v1 as components
from services.blocks.file_processor import split_smart_chunks

LANGUAGES = {"Vietnamese": "vi", "English":"en", "Chinese":"zh", "French":"fr", "Japanese":"ja", "Korean":"ko"}

def run():
    st.header("🌏 AI Translator Pro")
    if 'translator' not in st.session_state:
        st.session_state.translator = Translator()
    c1, c2, c3 = st.columns(3)
    with c1:
        source_lang = st.selectbox("Nguồn:", ["Chinese", "English", "Vietnamese"], index=0)
    with c2:
        target_lang = st.selectbox("Đích:", list(LANGUAGES.keys()), index=0)
    with c3:
        mode = st.radio("Chế độ:", ["Standard (Dịch câu)", "Interactive (Học từ)"])
    include_eng = st.checkbox("Kèm Tiếng Anh", value=True)
    text = st.text_area("Nhập văn bản:", height=200)
    if st.button("Dịch Ngay"):
        if not text.strip():
            st.warning("Chưa nhập chữ!")
            return
        progress_bar = st.progress(0)
        status = st.empty()
        try:
            if mode == "Interactive (Học từ)":
                if source_lang != "Chinese":
                    st.error("Chế độ học từ chỉ hỗ trợ nguồn Tiếng Trung.")
                    return
                html = translate_document(text, lambda p: progress_bar.progress(int(p)), include_english=include_eng, source_lang=source_lang, target_lang=LANGUAGES[target_lang], mode="Interactive Word-by-Word", processed_words=None)
            else:
                html = translate_document(text, lambda p: progress_bar.progress(int(p)), include_english=include_eng, source_lang=source_lang, target_lang=LANGUAGES[target_lang], mode="Standard Translation")
            status.success("Xong!")
            st.download_button("Tải HTML", html, "trans.html", "text/html")
            components.html(html, height=600, scrolling=True)
        except Exception as e:
            st.error(f"Lỗi dịch: {e}")
