class ServiceLocator:
    _services = {}
    
    @classmethod
    def register(cls, name, service):
        cls._services[name] = service
    
    @classmethod
    def get(cls, name):
        if name not in cls._services:
            cls._services[name] = cls._create_service(name)
        return cls._services[name]
    
    @classmethod
    def _create_service(cls, name):
        """Factory method - Import đúng đường dẫn services.blocks"""
        
        # 1. AI Core
        if name == "ai_core":
            # 👇 Sửa dòng này: Thêm services.blocks
            from services.blocks.ai_core import AI_Core
            return AI_Core()
            
        # 2. Voice Engine
        elif name == "voice_engine":
            try:
                # 👇 Sửa dòng này
                from services.blocks.voice_block import Voice_Engine
                return Voice_Engine()
            except ImportError:
                return None

        # 3. Reading Tracker (Ví dụ)
        elif name == "reading_tracker":
             # Với các class cần tham số động (user_id), Locator thường không tự tạo
             # mà chỉ dùng để lưu trữ (register) sau khi tạo bên ngoài.
             pass

        raise ValueError(f"❌ ServiceLocator: Không tìm thấy dịch vụ '{name}'")
