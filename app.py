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

# ----------------------
# FUNCIÓN: RESUMEN OBSERVACIONES + DETALLES CLAVE
# ----------------------
def procesar_observaciones(texto, max_caracteres=45):
    if pd.isna(texto):
        return ""
    texto = str(texto).strip()
    # Palabras clave que siempre se muestran completas
    claves = ["Llegan a las", "CAMBIO DE HORARIO", "alergia", "alergico", "preferencia", "mesa", "especial"]
    if any(clave.lower() in texto.lower() for clave in claves):
        return texto
    # Resumir si es muy largo
    if len(texto) > max_caracteres:
        return texto[:max_caracteres] + "..."
    return texto

# ----------------------
# CONFIGURACIÓN DE INTERFAZ
# ----------------------
st.sidebar.header("⚙️ Configuración")
nombre_cabecera = st.sidebar.text_input("Nombre para reemplazar CIRCO:", value="CHATEAU")
zona_etiqueta = st.sidebar.text_input("Etiqueta de zona (Residencia/Diamante):", value="Residencia")
orientacion = st.sidebar.radio("Orientación:", ["Horizontal", "Vertical"])
tamano_tapia = st.sidebar.radio("Tamaño de tapia:", ["Grande (actual)", "Chica (8x7 por hoja)"])
limite_mesa_grande = st.sidebar.number_input("Resaltar PX desde ≥", min_value=1, value=6)

archivo_subido = st.file_uploader("Sube tu Excel (.xlsx)", type="xlsx")

# ----------------------
# PROCESAMIENTO PRINCIPAL
# ----------------------
if archivo_subido:
    try:
        df = pd.read_excel(archivo_subido)
        # Inicialización SEGURA de la variable problemática
        lineas_2 = ""

        # Unir reservas duplicadas por nombre o habitación
        agrupado = df.groupby(["nombre_reserva", "habitacion"], dropna=False, sort=False).agg(
            px_total=("px", "sum"),
            hora=("hora", "first"),
            observaciones=("observaciones", lambda x: " | ".join(str(v) for v in x if pd.notna(v))),
            zona=("zona", "first")
        ).reset_index()

        # ----------------------
        # AJUSTE DE HORA (prioridad observaciones)
        # ----------------------
        def extraer_hora(hora_base, obs):
            if pd.notna(obs):
                coincidencia = re.search(r"Llegan a las (\d{1,2}:\d{2})", str(obs))
                if coincidencia:
                    return coincidencia.group(1), True
            return str(hora_base), False

        # ----------------------
        # GENERAR HTML PARA IMPRESIÓN
        # ----------------------
        estilos_css = f"""
        <style>
            .contenedor-tapias {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 15px; }}
            .tapia {{ 
                border: 1px solid #333; 
                padding: 10px; 
                font-family: Arial, sans-serif;
                {'width: 220px;' if tamano_tapia.startswith('Grande') else 'width: 160px;'}
                {'height: 140px;' if tamano_tapia.startswith('Grande') else 'height: 110px;'}
                page-break-inside: avoid;
            }}
            .cabecera {{ display: flex; justify-content: space-between; font-size: 13px; font-weight: bold; margin-bottom: 6px; }}
            .mesa-grande {{ background-color: #fff3cd; border: 2px solid #d97706; }}
            .etiqueta-zona {{ font-size: 12px; color: #555; }}
            .datos {{ font-size: 14px; line-height: 1.3; }}
            .obs {{ font-size: 12px; color: #444; margin-top: 5px; word-wrap: break-word; }}
            .cambio-horario {{ color: #b91c1c; font-weight: bold; font-size: 11px; }}
        </style>
        """

        html_tapias = [estilos_css, '<div class="contenedor-tapias">']

        for _, fila in agrupado.iterrows():
            apellido = obtener_primer_apellido(fila["nombre_reserva"])
            habitacion = str(fila["habitacion"]).strip().rstrip('.0') if pd.notna(fila["habitacion"]) else ""
            px = int(fila["px_total"])
            hora_final, hay_cambio = extraer_hora(fila["hora"], fila["observaciones"])
            obs_procesadas = procesar_observaciones(fila["observaciones"])

            # Clase visual para mesas grandes
            clase_mesa = "mesa-grande" if px >= limite_mesa_grande else ""

            # Construir tarjeta
            tarjeta = f'''
            <div class="tapia {clase_mesa}">
                <div class="cabecera">
                    <span class="etiqueta-zona">{zona_etiqueta}</span>
                    <span>{nombre_cabecera}</span>
                </div>
                <div class="datos">
                    <strong>APELLIDO:</strong> {apellido}<br>
                    <strong>HAB:</strong> {habitacion}<br>
                    <strong>PX:</strong> {px} personas<br>
                    <strong>HORA:</strong> {hora_final}
                    { '<span class="cambio-horario"> ⚠️ CAMBIO</span>' if hay_cambio else ''}
                </div>
                <div class="obs">{obs_procesadas}</div>
            </div>
            '''
            html_tapias.append(tarjeta)

        html_tapias.append("</div>")
        codigo_completo = "".join(html_tapias)

        # Mostrar y permitir descarga
        st.markdown(codigo_completo, unsafe_allow_html=True)
        st.download_button("📥 Descargar para imprimir (HTML)", data=codigo_completo, file_name="tapias_listas.html", mime="text/html")

    except Exception as e:
        st.error(f"Error procesando archivo: {str(e)}")
        st.exception(e)
else:
    st.info("⬆️ Sube tu archivo Excel para comenzar.")
