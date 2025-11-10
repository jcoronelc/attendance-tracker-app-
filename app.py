import streamlit as st
import pandas as pd
import altair as alt
import os
from datetime import date, datetime

# --- Configuración general ---
st.set_page_config(page_title="Asistencia Scouts", page_icon="🏕️", layout="wide")

# --- Constantes y rutas ---
USUARIOS_PATH = "data/usuarios.csv"
ASISTENCIAS_PATH = "data/asistencias.csv"
ADMIN_PASSWORD = "scout2025"  # 🔒 Contraseña del dirigente

# --- Funciones auxiliares ---
def load_usuarios():
    try:
        return pd.read_csv(USUARIOS_PATH)
    except FileNotFoundError:
        return pd.DataFrame(columns=["nombre", "contraseña"])

def save_usuarios(df):
    df.to_csv(USUARIOS_PATH, index=False)

def load_asistencias():
    if os.path.exists(ASISTENCIAS_PATH):
        df = pd.read_csv(ASISTENCIAS_PATH)
    else:
        df = pd.DataFrame(columns=["nombre", "fecha", "estado", "comentario"])
        df.to_csv(ASISTENCIAS_PATH, index=False)
    # ✅ Normalizar formato de fecha siempre al cargar
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    return df

def save_asistencias(df):
    # ✅ Convertir a string ISO al guardar para evitar problemas de tipo
    df["fecha"] = df["fecha"].apply(lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else "")
    df.to_csv(ASISTENCIAS_PATH, index=False)

def calcular_racha(df, nombre):
    registros = df[df["nombre"] == nombre].copy()
    registros["fecha"] = pd.to_datetime(registros["fecha"], errors="coerce")
    registros = registros.dropna(subset=["fecha"]).sort_values("fecha")

    racha, max_racha = 0, 0
    ultima_fecha = None
    for _, row in registros.iterrows():
        if row["estado"] == "Presente":
            fecha_row = row["fecha"]
            if ultima_fecha is None:
                racha = 1
            else:
                diferencia = (fecha_row - ultima_fecha).days
                racha = racha + 1 if diferencia <= 7 else 1
            ultima_fecha = fecha_row
            max_racha = max(max_racha, racha)
        else:
            racha = 0
    return max_racha

def obtener_insignias(historial, racha_actual):
    insignias = []
    if len(historial) >= 5:
        insignias.append("🎖️ Participante activo")
    if racha_actual >= 3:
        insignias.append("🏅 Constante del mes")
    if len(historial[historial["estado"] == "Presente"]) >= 10:
        insignias.append("🏆 Compromiso ejemplar")
    if len(insignias) == 0:
        insignias.append("🌱 En camino a su primera insignia")
    return insignias

# --- Interfaz principal ---
st.title("🏕️ Sistema de Asistencia Scout")

modo = st.sidebar.radio("Selecciona modo:", ["Participante", "Dirigente"])

usuarios_df = load_usuarios()
asist_df = load_asistencias()

# --- PARTICIPANTE ---
if modo == "Participante":
    st.header("👤 Registro de asistencia personal")

    nombres = sorted([str(n) for n in usuarios_df["nombre"].dropna().unique().tolist() if str(n).strip() != ""] + ["Nuevo participante"])
    nombre = st.selectbox("Tu nombre:", nombres)

    # Crear nuevo usuario
    if nombre == "Nuevo participante":
        nuevo_nombre = st.text_input("Crea tu nombre:")
        nueva_contra = st.text_input("Crea tu contraseña:", type="password")
        if st.button("Registrar nuevo participante", use_container_width=True):
            if nuevo_nombre and nueva_contra:
                if nuevo_nombre in usuarios_df["nombre"].values:
                    st.warning("Ese nombre ya existe. Elige otro.")
                else:
                    nuevo = pd.DataFrame([[nuevo_nombre, nueva_contra]], columns=["nombre", "contraseña"])
                    usuarios_df = pd.concat([usuarios_df, nuevo], ignore_index=True)
                    save_usuarios(usuarios_df)
                    st.success(f"Usuario {nuevo_nombre} creado con éxito 🎉")
                    st.stop()
            else:
                st.warning("Debes ingresar un nombre y una contraseña.")
        st.stop()

    # Verificación de contraseña
    stored_pass = usuarios_df.loc[usuarios_df["nombre"] == nombre, "contraseña"].iloc[0] if nombre in usuarios_df["nombre"].values else None
    input_pass = st.text_input("Ingresa tu contraseña:", type="password")

    if stored_pass and input_pass == str(stored_pass):
        st.success("Acceso correcto ✅")

        st.markdown("### Selecciona tu estado:")

        if "estado" not in st.session_state:
            st.session_state.estado = None

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("✅ Presente", use_container_width=True):
                st.session_state.estado = "Presente"
        with col2:
            if st.button("📝 Ausente justificado", use_container_width=True):
                st.session_state.estado = "Ausente justificado"
        with col3:
            if st.button("❌ Ausente injustificado", use_container_width=True):
                st.session_state.estado = "Ausente injustificado"

        estado = st.session_state.estado

        if estado:
            comentario = ""
            if estado == "Presente":
                comentario = st.text_area("Comentario (opcional):", placeholder="¿Cómo te fue hoy?")
            fecha = st.date_input("📅 Fecha", value=date.today())

            if st.button("💾 Registrar asistencia", use_container_width=True):
                nuevo = pd.DataFrame([[nombre, pd.to_datetime(fecha), estado, comentario]],
                     columns=["nombre", "fecha", "estado", "comentario"])
                asist_df = pd.concat([asist_df, nuevo], ignore_index=True)
                save_asistencias(asist_df)
                st.success(f"Registro guardado para {nombre} el {fecha}")
                st.session_state.estado = None

        # Mostrar historial
        historial = asist_df[asist_df["nombre"] == nombre].copy()
        if not historial.empty:
            st.subheader("📜 Tu historial")
            historial["fecha"] = pd.to_datetime(historial["fecha"], errors="coerce")
            st.dataframe(historial.sort_values("fecha", ascending=False), use_container_width=True)

            conteo = historial["estado"].value_counts().reset_index()
            conteo.columns = ["Estado", "Cantidad"]

            colores_estado = alt.Scale(
                domain=["Presente", "Ausente justificado", "Ausente injustificado"],
                range=["#2ecc71", "#3498db", "#e74c3c"]  # verde, azul, rojo
            )
            
            chart = alt.Chart(conteo).mark_bar().encode(
                x=alt.X("Estado", sort="-y"),
                y="Cantidad",
                color=alt.Color("Estado", scale=colores_estado, legend=None),
                tooltip=["Estado", "Cantidad"]
            ).properties(width=500, height=300, title="Distribución de tus asistencias")

            st.altair_chart(chart, use_container_width=True)

            # Racha e insignias
            racha_actual = calcular_racha(asist_df, nombre)
            # --- Bloque de estadísticas con mejor diseño ---
            racha_html = f"""
            <div style="
                background: linear-gradient(135deg, #7650c3 0%, #284594 100%);
                border-radius: 20px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                height: 100%;
            ">
                <h2 style="font-size: 2.2em; margin-bottom: 10px;">🔥</h2>
                <h3 style="margin: 0; font-weight: 600;">Racha actual</h3>
                <p style="font-size: 1.4em; margin-top: 10px;">{racha_actual} asistencias seguidas</p>
            </div>
            """

            insignias = obtener_insignias(historial, racha_actual)
            insignias_html = " ".join([f"<span style='font-size:2em; margin:0 6px;'>{i}</span>" for i in insignias])

            insignias_card = f"""
            <div style="
                background: linear-gradient(135deg, #7ed957 0%, #38b6ff 100%);
                border-radius: 20px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                height: 100%;
            ">
                <h2 style="font-size: 2.2em; margin-bottom: 10px;">🏆</h2>
                <h3 style="margin: 0; font-weight: 600;">Tus insignias</h3>
                <div style="margin-top: 10px;">{insignias_html}</div>
            </div>
            """

            # Mostrar dos tarjetas lado a lado
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(racha_html, unsafe_allow_html=True)
            with col2:
                st.markdown(insignias_card, unsafe_allow_html=True)

        else:
            st.info("Aún no tienes registros.")
    elif input_pass and input_pass != stored_pass:
        st.error("Contraseña incorrecta ❌")

# --- DIRIGENTE ---
else:
    st.header("🧭 Panel del dirigente")

    admin_pass = st.text_input("Contraseña del dirigente:", type="password")
    if admin_pass != ADMIN_PASSWORD:
        st.warning("Introduce la contraseña correcta para acceder.")
        st.stop()

    opcion = st.selectbox("Ver datos de:", ["Todos"] + sorted(asist_df["nombre"].unique().tolist()))
    if opcion == "Todos":
        vista = asist_df
    else:
        vista = asist_df[asist_df["nombre"] == opcion]

    vista["fecha"] = pd.to_datetime(vista["fecha"], errors="coerce")
    st.dataframe(vista.sort_values("fecha", ascending=False), use_container_width=True)

    st.subheader("📊 Resumen general")
    if not asist_df.empty:
        resumen = asist_df[asist_df["estado"] == "Presente"]["nombre"].value_counts().reset_index()
        resumen.columns = ["nombre", "asistencias"]
        resumen["racha"] = resumen["nombre"].apply(lambda n: calcular_racha(asist_df, n))
        top5 = resumen.sort_values(["asistencias", "racha"], ascending=False).head(5)

        st.write("🏅 Top 5 constancia")
        st.dataframe(top5, use_container_width=True)

        chart = alt.Chart(top5).mark_bar().encode(
            x="nombre",
            y="asistencias",
            color="nombre",
            tooltip=["nombre", "asistencias", "racha"]
        ).properties(title="Top 5 en asistencias")
        st.altair_chart(chart, use_container_width=True)

    st.download_button(
        "⬇️ Descargar base de datos de asistencias",
        asist_df.to_csv(index=False).encode("utf-8"),
        "asistencias.csv",
        "text/csv"
    )
