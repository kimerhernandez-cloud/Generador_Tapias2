import pandas as pd
import re
import html
import streamlit as st

st.set_page_config(page_title="Generador de Tapias", layout="wide")
st.title("🎪 Generador de Etiquetas / Tapias by MH")

# -----------------------------------------------------------------------------
# IDENTIFICACIÓN DE NOMBRES INTERNACIONALES
# -----------------------------------------------------------------------------
def obtener_nombre_mostrar(nombre_completo):
    if pd.isna(nombre_completo):
        return ""
    partes = str(nombre_completo).strip().split()
    if not partes:
        return ""
    
    primer_nombre = partes[0]
    
    patrones_palabras_enlace = [
        r'^de$', r'^del$', r'^de\s+la$', r'^de\s+los$', r'^de\s+las$',
        r'^la$', r'^los$', r'^las$', r'^san$', r'^santa$', r'^santo$',
        r'^y$', r'^e$', r'^mc$', r'^mac$', r'^van$', r'^van\s+der$', r'^van\s+den$',
        r'^von$', r'^der$', r'^den$', r'^het$',
        r'^bin$', r'^binti$', r'^al$', r'^el$', r'^ibn$',
        r'^kim$', r'^lee$', r'^park$', r'^wang$', r'^zhang$', r'^li$', r'^singh$', r'^kaur$'
    ]
    
    idx = 1
    primer_apellido = ""
    while idx < len(partes):
        es_enlace = any(re.match(p, partes[idx].lower(), re.IGNORECASE) for p in patrones_palabras_enlace)
        if es_enlace and idx + 1 < len(partes):
            idx += 1
            primer_apellido = partes[idx]
            break
        else:
            primer_apellido = partes[idx]
            break
    
    if primer_apellido:
        return f"{primer_nombre} {primer_apellido.upper()}"
    return primer_nombre.upper()

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
# 🔹 AGRUPACIÓN: PRIORIDAD TOTAL A OBSERVACIONES
# -----------------------------------------------------------------------------
def agrupar_reservas(df):
    df = df.copy()
    # CLAVE PRINCIPAL: TEXTO DE OBSERVACIONES LIMPIO Y UNIFICADO
    df['clave_grupo'] = df['observaciones'].fillna('').astype(str).str.strip().str.upper()
    # Quitamos detalles menores (horas, fechas, horas de creación) para que coincidan aunque cambie algo pequeño
    df['clave_grupo'] = df['clave_grupo'].apply(lambda x: re.sub(r'\d{1,2}[:.]\d{2}.*$', '', x).strip())
    df['clave_grupo'] = df['clave_grupo'].apply(lambda x: re.sub(r'\d{1,2}/\d{1,2}/\d{4}.*$', '', x).strip())
    
    # Clave secundaria: mismo creador + mismo apellido (solo si la observación es vacía o muy parecida)
    tiene_creador = 'creado_por' in df.columns or 'usuario' in df.columns
    if tiene_creador:
        col_creador = 'creado_por' if 'creado_por' in df.columns else 'usuario'
        df['clave_secundaria'] = df[col_creador].fillna('').astype(str).str.strip() + "||" + df['nombre_reserva'].apply(lambda x: obtener_nombre_mostrar(x).split()[-1].upper() if pd.notna(x) else '')
    else:
        df['clave_secundaria'] = ""
    
    grupos = []
    ya_procesado = set()
    
    for idx, fila in df.iterrows():
        if idx in ya_procesado:
            continue
        
        # BUSCAMOS PRIMERO POR OBSERVACIÓN: ES LA REGLA DE ORO
        coinciden = df[df['clave_grupo'] == fila['clave_grupo']].index.tolist()
        
        # Si no hay coincidencia por observación, usamos secundaria SOLO si aplica
        if len(coinciden) == 1 and tiene_creador and fila['clave_grupo'] != "":
            coinciden_sec = df[df['clave_secundaria'] == fila['clave_secundaria']].index.tolist()
            if len(coinciden_sec) > 1:
                coinciden = coinciden_sec
        
        # PROCESAMOS EL GRUPO
        if len(coinciden) > 1:
            datos_grupo = df.loc[coinciden]
            grupos.append({
                'nombre_reserva': datos_grupo['nombre_reserva'].iloc[0],
                'habitacion': ", ".join(sorted(datos_grupo['habitacion'].astype(str).str.strip().str.rstrip('.0').unique())),
                'pax': datos_grupo['pax'].sum(),
                'hora': ", ".join(sorted(datos_grupo['hora'].astype(str).str[:5].unique())),
                'observaciones': datos_grupo['observaciones'].iloc[0],
                'es_grupo_auto': True
            })
            ya_procesado.update(coinciden)
        else:
            fila_sola = fila.to_dict()
            fila_sola['es_grupo_auto'] = False
            grupos.append(fila_sola)
            ya_procesado.add(idx)
    
    return pd.DataFrame(grupos)

# -----------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# -----------------------------------------------------------------------------
def generar_html(df, titulo_etiqueta, limite_mesa_grande, orientacion, tam_tapia):
    columnas_requeridas = ['nombre_reserva', 'habitacion', 'pax', 'hora', 'observaciones']
    faltantes = [c for c in columnas_requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(faltantes)}")

    # Aplicamos agrupación primero
    df_procesado = agrupar_reservas(df)

    # TAMAÑOS: NOMBRE +2pts, ESPACIO APROVECHADO, MÁRGENES IGUALES
    if tam_tapia == "Grande":
        alto_tarjeta = "29mm" if orientacion == "Horizontal" else "27mm"
        cols_grid = 6
        base_nombre = "11.5pt"  # +2 puntos exactos
        base_datos = "10.5pt"
        base_etiquetas = "6.5pt"
        base_obs = "7pt"
    else:
        alto_tarjeta = "22mm"
        cols_grid = 8
        base_nombre = "9pt"  # +2 puntos exactos
        base_datos = "8pt"
        base_etiquetas = "5pt"
        base_obs = "5.5pt"

    reporte_horas = {}
    total_pax = 0
    tarjetas = []

    for _, fila in df_procesado.iterrows():
        nombre_completo = obtener_nombre_completo_seguro(fila['nombre_reserva'])
        habitacion = fila['habitacion']
        personas = fila['pax']
        hora = obtener_nombre_completo_seguro(fila['hora'])
        observaciones = obtener_nombre_completo_seguro(fila['observaciones'])
        es_grupo = fila.get('es_grupo_auto', False)

        nombre_mostrar = obtener_nombre_mostrar(nombre_completo)
        hab_texto = str(habitacion).strip().rstrip('.0') if pd.notna(habitacion) else ""

        try:
            personas = int(personas)
            if personas < 1: personas = 1
        except: personas = 1
        total_pax += personas

        # DETECCIÓN DE PERSONAS
        for patron, valor in [
            (r'22\s*PAX',22),(r'SON\s*PAX\s*0?7',7),(r'SON\s*0?3\s*PAX',3),
            (r'SON\s*4\s*PAX',4),(r'SON\s*10\s*PAX|10\s*PAX',10),(r'SON\s*5\s*PAX',5),
            (r'SON\s*6\s*PAX',6),(r'SON\s*8\s*PAX',8),(r'SON\s*9\s*PAX',9),
            (r'SON\s*11\s*PAX',11),(r'SON\s*12\s*PAX',12),(r'\bSON\s+(\d{1,2})\s+PAX\b',None)
        ]:
            m = re.search(patron, observaciones.upper())
            if m: personas = valor if valor else int(m.group(1)); break

        # FORMATO DE HORA
        hora_final = ""
        if isinstance(fila['hora'], pd.Timestamp):
            hora_final = fila['hora'].strftime('%H:%M')
        else:
            m = re.search(r'(\d{1,2})[:.]?(\d{2})', str(hora))
            hora_final = f"{int(m.group(1)):02d}:{m.group(2)}" if m else str(hora)[:5]

        # CAMBIO DE HORARIO
        cambio_hora = False
        m_hora = re.search(r'llegan?\s+a\s+las\s+(\d{1,2})[:.]?(\d{2})|arrive\s+(at|around)?\s*(\d{1,2})[:.]?(\d{2})', observaciones, re.I)
        if m_hora:
            g = m_hora.groups()
            h = g[0] or g[3]; min = g[1] or g[4]
            hora_final = f"{int(h):02d}:{min}"
            cambio_hora = True
        else:
            for patron, hora_cambio in [
                (r'llegará?n\s+6\s*pm|arrive.*6\s*pm',"18:00"),
                (r'llegará?n\s+7\s*pm|arrive.*7\s*pm',"19:00"),
                (r'llegará?n\s+8\s*pm|arrive.*8\s*pm',"20:00"),
                (r'llegará?n\s+9\s*pm|arrive.*9\s*pm',"21:00"),
                (r'llegará?n\s+10\s*pm|arrive.*10\s*pm',"22:00")
            ]:
                if re.search(patron, observaciones, re.I):
                    hora_final, cambio_hora = hora_cambio, True; break

        # ---------------------------------------------------------------------
        # ETIQUETAS EXACTAS: SOLO HBD / ANIVERSARIO + GRUPO
        # ---------------------------------------------------------------------
        obs_mayus = observaciones.upper()
        es_residencia = bool(re.search(r'RESIDENCE|S\.\s*RESIDENCE', obs_mayus))
        es_diamante = bool(re.search(r'DIAMANTE|DIAMOND', obs_mayus))
        es_seguimiento = bool(re.search(r'SEGUIMIENTO|FOLLOW.*UP', obs_mayus))
        tiene_excl = bool(re.search(r'SIN\s+ALERGIAS|NO\s+ALERGIES|CONFIRMAR', obs_mayus))
        tiene_restriccion = bool(re.search(r'CELIACO|GLUTEN|ALERGIA|ALERGY|SHELLFISH|NUTS|VEGETARIAN|VEGAN|DIABETES|NO PORK', obs_mayus))
        es_alergia = tiene_restriccion and not tiene_excl
        
        # SOLO HBD cuando sea cumpleaños
        es_hbd = bool(re.search(r'cumpleaños|cumple\s+año|cumple\s+años|birthday|birth\s+day', observaciones, re.I))
        # SOLO ANIVERSARIO
        es_aniversario = bool(re.search(r'aniversario|aniversarios|anniversary', observaciones, re.I))
        # GRUPO: detectado automáticamente + manual
        es_grupo_final = es_grupo or bool(re.search(r'sentar juntos|compartir mesa|grupo|together|same table|group', obs_mayus))
        
        es_nuevo = bool(re.search(r'nuevos?\s+socios?|new members|new guest', observaciones, re.I))
        es_dia_pase = bool(re.search(r'day pass|visitor|external guest', observaciones, re.I))
        es_privado = bool(re.search(r'privado|private|vip', obs_mayus))

        obs_limpia = limpiar_obs_base(observaciones)

        # AJUSTE DE LETRA APROVECHANDO ESPACIO
        cantidad_etiquetas = sum([es_residencia,es_diamante,es_seguimiento,es_alergia,es_hbd,es_aniversario,es_nuevo,es_dia_pase,es_privado,es_grupo_final,cambio_hora])
        largo_obs = len(obs_limpia)
        largo_nombre = len(nombre_mostrar)
        total_caracteres = len(nombre_mostrar) + len(hab_texto) + len(str(personas)) + len(hora_final) + len(obs_limpia) + (cantidad_etiquetas * 15)

        if total_caracteres > 200 or cantidad_etiquetas >=4 or largo_obs>130 or largo_nombre>20:
            tam_nombre, tam_datos, tam_etq, tam_obs = "9.5pt", "8pt", "5pt", "5.5pt"
        elif total_caracteres > 150 or cantidad_etiquetas >=3 or largo_obs>90 or largo_nombre>15:
            tam_nombre, tam_datos, tam_etq, tam_obs = "10pt", "8.5pt", "5.5pt", "6pt"
        elif total_caracteres > 90 or cantidad_etiquetas >=2 or largo_obs>50 or largo_nombre>12:
            tam_nombre, tam_datos, tam_etq, tam_obs = "10.5pt", "9pt", "6pt", "6.5pt"
        else:
            tam_nombre, tam_datos, tam_etq, tam_obs = base_nombre, base_datos, base_etiquetas, base_obs

        # RECUADRO ROJO MESAS GRANDES
        if personas >= limite_mesa_grande:
            estilo_recuadro = "border:1.5px solid #c00;padding:2px 4px;border-radius:3px;background:#FFECEC;"
            linea_datos = f'<div style="font-size:{tam_datos};text-align:left;{estilo_recuadro}"><b>Hab:</b> {html.escape(hab_texto)} | <b>PX:</b> {personas}</div>'
        else:
            linea_datos = f'<div style="font-size:{tam_datos};text-align:left;"><b>Hab:</b> {html.escape(hab_texto)} | <b>PX:</b> {personas}</div>'

        # ESTILOS ETIQUETAS
        est_cabecera = f"padding:1px 3px;border-radius:2px;flex-wrap:wrap;gap:1px;font-size:{tam_etq};"
        if es_residencia or es_diamante: est_cabecera += "background:#E0F7FF;border:1px solid #4682B4;"
        azul = f"display:inline-block;border:1px solid #4682B4;background:#E0F7FF;color:#005580;padding:1px 3px;border-radius:2px;font-size:{tam_etq};font-weight:bold;margin-right:2px;"
        naranja = azul.replace("#E0F7FF","#FFF3E0").replace("#4682B4","#F57C00").replace("#005580","#E65100")
        verde = azul.replace("#E0F7FF","#E8F5E9").replace("#4682B4","#2E7D32").replace("#005580","#1B5E20")
        etiquetas = []
        if es_residencia: etiquetas.append(f'<span style="{azul}">🔑 RESIDENCE</span>')
        if es_diamante: etiquetas.append(f'<span style="{azul}">💎 DIAMANTE</span>')
        if es_seguimiento: etiquetas.append(f'<span style="{naranja}">🛑 SEGUIMIENTO</span>')
        if es_alergia: etiquetas.append('⚠️ ALERGIAS')
        if es_grupo_final: etiquetas.append(f'<span style="{verde}">👥 GRUPO</span>')
        cabecera = f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:2px;line-height:1.1;{est_cabecera}"><span style="display:flex;gap:2px;flex-wrap:wrap;">{" ".join(etiquetas)}</span><span style="font-weight:bold;white-space:nowrap;">{html.escape(titulo_etiqueta)}</span></div>'

        # ETIQUETAS EXACTAS
        texto_etq = ""
        if es_hbd:
            texto_etq='<div style="font-weight:bold;font-size:7pt;text-align:center;color:#c00;margin:0.5mm 0 0.3mm 0;white-space:nowrap;">🎂 HBD</div>'
            obs_limpia=""
        if es_aniversario and not es_hbd:
            texto_etq='<div style="font-weight:bold;font-size:7pt;text-align:center;color:#800080;margin:0.5mm 0 0.3mm 0;white-space:nowrap;">💍 ANIVERSARIO</div>'
            obs_limpia=""
        if es_nuevo and not es_hbd and not es_aniversario:
            texto_etq='<div style="font-weight:bold;font-size:6.5pt;text-align:center;color:#006;margin:0.5mm 0 0.3mm 0;white-space:nowrap;">🆕 NUEVO SOCIO</div>'
            obs_limpia=""
        if es_dia_pase and not es_hbd and not es_aniversario:
            texto_etq='<div style="font-weight:bold;font-size:6.5pt;text-align:center;color:#333;margin:0.5mm 0 0.3mm 0;white-space:nowrap;">🎟️ DAY PASS</div>'
            obs_limpia=""
        aviso_cambio = f'<div style="color:#c00;font-weight:bold;font-size:{tam_etq};margin:0.2mm 0;text-align:left;">⚠️ CAMBIO DE HORARIO</div>' if cambio_hora else ""
        texto_obs = f'<div style="font-size:{tam_obs};line-height:1.2;overflow-wrap:break-word;margin-top:0.1mm;text-align:left;">{html.escape(obs_limpia)}</div>' if obs_limpia else ""

        clave_hora = hora_final[:5]
        if clave_hora: reporte_horas[clave_hora] = reporte_horas.get(clave_hora,0) + personas

        # ARMAMOS LA TARJETA
        tarjetas.append(f'''<div style="width:100%;height:100%;border:1px solid #000;box-sizing:border-box;padding:1.5mm;overflow:hidden;display:flex;flex-direction:column;justify-content:center;gap:0.15mm;page-break-inside:avoid;">
{cabecera}
<div style="font-weight:bold;font-size:{tam_nombre};line-height:1.05;margin-top:0.1mm;text-align:left;">{html.escape(nombre_mostrar)}</div>
{linea_datos}
<div style="font-size:{tam_datos};text-align:left;"><b>Hora:</b> {hora_final}</div>
{aviso_cambio}{texto_etq}{texto_obs}
</div>'''.replace('\n',''))

    # ---- REPORTE FINAL ----
    horas_ordenadas = sorted(reporte_horas.keys())
    total_horas = len(horas_ordenadas)
    max_por_tapia = 14

    bloque1 = horas_ordenadas[:max_por_tapia]
    reporte1 = f'''<div style="width:100%;height:100%;border:1px solid #000;box-sizing:border-box;padding:1.5mm;overflow:hidden;display:flex;flex-direction:column;justify-content:center;gap:0.15mm;page-break-inside:avoid;">
<div style="font-weight:bold;text-align:center;font-size:6.8pt;margin-bottom:0.3mm;">📊 REPORTE</div>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.1mm;">'''
    for h in bloque1:
        reporte1 += f'<div style="font-size:4.5pt;line-height:1.1;">{h} — {reporte_horas[h]}</div>'
    reporte1 += "</div>"
    if total_horas <= max_por_tapia:
        reporte1 += f'<div style="font-weight:bold;text-align:right;font-size:5.5pt;margin-top:0.3mm;">TOTAL: {total_pax}</div>'
    reporte1 += "</div>"
    tarjetas.append(reporte1)

    if total_horas > max_por_tapia:
        bloque2 = horas_ordenadas[max_por_tapia:]
        reporte2 = f'''<div style="width:100%;height:100%;border:1px solid #000;box-sizing:border-box;padding:1.5mm;overflow:hidden;display:flex;flex-direction:column;justify-content:center;gap:0.15mm;page-break-inside:avoid;">
<div style="font-weight:bold;text-align:center;font-size:6.8pt;margin-bottom:0.3mm;">📊 REPORTE (CONT)</div>
<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.1mm;">'''
        for h in bloque2:
            reporte2 += f'<div style="font-size:4.5pt;line-height:1.1;">{h} — {reporte_horas[h]}</div>'
        reporte2 += "</div>"
        reporte2 += f'<div style="font-weight:bold;text-align:right;font-size:5.5pt;margin-top:0.3mm;">TOTAL: {total_pax}</div></div>'
        tarjetas.append(reporte2)

    # CONFIGURACIÓN FINAL
    config = "size:letter;margin:2mm;" if tam_tapia=="Chica" else "size:letter;margin:3mm;"
    if orientacion=="Horizontal": config = config.replace("size:letter","size:letter landscape")
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Tapias - {html.escape(titulo_etiqueta)}</title>
<style>@page {{{config}}} *{{box-sizing:border-box;margin:0;padding:0;-webkit-print-color-adjust:exact;print-color-adjust:exact;}} body{{margin:0;padding:0;width:100%;font-family:Arial,sans-serif;}} .grid{{display:grid;grid-template-columns:repeat({cols_grid},1fr);grid-auto-rows:{alto_tarjeta};gap:0.4mm;width:100%;border:none;}}</style></head>
<body><div class="grid">{"".join(tarjetas)}</div></body></html>"""

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
        st.success("✅ LISTO")
        st.download_button("📄 Descargar TAPIAS.html", html_final, "TAPIAS_HOJA_COMPLETA.html", "text/html")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
