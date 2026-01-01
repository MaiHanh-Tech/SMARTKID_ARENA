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
    """
    Vũ Trụ Tri Thức - Graph đa tầng với:
    1. Node: Concepts (từ sách, từ user input)
    2. Edge: Relations (similarity, causality, contradiction)
    3. Meta-layer: Episteme (hệ tri thức - Foucault)
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()  # Directed graph cho quan hệ nhân quả
        self.encoder = self._load_encoder()
        self.episteme_layers = {
            "Toán học & Logic": [],
            "Vật lý & Sinh học": [],
            "Văn hóa & Quyền lực": [],
            "Ý thức & Giải phóng": []
        }
        
    @st.cache_resource
    def _load_encoder(_self):
        """Load embedding model một lần duy nhất"""
        return SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2",
            device='cpu'
        )
    
    def add_book(self, title, content_summary, metadata=None):
        """
        Thêm sách vào graph với phân tầng tự động
        
        Args:
            title: Tên sách
            content_summary: Tóm tắt nội dung (để embedding)
            metadata: Dict chứa {author, year, tags, layer}
        """
        if metadata is None:
            metadata = {}
        
        # 1. Tạo node
        node_id = f"book_{len(self.graph.nodes)}"
        embedding = self.encoder.encode([content_summary])[0]
        
        self.graph.add_node(
            node_id,
            type="book",
            title=title,
            embedding=embedding,
            added_at=datetime.now().isoformat(),
            **metadata
        )
        
        # 2. Phân tầng tri thức (dựa trên tags hoặc AI classification)
        layer = self._classify_episteme(content_summary, metadata.get("tags", []))
        if layer in self.episteme_layers:
            self.episteme_layers[layer].append(node_id)
        
        # 3. Tự động tạo edges với sách hiện có
        self._auto_link_node(node_id)
        
        return node_id
    
    def _classify_episteme(self, text, tags):
        """
        [Inference] Phân loại sách vào tầng tri thức
        Logic: Dựa trên keywords và user tags
        """
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
        
        return "Văn hóa & Quyền lực"  # Default layer
    
    def _auto_link_node(self, node_id, threshold=0.6):
        """
        Tự động tạo edges dựa trên:
        1. Cosine similarity (quan hệ tương đồng)
        2. Temporal order (sách cũ → sách mới: influence)
        3. Same episteme (cùng tầng tri thức: dialog)
        """
        new_node = self.graph.nodes[node_id]
        new_emb = new_node["embedding"]
        new_time = datetime.fromisoformat(new_node["added_at"])
        
        for other_id in self.graph.nodes:
            if other_id == node_id:
                continue
            
            other_node = self.graph.nodes[other_id]
            other_emb = other_node["embedding"]
            other_time = datetime.fromisoformat(other_node["added_at"])
            
            # Tính similarity
            sim = cosine_similarity([new_emb], [other_emb])[0][0]
            
            if sim > threshold:
                # Xác định hướng edge (temporal causality)
                if new_time > other_time:
                    # Sách cũ → sách mới
                    self.graph.add_edge(
                        other_id, node_id,
                        relation="influence",
                        weight=sim,
                        confidence=sim
                    )
                else:
                    # Sách mới → sách cũ (ít phổ biến)
                    self.graph.add_edge(
                        node_id, other_id,
                        relation="reference",
                        weight=sim,
                        confidence=sim
                    )
    
    def find_related_books(self, query_text, top_k=5):
        """
        Tìm sách liên quan đến query (user input hoặc tài liệu mới)
        
        Returns:
            List[Tuple]: [(node_id, title, similarity, path_explanation)]
        """
        query_emb = self.encoder.encode([query_text])[0]
        
        results = []
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            if node["type"] != "book":
                continue
            
            sim = cosine_similarity([query_emb], [node["embedding"]])[0][0]
            
            # Giải thích đường đi tri thức (nếu có path)
            path_explanation = self._explain_connection(query_text, node_id)
            
            results.append((
                node_id,
                node["title"],
                float(sim),
                path_explanation
            ))
        
        # Sort by similarity
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:top_k]
    
    def _explain_connection(self, query, node_id):
        """
        [Inference] Giải thích tại sao sách này liên quan
        Dựa trên graph structure và episteme layer
        """
        node = self.graph.nodes[node_id]
        layer = None
        for l, nodes in self.episteme_layers.items():
            if node_id in nodes:
                layer = l
                break
        
        # Tìm sách trung gian (nếu có)
        neighbors = list(self.graph.neighbors(node_id))
        
        explanation = f"Thuộc tầng '{layer}'"
        if neighbors:
            neighbor_titles = [self.graph.nodes[n]["title"] for n in neighbors[:2]]
            explanation += f" | Liên quan: {', '.join(neighbor_titles)}"
        
        return explanation
    
    def get_episteme_summary(self):
        """
        Trả về tổng quan 4 tầng tri thức
        
        Returns:
            Dict: {layer_name: {count, recent_books}}
        """
        summary = {}
        for layer, node_ids in self.episteme_layers.items():
            books = [
                self.graph.nodes[nid]["title"] 
                for nid in node_ids[-3:]  # 3 sách gần nhất
            ]
            summary[layer] = {
                "count": len(node_ids),
                "recent": books
            }
        return summary
    
    def detect_contradictions(self, threshold=0.8):
        """
        [Inference] Phát hiện mâu thuẫn tri thức
        
        Logic:
        - Nếu 2 sách có similarity cao (>0.8) nhưng thuộc 2 tầng khác xa
          → Có thể mâu thuẫn episteme (VD: Vật lý vs Tâm linh)
        
        Returns:
            List[Tuple]: [(book1, book2, reason)]
        """
        contradictions = []
        layer_distance = {
            ("Toán học & Logic", "Ý thức & Giải phóng"): 3,
            ("Vật lý & Sinh học", "Văn hóa & Quyền lực"): 2
        }
        
        # TODO: Implement logic phức tạp hơn
        # (Cần AI để phân tích semantic contradiction)
        
        return contradictions
    
    def export_for_visualization(self):
        """
        Export data cho streamlit-agraph hoặc Plotly
        
        Returns:
            Tuple: (nodes_list, edges_list)
        """
        nodes = []
        edges = []
        
        # Color map cho từng tầng
        color_map = {
            "Toán học & Logic": "#FF6B6B",
            "Vật lý & Sinh học": "#4ECDC4",
            "Văn hóa & Quyền lực": "#FFD93D",
            "Ý thức & Giải phóng": "#A8E6CF"
        }
        
        for node_id in self.graph.nodes:
            node_data = self.graph.nodes[node_id]
            
            # Xác định màu theo layer
            layer = None
            for l, nids in self.episteme_layers.items():
                if node_id in nids:
                    layer = l
                    break
            
            nodes.append({
                "id": node_id,
                "label": node_data["title"],
                "color": color_map.get(layer, "#CCCCCC"),
                "size": 20
            })
        
        for u, v, data in self.graph.edges(data=True):
            edges.append({
                "source": u,
                "target": v,
                "label": data.get("relation", ""),
                "color": "#888888",
                "width": data.get("weight", 1) * 3
            })
        
        return nodes, edges


# === HÀM HELPER ĐỂ TÍCH HỢP VÀO module_weaver.py ===

@st.cache_resource
def init_knowledge_universe():
    """Khởi tạo Knowledge Universe (cache để tái sử dụng)"""
    return KnowledgeUniverse()

def upgrade_existing_database(excel_path, kg: KnowledgeUniverse):
    """
    Chuyển đổi database Excel cũ sang Knowledge Graph mới
    
    Args:
        excel_path: Đường dẫn file Excel
        kg: Instance của KnowledgeUniverse
    """
    import pandas as pd
    
    df = pd.read_excel(excel_path).dropna(subset=["Tên sách"])
    
    for idx, row in df.iterrows():
        title = row["Tên sách"]
        summary = str(row.get("CẢM NHẬN", ""))
        metadata = {
            "author": row.get("Tác giả", "Unknown"),
            "tags": str(row.get("Tags", "")).split(",")
        }
        
        kg.add_book(title, summary, metadata)
    
    return kg
