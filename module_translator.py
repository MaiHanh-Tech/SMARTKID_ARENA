import streamlit as st
import io
import time
from ai_core import AI_Core

# optional orchestrator / html helpers (fall back if missing)
try:
    from services.blocks.translation_orchestrator import translate_document
except Exception:
    translate_document = None

try:
    from services.blocks.html_generator import load_template, create_html_block, create_interactive_html_block
except Exception:
    load_template = None
    create_html_block = None
    create_interactive_html_block = None

# --- Styles mapping ---
STYLE_OPTIONS = {
    "Văn học": "Write in a literary style, rich imagery and elegant phrasing.",
    "Khoa học": "Write in a scientific/technical style, precise, formal, cite facts and use technical terms.",
    "Đời thường": "Write in a casual, conversational everyday style, simple vocabulary.",
    "Hàn lâm": "Write in an academic style, formal tone and structured argumentation.",
    "Thương mại": "Write in a business style, concise, persuasive, and professional."
}

LANG_OPTIONS = ["Tiếng Việt", "English", "中文", "French", "Japanese"]

def build_prompt(source_text: str, target_lang: str, style_instruction: str):
    return (
        f"Translate the following text into {target_lang}.\n"
        f"Style instructions: {style_instruction}\n\n"
        f"Text:\n{source_text}"
    )

def run():
    ai = AI_Core()

    st.header("✍️ AI Translator")
    st.markdown("Dịch văn bản với nhiều phong cách; có thể tải file HTML kết quả.")

    with st.form("translator_form", clear_on_submit=False):
        src = st.text_area("Input text", height=300, key="trans_input")
        cols = st.columns([1,1])
        with cols[0]:
            target = st.selectbox("Target language", LANG_OPTIONS, index=0, key="trans_target")
        with cols[1]:
            style = st.selectbox("Phong cách dịch", list(STYLE_OPTIONS.keys()), index=0, key="trans_style")
        submitted = st.form_submit_button("✍️ Dịch ngay")

    if submitted and src:
        style_instr = STYLE_OPTIONS.get(style, "")
        # Prefer orchestrator if available (may handle edge cases / file conversion)
        translated = None
        with st.spinner("Đang dịch..."):
            try:
                if translate_document:
                    # translate_document may accept (text, target_lang, style) - try generic call
                    try:
                        translated = translate_document(src, target, style)
                    except TypeError:
                        # fallback to two-arg
                        translated = translate_document(src, target)
                else:
                    prompt = build_prompt(src, target, style_instr)
                    translated = ai.generate(prompt, model_type="pro")
            except Exception as e:
                st.error(f"❌ Lỗi dịch: {e}")
                translated = None

        if translated:
            st.subheader("Kết quả dịch")
            st.markdown(translated)

            # Build HTML (prefer html_generator if present)
            html_content = None
            try:
                if create_interactive_html_block:
                    html_content = create_interactive_html_block(translated, title=f"Translation - {style} - {target}")
                elif create_html_block:
                    html_content = create_html_block(translated, title=f"Translation - {style} - {target}")
                elif load_template:
                    tmpl = load_template()
                    html_content = tmpl.replace("{{content}}", translated).replace("{{title}}", f"Translation - {style} - {target}")
                else:
                    # minimal HTML fallback
                    html_content = f"<html><head><meta charset='utf-8'><title>Translation</title></head><body><h2>{style} ({target})</h2><pre>{translated}</pre></body></html>"
            except Exception as e:
                # last-resort HTML
                html_content = f"<html><head><meta charset='utf-8'><title>Translation</title></head><body><h2>{style} ({target})</h2><pre>{translated}</pre></body></html>"

            # Show HTML preview in an expander
            with st.expander("Xem trước HTML / Download"):
                st.components.v1.html(html_content, height=400, scrolling=True)

                # prepare download (filename with timestamp)
                ts = time.strftime("%Y%m%d_%H%M%S")
                filename = f"translation_{style.replace(' ', '_')}_{ts}.html"
                # use BytesIO to ensure correct encoding
                bio = io.BytesIO()
                bio.write(html_content.encode("utf-8"))
                bio.seek(0)

                st.download_button(
                    label="⬇️ Tải file HTML",
                    data=bio,
                    file_name=filename,
                    mime="text/html"
                )

            # also store a short history if DB helper exists (non-blocking)
            try:
                # keep the call optional: some apps expose store_history or luu_lich_su
                from services.blocks.rag_orchestrator import store_history
                store_history("Dịch Thuật", f"{target} - {style}", src[:200])
            except Exception:
                try:
                    from services.blocks.module_weaver import luu_lich_su  # fallback name in some variants
                    luu_lich_su("Dịch Thuật", f"{target} - {style}", src[:200])
                except Exception:
                    pass
