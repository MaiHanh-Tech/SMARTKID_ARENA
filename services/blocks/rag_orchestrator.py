import streamlit as st
from services.blocks.file_processor import clean_pdf_text, split_smart_chunks
from services.blocks.embedding_engine import load_encoder, encode_texts
from ai_core import AI_Core
from services.blocks.db_block import DBBlock
# knowledge_graph_v2 and personal_rag_system integrated in services.blocks (import below)
from services.blocks import knowledge_graph_v2 as kg_module
from services.blocks import personal_rag_system as pr_module

db = DBBlock()
ai = AI_Core()

def analyze_document_streamlit(file_name, text, user_lang='vi', max_chars=30000):
    """
    High-level function to analyze a document (used by UI).
    Uses ai.analyze_static (cached) for RAG analysis.
    """
    instr = st.secrets.get("book_analysis_prompt", None)
    # fallback to prompts.BOOK_ANALYSIS_PROMPT if available
    try:
        from prompts import BOOK_ANALYSIS_PROMPT
    except Exception:
        BOOK_ANALYSIS_PROMPT = instr or "Analyze the document."

    content = text[:max_chars]
    return ai.analyze_static(content, BOOK_ANALYSIS_PROMPT)

def store_history(loai, title, content):
    user = st.session_state.get("current_user", "Unknown")
    db.insert_history(loai, title, content[:1000], user)

def compute_similarity_with_excel(text, excel_df, encoder=None):
    """
    Given document text and an excel dataframe of books (column 'Tên sách' and optional 'CẢM NHẬN'),
    compute similarity and return top matches.
    """
    if encoder is None:
        encoder = load_encoder()
    if encoder is None or excel_df is None or excel_df.empty:
        return []
    db_texts = [f"{r['Tên sách']} {str(r.get('CẢM NHẬN',''))}" for _, r in excel_df.iterrows()]
    emb_db = encode_texts(encoder, db_texts)
    q_emb = encode_texts(encoder, [text[:2000]])[0]
    from sklearn.metrics.pairwise import cosine_similarity
    sims = cosine_similarity([q_emb], emb_db)[0]
    idx = sims.argsort()[::-1][:3]
    matches = []
    for i in idx:
        if sims[i] > 0.35:
            matches.append((excel_df.iloc[i]["Tên sách"], float(sims[i])))
    return matches

# Helpers to expose KnowledgeUniverse / PersonalRAG
def init_knowledge_universe():
    return kg_module.init_knowledge_universe()

def create_personal_rag(supabase_client, user_id):
    return pr_module.PersonalRAG(supabase_client, user_id)
