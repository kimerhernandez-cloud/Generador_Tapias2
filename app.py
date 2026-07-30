import pandas as pd
import re
import html
import streamlit as st

st.set_page_config(page_title="Generador de Tapias", layout="wide")
st.title("🎪 Generador de Etiquetas / Tapias")

# ----------------------
# FUNCIÓN: OBTENER PRIMER APELLIDO
# ----------------------
def obtener_primer_apellido(nombre_completo):
    if pd.isna(nombre_completo):
        return ""
    partes = str(nombre_completo).strip().split()
    if len(partes) >= 3:
        return partes[2].upper()
    elif len(partes) == 2:
        return partes[1].upper()
    else:
        return partes[0].upper()

def generar_html(df, titulo_etiqueta, limite_mesa_grande):
    grouped = df.groupby(['nombre_reserva', 'habitacion'], sort=False).agg({
        'pax': 'sum',
        'hora': 'first',
        'observaciones': 'first'
    }).reset_index()
    
    cards = []

    for _, fila in grouped.iterrows():
        nombre = fila['nombre_reserva']
        habitacion = fila['habitacion']
        pax = int(fila['pax'])
        hora_val = fila['hora']
        obs_full = str(fila['observaciones']).strip() if pd.notna(fila['observaciones']) else ""

        primer_apellido = obtener_primer_apellido(nombre)
        hab_str = str(habitacion).strip() if pd.notna(habitacion) else ""
        if hab_str.endswith('.0'):
            hab_str = hab_str[:-2]

        # Reglas especiales PAX desde observaciones
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

        # FORMATO HORA + FILTRO ANTES DE 22:00
        hora = ""
        if isinstance(hora_val, pd.Timestamp):
            hora = hora_val.strftime('%H:%M')
        else:
            hora_str = str(hora_val)[:5]
            if re.match(r'^\d{1,2}:\d{2}$', hora_str):
                h, m = hora_str.split(':')
                hora = f"{int(h):02d}:{m}" if int(h) < 22 else f"21:{m}"
            else:
                hora = hora_str

        cambio_horario = False
        m_hora = re.search(r'llegan?\s+a\s+las\s+(\d{1,2}:\d{2})', obs_full, re.I)
        if m_hora:
            h_obs = m_hora.group(1)
            h, m = h_obs.split(':')
            hora = f"{int(h):02d}:{m}" if int(h) < 22 else f"21:{m}"
            cambio_horario = True
        elif re.search(r'llegar[aá]n\s+6\s*pm', obs_full, re.I):
            hora, cambio_horario = "18:00", True
        elif re.search(r'llegar[aá]n\s+7\s*pm', obs_full, re.I):
            hora, cambio_horario = "19:00", True

        # Etiquetas especiales
        badges = []
        obs_upper = obs_full.upper()
        es_residence = bool(re.search(r'RESIDENCE|S\.\s*RESIDENCE', obs_upper))
        es_diamante = bool(re.search(r'DIAMANTE|DIAMANTES|A\.\s*DIAMANTE|DIAMOND', obs_upper))
        
        estilo_badge_azul = "display:inline-block;border:1px solid #4682B4;background-color:#E0F7FF;color:#005580;padding:1px 3px;border-radius:2px;font-size:8pt;font-weight:bold;margin-right:2px;"
        if es_residence:
            badges.append(f'<span style="{estilo_badge_azul}">🔑 RESIDENCE</span>')
        if es_diamante:
            badges.append(f'<span style="{estilo_badge_azul}">💎 DIAMANTE</span>')
        if re.search(r'SEGUIMIENTO', obs_upper):
            badges.append('🛑 SEGUIMIENTO')

        tiene_exclusion = re.search(
            r'SIN\s+ALERGIAS|NO\s+ALERGIAS|NO\s+ALERGIES|SIN\s+ALERGIA|NO\s+ALERGIA|CONFIRMAR\s+ALERGIAS|PREGUNTAR\s+ALERGIAS|VERIFICAR\s+ALERGIAS|ALERGIAS\s+POR\s+CONFIRMAR',
            obs_upper
        )
        tiene_restriccion_real = re.search(
            r'CELIACO|CELIACA|CELIACOS|CELIACAS|GLUTEN FREE|GLUTEN|ALERGIA|ALERGIES|ALERGIE|SHELLFISH|MARISCOS|NUECES|NUTS|ALERGIA SEVERA|NO PORK|VEGETARIAN|VEGETARIANOS|CHOCOLATE',
            obs_upper
        )
        if tiene_restriccion_real and not tiene_exclusion:
            badges.append('⚠️ ALERGIAS')

        es_hbd = re.search(r'cumpleaños|festejando|birthday|birthday\'s|graduacion|graduation|pastel|vela|\byear\'s\b|\byear\b', obs_full, re.I)
        es_ns = re.search(r'nuevos?\s+socios?|nuevos\s+miembros|nuevo\s+socio', obs_full, re.I)
        es_daypass = re.search(r'day\s+pass', obs_full, re.I)

        # LIMPIEZA MEJORADA: se agrega el texto completo de políticas
        obs_clean = obs_full
        patrones_borrar = [
            r'Se informa código de vestir y tiempos\.?',
            r'Huésped enterado de políticas de cancelación hasta \d+\s*(horas?|hrs?)\s*antes de su cena y cargo extra de \$25 dólares por mesa por no presentarse y no cancelar a tiempo\.?',
            r'Huésped enterado de políticas de cancelación 2 hrs antes de su cena y cargo extra de \$25 dólares por mesa por no presentarse y no cancelar a tiempo\.?',
            r'Sin alergias, ni dietas? especiales\.?', r'Sin alergias, ni dieta especial\.?',
            r'No alergias, No dietas especiales\.?', r'sin alergias reportadas', r'SIN ALERGIAS REPORTADAS',
            r'Sin alergias reportadas', r'sin observaciones especiales', r'NO ALERGIAS',
            r'CONFIRMAR ALERGIAS', r'PREGUNTAR ALERGIAS', r'VERIFICAR ALERGIAS', r'ALERGIAS POR CONFIRMAR',
            r'Son\s*\d*\s*pax[,.\s]*', r'Son\s*\d*\s*pas[,.\s]*',
            r',\s*Huésped enterado de políticas de cancelación.*?$', r',\s*Se informa código de vestir.*?$'
        ]
        for pat in patrones_borrar:
            obs_clean = re.sub(pat, '', obs_clean, flags=re.I | re.DOTALL)
        obs_clean = re.sub(r'\s+', ' ', obs_clean).strip().strip(',.;:')

        # RECUADRO ROJO AMPLIADO: desde "PX:" hasta el número
        etiqueta_pax = f"<b>PX:</b> {pax}"
        estilo_pax_completo = ""
        if pax >= limite_mesa_grande:
            estilo_pax_completo = "display:inline-block;border:1px solid #cc0000;background-color:#FFECEC;color:#cc0000;padding:1px 5px;border-radius:2px;font-weight:bold;"
            etiqueta_pax = f'<span style="{estilo_pax_completo}"><b>PX:</b> {pax}</span>'

        # ENCABEZADO: FONDO AZUL CIELO SI ES RESIDENCE O DIAMANTE
        estilo_encabezado = "padding: 1px 3px; border-radius: 2px; flex-wrap: wrap; gap: 1px;"
        if es_residence or es_diamante:
            estilo_encabezado += "background-color:#E0F7FF;border:1px solid #4682B4;"

        cabecera = f'''
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:2px;font-size:8.5pt;line-height:1.1;{estilo_encabezado}">
            <span style="display:flex;gap:2px;flex-wrap:wrap;">{" ".join(badges) if badges else ""}</span>
            <span style="font-weight:bold;white-space:nowrap;">{html.escape(titulo_etiqueta)}</span>
        </div>'''

        # ETIQUETAS ESPECIALES CENTRADAS
        etiqueta_especial = ""
        if es_hbd:
            etiqueta_especial = '<div style="font-weight:bold;font-size:12pt;text-align:center;color:#c00;margin:0.3mm 0;white-space:nowrap;">🎂 HBD</div>'
            obs_clean = ""
        if es_ns:
            etiqueta_especial = '<div style="font-weight:bold;font-size:11pt;text-align:center;color:#006;margin:0.3mm 0;white-space:nowrap;">🆕 NS</div>'
            obs_clean = ""
        if es_daypass:
            etiqueta_especial = '<div style="font-weight:bold;font-size:11pt;text-align:center;color:#333;margin:0.3mm 0;white-space:nowrap;">🎟️ Day Pass</div>'
            obs_clean = ""

        # ESPACIO AMPLIADO + LETRA COMO ESTABA
        if len(obs_clean) < 50:
            tam_obs = '8.5pt'
        elif len(obs_clean) < 85:
            tam_obs = '8pt'
        elif len(obs_clean) < 120:
            tam_obs = '7.5pt'
        else:
            tam_obs = '7pt'

        obs_html = f'<div style="font-size:{tam_obs};line-height:1.4;min-height:9mm;max-height:18mm;overflow:hidden;word-wrap:break-word;margin-top:0.5mm;padding:0 1px;">{html.escape(obs_clean)}</div>' if obs_clean else ''
        cambio_html = f'<div style="color:#c00;font-weight:bold;font-size:8.5pt;margin:0.2mm 0;">⚠️ CAMBIO DE HORARIO</div>' if cambio_horario else ''

        cards.append(f"""
<div style="width:100%;height:100%;border:1px solid #000;box-sizing:border-box;padding:1mm;overflow:hidden;display:flex;flex-direction:column;gap:0.2mm;page-break-inside:avoid;">
{cabecera}
<div style="font-weight:bold;font-size:11.5pt;line-height:1.1;margin-top:0.4mm;">{html.escape(primer_apellido)}</div>
<div style="font-size:12pt;"><b>Hab:</b> {html.escape(hab_str)} | {etiqueta_pax}</div>
<div style="font-size:12pt;"><b>Hora:</b> {hora}</div>
{cambio_html}
{etiqueta_especial}
{obs_html}
</div>""".replace('\n',''))

    html_total = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Tapias - {html.escape(titulo_etiqueta)}</title>
<style>
@page {{ size: letter; margin: 3mm; }}
* {{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact;}}
body {{margin:0;padding:0;width:100%;font-family:Arial, sans-serif;}}
.grid {{display:grid;grid-template-columns:repeat(6, 1fr);grid-auto-rows:29mm;gap:0.5mm;width:100%;}}
</style>
</head><body><div class="grid">{"".join(cards)}</div></body></html>"""
    return html_total

# ----------------------
# INTERFAZ
# ----------------------
nombre_etiqueta = st.text_input("Nombre para reemplazar CIRCO:", value="CIRCO")
limite_mesa_grande = st.number_input("🔴 Mesa grande: resaltar PX desde ≥", min_value=5, value=7, step=1)
archivo = st.file_uploader("📂 Sube tu archivo Excel (.xlsx)", type="xlsx")

if archivo and nombre_etiqueta.strip():
    try:
        df = pd.read_excel(archivo, engine="openpyxl")
        html_final = generar_html(df, nombre_etiqueta.strip(), limite_mesa_grande)

        st.success(f"✅ ¡Listo!")
        st.download_button(
            label="📄 Descargar TAPIAS_HOJA_COMPLETA.html",
            data=html_final,
            file_name="TAPIAS_HOJA_COMPLETA.html",
            mime="text/html"
        )
        st.info("💡 Para PDF: abre el archivo → Imprimir → Destino: Guardar como PDF → Márgenes: Ninguno")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
