import logging
import os  
from datetime import datetime

class AppLogger:
    def __init__(self):
        self.logger = logging.getLogger("CognitiveWeaver")
        self.logger.setLevel(logging.INFO)
        
        if not os.path.exists("logs"):
            os.makedirs("logs")
        
        # File handler
        fh = logging.FileHandler(f"logs/app_{datetime.now().strftime('%Y%m%d')}.log")
        fh.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        
        # Tránh add handler nhiều lần nếu reload (duplicate logs)
        if not self.logger.handlers:
            self.logger.addHandler(fh)
    
    def log_api_call(self, model, tokens, latency, success):
        """Log mỗi API call để phân tích sau"""
        self.logger.info(f"API_CALL | Model={model} | Tokens={tokens} | Latency={latency:.2f}s | Success={success}")
    
    def log_error(self, module, error, traceback):
        """Log errors với full traceback"""
        self.logger.error(f"ERROR | Module={module} | Error={error}\n{traceback}")
    
    def log_user_action(self, user, action, metadata):
        """Log user actions cho analytics"""
        self.logger.info(f"USER_ACTION | User={user} | Action={action} | Metadata={metadata}")
