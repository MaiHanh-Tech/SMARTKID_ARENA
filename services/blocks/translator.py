import streamlit as st
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import time
import json
import jieba
from pypinyin import pinyin, Style
from pydantic import BaseModel, Field
from typing import List
from collections import OrderedDict

# 👇 IMPORT MỚI (Từ thư mục blocks)
from services.blocks.config import AppConfig
from services.blocks.logger import AppLogger

class WordDefinition(BaseModel):
    word: str
    pinyin: str
    translation: str

class InteractiveTranslation(BaseModel):
    words: List[WordDefinition]

class Translator:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if not self.initialized:
            self.logger = AppLogger() # ✅ Khởi tạo Logger

            # 1. Lấy API Key
            self.api_key = st.secrets.get("google_genai", {}).get("api_key", "") or st.secrets.get("api_key", "")
            # Fallback sang key của AI_Core nếu có
            if not self.api_key and "api_keys" in st.secrets:
                self.api_key = st.secrets["api_keys"].get("gemini_api_key", "")

            if self.api_key: 
                genai.configure(api_key=self.api_key)
            else:
                self.logger.log_error("Translator", "Missing API Key", "")
            
            # 2. Cấu hình Model (✅ LẤY TỪ CONFIG)
            self.model_flash = AppConfig.GEMINI_MODELS["flash"]
            self.model_pro = AppConfig.GEMINI_MODELS["pro"]
            
            # Nếu user cấu hình đè trong secrets
            if "google_genai" in st.secrets:
                self.model_flash = st.secrets["google_genai"].get("model_flash", self.model_flash)
                self.model_pro = st.secrets["google_genai"].get("model_pro", self.model_pro)

            self.safety = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE
            }
            
            # ✅ DÙNG OrderedDict VỚI GIỚI HẠN
            self.cache = OrderedDict()
            self.MAX_CACHE_SIZE = 100
            
            self.initialized = True

    def _generate(self, model_name, prompt, structured_output=None):
        if not self.api_key: return "Error: Chưa nhập API Key"
        
        start_time = time.time() # ✅ Đo thời gian
        gen_config = {"temperature": 0.3}
        if structured_output:
            gen_config.update({"response_mime_type": "application/json", "response_schema": structured_output})

        model = genai.GenerativeModel(model_name=model_name, safety_settings=self.safety, generation_config=gen_config)

        # Thử tối đa 2 lần, chờ ngắn
        for attempt in range(2):
            try:
                response = model.generate_content(prompt)
                if response.text: 
                    # ✅ Ghi Log thành công
                    latency = time.time() - start_time
                    self.logger.log_api_call(model_name, len(prompt), latency, True)
                    return response.text
            except Exception as e:
                err = str(e)
                self.logger.log_error("Translator_Generate", err, "") # ✅ Ghi Log lỗi

                # Nếu sai model (404)
                if "404" in err or "Not Found" in err:
                    return f"[Model Error: Model {model_name} không tồn tại]"
                
                # Nếu quá tải (429) -> Chờ 2s rồi thử lại
                if "429" in err or "exhausted" in err:
                    time.sleep(2)
                    continue
                
                return f"[API Error: {err}]"
        
        return "[System Busy: Quá tải, vui lòng thử lại sau vài giây]"

    def _add_to_cache(self, key, value):
        """Thêm vào cache với giới hạn kích thước"""
        if len(self.cache) >= self.MAX_CACHE_SIZE:
            self.cache.popitem(last=False)
        self.cache[key] = value

    def translate_text(self, text, source, target, prompt_template=None):
        if not text.strip(): return ""
        
        cache_key = f"{text[:200]}|{source}|{target}"
        if cache_key in self.cache: 
            return self.cache[cache_key]

        full_prompt = f"{prompt_template}\n\nNguồn: {source}\nĐích: {target}\nVăn bản: {text}"
        
        # Luôn dùng Flash trước
        res = self._generate(self.model_flash, full_prompt)
        
        # Nếu Flash lỗi model, fallback sang config default
        if "Model Error" in res:
            res = self._generate(AppConfig.GEMINI_MODELS["flash"], full_prompt)

        if "API Error" not in res and "System Busy" not in res:
            self._add_to_cache(cache_key, res.strip())
            
        return res.strip()

    def process_word_by_word(self, text, source, target):
        prompt = f"Phân tích từ vựng: '{text}' ({source}->{target})."
        res = self._generate(self.model_flash, prompt, structured_output=InteractiveTranslation)
        try:
            return [w.model_dump() for w in InteractiveTranslation.model_validate_json(res).words]
        except:
            return [{'word': w, 'pinyin': '', 'translations': []} for w in jieba.cut(text)]
