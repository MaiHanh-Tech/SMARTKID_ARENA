"""
Robust RAG orchestrator helpers used by UI modules.

Exports:
- analyze_document_streamlit(title, text, user_lang, max_chars)
- compute_similarity_with_excel(text, excel_df, encoder=None, top_k=3)
- store_history(loai, title, content)
- init_knowledge_universe()
- create_personal_rag(supabase_client, user_id)
- tai_lich_su(limit=50)
"""
from typing import List, Tuple, Any
import streamlit as st
import traceback

# Local blocks
from services.blocks.embedding_engine import load_encoder, encode_texts
from services.blocks import knowledge_graph_v2 as kg_module
from services.blocks import personal_rag_system as pr_module

from ai_core import AI_Core
from prompts import BOOK_ANALYSIS_PROMPT

# sklearn (optional)
try:
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:
    cosine_similarity = None

# Supabase client (try import)
try:
    from supabase import create_client
except Exception:
    create_client = None

# Helper: create supabase client from st.secrets if available
def _get_supabase_client():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
    except Exception:
        return None
    if not create_client:
        return None
    try:
        return create_client(url, key)
    except Exception:
        # Some environments may expose a different factory; return None
        return None


# -------------------------
# Core helpers / wrappers
# -------------------------
def analyze_document_streamlit(title: str, text: str, user_lang: str = "vi", max_chars: int = 30000) -> str:
    """
    Thin wrapper around AI_Core.analyze_static for UI.
    Returns AI text (or error string).
    """
    try:
        ai = AI_Core()
        content = text[:max_chars]
        return ai.analyze_static(content, BOOK_ANALYSIS_PROMPT)
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
        import numpy as np
        idx = np.argsort(sims)[::-1][:top_k]
        matches = []
        for i in idx:
            if sims[i] > 0.0:
                matches.append((excel_df.iloc[i]["Tên sách"], float(sims[i])))
        return matches
    except Exception:
        return []


# -------------------------
# History / Supabase helpers
# -------------------------
def _try_insert_supabase(client, table: str, data: dict) -> bool:
    """
    Try common supabase client APIs to insert data.
    Returns True if seems successful, False otherwise.
    """
    if not client:
        return False

    # Try client.table(...).insert(...).execute()
    try:
        if hasattr(client, "table"):
            resp = client.table(table).insert(data).execute()
            # resp might be object or dict
            err = getattr(resp, "error", None) or (resp.get("error") if isinstance(resp, dict) else None)
            status = getattr(resp, "status_code", None) or (resp.get("status_code") if isinstance(resp, dict) else None)
            if not err and (status is None or int(status) in (200, 201, 204)):
                return True
    except Exception:
        pass

    # Try client.from_(...).insert(...).execute()
    try:
        if hasattr(client, "from_"):
            resp = client.from_(table).insert(data).execute()
            err = getattr(resp, "error", None) or (resp.get("error") if isinstance(resp, dict) else None)
            status = getattr(resp, "status_code", None) or (resp.get("status_code") if isinstance(resp, dict) else None)
            if not err and (status is None or int(status) in (200, 201, 204)):
                return True
    except Exception:
        pass

    return False


def store_history(loai: str, title: str, content: str) -> bool:
    """
    Store a history record in Supabase. Returns True on success.
    Tries multiple table name variations and client API styles.
    """
    client = _get_supabase_client()
    if not client:
        # no supabase configured
        return False

    user = st.session_state.get("current_user", "Unknown")
    data = {
        "type": loai,
        "title": title,
        "content": content,
        "user_name": user,
        "sentiment_score": 0.0,
        "sentiment_label": "Neutral"
    }

    table_names = ["history_logs", "History_Logs", "historylogs", "historyLogs"]
    last_exc = None
    for table in table_names:
        try:
            ok = _try_insert_supabase(client, table, data)
            if ok:
                return True
        except Exception as e:
            last_exc = e
            continue

    # As last resort, print traceback to logs for debugging
    if last_exc:
        traceback.print_exception(type(last_exc), last_exc, last_exc.__traceback__)
    else:
        print("store_history: insert attempts failed without exception (check response formats).")
    return False


def _try_select_supabase(client, table: str, limit: int = 50):
    """
    Try to select rows from supabase using common client APIs.
    Returns parsed 'data' or None.
    """
    if not client:
        return None
    # style: client.table(...).select(...).order(...).limit(...).execute()
    try:
        if hasattr(client, "table"):
            resp = client.table(table).select("*").order("created_at", desc=True).limit(limit).execute()
            data = getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else None)
            return data
    except Exception:
        pass

    # style: client.from_(...).select(...).order(...).limit(...).execute()
    try:
        if hasattr(client, "from_"):
            resp = client.from_(table).select("*").order("created_at", desc=True).limit(limit).execute()
            data = getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else None)
            return data
    except Exception:
        pass

    return None


def tai_lich_su(limit: int = 50) -> List[dict]:
    """
    Exported VN-named helper that fetches history records from Supabase and normalizes fields.
    Returns [] on failure or when no data.
    """
    client = _get_supabase_client()
    if not client:
        return []

    table_names = ["history_logs", "History_Logs", "historylogs", "historyLogs"]
    raw_data = None
    for table in table_names:
        try:
            raw_data = _try_select_supabase(client, table, limit=limit)
            if raw_data:
                break
        except Exception:
            continue

    if not raw_data:
        return []

    formatted = []
    for item in raw_data:
        # helper to get value irrespective of key case / naming
        def get_val(keys, default=""):
            for k in keys:
                if k in item and item[k] is not None:
                    return item[k]
            return default

        raw_time = get_val(["created_at", "createdAt", "Time", "time"], "")
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


# -------------------------
# Re-exports / factories
# -------------------------
def init_knowledge_universe():
    """
    Re-export init from knowledge_graph_v2 (if available).
    """
    try:
        return kg_module.init_knowledge_universe()
    except Exception:
        return None


def create_personal_rag(supabase_client, user_id: str):
    """
    Factory to create PersonalRAG instance (wrapper).
    """
    try:
        return pr_module.PersonalRAG(supabase_client, user_id)
    except Exception:
        return None
