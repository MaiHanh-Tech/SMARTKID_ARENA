from pypdf import PdfReader
from docx import Document
import re

def doc_file(uploaded_file):
    """
    Đọc nội dung từ file upload hoặc file path
    Hỗ trợ: PDF, DOCX, TXT, MD
    """
    if not uploaded_file: 
        return ""
    
    try:
        # Lấy extension
        if hasattr(uploaded_file, 'name'):
            ext = uploaded_file.name.split('.')[-1].lower()
        else:
            ext = str(uploaded_file).split('.')[-1].lower()
        
        if ext == "pdf":
            reader = PdfReader(uploaded_file)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
            return clean_text(text)
            
        elif ext == "docx":
            doc = Document(uploaded_file)
            text = "\n".join([p.text for p in doc.paragraphs])
            return clean_text(text)
            
        elif ext in ["txt", "md", "html"]:
            if hasattr(uploaded_file, 'read'):
                content = uploaded_file.read()
                if isinstance(content, bytes):
                    return clean_text(content.decode('utf-8'))
                return clean_text(content)
            else:
                with open(uploaded_file, 'r', encoding='utf-8') as f:
                    return clean_text(f.read())
                    
    except Exception as e:
        print(f"Lỗi đọc file: {e}")
        return ""
    
    return ""

def clean_text(text):
    """Làm sạch văn bản (loại bỏ ký tự lạ, khoảng trắng thừa)"""
    if not text: 
        return ""
    
    # Loại bỏ ký tự điều khiển
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    
    # Chuẩn hóa khoảng trắng
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()
