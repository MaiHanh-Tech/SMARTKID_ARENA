import google.generativeai as genai
import streamlit as st
import time
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError, InvalidArgument

class AI_Core:
    def __init__(self):
        self.api_ready = False
        try:
            # Kiểm tra key tồn tại trước khi lấy
            if "api_keys" in st.secrets and "gemini_api_key" in st.secrets["api_keys"]:
                api_key = st.secrets["api_keys"]["gemini_api_key"]
                genai.configure(api_key=api_key)
                self.api_ready = True
            else:
                st.error("⚠️ Chưa cấu hình API Key trong secrets.toml")
                return

            # Cấu hình Safety (Chặn nội dung độc hại)
            self.safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # Cấu hình Generation Config (Tối ưu cho câu hỏi)
            self.gen_config = genai.GenerationConfig(
                temperature=0.7,  # Cân bằng giữa sáng tạo và chính xác
                max_output_tokens=4000,  # Đủ cho 20 câu hỏi
                top_p=0.95,
                top_k=40
            )

        except Exception as e:
            st.error(f"❌ Lỗi khởi tạo AI Core: {e}")

    def _get_model(self, model_name, system_instr=None):
        """Hàm helper để khởi tạo model đúng phiên bản"""
        valid_names = {
            "flash": "gemini-2.0-flash-exp",
            "pro": "gemini-2.0-flash-exp",  # Dùng flash exp cho cả 2 (nhanh + rẻ)
        }
        
        target_name = valid_names.get(model_name, "gemini-2.0-flash-exp")
        
        try:
            return genai.GenerativeModel(
                model_name=target_name,
                safety_settings=self.safety_settings,
                generation_config=self.gen_config,
                system_instruction=system_instr
            )
        except Exception:
            return None

    def generate(self, prompt, model_type="flash", system_instruction=None):
        """
        Hàm gọi AI chính: Tự động chuyển model nếu lỗi (Fallback Strategy)
        """
        if not self.api_ready:
            return "⚠️ API Key chưa sẵn sàng."

        # Chiến thuật ưu tiên: Flash (nhanh) -> Pro (dự phòng)
        plan = [
            ("flash", "Gemini 2.0 Flash Exp", 2), 
            ("pro", "Gemini 2.0 Flash Exp", 2),
        ]

        last_errors = []
        quota_exhausted_count = 0

        for m_type, m_name, base_wait_time in plan:
            try:
                # Khởi tạo model
                model = self._get_model(m_type, system_instr=system_instruction)
                if not model: 
                    continue
                
                # Gọi API
                response = model.generate_content(prompt)
                
                # Kiểm tra kết quả
                if response and hasattr(response, 'text') and response.text:
                    return response.text
                
                # Xử lý các lý do bị chặn (Safety, Token...)
                if response and hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        reason = candidate.finish_reason.name
                        if reason == "SAFETY":
                            last_errors.append(f"{m_name}: Bị chặn (Safety)")
                            continue
                        elif reason == "MAX_TOKENS":
                            last_errors.append(f"{m_name}: Quá dài (Max Tokens)")
                            continue
                
                last_errors.append(f"{m_name}: Trả về rỗng")
                continue
            
            except ResourceExhausted:
                quota_exhausted_count += 1
                error_msg = f"{m_name}: Hết Quota (429)"
                last_errors.append(error_msg)
                time.sleep(base_wait_time * quota_exhausted_count)
                
            except (ServiceUnavailable, InternalServerError):
                last_errors.append(f"{m_name}: Lỗi Server (5xx)")
                time.sleep(2)
            
            except InvalidArgument as e:
                return f"⚠️ Lỗi Input (Prompt không hợp lệ): {str(e)[:200]}"
                
            except Exception as e:
                last_errors.append(f"{m_name}: Lỗi lạ ({str(e)[:50]})")
                time.sleep(1)

        # Nếu thử hết các model mà vẫn lỗi
        error_summary = "\n".join(f"- {e}" for e in last_errors[-3:])
        return f"⚠️ Hệ thống đang bận hoặc gặp lỗi:\n{error_summary}\n\n💡 Vui lòng thử lại sau 1 phút."
