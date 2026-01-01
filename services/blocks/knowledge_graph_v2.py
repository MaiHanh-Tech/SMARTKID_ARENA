# (Nội dung nguyên bản knowledge_graph_v2.py được đưa vào đây)
"""
KNOWLEDGE GRAPH V2 - Hệ thống Tri thức Đa tầng
Triết lý: Dựa trên "The Order of Things" (Foucault) và "Thinking in Systems" (Meadows)
"""
import networkx as nx
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering
import streamlit as st
from datetime import datetime

class KnowledgeUniverse:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.encoder = self._load_encoder()
        self.episteme_layers = {
            "Toán học & Logic": [],
            "Vật lý & Sinh học": [],
            "Văn hóa & Quyền lực": [],
            "Ý thức & Giải phóng": []
        }
    @st.cache_resource
    def _load_encoder(_self):
        return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device='cpu')
    def add_book(self, title, content_summary, metadata=None):
        if metadata is None:
            metadata = {}
        node_id = f"book_{len(self.graph.nodes)}"
        embedding = self.encoder.encode([content_summary])[0]
        self.graph.add_node(node_id, type="book", title=title, embedding=embedding, added_at=datetime.now().isoformat(), **metadata)
        layer = self._classify_episteme(content_summary, metadata.get("tags", []))
        if layer in self.episteme_layers:
            self.episteme_layers[layer].append(node_id)
        self._auto_link_node(node_id)
        return node_id
    def _classify_episteme(self, text, tags):
        keywords_map = {
            "Toán học & Logic": ["logic", "math", "proof", "toán", "xác suất"],
            "Vật lý & Sinh học": ["physics", "evolution", "brain", "não bộ", "vật lý"],
            "Văn hóa & Quyền lực": ["power", "culture", "society", "quyền lực", "văn hóa"],
            "Ý thức & Giải phóng": ["consciousness", "mindfulness", "thiền", "ý thức"]
        }
        text_lower = text.lower()
        for layer, keywords in keywords_map.items():
            if any(kw in text_lower or kw in tags for kw in keywords):
                return layer
        return "Văn hóa & Quyền lực"
    def _auto_link_node(self, node_id, threshold=0.6):
        new_node = self.graph.nodes[node_id]
        new_emb = new_node["embedding"]
        new_time = datetime.fromisoformat(new_node["added_at"])
        for other_id in self.graph.nodes:
            if other_id == node_id:
                continue
            other_node = self.graph.nodes[other_id]
            other_emb = other_node["embedding"]
            other_time = datetime.fromisoformat(other_node["added_at"])
            sim = cosine_similarity([new_emb], [other_emb])[0][0]
            if sim > threshold:
                if new_time > other_time:
                    self.graph.add_edge(other_id, node_id, relation="influence", weight=sim, confidence=sim)
                else:
                    self.graph.add_edge(node_id, other_id, relation="reference", weight=sim, confidence=sim)
    def find_related_books(self, query_text, top_k=5):
        query_emb = self.encoder.encode([query_text])[0]
        results = []
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            if node["type"] != "book":
                continue
            sim = cosine_similarity([query_emb], [node["embedding"]])[0][0]
            path_explanation = self._explain_connection(query_text, node_id)
            results.append((node_id, node["title"], float(sim), path_explanation))
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:top_k]
    def _explain_connection(self, query, node_id):
        node = self.graph.nodes[node_id]
        layer = None
        for l, nodes in self.episteme_layers.items():
            if node_id in nodes:
                layer = l
                break
        neighbors = list(self.graph.neighbors(node_id))
        explanation = f"Thuộc tầng '{layer}'"
        if neighbors:
            neighbor_titles = [self.graph.nodes[n]["title"] for n in neighbors[:2]]
            explanation += f" | Liên quan: {', '.join(neighbor_titles)}"
        return explanation
    def get_episteme_summary(self):
        summary = {}
        for layer, node_ids in self.episteme_layers.items():
            books = [self.graph.nodes[nid]["title"] for nid in node_ids[-3:]]
            summary[layer] = {"count": len(node_ids), "recent": books}
        return summary
        
    def detect_contradictions(self, threshold=0.8):
        """
        Tìm các cặp sách có nội dung giống nhau (sim > threshold)
        NHƯNG thuộc các tầng tri thức đối lập nhau (Episteme Conflict).
        """
        contradictions = []
        # Định nghĩa các cặp tầng kiến thức thường có xung đột triết học
        conflict_pairs = [
            ("Vật lý & Sinh học", "Ý thức & Giải phóng"),  # Duy vật (Khoa học) vs Duy tâm (Tâm linh)
            ("Toán học & Logic", "Văn hóa & Quyền lực")    # Chân lý tuyệt đối vs Chân lý tương đối (Xã hội)
        ]

        for layer_a, layer_b in conflict_pairs:
            nodes_a = self.episteme_layers.get(layer_a, [])
            nodes_b = self.episteme_layers.get(layer_b, [])

            for id_a in nodes_a:
                for id_b in nodes_b:
                    # Bỏ qua nếu node không tồn tại trong graph
                    if id_a not in self.graph.nodes or id_b not in self.graph.nodes:
                        continue
                        
                    node_a = self.graph.nodes[id_a]
                    node_b = self.graph.nodes[id_b]
                    
                    # Tính độ tương đồng
                    sim = cosine_similarity([node_a["embedding"]], [node_b["embedding"]])[0][0]
                    
                    if sim > threshold:
                        contradictions.append({
                            "book_1": node_a["title"],
                            "book_2": node_b["title"],
                            "similarity": float(sim),
                            "tension": f"{layer_a} ⚡ {layer_b}",
                            "explanation": "Cùng chủ đề nhưng khác hệ quy chiếu triết học (Episteme Conflict)."
                        })
        
        # Sắp xếp theo độ mâu thuẫn giảm dần
        contradictions.sort(key=lambda x: x["similarity"], reverse=True)
        return contradictions
    
    
    def export_for_visualization(self):
        nodes = []
        edges = []
        color_map = {
            "Toán học & Logic": "#FF6B6B",
            "Vật lý & Sinh học": "#4ECDC4",
            "Văn hóa & Quyền lực": "#FFD93D",
            "Ý thức & Giải phóng": "#A8E6CF"
        }
        for node_id in self.graph.nodes:
            node_data = self.graph.nodes[node_id]
            layer = None
            for l, nids in self.episteme_layers.items():
                if node_id in nids:
                    layer = l
                    break
            nodes.append({"id": node_id, "label": node_data["title"], "color": color_map.get(layer, "#CCCCCC"), "size": 20})
        for u, v, data in self.graph.edges(data=True):
            edges.append({"source": u, "target": v, "label": data.get("relation", ""), "color": "#888888", "width": data.get("weight", 1) * 3})
        return nodes, edges

@st.cache_resource
def init_knowledge_universe():
    return KnowledgeUniverse()

def upgrade_existing_database(excel_path, kg: KnowledgeUniverse):
    import pandas as pd
    df = pd.read_excel(excel_path).dropna(subset=["Tên sách"])
    for idx, row in df.iterrows():
        title = row["Tên sách"]
        summary = str(row.get("CẢM NHẬN", ""))
        metadata = {"author": row.get("Tác giả", "Unknown"), "tags": str(row.get("Tags", "")).split(",")}
        kg.add_book(title, summary, metadata)
    return kg
