# services/report_generator.py
from fpdf import FPDF
from datetime import datetime

class ReportGenerator:
    @staticmethod
    def generate_quiz_report(player, quiz_results, weakness_topics=None):
        pdf = FPDF()
        pdf.add_page()
        
        # Tiếng Việt cần font hỗ trợ Unicode
        pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)  # Tải font này về thư mục dự án
        pdf.set_font("DejaVu", size=12)
        
        pdf.cell(200, 10, txt="BÁO CÁO HỌC TẬP - SMARTKID ARENA", ln=1, align="C")
        pdf.ln(10)
        
        pdf.cell(200, 10, txt=f"Học sinh: {player.name}", ln=1)
        pdf.cell(200, 10, txt=f"Ngày: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=1)
        pdf.ln(10)
        
        # Thống kê
        total = len(quiz_results)
        correct = sum(1 for q in quiz_results if q['is_correct'])
        pdf.cell(200, 10, txt=f"Tổng câu: {total}", ln=1)
        pdf.cell(200, 10, txt=f"Đúng: {correct} ({correct/total*100:.1f}%)", ln=1)
        pdf.ln(10)
        
        if weakness_topics:
            pdf.cell(200, 10, txt="Chủ đề cần tập trung:", ln=1)
            for topic in weakness_topics:
                pdf.cell(200, 10, txt=f"- {topic}", ln=1)
        
        # Lưu file tạm
        filename = f"report_{player.name}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        pdf.output(filename)
        return filename
