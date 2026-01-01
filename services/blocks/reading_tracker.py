from datetime import datetime, timedelta
import streamlit as st

class ReadingProgressTracker:
    def __init__(self, db_client, user_id):
        self.db = db_client
        self.user_id = user_id
    
    def start_reading(self, book_id, book_title, total_pages):
        data = {
            "user_id": self.user_id,
            "book_id": book_id,
            "book_title": book_title,
            "total_pages": total_pages,
            "current_page": 0,
            "started_at": datetime.now().isoformat(),
            "status": "reading"
        }
        self.db.table("reading_progress").insert(data).execute()
    
    def update_progress(self, book_id, current_page):
        self.db.table("reading_progress").update({
            "current_page": current_page,
            "last_read": datetime.now().isoformat()
        }).eq("user_id", self.user_id).eq("book_id", book_id).execute()
        
        record = self.db.table("reading_progress").select("*").eq("book_id", book_id).single().execute()
        if record.data and current_page >= record.data["total_pages"]:
            self._mark_completed(book_id)
    
    def _mark_completed(self, book_id):
        self.db.table("reading_progress").update({
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }).eq("book_id", book_id).execute()
        self._create_review_card(book_id)
    
    def _create_review_card(self, book_id):
        data = {
            "user_id": self.user_id,
            "book_id": book_id,
            "repetition": 0,
            "ease_factor": 2.5,
            "interval": 1,
            "next_review": (datetime.now() + timedelta(days=1)).isoformat()
        }
        self.db.table("review_cards").insert(data).execute()
    
    def get_due_reviews(self):
        try:
            now = datetime.now().isoformat()
            response = self.db.table("review_cards")\
                .select("*, reading_progress(book_title)")\
                .eq("user_id", self.user_id)\
                .lte("next_review", now)\
                .execute()
            return response.data
        except Exception:
            return []
    
    def review_book(self, book_id, quality):
        card = self.db.table("review_cards").select("*")\
            .eq("book_id", book_id).single().execute().data
        
        if quality < 3:
            new_repetition = 0
            new_interval = 1
            new_ease = card["ease_factor"]
        else:
            new_repetition = card["repetition"] + 1
            if new_repetition == 1: new_interval = 1
            elif new_repetition == 2: new_interval = 6
            else: new_interval = int(card["interval"] * card["ease_factor"])
            new_ease = card["ease_factor"] + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            new_ease = max(1.3, new_ease)
        
        next_review = datetime.now() + timedelta(days=new_interval)
        self.db.table("review_cards").update({
            "repetition": new_repetition,
            "interval": new_interval,
            "ease_factor": new_ease,
            "next_review": next_review.isoformat(),
            "last_reviewed": datetime.now().isoformat()
        }).eq("book_id", book_id).execute()
