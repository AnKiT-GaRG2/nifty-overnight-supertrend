"""Minimal Markdown -> PDF (headings, paragraphs, bullets, numbered lists, tables) using reportlab. Usage: md_to_pdf.py in.md out.pdf"""
import sys, re
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
ss = getSampleStyleSheet()
B = ParagraphStyle('b', parent=ss['BodyText'], fontSize=9, leading=12)
T = ParagraphStyle('t', parent=B, fontSize=7.5, leading=9.5)
TH = ParagraphStyle('th', parent=T, fontName='Helvetica-Bold', textColor=colors.white)
H = {1: ParagraphStyle('h1', parent=ss['Heading1'], fontSize=16), 2: ParagraphStyle('h2', parent=ss['Heading2'], fontSize=12.5), 3: ParagraphStyle('h3', parent=ss['Heading3'], fontSize=10.5)}
def inl(t):
    t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t); t = re.sub(r'(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)', r'<i>\1</i>', t)
    return re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', t)
lines = open(sys.argv[1], encoding='utf-8').read().split('\n'); out = []; i = 0
W = landscape(A4)[0] - 24 * mm
while i < len(lines):
    l = lines[i]
    if l.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            if not re.match(r'^\|[\s\-|:]+\|$', lines[i]): rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
            i += 1
        k = len(rows[0]); data = [[Paragraph(inl(c), TH if r == 0 else T) for c in row + [''] * (k - len(row))] for r, row in enumerate(rows)]
        first = 0.22 if k > 3 else 0.3; cw = [W * first] + [W * (1 - first) / (k - 1)] * (k - 1)
        t = Table(data, colWidths=cw, repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2b4a6f')), ('GRID', (0, 0), (-1, -1), 0.3, colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f5f9')]), ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]))
        out += [t, Spacer(1, 6)]; continue
    m = re.match(r'^(#{1,3}) (.*)', l)
    if m: out.append(Paragraph(inl(m.group(2)), H[len(m.group(1))]))
    elif l.startswith('- '): out.append(Paragraph('• ' + inl(l[2:]), B, ))
    elif l.startswith('> '): out.append(Paragraph(inl(l[2:]), B))
    elif l.strip(): out.append(Paragraph(inl(l), B))
    else: out.append(Spacer(1, 3))
    i += 1
def foot(c, d): c.setFont('Helvetica', 7); c.drawRightString(landscape(A4)[0] - 12 * mm, 8 * mm, f'Page {d.page}')
SimpleDocTemplate(sys.argv[2], pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=14 * mm, title='Nifty futures factor backtest report', author='Ankit Garg').build(out, onFirstPage=foot, onLaterPages=foot)
