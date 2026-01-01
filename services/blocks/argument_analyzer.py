import json
from services.blocks.ai_core import AI_Core

class ArgumentAnalyzer:
    FALLACIES = {
        "ad_hominem": {
            "keywords": ["ngu", "dốt", "không hiểu biết", "kém"],
            "pattern": r"(bạn|anh|chị).*(ngu|dốt|kém)",
            "severity": "high",
            "explanation": "Tấn công cá nhân thay vì phản biện lập luận"
        },
        "strawman": {
            "keywords": ["bạn nói rằng", "theo bạn thì"],
            "severity": "high",
            "explanation": "Bóp méo lập luận của đối phương để dễ bác bỏ"
        },
        "appeal_to_authority": {
            "keywords": ["theo giáo sư", "nhà khoa học nói", "chuyên gia cho rằng"],
            "severity": "medium",
            "explanation": "Dựa vào uy tín thay vì bằng chứng"
        },
        "false_dichotomy": {
            "keywords": ["hoặc là", "chỉ có 2 lựa chọn", "không thì"],
            "severity": "medium",
            "explanation": "Đưa ra lựa chọn nhị phân khi có nhiều khả năng hơn"
        }
    }
    
    def __init__(self):
        self.ai = AI_Core()
    
    def analyze_argument(self, text):
        structure = self._extract_structure(text)
        fallacies = self._detect_fallacies(text)
        strength = self._calculate_strength(structure, fallacies)
        return {**structure, "fallacies": fallacies, "strength": strength}
    
    def _extract_structure(self, text):
        prompt = f"""Phân tích cấu trúc lập luận sau theo mô hình Toulmin:
Text: {text}
Trả về JSON format:
{{
  "claims": ["luận điểm 1"],
  "evidence": ["bằng chứng 1"],
  "warrants": ["lý do 1"],
  "qualifiers": ["điều kiện 1"],
  "rebuttals": ["phản biện 1"]
}}
Chỉ trả về JSON."""
        result = self.ai.generate(prompt, model_type="flash")
        try:
            return json.loads(result)
        except:
            return {"claims": [], "evidence": [], "warrants": [], "qualifiers": [], "rebuttals": []}
    
    def _detect_fallacies(self, text):
        detected = []
        text_lower = text.lower()
        for fallacy_name, config in self.FALLACIES.items():
            if any(kw in text_lower for kw in config["keywords"]):
                detected.append({
                    "type": fallacy_name,
                    "severity": config["severity"],
                    "explanation": config["explanation"],
                    "confidence": "medium"
                })
        
        if not detected:
            ai_fallacies = self._ai_fallacy_detection(text)
            detected.extend(ai_fallacies)
        return detected
    
    def _ai_fallacy_detection(self, text):
        prompt = f"""Tìm các ngụy biện (logical fallacies) trong đoạn: {text}
Trả về JSON: [{{"type": "tên_ngụy_biện", "explanation": "giải thích", "quote": "đoạn trích"}}]
Chỉ trả về JSON."""
        result = self.ai.generate(prompt, model_type="flash")
        try:
            return json.loads(result)
        except:
            return []
    
    def _calculate_strength(self, structure, fallacies):
        base_score = 50
        fallacy_penalty = sum({"high": 20, "medium": 10, "low": 5}.get(f["severity"], 0) for f in fallacies)
        structure_bonus = 0
        if len(structure.get("evidence", [])) > 0: structure_bonus += 20
        if len(structure.get("warrants", [])) > 0: structure_bonus += 15
        if len(structure.get("rebuttals", [])) > 0: structure_bonus += 15
        return max(0, min(100, base_score - fallacy_penalty + structure_bonus))
