import pandas as pd
import re
import html
import streamlit as st

# Configuración general
st.set_page_config(page_title="Generador de Tapias", layout="centered")
st.title("🎪 Generador de Etiquetas / Tapias")

# ----------------------
# FUNCIÓN ACTUALIZADA: OBTENER PRIMER APELLIDO
# ----------------------
def obtener_primer_apellido(nombre_completo):
    """
    Toma el nombre completo y devuelve SOLO EL PRIMER APELLIDO como identificador:
    - Ej: "Juan Carlos Pérez López" → "PÉREZ"
    - Ej: "María González" → "GONZÁLEZ"
    - Si solo hay nombre, usa ese mismo
    """
    if pd.isna(nombre_completo):
        return ""
    # Limpia espacios y divide por palabras
    partes = str(nombre_completo).strip().split()
    # Regla estándar: nombres → apellidos; el primer apellido suele ser la 3ra palabra,
    # pero si hay pocas palabras, toma la última o la que corresponda como primer apellido
    if len(partes) >= 3:
        # Nombre(s) + Primer apellido + [segundo apellido] → tomamos el 3er elemento
        return partes[2].upper()
    elif len(partes) == 2:
        # Nombre + Primer apellido → tomamos el 2do elemento
        return partes[1].upper()
    else:
        # Solo nombre o un solo dato → usamos lo que haya
        return partes[0].upper()

def generar_html(df, titulo_etiqueta):
    grouped = df.groupby(['nombre_reserva', 'habitacion'], sort=False)
    cards = []

    for (nombre, habitacion), group in grouped:
        # ✅ AHORA USAMOS EL PRIMER APELLIDO COMO IDENTIFICADOR
        primer_apellido = obtener_primer_apellido(nombre)
        hab_str = str(habitacion).strip() if pd.notna(habitacion) else ""
        if hab_str.endswith('.0'):
            hab_str = hab_str[:-2]

        pax = int(group['pax'].sum())
        obs_full = str(group['observaciones'].iloc[0]).strip() if pd.notna(group['observaciones'].iloc[0]) else ""

        # Reglas para sobrescribir PAX
        pax_rules = [
            (r'22\s*PAX', 22), (r'SON\s*PAX\s*07|SON\s*PAX\s*7', 7),
            (r'SON\s*03\s*PAX|SON\s*3\s*PAX', 3), (r'SON\s*4\s*PAX', 4),
            (r'SON\s*10\s*PAX|10\s*PAX', 10), (r'SON\s*5\s*PAX', 5),
            (r'SON\s*6\s*PAX', 6), (r'SON\s*8\s*PAX', 8),
            (r'SON\s*9\s*PAX', 9), (r'SON\s*11\s*PAX', 11),
            (r'SON\s*12\s*PAX', 12)
        ]
        for pat, val in pax_rules:
            if re.search(pat, obs_full.upper()):
                pax = val
                break

        # Hora y cambios de horario
        hora_val = group['hora'].iloc[0]
        hora = hora_val.strftime('%H:%M') if isinstance(hora_val, pd.Timestamp) else str(hora_val)[:5]
        cambio_horario = False
        m_hora = re.search(r'llegan?\s+a\s+las\s+(\d{1,2}:\d{2})', obs_full, re.I)
        if m_hora:
            hora = m_hora.group(1)
            cambio_horario = True
        elif re.search(r'llegar[aá]n\s+6\s*pm', obs_full, re.I):
            hora, cambio_horario = "18:00", True
        elif re.search(r'llegar[aá]n\s+7\s*pm', obs_full, re.I):
            hora, cambio_horario = "19:00", True

        # Etiquetas adicionales
        badges = []
        if re.search(r'RESIDENCE|S\.\s*RESIDENCE', obs_full.upper()):
            badges.append('🔑RESIDENCE')
        if re.search(r'DIAMANTE|DIAMANTES|A\.\s*DIAMANTE', obs_full.upper()):
            badges.append('💎DIAMANTE')
        if re.search(r'SEGUIMIENTO', obs_full.upper()):
            badges.append('🛑SEGUIMIENTO')

        # Etiquetas automáticas HBD / NS / Day Pass
        palabras_hbd = r'cumpleaños|festejando|birthday|birthday\'s|graduacion|graduation|pastel|vela|\byear\'s\b|\byear\b'
        es_hbd = re.search(palabras_hbd, obs_full, re.I)
        es_ns = re.search(r'nuevos?\s+socios?|nuevos\s+miembros|nuevo\s+socio', obs_full, re.I)
        es_daypass = re.search(r'day\s+pass', obs_full, re.I)

        # Limpieza de observaciones
        obs_clean = obs_full
        patrones_borrar = [
            r'Se informa código de vestir y tiempos\.?',
            r'Huésped enterado de políticas de cancelación hasta \d+\s*(horas?|hrs?)\s*antes de su cena y cargo extra de \$25 dólares por mesa por no presentarse y no cancelar a tiempo\.?',
            r'Sin alergias, ni dietas? especiales\.?', r'Sin alergias, ni dieta especial\.?',
            r'No alergias, No dietas especiales\.?', r'sin alergias reportadas', r'SIN ALERGIAS REPORTADAS',
            r'Sin alergias reportadas', r'sin observaciones especiales', r'NO ALERGIAS',
            r'Son\s*\d*\s*pax[,.\s]*', r'Son\s*\d*\s*pas[,.\s]*',
            r',\s*Huésped enterado de políticas de cancelación.*?$', r',\s*Se informa código de vestir.*?$'
        ]
        for pat in patrones_borrar:
            obs_clean = re.sub(pat, '', obs_clean, flags=re.I | re.DOTALL)

        etiqueta_especial = ""
        if es_hbd:
            etiqueta_especial += '<div style="font-weight:bold;font-size:14pt;text-align:center;color:#c00;margin:0.8mm 0 0.4mm 0;white-space:nowrap;line-height:1.2;">🎂 HBD</div>'
            obs_clean = ""
        if es_ns:
            etiqueta_especial += '<div style="font-weight:bold;font-size:13pt;text-align:center;color:#006;margin:0.8mm 0 0.4mm 0;white-space:nowrap;line-height:1.2;">🆕 NS</div>'
            obs_clean = ""
        if es_daypass:
            etiqueta_especial += '<div style="font-weight:bold;font-size:13pt;text-align:center;color:#333;margin:0.8mm 0 0.4mm 0;white-space:nowrap;line-height:1.2;">🎟️ Day Pass</div>'
            obs_clean = ""

        obs_clean = re.sub(r'\s+', ' ', obs_clean).strip().strip(',.;:')
        tam_obs = '9pt' if len(obs_clean) < 60 else '7.5pt'
        obs_html = f'<div style="font-size:{tam_obs};line-height:1.45;max-height:11mm;overflow:hidden;word-wrap:break-word;margin-top:0.3mm;">{html.escape(obs_clean)}</div>' if obs_clean else ''
        cambio_html = f'<div style="color:#c00;font-weight:bold;font-size:9pt;margin:0.2mm 0;">⚠️ CAMBIO DE HORARIO</div>' if cambio_horario else ''
        badges_html = f'<div style="font-size:9pt;margin:0.1mm 0 0.3mm 0;">{" ".join(badges)}</div>' if badges else ''

        # ✅ MUESTRA EL PRIMER APELLIDO COMO IDENTIFICADOR PRINCIPAL
        cards.append(f"""
<div style="width:100%;height:100%;border:1px solid #000;box-sizing:border-box;padding:0.8mm;overflow:hidden;display:flex;flex-direction:column;gap:0.15mm;page-break-inside:avoid;">
{badges_html if badges_html else ""}
<div style="text-align:center;font-weight:bold;font-size:9pt;border-bottom:0.5pt solid #666;padding-bottom:0.2mm;">🎪 {html.escape(titulo_etiqueta)}</div>
<div style="font-weight:bold;font-size:11.5pt;line-height:1.1;word-wrap:break-word;white-space:normal;">{html.escape(primer_apellido)}</div>
<div style="font-size:12pt;"><b>Hab:</b> {html.escape(hab_str)} | <b>PX:</b> {pax}</div>
<div style="font-size:12pt;"><b>Hora:</b> {hora}</div>
{cambio_html}
{etiqueta_especial}
{obs_html}
</div>""".replace('\n',''))

    html_total = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Tapias - {html.escape(titulo_etiqueta)}</title>
<style>
@page {{ size: letter landscape; margin: 0mm; }}
* {{box-sizing:border-box;margin:0;padding:0;}}
body {{margin:0;padding:0;width:100%;}}
.grid {{display:grid;grid-template-columns:repeat(6, 1fr);grid-auto-rows:27mm;gap:0;width:100%;}}
</style>
</head><body><div class="grid">{"".join(cards)}</div></body></html>"""
    return html_total

# ----------------------
# INTERFAZ DE USUARIO
# ----------------------
nombre_etiqueta = st.text_input("Nombre para reemplazar CIRCO:", value="CIRCO")
archivo = st.file_uploader("📂 Sube tu archivo Excel (.xlsx)", type="xlsx")

if archivo and nombre_etiqueta.strip():
    try:
        df = pd.read_excel(archivo, engine="openpyxl")
        html_final = generar_html(df, nombre_etiqueta.strip())

        st.success("✅ ¡Listo! Las etiquetas usan el PRIMER APELLIDO como identificador:")
        st.download_button(
            label="📄 Descargar TAPIAS_HOJA_COMPLETA.html",
            data=html_final,
            file_name="TAPIAS_HOJA_COMPLETA.html",
            mime="text/html"
        )
        st.info("💡 Para obtener PDF: abre el archivo descargado en tu navegador → Imprimir → Guardar como PDF")
    except Exception as e:
        st.error(f"❌ Error al procesar: {str(e)}")
