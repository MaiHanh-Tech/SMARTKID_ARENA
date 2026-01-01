import google.generativeai as genai
import streamlit as st
import time
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError, InvalidArgument

# 👇 IMPORT MỚI: Config và Logger từ thư mục blocks
from services.blocks.config import AppConfig
from services.blocks.logger import AppLogger

class AI_Core:
    def __init__(self):
        self.logger = AppLogger() # ✅ Khởi tạo Logger
        self.api_ready = False
        try:
            # Kiểm tra key tồn tại trước khi lấy
            if "api_keys" in st.secrets and "gemini_api_key" in st.secrets["api_keys"]:
                api_key = st.secrets["api_keys"]["gemini_api_key"]
                genai.configure(api_key=api_key)
                self.api_ready = True
            else:
                st.error("⚠️ Chưa cấu hình API Key trong secrets.toml")
                self.logger.log_error("AI_Core", "Missing API Key", "") # ✅ Log lỗi
                return

            # Cấu hình Safety (Chặn nội dung độc hại)
            self.safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            # Cấu hình Quota Monitor (Theo yêu cầu B)
            self.quota_tracker = {
                "daily_calls": 0,
                "daily_limit": AppConfig.API_LIMITS["gemini_daily"], # ✅ Lấy từ Config
                "cost_estimate": 0.0
            }

        except Exception as e:
            st.error(f"❌ Lỗi khởi tạo AI Core: {e}")
            self.logger.log_error("AI_Core_Init", str(e), "") # ✅ Log lỗi

    # Cấu hình Generation Config (Theo yêu cầu A)
    def _get_gen_config(self, task_type="general"):
        configs = {
            "debate": {"temperature": 0.9, "max_tokens": 2048},
            "translation": {"temperature": 0.3, "max_tokens": 4096},
            "book_analysis": {"temperature": 0.7, "max_tokens": 8192},
            "general": {"temperature": 0.8, "max_tokens": 1024}
        }
        return genai.GenerationConfig(**configs.get(task_type, configs["general"]))

    # Track usage (Theo yêu cầu B)
    def _track_usage(self, model_name, tokens_used):
        """Track API usage để tránh vượt quota"""
        self.quota_tracker["daily_calls"] += 1
        
        # Gemini pricing (example)
        cost_per_1k = {
            "gemini-2.5-pro": 0.0035,
            "gemini-2.5-flash": 0.00035
        }
        self.quota_tracker["cost_estimate"] += (tokens_used / 1000) * cost_per_1k.get(model_name, 0)
        
        if self.quota_tracker["daily_calls"] > self.quota_tracker["daily_limit"]:
            st.warning(f"⚠️ Đã sử dụng {self.quota_tracker['daily_calls']} API calls hôm nay!")

    def _get_model(self, model_name, system_instr=None, task_type="general"):
        """Hàm helper để khởi tạo model đúng phiên bản"""
        # ✅ DANH SÁCH MODEL TỪ CONFIG
        valid_names = AppConfig.GEMINI_MODELS
        
        # Mặc định fallback về 2.5 Flash nếu tên sai
        target_name = valid_names.get(model_name, valid_names["flash"])
        
        try:
            return genai.GenerativeModel(
                model_name=target_name,
                safety_settings=self.safety_settings,
                generation_config=self._get_gen_config(task_type), # Cập nhật dùng config động
                system_instruction=system_instr
            )
        except Exception as e:
            # st.warning(f"⚠️ Không thể khởi tạo model {target_name}: {e}")
            return None

    def generate(self, prompt, model_type="flash", system_instruction=None, task_type="general"):
        """
        Hàm gọi AI chính: Tự động chuyển model nếu lỗi (Fallback Strategy)
        """
        start_time = time.time() # ✅ Bắt đầu đo thời gian

        if not self.api_ready:
            return "⚠️ API Key chưa sẵn sàng."

        # ✅ CHIẾN THUẬT ƯU TIÊN: Pro -> Flash -> Exp
        if model_type == "pro":
            # Với task khó (Tranh biện): Ưu tiên 2.5 Pro
            plan = [
                ("pro", "Gemini 2.5 pro", 6), 
                ("flash", "Gemini 2.5 Flash", 3), 
                ("exp", "gemini-2.5-flash-lite", 3)
            ]
        else:
            # Với task thường: Ưu tiên Flash cho nhanh
            plan = [
                ("flash", "Gemini 2.5 Flash", 2), 
                ("exp", "gemini-2.5-flash-lite", 2),
                ("pro", "Gemini 2.5 Pro", 6)
            ]

        last_errors = []
        quota_exhausted_count = 0

        for m_type, m_name, base_wait_time in plan:
            try:
                # Khởi tạo model
                model = self._get_model(m_type, system_instr=system_instruction, task_type=task_type)
                if not model: continue
                
                # Gọi API
                response = model.generate_content(prompt)
                
                # Kiểm tra kết quả
                if response and hasattr(response, 'text') and response.text:
                    # Tracking usage khi thành công
                    token_count = 0
                    if hasattr(response, 'usage_metadata'):
                        token_count = response.usage_metadata.total_token_count
                    self._track_usage(m_name, token_count)
                    
                    # ✅ Log thành công
                    latency = time.time() - start_time
                    self.logger.log_api_call(m_type, token_count or len(prompt), latency, True)
                    
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
                # Lỗi hết tiền/quota -> Chờ lâu hơn một chút rồi thử model khác
                quota_exhausted_count += 1
                error_msg = f"{m_name}: Hết Quota (429)"
                last_errors.append(error_msg)
                self.logger.log_error("Generate", error_msg, "") # ✅ Log lỗi
                time.sleep(base_wait_time * quota_exhausted_count)
                
            except (ServiceUnavailable, InternalServerError):
                # Lỗi Server Google -> Chờ ngắn
                last_errors.append(f"{m_name}: Lỗi Server (5xx)")
                time.sleep(2)
            
            except InvalidArgument as e:
                # Lỗi Input -> Dừng luôn, không thử lại
                self.logger.log_error("Generate", f"Invalid Argument: {str(e)}", "") # ✅ Log lỗi
                return f"⚠️ Lỗi Input (Prompt không hợp lệ): {str(e)[:200]}"
                
            except Exception as e:
                last_errors.append(f"{m_name}: Lỗi lạ ({str(e)[:50]})")
                self.logger.log_error("Generate", f"Exception: {str(e)}", "") # ✅ Log lỗi
                time.sleep(1)

        # Nếu thử hết các model mà vẫn lỗi
        error_summary = "\n".join(f"- {e}" for e in last_errors[-3:])

        # --- NEW: Log detailed last_errors for debugging ---
        try:
            if hasattr(self, "logger"):
                self.logger.log_error("Generate_Final_Errors", error_summary, str(last_errors))
        except Exception:
            pass

        return f"⚠️ Hệ thống đang bận hoặc gặp lỗi:\n{error_summary}\n\n💡 Vui lòng thử lại sau 1 phút."lại sau 1 phút."

    @staticmethod
    @st.cache_data(show_spinner=False, ttl=3600)
    def analyze_static(text_hash, text, instruction):
        """
        text_hash = hashlib.md5(text.encode()).hexdigest()
        Chỉ cache theo hash, tiết kiệm bộ nhớ
        Hàm dùng riêng cho RAG (Đọc tài liệu) - Có Cache để tiết kiệm tiền
        """
        try:
            api_key = st.secrets["api_keys"]["gemini_api_key"]
            genai.configure(api_key=api_key)
            
            # Luôn dùng Flash cho RAG vì nó đọc context dài tốt và rẻ
            model = genai.GenerativeModel(
                "gemini-2.5-flash",
                system_instruction=instruction
            )
            
            # Cắt bớt nếu text quá dài (tránh lỗi quá tải)
            max_chars = 200000 
            truncated_text = text[:max_chars]
            
            if len(text) > max_chars:
                st.warning(f"⚠️ Tài liệu quá dài, chỉ phân tích {max_chars:,} ký tự đầu.")
            
            response = model.generate_content(truncated_text)
            
            if response and hasattr(response, 'text') and response.text:
                return response.text
            else:
                return "⚠️ Không có phản hồi từ AI."
                
        except Exception as e:
            return f"❌ Lỗi phân tích tĩnh: {str(e)[:200]}"
