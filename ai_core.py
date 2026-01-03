import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import time
from google.api_core.exceptions import ResourceExhausted as GeminiResourceExhausted, ServiceUnavailable as GeminiServiceUnavailable
from openai import ResourceExhausted as GrokResourceExhausted, ServiceUnavailable as GrokServiceUnavailable, InternalServerError as GrokInternalServerError

class AI_Core:
    def __init__(self):
        self.gemini_ready = False
        self.grok_ready = False
        self.grok_client = None
        self.status_container = st.container()

        # Gemini setup
        try:
            if "api_keys" in st.secrets and "gemini_api_key" in st.secrets["api_keys"]:
                genai.configure(api_key=st.secrets["api_keys"]["gemini_api_key"])
                self.safety_settings = [{"category": c, "threshold": "BLOCK_NONE"} for c in
                    ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                     "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
                self.gen_config = genai.GenerationConfig(temperature=0.7, max_output_tokens=4000, top_p=0.95, top_k=40)
                self.gemini_ready = True
        except Exception:
            pass

        # Grok setup
        try:
            if "xai" in st.secrets and "api_key" in st.secrets["xai"]:
                self.grok_client = OpenAI(api_key=st.secrets["xai"]["api_key"], base_url="https://api.x.ai/v1")
                self.grok_ready = True
        except Exception:
            pass

        # Status một lần
        with self.status_container:
            status = []
            if self.grok_ready: status.append("✅ Grok (ưu tiên)")
            else: status.append("❌ Grok")
            if self.gemini_ready: status.append("✅ Gemini (backup)")
            else: status.append("❌ Gemini")
            st.caption(f"**API Status:** {' | '.join(status)}")

    def _generate_with_grok(self, prompt, model_type="pro", system_instruction=None):
        if not self.grok_ready: return None

        # Fallback rộng hơn (mạnh → fast → non-reasoning)
        if model_type == "pro":
            models = ["grok-4", "grok-4-1-fast-reasoning", "grok-4-fast-reasoning", "grok-4-1-fast-non-reasoning"]
        else:
            models = ["grok-4-fast-non-reasoning", "grok-4-1-fast-non-reasoning"]

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        for model in models:
            try:
                response = self.grok_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4000,
                    top_p=0.95
                )
                return response.choices[0].message.content.strip()
            except (GrokResourceExhausted, GrokServiceUnavailable, GrokInternalServerError):
                time.sleep(3)  # Chờ lâu hơn chút
                continue
            except Exception:
                continue
        return None

    def _generate_with_gemini(self, prompt, system_instruction=None):
        if not self.gemini_ready: return None
        try:
            # Dùng model mới hơn nếu muốn (chị thử gemini-2.5-flash hoặc gemini-3-flash-preview nếu ổn định)
            model = genai.GenerativeModel(
                "gemini-2.0-flash-exp",  # Giữ tạm, hoặc đổi thành "gemini-2.5-flash" nếu chị test ok
                safety_settings=self.safety_settings,
                generation_config=self.gen_config,
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            return response.text
        except (GeminiResourceExhausted, GeminiServiceUnavailable):
            return None
        except Exception:
            return None

    def generate(self, prompt, model_type="pro", system_instruction=None):
        with st.spinner("🤖 AI đang suy nghĩ..."):
            # Ưu tiên Grok
            if self.grok_ready:
                result = self._generate_with_grok(prompt, model_type, system_instruction)
                if result:
                    with self.status_container:
                        st.success("🎯 Đã dùng Grok")
                    return result

            # Fallback Gemini
            if self.gemini_ready:
                result = self._generate_with_gemini(prompt, system_instruction)
                if result:
                    with self.status_container:
                        st.caption("🔄 Fallback sang Gemini")
                    return result

            return "⚠️ Cả Grok và Gemini đều đang bận hoặc hết quota tạm thời. Bạn chờ 1-2 phút rồi thử lại nhé!"
