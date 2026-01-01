import logging
from datetime import datetime

class AppLogger:
    def __init__(self):
        self.logger = logging.getLogger("CognitiveWeaver")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(f"logs/app_{datetime.now().strftime('%Y%m%d')}.log")
        fh.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        
        self.logger.addHandler(fh)
    
    def log_api_call(self, model, tokens, latency, success):
        """Log mỗi API call để phân tích sau"""
        self.logger.info(f"API_CALL | Model={model} | Tokens={tokens} | Latency={latency}s | Success={success}")
    
    def log_error(self, module, error, traceback):
        """Log errors với full traceback"""
        self.logger.error(f"ERROR | Module={module} | Error={error}\n{traceback}")
    
    def log_user_action(self, user, action, metadata):
        """Log user actions cho analytics"""
        self.logger.info(f"USER_ACTION | User={user} | Action={action} | Metadata={metadata}")

# Sử dụng trong ai_core.py:
from logger import AppLogger
logger = AppLogger()

def generate(self, prompt, model_type="flash"):
    start = time.time()
    try:
        result = ...
        latency = time.time() - start
        logger.log_api_call(model_type, len(prompt), latency, True)
        return result
    except Exception as e:
        logger.log_error("AI_Core", str(e), traceback.format_exc())
        raise
