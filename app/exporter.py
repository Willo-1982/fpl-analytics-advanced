from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io, pandas as pd
def df_to_csv_bytes(df: pd.DataFrame)->bytes: return df.to_csv(index=False).encode('utf-8')
def tables_pdf(title, sections: dict)->bytes:
    buf=io.BytesIO(); doc=SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles=getSampleStyleSheet(); story=[Paragraph(title, styles['Title']), Spacer(1,12)]
    for t, df in sections.items():
        story.append(Paragraph(t, styles['Heading2'])); data=[list(df.columns)]+df.astype(str).values.tolist()
        tbl=Table(data, repeatRows=1); tbl.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('GRID',(0,0),(-1,-1),0.25,colors.grey)]))
        story.append(tbl); story.append(Spacer(1,12))
    doc.build(story); pdf=buf.getvalue(); buf.close(); return pdf
