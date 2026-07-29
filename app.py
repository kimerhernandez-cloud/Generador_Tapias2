import pandas as pd
import re
import html
import streamlit as st

st.set_page_config(page_title="Generador de Tapias", layout="centered")
st.title("🎪 Generador de Etiquetas / Tapias")

def obtener_apellido(nombre_completo):
    if pd.isna(nombre_completo): return ""
    partes = str(nombre_completo).strip().split()
    return partes[-1].upper() if len(partes)>=2 else str(nombre_completo).strip().upper()

def generar_html(df, titulo_etiqueta):
    grouped = df.groupby(['nombre_reserva', 'habitacion'], sort=False)
    cards = []
    for (nombre, habitacion), group in grouped:
        apellido_str = obtener_apellido(nombre)
        hab_str = str(habitacion).strip() if pd.notna(habitacion) else ""
        if hab_str.endswith('.0'): hab_str = hab_str[:-2]
        pax = int(group['pax'].sum())
        obs_full = str(group['observaciones'].iloc[0]).strip() if pd.notna(group['observaciones'].iloc[0]) else ""

        pax_rules = [(r'22\s*PAX',22),(r'SON\s*PAX\s*07|SON\s*PAX\s*7',7),(r'SON\s*03\s*PAX|SON\s*3\s*PAX',3),(r'SON\s*4\s*PAX',4),(r'SON\s*10\s*PAX|10\s*PAX',10),(r'SON\s*5\s*PAX',5),(r'SON\s*6\s*PAX',6),(r'SON\s*8\s*PAX',8),(r'SON\s*9\s*PAX',9),(r'SON\s*11\s*PAX',11),(r'SON\s*12\s*PAX',12)]
        for pat,val in pax_rules:
            if re.search(pat, obs_full.upper()): pax=val; break

        hora_val = group['hora'].iloc[0]
        hora = hora_val.strftime('%H:%M') if isinstance(hora_val, pd.Timestamp) else str(hora_val)[:5]
        cambio_horario=False
        m_hora = re.search(r'llegan?\s+a\s+las\s+(\d{1,2}:\d{2})', obs_full, re.I)
        if m_hora: hora=m_hora.group(1); cambio_horario=True
        elif re.search(r'llegar[aá]n\s+6\s*pm', obs_full, re.I): hora,cambio_horario="18:00",True
        elif re.search(r'llegar[aá]n\s+7\s*pm', obs_full, re.I): hora,cambio_horario="19:00",True

        badges=[]
        if re.search(r'RESIDENCE|S\.\s*RESIDENCE', obs_full.upper()): badges.append('🔑RESIDENCE')
        if re.search(r'DIAMANTE|DIAMANTES|A\.\s*DIAMANTE', obs_full.upper()): badges.append('💎DIAMANTE')
        if re.search(r'SEGUIMIENTO', obs_full.upper()): badges.append('🛑SEGUIMIENTO')

        palabras_hbd = r'cumpleaños|festejando|birthday|birthday\'s|graduacion|graduation|pastel|vela|\byear\'s\b|\byear\b'
        es_hbd = re.search(palabras_hbd, obs_full, re.I)
        es_ns = re.search(r'nuevos?\s+socios?|nuevos\s+miembros|nuevo\s+socio', obs_full, re.I)
        es_daypass = re.search(r'day\s+pass', obs_full, re.I)

        obs_clean = obs_full
        patrones_borrar = [r'Se informa código de vestir y tiempos\.?',r'Huésped enterado de políticas de cancelación hasta \d+\s*(horas?|hrs?)\s*antes de su cena y cargo extra de \$25 dólares por mesa por no presentarse y no cancelar a tiempo\.?',r'Sin alergias, ni dietas? especiales\.?',r'Sin alergias, ni dieta especial\.?',r'No alergias, No dietas especiales\.?',r'sin alergias reportadas',r'SIN ALERGIAS REPORTADAS',r'Sin alergias reportadas',r'sin observaciones especiales',r'NO ALERGIAS',r'Son\s*\d*\s*pax[,.\s]*',r'Son\s*\d*\s*pas[,.\s]*',r',\s*Huésped enterado de políticas de cancelación.*?$',r',\s*Se informa código de vestir.*?$']
        for pat in patrones_borrar: obs_clean = re.sub(pat,'',obs_clean,flags=re.I|re.DOTALL)

        etiqueta_especial=""
        if es_hbd: etiqueta_especial+='<div style="font-weight:bold;font-size:14pt;text-align:center;color:#c00;margin:0.8mm 0 0.4mm 0;white-space:nowrap;line-height:1.2;">🎂 HBD</div>'; obs_clean=""
        if es_ns: etiqueta_especial+='<div style="font-weight:bold;font-size:13pt;text-align:center;color:#006;margin:0.8mm 0 0.4mm 0;white-space:nowrap;line-height:1.2;">🆕 NS</div>'; obs_clean=""
        if es_daypass: etiqueta_especial+='<div style="font-weight:bold;font-size:13pt;text-align:center;color:#333;margin:0.8mm 0 0.4mm 0;white-space:nowrap;line-height:1.2;">🎟️ Day Pass</div>'; obs_clean=""

        obs_clean = re.sub(r'\s+',' ',obs_clean).strip().strip(',.;:')
        tam_obs = '9pt' if len(obs_clean)<60 else '7.5pt'
        obs_html = f'<div style="font-size:{tam_obs};line-height:1.45;max-height:11mm;overflow:hidden;word-wrap:break-word;margin-top:0.3mm;">{html.escape(obs_clean)}</div>' if obs_clean else ''
        cambio_html = f'<div style="color:#c00;font-weight:bold;font-size:9pt;margin:0.2mm 0;">⚠️ CAMBIO DE HORARIO</div>' if cambio_horario else ''
        badges_html = f'<div style="font-size:9pt;margin:0.1mm 0 0.3mm 0;">{" ".join(badges)}</div>' if badges else ''

        cards.append(f'<div style="width:100%;height:100%;border:1px solid #000;box-sizing:border-box;padding:0.8mm;overflow:hidden;display:flex;flex-direction:column;gap:0.15mm;page-break-inside:avoid;">{badges_html if badges_html else ""}<div style="text-align:center;font-weight:bold;font-size:9pt;border-bottom:0.5pt solid #666;padding-bottom:0.2mm;">🎪 {html.escape(titulo_etiqueta)}</div><div style="font-weight:bold;font-size:11.5pt;line-height:1.1;word-wrap:break-word;white-space:normal;">{html.escape(apellido_str)}</div><div style="font-size:12pt;"><b>Hab:</b> {html.escape(hab_str)} | <b>PX:</b> {pax}</div><div style="font-size:12pt;"><b>Hora:</b> {hora}</div>{cambio_html}{etiqueta_especial}{obs_html}</div>')

    html_total = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Tapias - {html.escape(titulo_etiqueta)}</title><style>@page{{size:letter landscape;margin:0mm;}}*{{box-sizing:border-box;margin:0;padding:0;}}body{{margin:0;padding:0;width:100%;}}.grid{{display:grid;grid-template-columns:repeat(6,1fr);grid-auto-rows:27mm;gap:0;width:100%;}}</style></head><body><div class="grid">{"".join(cards)}</div></body></html>'
    return html_total

nombre_etiqueta = st.text_input("Nombre para reemplazar CIRCO:", value="CIRCO")
archivo = st.file_uploader("📂 Sube tu archivo Excel (.xlsx)", type="xlsx")

if archivo and nombre_etiqueta.strip():
    df = pd.read_excel(archivo, engine="openpyxl")
    html_final = generar_html(df, nombre_etiqueta.strip())
    st.success("✅ ¡Listo! Descarga el archivo:")
    st.download_button("📄 Descargar TAPIAS_HOJA_COMPLETA.html", html_final, "TAPIAS_HOJA_COMPLETA.html", "text/html")
    st.info("💡 Para PDF: abre el archivo en tu navegador → Imprimir → Guardar como PDF")
