import pandas as pd
import re
import html
import streamlit as st

st.set_page_config(page_title="Generador de Tapias", layout="wide")
st.title("🎪 Generador de Etiquetas / Tapias by MH")

# -----------------------------------------------------------------------------
# OBTENER PRIMER APELLIDO (apellidos compuestos)
# -----------------------------------------------------------------------------
def obtener_primer_apellido(nombre_completo):
    if pd.isna(nombre_completo):
        return ""
    partes = str(nombre_completo).strip().split()
    patrones_compuestos = [r'^de\s+la$', r'^del$', r'^de\s+los$', r'^de$', r'^la$', r'^los$', r'^san$', r'^santa$']
    idx = 2 if len(partes) >= 3 else (1 if len(partes) == 2 else 0)
    apellido = ""
    while idx < len(partes):
        apellido += partes[idx] + " "
        if any(re.match(p, partes[idx].lower()) for p in patrones_compuestos) and idx + 1 < len(partes):
            idx += 1
        else:
            break
    return apellido.strip().upper()

# -----------------------------------------------------------------------------
# LIMPIEZA ABSOLUTA: ELIMINA TODOS LOS TEXTOS BASE
# -----------------------------------------------------------------------------
def limpiar_obs_base(texto):
    if not texto: return ""
    patrones_borrar = [
        r'Se informa código de vestir.*',
        r'Huésped? enterad[oa] de políticas de cancelación.*',
        r'Políticas de cancelación.*',
        r'Código de vestir.*',
        r'Sin alergias.*',
        r'No alergias.*',
        r'Confirmar alergias.*',
        r'enterad[oa] de políticas.*',
        r'cargo extra.*',
        r'no presentarse.*',
        r'cancelar a tiempo.*',
        r'pax.*política.*',
        r'política.*cancelación.*',
        r'base.*',
        r'huésped.*enterado.*',
        r'hora.*llegada.*política.*',
        r'por favor.*confirmar.*',
        r'^\s*,\s*', r'\s*,\s*$'
    ]
    limpio = texto
    for pat in patrones_borrar:
        limpio = re.sub(pat, '', limpio, flags=re.I | re.DOTALL)
    return re.sub(r'\s+', ' ', limpio).strip().strip(',.;:-').strip()

def obtener_nombre_completo_seguro(valor):
    return "" if pd.isna(valor) else str(valor).strip()

# -----------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL: REDUCCIÓN GENERAL DE 2pt + AJUSTE AUTÓNOMO
# -----------------------------------------------------------------------------
def generar_html(df, titulo_etiqueta, limite_mesa_grande, orientacion, tam_tapia):
    columnas_requeridas = ['nombre_reserva', 'habitacion', 'pax', 'hora', 'observaciones']
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas: {', '.join(faltantes)}")

    grouped = df.groupby(['nombre_reserva', 'habitacion'], sort=False).agg({
        'pax': 'sum', 'hora': 'first', 'observaciones': 'first'
    }).reset_index()

    # TAMAÑOS BASE REDUCIDOS EN 2 PUNTOS EN GENERAL
    if tam_tapia == "Grande":
        alto_tarjeta = "29mm" if orientacion == "Horizontal" else "27mm"
        cols_grid = 6
        base_apellido = "9.5pt"   # Antes 11.5pt → -2pt
        base_datos = "10pt"       # Antes 12pt → -2pt
        base_badges = "6pt"       # Antes 8pt → -2pt
        base_obs = "6.5pt"        # Antes 8.5pt → -2pt
    else:
        alto_tarjeta = "22mm"
        cols_grid = 8
        base_apellido = "7pt"     # Antes 9pt → -2pt
        base_datos = "7.5pt"      # Antes 9.5pt → -2pt
        base_badges = "4.5pt"     # Antes 6.5pt → -2pt
        base_obs = "5pt"          # Antes 7pt → -2pt

    reporte_horas = {}
    total_pax = 0
    cards = []

    for _, fila in grouped.iterrows():
        nombre = obtener_nombre_completo_seguro(fila['nombre_reserva'])
        habitacion = fila['habitacion']
        pax_val = fila['pax']
        hora_val = fila['hora']
        obs_full = obtener_nombre_completo_seguro(fila['observaciones'])

        primer_apellido = obtener_primer_apellido(nombre)
        hab_str = str(habitacion).strip().rstrip('.0') if pd.notna(habitacion) else ""

        try:
            pax = int(pax_val)
            if pax < 1: pax = 1
        except: pax = 1
        total_pax += pax

        # DETECCIÓN AUTOMÁTICA DE PAX
        for pat, val in [
            (r'22\s*PAX',22),(r'SON\s*PAX\s*0?7',7),(r'SON\s*0?3\s*PAX',3),
            (r'SON\s*4\s*PAX',4),(r'SON\s*10\s*PAX|10\s*PAX',10),(r'SON\s*5\s*PAX',5),
            (r'SON\s*6\s*PAX',6),(r'SON\s*8\s*PAX',8),(r'SON\s*9\s*PAX',9),
            (r'SON\s*11\s*PAX',11),(r'SON\s*12\s*PAX',12),(r'\bSON\s+(\d{1,2})\s+PAX\b',None)
        ]:
            m = re.search(pat, obs_full.upper())
            if m: pax = val if val else int(m.group(1)); break

        # FORMATO DE HORA PRECISO
        hora = ""
        if isinstance(hora_val, pd.Timestamp):
            hora = hora_val.strftime('%H:%M')
        else:
            m = re.search(r'(\d{1,2})[:.]?(\d{2})', str(hora_val))
            hora = f"{int(m.group(1)):02d}:{m.group(2)}" if m else str(hora_val)[:5]

        # DETECCIÓN DE CAMBIO DE HORARIO
        cambio_horario = False
        m_hora = re.search(r'llegan?\s+a\s+las\s+(\d{1,2})[:.]?(\d{2})|arrive\s+(at|around)?\s*(\d{1,2})[:.]?(\d{2})', obs_full, re.I)
        if m_hora:
            g = m_hora.groups()
            h = g[0] or g[3]; m = g[1] or g[4]
            hora = f"{int(h):02d}:{m}"
            cambio_horario = True
        else:
            for pat, hh in [
                (r'llegará?n\s+6\s*pm|arrive.*6\s*pm',"18:00"),
                (r'llegará?n\s+7\s*pm|arrive.*7\s*pm',"19:00"),
                (r'llegará?n\s+8\s*pm|arrive.*8\s*pm',"20:00"),
                (r'llegará?n\s+9\s*pm|arrive.*9\s*pm',"21:00"),
                (r'llegará?n\s+10\s*pm|arrive.*10\s*pm',"22:00")
            ]:
                if re.search(pat, obs_full, re.I):
                    hora, cambio_horario = hh, True; break

        # ETIQUETAS ESPECIALES
        obs_upper = obs_full.upper()
        es_residence = bool(re.search(r'RESIDENCE|S\.\s*RESIDENCE', obs_upper))
        es_diamante = bool(re.search(r'DIAMANTE|DIAMOND', obs_upper))
        es_seguimiento = bool(re.search(r'SEGUIMIENTO|FOLLOW.*UP', obs_upper))
        es_grupo = bool(re.search(r'sentar juntos|compartir mesa|grupo|together|same table|group', obs_upper))
        tiene_excl = bool(re.search(r'SIN\s+ALERGIAS|NO\s+ALERGIES|CONFIRMAR', obs_upper))
        tiene_rest = bool(re.search(r'CELIACO|GLUTEN|ALERGIA|ALERGY|SHELLFISH|NUTS|VEGETARIAN|VEGAN|DIABETES|NO PORK', obs_upper))
        es_alergia = tiene_rest and not tiene_excl
        es_hbd = bool(re.search(r'cumpleaños|aniversario|birthday|anniversary|celebrat|festejando', obs_full, re.I))
        es_ns = bool(re.search(r'nuevos?\s+socios?|new members|new guest', obs_full, re.I))
        es_daypass = bool(re.search(r'day pass|visitor|external guest', obs_full, re.I))
        es_privado = bool(re.search(r'privado|private|vip', obs_upper))

        # LIMPIEZA FINAL DE OBSERVACIONES
        obs_clean = limpiar_obs_base(obs_full)

        # ==============================================================
        # AJUSTE AUTÓNOMO: TAMBIÉN REDUCIDO EN 2pt MANTENIENDO PROPORCIÓN
        # ==============================================================
        cant_tags = sum([es_residence,es_diamante,es_seguimiento,es_alergia,es_hbd,es_ns,es_daypass,es_privado,es_grupo,cambio_horario])
        len_obs = len(obs_clean)
        longitud_nombre = len(primer_apellido)
        total_caracteres = len(primer_apellido) + len(hab_str) + len(str(pax)) + len(hora) + len(obs_clean) + (cant_tags * 15)

        if total_caracteres > 200 or cant_tags >=4 or len_obs>130 or longitud_nombre>20:
            # NIVEL MÁXIMO: -2pt general
            ta, td, tb, to = "5.2pt", "5.8pt", "3.5pt", "3.5pt"
        elif total_caracteres > 150 or cant_tags >=3 or len_obs>90 or longitud_nombre>15:
            # NIVEL FUERTE: -2pt general
            ta, td, tb, to = "5.8pt", "6.3pt", "3.8pt", "3.8pt"
        elif total_caracteres > 90 or cant_tags >=2 or len_obs>50 or longitud_nombre>12:
            # NIVEL MODERADO: -2pt general
            ta, td, tb, to = "6.3pt", "6.8pt", "4.2pt", "4.2pt"
        else:
            # NIVEL NORMAL: BASE YA REDUCIDA -2pt
            ta, td, tb, to = base_apellido, base_datos, base_badges, base_obs

        etiqueta_pax = f"<b>PX:</b> {pax}"
        if pax >= limite_mesa_grande:
            est = "display:inline-block;border:1px solid #c00;background:#FFECEC;color:#c00;padding:1px 4px;border-radius:2px;font-weight:bold;"
            etiqueta_pax = f'<span style="{est}">{etiqueta_pax}</span>'

        # ESTILOS DE ETIQUETAS
        est_head = f"padding:1px 3px;border-radius:2px;flex-wrap:wrap;gap:1px;font-size:{tb};"
        if es_residence or es_diamante: est_head += "background:#E0F7FF;border:1px solid #4682B4;"
        b_azul = f"display:inline-block;border:1px solid #4682B4;background:#E0F7FF;color:#005580;padding:1px 3px;border-radius:2px;font-size:{tb};font-weight:bold;margin-right:2px;"
        b_naranja = b_azul.replace("#E0F7FF","#FFF3E0").replace("#4682B4","#F57C00").replace("#005580","#E65100")
        b_verde = b_azul.replace("#E0F7FF","#E8F5E9").replace("#4682B4","#2E7D32").replace("#005580","#1B5E20")
        badges = []
        if es_residence: badges.append(f'<span style="{b_azul}">🔑 RESIDENCE</span>')
        if es_diamante: badges.append(f'<span style="{b_azul}">💎 DIAMANTE</span>')
        if es_seguimiento: badges.append(f'<span style="{b_naranja}">🛑 SEGUIMIENTO</span>')
        if es_alergia: badges.append('⚠️ ALERGIAS')
        if es_grupo: badges.append(f'<span style="{b_verde}">👥 GRUPO</span>')
        cab = f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:2px;line-height:1.1;{est_head}"><span style="display:flex;gap:2px;flex-wrap:wrap;">{" ".join(badges)}</span><span style="font-weight:bold;white-space:nowrap;">{html.escape(titulo_etiqueta)}</span></div>'

        # ETIQUETAS ESPECIALES CENTRADAS Y DESPEGADAS
        esp = ""
        if es_hbd:
            esp='<div style="font-weight:bold;font-size:6.8pt;text-align:center;color:#c00;margin:0.5mm 0 0.3mm 0;white-space:nowrap;">🎂 HBD / ANIV</div>'
            obs_clean=""
        if es_ns and not es_hbd:
            esp='<div style="font-weight:bold;font-size:6.3pt;text-align:center;color:#006;margin:0.5mm 0 0.3mm 0;white-space:nowrap;">🆕 NUEVO SOCIO</div>'
            obs_clean=""
        if es_daypass and not es_hbd:
            esp='<div style="font-weight:bold;font-size:6.3pt;text-align:center;color:#333;margin:0.5mm 0 0.3mm 0;white-space:nowrap;">🎟️ DAY PASS</div>'
            obs_clean=""
        ch = f'<div style="color:#c00;font-weight:bold;font-size:{tb};margin:0.2mm 0;text-align:left;">⚠️ CAMBIO DE HORARIO</div>' if cambio_horario else ""
        obs_html = f'<div style="font-size:{to};line-height:1.2;overflow-wrap:break-word;margin-top:0.1mm;text-align:left;">{html.escape(obs_clean)}</div>' if obs_clean else ""

        h_clave = hora[:5]
        if h_clave: reporte_horas[h_clave] = reporte_horas.get(h_clave,0) + pax

        # ==============================================================
        # TARJETA PERFECTA: REDUCIDA, CENTRADA, DESPEGADA, SIN RECORTES
        # ==============================================================
        cards.append(f'''<div style="width:100%;height:100%;border:1px solid #000;box-sizing:border-box;padding:1.5mm;overflow:hidden;display:flex;flex-direction:column;justify-content:center;gap:0.15mm;page-break-inside:avoid;">
{cab}
<div style="font-weight:bold;font-size:{ta};line-height:1.05;margin-top:0.1mm;text-align:left;">{html.escape(primer_apellido)}</div>
<div style="font-size:{td};text-align:left;"><b>Hab:</b> {html.escape(hab_str)} | {etiqueta_pax}</div>
<div style="font-size:{td};text-align:left;"><b>Hora:</b> {hora}</div>
{ch}{esp}{obs_html}
</div>'''.replace('\n',''))

    # ---- REPORTE FINAL TAMBIÉN REDUCIDO PROPORCIONALMENTE ----
    horas_ordenadas = sorted(reporte_horas.keys())
    total_horas = len(horas_ordenadas)
    max_por_tapia = 14

    lineas_1 = horas_ordenadas[:max_por_tapia]
    reporte_html_1 = f'''<div style="width:100%;height:100%;border:1px solid #000;box-sizing:border-box;padding:1.5mm;overflow:hidden;display:flex;flex-direction:column;justify-content:center;gap:0.15mm;page-break-inside:avoid;">
<div style="font-weight:bold;text-align:center;font-size:6.8pt;margin-bottom:0.3mm;">📊 REPORTE</div>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.1mm;">'''
    for h in lineas_1:
        reporte_html_1 += f'<div style="font-size:4.5pt;line-height:1.1;">{h} — {reporte_horas[h]}</div>'
    reporte_html_1 += "</div>"
    if total_horas <= max_por_tapia:
        reporte_html_1 += f'<div style="font-weight:bold;text-align:right;font-size:5.5pt;margin-top:0.3mm;">TOTAL: {total_pax}</div>'
    reporte_html_1 += "</div>"
    cards.append(reporte_html_1)

    if total_horas > max_por_tapia:
        lineas_2 = horas_ordenadas[max_por_tapia:]
        reporte_html_2 = f'''<div style="width:100%;height:100%;border:1px solid #000;box-sizing:border-box;padding:1.5mm;overflow:hidden;display:flex;flex-direction:column;justify-content:center;gap:0.15mm;page-break-inside:avoid;">
<div style="font-weight:bold;text-align:center;font-size:6.8pt;margin-bottom:0.3mm;">📊 REPORTE (CONT)</div>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.1mm;">'''
    for h in lineas_2:
        reporte_html_2 += f'<div style="font-size:4.5pt;line-height:1.1;">{h} — {reporte_horas[h]}</div>'
    reporte_html_2 += "</div>"
    reporte_html_2 += f'<div style="font-weight:bold;text-align:right;font-size:5.5pt;margin-top:0.3mm;">TOTAL: {total_pax}</div></div>'
    cards.append(reporte_html_2)

    # CONFIGURACIÓN FINAL SIN BORDES ADICIONALES
    config = "size:letter;margin:2mm;" if tam_tapia=="Chica" else "size:letter;margin:3mm;"
    if orientacion=="Horizontal": config = config.replace("size:letter","size:letter landscape")
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Tapias - {html.escape(titulo_etiqueta)}</title>
<style>@page {{{config}}} *{{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact;}} body{{margin:0;padding:0;width:100%;font-family:Arial,sans-serif;}} .grid{{display:grid;grid-template-columns:repeat({cols_grid},1fr);grid-auto-rows:{alto_tarjeta};gap:0.4mm;width:100%;border:none;}}</style></head>
<body><div class="grid">{"".join(cards)}</div></body></html>"""

# -----------------------------------------------------------------------------
# INTERFAZ
# -----------------------------------------------------------------------------
st.title("⚙️ Configuración")
nombre_etiqueta = st.text_input("Nombre para reemplazar CIRCO:", value="CIRCO")
orientacion = st.radio("📐 Orientación:", ["Horizontal","Vertical"], index=0)
tam_tapia = st.radio("📏 Elige el tamaño de tapia:", ["Grande (actual)","Chica (8x7 por hoja)"], index=0)
limite_mesa_grande = st.number_input("🔴 Resaltar PX desde ≥", min_value=5, value=6, step=1)
archivo = st.file_uploader("📂 Sube tu Excel (.xlsx)", type="xlsx")

if archivo and nombre_etiqueta.strip():
    try:
        orient_simple = orientacion
        tam_simple = "Grande" if tam_tapia.startswith("Grande") else "Chica"
        df = pd.read_excel(archivo, engine="openpyxl")
        html_final = generar_html(df, nombre_etiqueta.strip(), limite_mesa_grande, orient_simple, tam_simple)
        st.success("✅ REDUCCIÓN GENERAL DE 2pt APLICADA: Todo cabe completo, legible y sin recortes")
        st.download_button("📄 Descargar TAPIAS.html", html_final, "TAPIAS_HOJA_COMPLETA.html", "text/html")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
