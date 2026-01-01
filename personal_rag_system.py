"""
PERSONAL RAG SYSTEM - AI học phong cách tư duy của User
Triết lý: "Being No One" (Metzinger) - Ego là construct có thể mô hình hóa
"""

import streamlit as st
from datetime import datetime
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

class PersonalRAG:
    """
    Hệ thống RAG cá nhân hóa:
    1. Thu thập: Mọi tương tác (chat, debate, translation) → Memory
    2. Trích xuất: Patterns (keywords ưa thích, phong cách luận điểm)
    3. Tổng hợp: User Profile vector
    4. Áp dụng: Prompt injection để AI mô phỏng user
    """
    
    def __init__(self, supabase_client, user_id):
        self.db = supabase_client
        self.user_id = user_id
        self.encoder = self._load_encoder()
        self.profile = self._load_user_profile()
    
    @st.cache_resource
    def _load_encoder(_self):
        return SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2",
            device='cpu'
        )
    
    def _load_user_profile(self):
        """
        Load user profile từ DB hoặc tạo mới
        
        Profile structure:
        {
            "user_id": "alice",
            "thinking_style": {
                "favorite_keywords": ["entropy", "systems", "causality"],
                "writing_tone": "analytical, scientific, philosophical",
                "debate_strategy": "First-principles reasoning"
            },
            "knowledge_interests": ["Physics", "Philosophy", "Complex Systems"],
            "interaction_history_embeddings": [...],  # Vector trung bình
            "last_updated": "2026-01-01T00:00:00"
        }
        """
        try:
            # Lấy từ Supabase table "user_profiles"
            response = self.db.table("user_profiles").select("*").eq("user_id", self.user_id).execute()
            
            if response.data:
                return json.loads(response.data[0]["profile_json"])
            else:
                # Tạo profile mới
                default_profile = {
                    "user_id": self.user_id,
                    "thinking_style": {},
                    "knowledge_interests": [],
                    "interaction_history_embeddings": [],
                    "last_updated": datetime.now().isoformat()
                }
                return default_profile
        except Exception as e:
            st.warning(f"Không load được profile: {e}")
            return {}
    
    def record_interaction(self, interaction_type, content, context=None):
        """
        Ghi lại mọi tương tác của user
        
        Args:
            interaction_type: "debate", "translation", "book_analysis", "query"
            content: Nội dung user viết/nói
            context: Dict chứa thông tin bổ sung (VD: persona_used, result)
        """
        if not content or len(content.strip()) < 10:
            return  # Bỏ qua input quá ngắn
        
        # 1. Tạo embedding
        embedding = self.encoder.encode([content])[0].tolist()
        
        # 2. Lưu vào DB (table "user_interactions")
        data = {
            "user_id": self.user_id,
            "type": interaction_type,
            "content": content,
            "embedding": json.dumps(embedding),  # Supabase JSON field
            "context": json.dumps(context or {}),
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            self.db.table("user_interactions").insert(data).execute()
        except Exception as e:
            st.warning(f"Không ghi được interaction: {e}")
    
    def update_profile(self, force=False):
        """
        Cập nhật user profile dựa trên lịch sử tương tác
        
        Logic:
        1. Lấy 100 tương tác gần nhất
        2. Clustering → Tìm chủ đề ưa thích
        3. Keyword extraction → Từ ngữ đặc trưng
        4. Tone analysis → Phong cách viết
        """
        # Chỉ update 1 lần/ngày (trừ khi force=True)
        if not force:
            last_update = datetime.fromisoformat(self.profile.get("last_updated", "2020-01-01"))
            if (datetime.now() - last_update).days < 1:
                return
        
        try:
            # 1. Lấy lịch sử
            response = self.db.table("user_interactions")\
                .select("*")\
                .eq("user_id", self.user_id)\
                .order("timestamp", desc=True)\
                .limit(100)\
                .execute()
            
            if not response.data or len(response.data) < 10:
                st.info("Chưa đủ dữ liệu để xây dựng profile (cần ít nhất 10 tương tác)")
                return
            
            interactions = response.data
            
            # 2. Phân tích
            contents = [item["content"] for item in interactions]
            embeddings = [json.loads(item["embedding"]) for item in interactions]
            
            # 2a. Vector trung bình (đại diện phong cách tư duy)
            avg_embedding = np.mean(embeddings, axis=0).tolist()
            
            # 2b. Keyword extraction (đơn giản: word frequency)
            from collections import Counter
            all_words = " ".join(contents).lower().split()
            common_words = [word for word, count in Counter(all_words).most_common(20)
                          if len(word) > 4]  # Lọc từ ngắn
            
            # 2c. Phân loại tone (dựa trên interaction type distribution)
            type_counts = Counter([item["type"] for item in interactions])
            dominant_type = type_counts.most_common(1)[0][0]
            
            tone_map = {
                "debate": "analytical, argumentative, logical",
                "translation": "multilingual, literary",
                "book_analysis": "scholarly, reflective, interdisciplinary",
                "query": "curious, information-seeking"
            }
            
            # 3. Cập nhật profile
            self.profile.update({
                "thinking_style": {
                    "favorite_keywords": common_words[:10],
                    "writing_tone": tone_map.get(dominant_type, "neutral"),
                    "debate_strategy": "First-principles reasoning"  # [Inference] Giả định
                },
                "interaction_history_embeddings": avg_embedding,
                "last_updated": datetime.now().isoformat()
            })
            
            # 4. Lưu lại DB
            profile_json = json.dumps(self.profile, ensure_ascii=False)
            self.db.table("user_profiles")\
                .upsert({
                    "user_id": self.user_id,
                    "profile_json": profile_json
                })\
                .execute()
            
            st.success("✅ Đã cập nhật AI Profile!")
            
        except Exception as e:
            st.error(f"Lỗi update profile: {e}")
    
    def get_personalized_context(self, query, top_k=5):
        """
        Lấy context cá nhân hóa cho query
        
        Args:
            query: Câu hỏi/tình huống hiện tại
            top_k: Số tương tác cũ liên quan nhất
        
        Returns:
            str: Context để inject vào prompt
        """
        if not self.profile.get("interaction_history_embeddings"):
            return ""
        
        # 1. Encode query
        query_emb = self.encoder.encode([query])[0]
        
        # 2. Lấy lịch sử từ DB
        try:
            response = self.db.table("user_interactions")\
                .select("*")\
                .eq("user_id", self.user_id)\
                .order("timestamp", desc=True)\
                .limit(50)\
                .execute()
            
            if not response.data:
                return ""
            
            # 3. Tính similarity
            interactions = response.data
            embeddings = [json.loads(item["embedding"]) for item in interactions]
            
            similarities = cosine_similarity([query_emb], embeddings)[0]
            
            # 4. Lấy top_k
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            context_parts = []
            for idx in top_indices:
                item = interactions[idx]
                context_parts.append(
                    f"[{item['type']}] {item['content'][:200]}"
                )
            
            # 5. Build context string
            context = f"""
            === USER CONTEXT (Phong cách tư duy của người này) ===
            Keywords ưa thích: {', '.join(self.profile.get('thinking_style', {}).get('favorite_keywords', []))}
            Tone: {self.profile.get('thinking_style', {}).get('writing_tone', 'neutral')}
            
            === RELEVANT PAST INTERACTIONS ===
            {chr(10).join(context_parts)}
            ===
            """
            
            return context
            
        except Exception as e:
            st.warning(f"Không lấy được context: {e}")
            return ""
    
    def generate_persona_prompt(self):
        """
        [Inference] Tạo system prompt để AI mô phỏng user
        
        Returns:
            str: System instruction
        """
        if not self.profile:
            return None
        
        style = self.profile.get("thinking_style", {})
        keywords = ", ".join(style.get("favorite_keywords", []))
        tone = style.get("writing_tone", "neutral")
        
        prompt = f"""
        BẠN ĐANG MÔ PHỎNG PHONG CÁCH TƯ DUY CỦA USER "{self.user_id}".
        
        Đặc điểm:
        - Từ ngữ ưa dùng: {keywords}
        - Phong cách viết: {tone}
        - Chiến lược lập luận: First-principles reasoning, interdisciplinary connections
        
        Nhiệm vụ: Trả lời câu hỏi THEO PHONG CÁCH NÀY, như thể chính user đang tự trả lời.
        """
        
        return prompt


# === CÁCH TÍCH HỢP VÀO module_weaver.py ===

def demo_personal_rag():
    """
    Thêm vào TAB mới: "🧠 AI Học Tôi"
    """
    from personal_rag_system import PersonalRAG
    from ai_core import AI_Core
    
    st.header("🧠 AI Học Phong Cách Tư Duy Của Bạn")
    
    # Init
    if has_db:  # Biến global từ module_weaver.py
        user_id = st.session_state.get("current_user", "Unknown")
        rag = PersonalRAG(supabase, user_id)
        ai = AI_Core()
        
        # 1. Hiển thị Profile hiện tại
        with st.expander("📊 Profile hiện tại"):
            st.json(rag.profile)
        
        # 2. Nút cập nhật thủ công
        if st.button("🔄 Cập nhật Profile (phân tích lại lịch sử)"):
            rag.update_profile(force=True)
        
        # 3. Demo: AI mô phỏng user
        st.divider()
        st.subheader("🎭 AI Mô Phỏng Bạn")
        
        test_query = st.text_area(
            "Đặt một câu hỏi → AI sẽ trả lời THEO PHONG CÁCH CỦA BẠN:",
            height=100
        )
        
        if st.button("🚀 Chạy") and test_query:
            with st.spinner("Đang phân tích phong cách..."):
                # Lấy context cá nhân hóa
                context = rag.get_personalized_context(test_query, top_k=3)
                
                # Tạo persona prompt
                persona_prompt = rag.generate_persona_prompt()
                
                # Build full prompt
                full_prompt = f"""
                {context}
                
                === NHIỆM VỤ ===
                Câu hỏi: {test_query}
                
                Hãy trả lời theo phong cách tư duy được mô tả ở trên.
                """
                
                # Gọi AI
                response = ai.generate(
                    full_prompt,
                    model_type="pro",
                    system_instruction=persona_prompt
                )
                
                st.markdown("### 🤖 AI mô phỏng bạn:")
                st.markdown(response)
                
                # Ghi lại interaction này
                rag.record_interaction(
                    "query",
                    test_query,
                    {"ai_response": response}
                )
    else:
        st.error("Cần kết nối Supabase để dùng tính năng này")


# === CẤU TRÚC TABLE SUPABASE CẦN TẠO ===

"""
-- Table 1: user_profiles
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id TEXT UNIQUE NOT NULL,
    profile_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table 2: user_interactions
CREATE TABLE user_interactions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding JSONB NOT NULL,
    context JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Index cho tìm kiếm nhanh
CREATE INDEX idx_user_interactions_user_id ON user_interactions(user_id);
CREATE INDEX idx_user_interactions_timestamp ON user_interactions(timestamp DESC);
"""
