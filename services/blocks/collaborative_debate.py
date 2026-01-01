from datetime import datetime
from ai_core import AI_Core
import streamlit as st

class CollaborativeDebateRoom:
    def __init__(self, room_id, topic, db_client):
        self.room_id = room_id
        self.topic = topic
        self.db = db_client
        self.participants = {}
        self.messages = []
    
    def join_room(self, user_id, user_name, role="participant"):
        """User tham gia phòng tranh luận"""
        self.participants[user_id] = {
            "name": user_name,
            "role": role,
            "join_time": datetime.now(),
            "messages_count": 0
        }
        self._broadcast_message("system", f"{user_name} đã tham gia phòng tranh luận")
    
    def send_message(self, user_id, message):
        """User gửi message"""
        if user_id not in self.participants:
            return False, "Bạn chưa join room"
        
        msg_data = {
            "user_id": user_id,
            "user_name": self.participants[user_id]["name"],
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.messages.append(msg_data)
        self.participants[user_id]["messages_count"] += 1
        
        # Save to DB
        self._save_message_to_db(msg_data)
        
        # Check if AI should intervene (Every 5 messages)
        if len(self.messages) % 5 == 0:
            self._ai_moderator_summary()
        
        return True, "OK"
    
    def _ai_moderator_summary(self):
        recent_msgs = self.messages[-5:]
        context = "\n".join([f"{m['user_name']}: {m['message']}" for m in recent_msgs])
        
        ai = AI_Core()
        prompt = f"""Bạn là AI Moderator trong cuộc tranh luận về: {self.topic}
5 message gần nhất:
{context}
Nhiệm vụ:
1. Tóm tắt ngắn gọn quan điểm các bên (2-3 câu)
2. Chỉ ra điểm chung / khác biệt
3. Đề xuất câu hỏi tiếp theo để thảo luận sâu hơn
Trả lời ngắn gọn, súc tích."""

        summary = ai.generate(prompt, model_type="flash")
        self._broadcast_message("ai_moderator", summary)
    
    def _broadcast_message(self, sender, message):
        if "room_messages" not in st.session_state:
            st.session_state.room_messages = []
        
        st.session_state.room_messages.append({
            "sender": sender,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def _save_message_to_db(self, msg_data):
        try:
            data = {"room_id": self.room_id, **msg_data}
            self.db.table("debate_messages").insert(data).execute()
        except Exception:
            pass
