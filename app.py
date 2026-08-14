import pandas as pd
import re
import html
import streamlit as st

st.set_page_config(page_title="Generador de Tapias", layout="wide")
st.title("🎪 Generador de Etiquetas / Tapias by MH")

# -----------------------------------------------------------------------------
# ✅ FUNCIÓN DE NOMBRES: TODO COMPLETAMENTE EN MAYÚSCULAS
# -----------------------------------------------------------------------------
def obtener_nombre_mostrar(nombre_completo):
    if pd.isna(nombre_completo):
        return ""
    return str(nombre_completo).strip().upper()

# -----------------------------------------------------------------------------
# LIMPIEZA DE OBSERVACIONES
# -----------------------------------------------------------------------------
def limpiar_obs_base(texto):
    if not texto: return ""
    patrones_borrar = [
        r'Se informa código de vestir.*', r'Huésped? enterad[oa] de políticas.*',
        r'Políticas de cancelación.*', r'Código de vestir.*', r'Sin alergias.*',
        r'No alergias.*', r'Confirmar alergias.*', r'enterad[oa] de políticas.*',
        r'cargo extra.*', r'no presentarse.*', r'cancelar a tiempo.*',
        r'pax.*política.*', r'política.*cancelación.*', r'base.*',
        r'huésped.*enterado.*', r'hora.*llegada.*política.*', r'por favor.*confirmar.*',
        r'^\s*,\s*', r'\s*,\s*$'
    ]
    limpio = texto
    for pat in patrones_borrar:
        limpio = re.sub(pat, '', limpio, flags=re.I | re.DOTALL)
    return re.sub(r'\s+', ' ', limpio).strip().strip(',.;:-').strip()

def obtener_nombre_completo_seguro(valor):
    return "" if pd.isna(valor) else str(valor).strip()

# -----------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL: MARCA DE AGUA + DISTRIBUCIÓN INTELIGENTE
# -----------------------------------------------------------------------------
def generar_html(df, titulo_etiqueta, limite_mesa_grande, orientacion, tam_tapia):
    columnas_requeridas = ['nombre_reserva', 'habitacion', 'pax', 'hora', 'observaciones']
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas: {', '.join(faltantes)}")

    grouped = df.groupby(['nombre_reserva', 'habitacion'], sort=False).agg({
        'pax': 'sum', 'hora': 'first', 'observaciones': 'first'
    }).reset_index()

    # 📏 TAMAÑOS BASE
    if tam_tapia == "Grande":
        alto_tarjeta = "29mm" if orientacion == "Horizontal" else "27mm"
        cols_grid = 6
        base_apellido = "11.5pt"
        base_datos = "10.5pt"
        base_badges = "6.5pt"
        base_obs = "7pt"
    elif tam_tapia == "Mediana":
        alto_tarjeta = "25mm" if orientacion == "Horizontal" else "24mm"
        cols_grid = 7
        base_apellido = "10pt"
        base_datos = "9pt"
        base_badges = "5.5pt"
        base_obs = "6pt"
    else: # Chica
        alto_tarjeta = "22mm"
        cols_grid = 8
        base_apellido = "9pt"
        base_datos = "8pt"
        base_badges = "5pt"
        base_obs = "5.5pt"

    reporte_horas = {}
    total_pax = 0
    cards = []

    for _, fila in grouped.iterrows():
        nombre_completo = obtener_nombre_completo_seguro(fila['nombre_reserva'])
        habitacion = fila['habitacion']
        pax_val = fila['pax']
        hora_val = fila['hora']
        obs_full = obtener_nombre_completo_seguro(fila['observaciones'])

        nombre_mostrar = obtener_nombre_mostrar(nombre_completo)
        hab_str = str(habitacion).strip().rstrip('.0') if pd.notna(habitacion) else ""

        try:
            pax = int(pax_val)
            if pax < 1: pax = 1
        except: pax = 1
        total_pax += pax

        # Detección de personas desde observaciones
        for pat, val in [
            (r'22\s*PAX',22),(r'SON\s*PAX\s*0?7',7),(r'SON\s*0?3\s*PAX',3),
            (r'SON\s*4\s*PAX',4),(r'SON\s*10\s*PAX|10\s*PAX',10),(r'SON\s*5\s*PAX',5),
            (r'SON\s*6\s*PAX',6),(r'SON\s*8\s*PAX',8),(r'SON\s*9\s*PAX',9),
            (r'SON\s*11\s*PAX',11),(r'SON\s*12\s*PAX',12),
            (r'\bSON\s+(\d{1,2})\s+PAX\b',None)
        ]:
            m = re.search(pat, obs_full.upper())
            if m: pax = val if val else int(m.group(1)); break

        # Formato hora
        hora = ""
        if isinstance(hora_val, pd.Timestamp):
            hora = hora_val.strftime('%H:%M')
        else:
            m = re.search(r'(\d{1,2})[:.]?(\d{2})', str(hora_val))
            hora = f"{int(m.group(1)):02d}:{m.group(2)}" if m else str(hora_val)[:5]

        # Cambio de horario
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

        # Etiquetas especiales
        obs_upper = obs_full.upper()
        es_residence = bool(re.search(r'RESIDENCE|S\.\s*RESIDENCE', obs_upper))
        es_diamante = bool(re.search(r'DIAMANTE|DIAMOND', obs_upper))
        tiene_excl = bool(re.search(r'SIN\s+ALERGIAS|NO\s+ALERGIES|CONFIRMAR', obs_upper))
        tiene_rest = bool(re.search(r'CELIACO|GLUTEN|ALERGIA|ALERGY|SHELLFISH|NUTS|VEGETARIAN|VEGAN|DIABETES|NO PORK', obs_upper))
        es_alergia = tiene_rest and not tiene_excl

        es_seguimiento = bool(re.search(r'SEGUIMIENTO|FOLLOW.*UP', obs_upper))
        es_hbd = bool(re.search(r'cumpleaños|cumple\s+año|cumple\s+años|birthday|birth\s+day', obs_full, re.I))
        es_aniversario = bool(re.search(r'aniversario|aniversarios|anniversary', obs_full, re.I))
        es_grupo = bool(re.search(r'sentar juntos|compartir mesa|grupo|together|same table|group', obs_upper))
        es_ns = bool(re.search(r'nuevos?\s+socios?|new members|new guest', obs_full, re.I))
        es_daypass = bool(re.search(r'day pass|visitor|external guest', obs_full, re.I))
        es_privado = bool(re.search(r'privado|private|vip', obs_upper))

        obs_clean = limpiar_obs_base(obs_full)

        # ✅ BORDE AZUL CIELO MUY GRUESO (4px)
        if es_residence or es_diamante:
            borde_tarjeta = "border:4px solid #87CEEB;"
        else:
            borde_tarjeta = "border:1px solid #000;"

        # --- CONSTRUIR NOMBRE CON ETIQUETA AL PRINCIPIO ---
        prefijo_nombre = ""
        if es_diamante:
            prefijo_nombre = "💎 DIAMANTE — "
        elif es_residence:
            prefijo_nombre = "🔑 RESIDENCE — "

        longitud_nombre = len(prefijo_nombre + nombre_mostrar)
        longitud_obs = len(obs_clean)

        # ✅ DECISIÓN: APILAR O JUNTAR
        hay_mucha_info = (longitud_nombre > 20) or (longitud_obs > 50)

        cant_tags = sum([es_seguimiento,es_hbd,es_aniversario,es_ns,es_daypass,es_privado,es_grupo,cambio_horario,es_alergia])

        # Tamaños de fuente
        if hay_mucha_info:
            ta, td, tb, to = "8.5pt", "8pt", "5pt", "5.5pt"
        else:
            ta, td, tb, to = base_apellido, base_datos, base_badges, base_obs

        # Estilos etiquetas
        b_azul = f"display:inline-block;border:1px solid #4682B4;background:#E0F7FF;color:#005580;padding:1px 3px;border-radius:2px;font-size:{tb};font-weight:bold;margin:0 3px;"
        b_naranja = b_azul.replace("#E0F7FF","#FFF3E0").replace("#4682B4","#F57C00").replace("#005580","#E65100")
        b_verde = b_azul.replace("#E0F7FF","#E8F5E9").replace("#4682B4","#2E7D32").replace("#005580","#1B5E20")

        # Etiquetas que van arriba
        badges_top = []
        if es_seguimiento: badges_top.append(f'<span style="{b_naranja}">🛑 SEGUIMIENTO</span>')
        if es_grupo: badges_top.append(f'<span style="{b_verde}">👥 GRUPO</span>')
        if es_alergia: badges_top.append(f'<span style="display:inline-block;padding:1px 3px;border-radius:2px;background:#FFF3E0;border:1px solid #F57C00;color:#C00;font-size:{tb};font-weight:bold;margin:0 3px;">⚠️ ALERGIAS</span>')

        # --- NOMBRE FINAL CON PREFIJO ---
        nombre_completo_mostrar = prefijo_nombre + nombre_mostrar
        nombre_final = f'''<div style="font-weight:bold;font-size:{ta};line-height:1.15;text-align:left;word-wrap:break-word;">{html.escape(nombre_completo_mostrar)}</div>'''

        cab_etiquetas = f'<div style="display:flex;flex-wrap:wrap;gap:2px;line-height:1.2;margin-bottom:1px;">{" ".join(badges_top)}</div>' if badges_top else ""

        # --- DATOS: APILADOS O JUNTOS ---
        es_mesa_grande = pax >= limite_mesa_grande

        if hay_mucha_info:
            # Juntar en línea
            if es_mesa_grande:
                bloque_datos = f'''<div style="font-size:{td};line-height:1.2;margin:2px 0;border:1.5px solid #c00;padding:2px 4px;border-radius:3px;background:#FFECEC;display:flex;flex-wrap:wrap;gap:6px;">
                    <span><b>Hab:</b> {html.escape(hab_str)}</span>
                    <span><b>PX:</b> {pax}</span>
                    <span><b>Hora:</b> {hora}</span>
                </div>'''
            else:
                bloque_datos = f'''<div style="font-size:{td};line-height:1.2;margin:2px 0;display:flex;flex-wrap:wrap;gap:6px;">
                    <span><b>Hab:</b> {html.escape(hab_str)}</span>
                    <span><b>PX:</b> {pax}</span>
                    <span><b>Hora:</b> {hora}</span>
                </div>'''
        else:
            # Apilados uno debajo del otro
            if es_mesa_grande:
                bloque_datos = f'''<div style="font-size:{td};line-height:1.3;margin:2px 0;border:1.5px solid #c00;padding:3px 5px;border-radius:3px;background:#FFECEC;">
                    <div><b>Hab:</b> {html.escape(hab_str)}</div>
                    <div><b>PX:</b> {pax}</div>
                    <div><b>Hora:</b> {hora}</div>
                </div>'''
            else:
                bloque_datos = f'''<div style="font-size:{td};line-height:1.3;margin:2px 0;">
                    <div><b>Hab:</b> {html.escape(hab_str)}</div>
                    <div><b>PX:</b> {pax}</div>
                    <div><b>Hora:</b> {hora}</div>
                </div>'''

        # Etiquetas especiales abajo
        esp = ""
        if es_hbd:
            esp='<div style="font-weight:bold;font-size:7pt;text-align:center;color:#c00;margin:0.3mm 0;white-space:nowrap;">🎂 HBD</div>'
            obs_clean=""
        if es_aniversario and not es_hbd:
            esp='<div style="font-weight:bold;font-size:7pt;text-align:center;color:#800080;margin:0.3mm 0;white-space:nowrap;">💍 ANIVERSARIO</div>'
            obs_clean=""
        if es_ns and not es_hbd and not es_aniversario:
            esp='<div style="font-weight:bold;font-size:6.5pt;text-align:center;color:#006;margin:0.3mm 0;white-space:nowrap;">🆕 NUEVO SOCIO</div>'
            obs_clean=""
        if es_daypass and not es_hbd and not es_aniversario:
            esp='<div style="font-weight:bold;font-size:6.5pt;text-align:center;color:#333;margin:0.3mm 0;white-space:nowrap;">🎟️ DAY PASS</div>'
            obs_clean=""

        ch = f'<div style="color:#c00;font-weight:bold;font-size:{tb};margin:0.2mm 0;text-align:left;">⚠️ CAMBIO DE HORARIO</div>' if cambio_horario else ""
        obs_html = f'<div style="font-size:{to};line-height:1.2;overflow-wrap:break-word;margin-top:0.1mm;text-align:left;color:#008000;font-weight:500;">{html.escape(obs_clean)}</div>' if obs_clean else ""

        h_clave = hora[:5]
        if h_clave: reporte_horas[h_clave] = reporte_horas.get(h_clave,0) + pax

        # ✅ TARJETA FINAL CON MARCA DE AGUA DETRÁS
        marca_agua = f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-size:18pt;font-weight:bold;color:rgba(180,180,180,0.15);pointer-events:none;white-space:nowrap;z-index:0;">{html.escape(titulo_etiqueta)}</div>'

        cards.append(f'''<div style="position:relative;width:100%;height:100%;{borde_tarjeta}box-sizing:border-box;padding:1.8mm;overflow:hidden;display:flex;flex-direction:column;justify-content:center;gap:0.2mm;page-break-inside:avoid;">
{marca_agua}
<div style="position:relative;z-index:1;">
{cab_etiquetas}
{nombre_final}
{bloque_datos}
{ch}{esp}{obs_html}
</div>
</div>'''.replace('\n',''))

    # Reporte final por horas
    horas_ordenadas = sorted(reporte_horas.keys())
    total_horas = len(horas_ordenadas)
    max_por_tapia = 14

    lineas_1 = horas_ordenadas[:max_por_tapia]
    reporte_html_1 = f'''<div style="width:100%;height:100%;border:1px solid #000;box-sizing:border-box;padding:1.5mm;overflow:hidden;display:flex;flex-direction:column;justify-content:center;gap:0.15mm;page-break-inside:avoid;">
<div style="font-weight:bold;text-align:center;font-size:6.8pt;margin-bottom:0.3mm;">📊 REPORTE — {html.escape(titulo_etiqueta)}</div>
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
<div style="font-weight:bold;text-align:center;font-size:6.8pt;margin-bottom:0.3mm;">📊 REPORTE (CONT) — {html.escape(titulo_etiqueta)}</div>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.1mm;">'''
        for h in lineas_2:
            reporte_html_2 += f'<div style="font-size:4.5pt;line-height:1.1;">{h} — {reporte_horas[h]}</div>'
        reporte_html_2 += "</div>"
        reporte_html_2 += f'<div style="font-weight:bold;text-align:right;font-size:5.5pt;margin-top:0.3mm;">TOTAL: {total_pax}</div></div>'
        cards.append(reporte_html_2)

    config = "size:letter;margin:2mm;" if tam_tapia=="Chica" else ("size:letter;margin:2.5mm;" if tam_tapia=="Mediana" else "size:letter;margin:3mm;")
    if orientacion=="Horizontal": config = config.replace("size:letter","size:letter landscape")
    info_cant = {"Grande":"6 por fila ~30-36/hoja","Mediana":"7 por fila ~42-49/hoja","Chica":"8 por fila 56/hoja"}[tam_tapia]
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Tapias - {html.escape(titulo_etiqueta)}</title>
<style>@page {{{config}}} *{{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact;}} body{{margin:0;padding:0;width:100%;font-family:Arial,sans-serif;}} .grid{{display:grid;grid-template-columns:repeat({cols_grid},1fr);grid-auto-rows:{alto_tarjeta};gap:0.4mm;width:100%;border:none;}}</style></head>
<body><div class="grid">{"".join(cards)}</div></body></html>""", info_cant

# -----------------------------------------------------------------------------
# INTERFAZ
# -----------------------------------------------------------------------------
st.title("⚙️ Configuración")
nombre_etiqueta = st.text_input("Nombre para reemplazar CIRCO:", value="CIRCO")
orientacion = st.radio("📐 Orientación:", ["Horizontal","Vertical"], index=0)
tam_tapia = st.radio("📏 Elige el tamaño de tapia:", ["Grande", "Mediana", "Chica"], index=1)

if tam_tapia == "Grande":
    st.info("📌 **Grande**: 6 tapias por fila | ~30 a 36 por hoja carta")
elif tam_tapia == "Mediana":
    st.info("📌 **Mediana**: 7 tapias por fila | ~42-49 por hoja carta")
else:
    st.info("📌 **Chica**: 8 tapias por fila | 56 tapias por hoja carta")

limite_mesa_grande = st.number_input("🔴 Resaltar PX desde ≥", min_value=5, value=6, step=1)
archivo = st.file_uploader("📂 Sube tu Excel (.xlsx)", type="xlsx")

if archivo and nombre_etiqueta.strip():
    try:
        df = pd.read_excel(archivo, engine="openpyxl")
        html_final, info = generar_html(df, nombre_etiqueta.strip(), limite_mesa_grande, orientacion, tam_tapia)
        st.success(f"✅ Generado correctamente — {info}")
        st.download_button(f"📄 Descargar TAPIAS {tam_tapia}.html", html_final, f"TAPIAS_{tam_tapia.upper()}.html", "text/html")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
