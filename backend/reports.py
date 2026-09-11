import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


class ReportGenerator:
    def __init__(self, reports_folder):
        self.reports_folder = reports_folder
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a73e8'),
            alignment=TA_CENTER,
            spaceAfter=20
        )

        self.subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#5f6368'),
            alignment=TA_CENTER,
            spaceAfter=30
        )

        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a73e8'),
            spaceBefore=20,
            spaceAfter=10
        )

        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=10
        )

    def generate(self, scan_data):
        report_filename = f"DiabCare_Report_{scan_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        report_path = os.path.join(self.reports_folder, report_filename)

        doc = SimpleDocTemplate(
            report_path,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        elements = []
        elements.extend(self._build_header(scan_data))
        elements.extend(self._build_scan_info(scan_data))
        elements.extend(self._build_prediction(scan_data))
        elements.extend(self._build_risk_assessment(scan_data))
        elements.extend(self._build_recommendations(scan_data))
        elements.extend(self._build_footer())

        doc.build(elements)
        return report_path

    def _build_header(self, scan_data):
        elements = []
        elements.append(Paragraph("DiabCare AI", self.title_style))
        elements.append(Paragraph("Diabetic Foot Screening Report", self.subtitle_style))
        elements.append(Spacer(1, 10))

        date_str = datetime.fromisoformat(scan_data['created_at']).strftime('%B %d, %Y at %I:%M %p')
        elements.append(Paragraph(f"Report Generated: {date_str}", self.body_style))
        elements.append(Paragraph(f"Scan ID: {scan_data['id']}", self.body_style))
        elements.append(Spacer(1, 20))
        return elements

    def _build_scan_info(self, scan_data):
        elements = []
        elements.append(Paragraph("Scan Information", self.header_style))

        data = [
            ['Parameter', 'Value'],
            ['Filename', scan_data['filename']],
            ['Scan Date', scan_data['created_at']],
            ['Image Analyzed', 'Yes']
        ]

        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))
        return elements

    def _build_prediction(self, scan_data):
        elements = []
        elements.append(Paragraph("AI Prediction Results", self.header_style))

        prediction = scan_data['prediction']
        confidence = scan_data['confidence']

        if prediction == 'Ulcer':
            pred_color = '#dc3545'
            pred_status = 'ABNORMAL - Ulcer Pattern Detected'
        else:
            pred_color = '#28a745'
            pred_status = 'NORMAL - No Ulcer Pattern Detected'

        data = [
            ['Metric', 'Result'],
            ['Classification', Paragraph(f'<font color="{pred_color}"><b>{pred_status}</b></font>', self.body_style)],
            ['Confidence Score', f'{confidence}%'],
            ['Model Used', 'YOLOv8 Classification'],
            ['Analysis Date', scan_data['created_at']]
        ]

        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))
        return elements

    def _build_risk_assessment(self, scan_data):
        elements = []
        elements.append(Paragraph("Risk Assessment", self.header_style))

        risk_level = scan_data['risk_level']
        risk_colors = {
            'HIGH': ('#dc3545', 'High Risk - Immediate attention recommended'),
            'MEDIUM': ('#ffc107', 'Medium Risk - Monitor closely'),
            'LOW': ('#28a745', 'Low Risk - Continue regular screening'),
            'UNCERTAIN': ('#6c757d', 'Uncertain - Retake image or consult professional')
        }

        color, description = risk_colors.get(risk_level, ('#6c757d', 'Unknown'))

        data = [
            ['Risk Level', 'Assessment'],
            ['Level', Paragraph(f'<font color="{color}"><b>{risk_level}</b></font>', self.body_style)],
            ['Description', description],
            ['Risk Score', f'{scan_data.get("risk_score", "N/A")}']
        ]

        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a73e8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))
        return elements

    def _build_recommendations(self, scan_data):
        elements = []
        elements.append(Paragraph("Recommendations", self.header_style))

        recommendations = scan_data.get('recommendations', [])
        if not recommendations:
            recommendations = ['Consult a healthcare professional for evaluation']

        for i, rec in enumerate(recommendations, 1):
            elements.append(Paragraph(f"{i}. {rec}", self.body_style))

        elements.append(Spacer(1, 20))
        return elements

    def _build_footer(self):
        elements = []
        elements.append(Spacer(1, 30))

        disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#6c757d'),
            alignment=TA_CENTER,
            spaceBefore=20
        )

        elements.append(Paragraph(
            "<b>DISCLAIMER:</b> This report is generated by an AI screening tool and is NOT a medical diagnosis. "
            "The results should be interpreted by a qualified healthcare professional. "
            "Always consult with a medical professional for proper diagnosis and treatment.",
            disclaimer_style
        ))

        elements.append(Spacer(1, 10))
        elements.append(Paragraph(
            "DiabCare AI - AI-Powered Diabetic Foot Early Warning System",
            disclaimer_style
        ))

        return elements
