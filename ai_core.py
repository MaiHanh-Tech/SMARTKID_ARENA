import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import time
from google.api_core.exceptions import ResourceExhausted as GeminiResourceExhausted, ServiceUnavailable as GeminiServiceUnavailable, InternalServerError as GeminiInternalServerError, InvalidArgument as GeminiInvalidArgument
from openai import ResourceExhausted as GrokResourceExhausted, ServiceUnavailable as GrokServiceUnavailable, InternalServerError as GrokInternalServerError, BadRequest as GrokBadRequest

class AI_Core:
    def __init__(self):
        self.gemini_ready = False
        self.grok_ready = False
        self.grok_client = None
        
        # Khởi tạo Gemini (giữ nguyên như cũ)
        try:
            if "api_keys" in st.secrets and "gemini_api_key" in st.secrets["api_keys"]:
                gemini_key = st.secrets["api_keys"]["gemini_api_key"]
                genai.configure(api_key=gemini_key)
                
                self.safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
                
                self.gen_config = genai.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=4000,
                    top_p=0.95,
                    top_k=40
                )
                
                self.gemini_ready = True
            else:
                st.warning("⚠️ Chưa có Gemini API Key")
        except Exception as e:
            st.error(f"❌ Lỗi khởi tạo Gemini: {e}")
        
        # Khởi tạo Grok
        try:
            if "xai" in st.secrets and "api_key" in st.secrets["xai"]:
                grok_key = st.secrets["xai"]["api_key"]
                self.grok_client = OpenAI(
                    api_key=grok_key,
                    base_url="https://api.x.ai/v1"
                )
                self.grok_ready = True
                st.success("✅ Grok API sẵn sàng (ưu tiên dùng)")
            else:
                st.warning("⚠️ Chưa có Grok API Key → sẽ fallback Gemini nếu có")
        except Exception as e:
            st.error(f"❌ Lỗi khởi tạo Grok: {e}")

    def _generate_with_gemini(self, prompt, model_type="flash", system_instruction=None):
        """Hàm gọi Gemini (giữ logic cũ)"""
        if not self.gemini_ready:
            return None
        
        valid_names = {
            "flash": "gemini-2.0-flash-exp",
            "pro": "gemini-2.0-flash-exp",
        }
        target_name = valid_names.get(model_type, "gemini-2.0-flash-exp")
        
        try:
            model = genai.GenerativeModel(
                model_name=target_name,
                safety_settings=self.safety_settings,
                generation_config=self.gen_config,
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            if response and hasattr(response, 'text') and response.text:
                return response.text
        except (GeminiResourceExhausted, GeminiServiceUnavailable, GeminiInternalServerError, GeminiInvalidArgument) as e:
            return f"Gemini error: {str(e)[:100]}"
        except Exception as e:
            return f"Gemini unknown error: {str(e)[:50]}"
        
        return None

    def _generate_with_grok(self, prompt, model_type="pro", system_instruction=None):
        """Hàm gọi Grok với fallback nội bộ model mạnh → nhẹ"""
        if not self.grok_ready or not self.grok_client:
            return None
        
        # Ưu tiên model mạnh trước (cập nhật 2026)
        if model_type == "pro":
            model_plan = ["grok-4", "grok-4-1-fast-reasoning", "grok-4-fast-reasoning"]
        else:
            model_plan = ["grok-4-1-fast-non-reasoning", "grok-4-fast-non-reasoning"]
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        for model in model_plan:
            try:
                response = self.grok_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4000,
                    top_p=0.95
                )
                if response.choices and response.choices[0].message.content:
                    return response.choices[0].message.content.strip()
            except GrokResourceExhausted:
                st.info(f"🔸 Grok {model}: Hết quota → thử model nhẹ hơn")
                time.sleep(5)
                continue
            except (GrokServiceUnavailable, GrokInternalServerError):
                time.sleep(3)
                continue
            except GrokBadRequest as e:
                return f"Grok prompt error: {str(e)[:200]}"
            except Exception:
                continue
        
        return None

    def generate(self, prompt, model_type="pro", system_instruction=None):
        """Hàm chính: Ưu tiên Grok → fallback Gemini"""
        if not self.grok_ready and not self.gemini_ready:
            return "⚠️ Cả 2 API đều chưa sẵn sàng. Kiểm tra secrets.toml"
        
        # Bước 1: Thử Grok trước
        if self.grok_ready:
            st.info("🤖 Đang dùng Grok (ưu tiên)")
            grok_result = self._generate_with_grok(prompt, model_type, system_instruction)
            if grok_result:
                return grok_result
            else:
                st.warning("🔄 Grok bận/hết quota → chuyển sang Gemini")
        
        # Bước 2: Fallback Gemini
        if self.gemini_ready:
            st.info("🤖 Đang dùng Gemini (fallback)")
            gemini_result = self._generate_with_gemini(prompt, model_type, system_instruction)
            if gemini_result and "error" not in gemini_result.lower():
                return gemini_result
            else:
                return f"⚠️ Cả Grok và Gemini đều lỗi:\n- Grok: bận/hết quota\n- Gemini: {gemini_result or 'lỗi'}\n💡 Thử lại sau vài phút nhé chị!"
        
        return "⚠️ Không có API nào hoạt động."
