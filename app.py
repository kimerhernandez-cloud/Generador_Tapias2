st.title("⚙️ Configuración")
nombre_etiqueta = st.text_input("Nombre para reemplazar CIRCO:", value="CIRCO")
orientacion = st.radio("📐 Orientación:", ["Horizontal","Vertical"], index=0)

# 👇 ESTA ES LA LÍNEA CORREGIDA CON LA OPCIÓN MEDIANA VISIBLE
tam_tapia = st.radio(
    "📏 Elige el tamaño de tapia:",
    ["Grande", "Mediana", "Chica (8x7 por hoja)"],
    index=1
)

limite_mesa_grande = st.number_input("🔴 Resaltar PX desde ≥", min_value=5, value=6, step=1)
archivo = st.file_uploader("📂 Sube tu Excel (.xlsx)", type="xlsx")

if archivo and nombre_etiqueta.strip():
    try:
        df = pd.read_excel(archivo, engine="openpyxl")
        html_final = generar_html(df, nombre_etiqueta.strip(), limite_mesa_grande, orientacion, tam_tapia)
        st.success(f"✅ Listo — usando tamaño: {tam_tapia}")
        st.download_button(f"📄 Descargar TAPIAS {tam_tapia}.html", html_final, f"TAPIAS_{tam_tapia.replace(' ','_')}.html", "text/html")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
