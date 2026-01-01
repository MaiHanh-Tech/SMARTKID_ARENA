"""
Lightweight orchestrator for RAG-related helpers used by UI modules.

Exports:
- analyze_document_streamlit(title, text, user_lang, max_chars)
- compute_similarity_with_excel(text, excel_df, encoder=None)
- store_history(loai, title, content)
- init_knowledge_universe() -> re-export from knowledge_graph_v2
- create_personal_rag(supabase_client, user_id) -> factory for PersonalRAG
- tai_lich_su(limit=50) -> tải lịch sử từ DB (tên VN để tương thích module_weaver)
"""
from typing import List, Tuple, Any
import streamlit as st

# Local blocks
from services.blocks.db_block import DBBlock
from services.blocks.embedding_engine import load_encoder, encode_texts
from services.blocks import knowledge_graph_v2 as kg_module
from services.blocks import personal_rag_system as pr_module

from ai_core import AI_Core
from prompts import BOOK_ANALYSIS_PROMPT

# sklearn
try:
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:
    cosine_similarity = None


def analyze_document_streamlit(title: str, text: str, user_lang: str = "vi", max_chars: int = 30000) -> str:
    """
    Thin wrapper around AI_Core.analyze_static for UI.
    Returns AI text (or error string).
    """
    try:
        ai = AI_Core()
        prompt = BOOK_ANALYSIS_PROMPT if 'BOOK_ANALYSIS_PROMPT' in globals() else BOOK_ANALYSIS_PROMPT
        content = text[:max_chars]
        return ai.analyze_static(content, prompt)
    except Exception as e:
        return f"❌ Lỗi phân tích: {e}"


def compute_similarity_with_excel(text: str, excel_df, encoder=None, top_k: int = 3) -> List[Tuple[str, float]]:
    """
    Encode text and dataframe of books (column 'Tên sách' and optional 'CẢM NHẬN'),
    return list of (title, similarity) top_k matches.
    """
    if excel_df is None or excel_df.empty:
        return []

    try:
        enc = encoder or load_encoder()
        if enc is None or cosine_similarity is None:
            return []

        db_texts = [f"{r['Tên sách']} {str(r.get('CẢM NHẬN',''))}" for _, r in excel_df.iterrows()]
        emb_db = encode_texts(enc, db_texts)
        q_emb = encode_texts(enc, [text[:2000]])[0]
        sims = cosine_similarity([q_emb], emb_db)[0]
        idx = sims.argsort()[::-1][:top_k]
        matches = []
        for i in idx:
            if sims[i] > 0.0:
                matches.append((excel_df.iloc[i]["Tên sách"], float(sims[i])))
        return matches
    except Exception:
        return []


def store_history(loai: str, title: str, content: str) -> bool:
    """
    Lưu lại log vào history via DBBlock.
    """
    try:
        db = DBBlock()
        user = st.session_state.get("current_user", "Unknown")
        return db.insert_history(loai, title, content[:1000], user)
    except Exception:
        return False


# Re-export/init helpers for Knowledge Graph and Personal RAG
def init_knowledge_universe():
    """Return cached KnowledgeUniverse (or initialize)."""
    try:
        return kg_module.init_knowledge_universe()
    except Exception:
        return None


def create_personal_rag(supabase_client, user_id: str):
    """Factory to create PersonalRAG instance (wrapper)."""
    try:
        return pr_module.PersonalRAG(supabase_client, user_id)
    except Exception:
        return None


# VN-named helper used by module_weaver: tai_lich_su
def tai_lich_su(limit: int = 50) -> List[dict]:
    """
    Tải lịch sử từ Supabase (history_logs). Trả về danh sách dict theo cấu trúc cũ.
    Returns [] nếu không kết nối.
    """
    db = DBBlock()
    if not db.connected:
        return []

    try:
        raw = db.get_history(limit=limit)
        if not raw:
            return []

        # Normalize keys to expected names (Time, Type, Title, Content, User, SentimentScore, SentimentLabel)
        formatted = []
        for item in raw:
            def get_val(keys, default=""):
                for k in keys:
                    if k in item and item[k] is not None:
                        return item[k]
                return default

            raw_time = get_val(["created_at", "Time", "time"], "")
            clean_time = str(raw_time).replace("T", " ")[:19] if raw_time else ""

            formatted.append({
                "Time": clean_time,
                "Type": get_val(["type", "Type"], ""),
                "Title": get_val(["title", "Title"], ""),
                "Content": get_val(["content", "Content"], ""),
                "User": get_val(["user_name", "User", "user"], "Unknown"),
                "SentimentScore": get_val(["sentiment_score", "SentimentScore"], 0.0),
                "SentimentLabel": get_val(["sentiment_label", "SentimentLabel"], "Neutral")
            })
        return formatted
    except Exception:
        return []
