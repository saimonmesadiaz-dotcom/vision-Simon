"""
Centro de Comando · Reconocimiento de imagen
--------------------------------------------
App de Streamlit que envía una imagen a un modelo de visión de OpenAI y
muestra el informe de análisis en tiempo real. Misma estética de base de
comando espacial que la app de telemetría MQTT.

Ejecutar:  streamlit run app_imagen.py
"""

import base64
from html import escape

import streamlit as st
from openai import OpenAI


# ═════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═════════════════════════════════════════════════════════════════════════════
MODELO = "gpt-4o"
MAX_TOKENS = 1200
TIPOS_IMAGEN = ["jpg", "jpeg", "png"]
PROMPT_BASE = "Describe en español lo que ves en la imagen."


# ═════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE LA PÁGINA Y ESTILOS
# ═════════════════════════════════════════════════════════════════════════════
def configurar_pagina() -> None:
    st.set_page_config(
        page_title="Centro de Comando · Imagen",
        page_icon="🛰️",
        layout="centered",
        initial_sidebar_state="expanded",
    )


def inyectar_estilos() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600;700&display=swap');

        :root {
            --espacio:    #050914;
            --panel:      rgba(11, 22, 44, 0.78);
            --cian:       #35E0F2;
            --cian-tenue: rgba(53, 224, 242, 0.28);
            --violeta:    #8B5CF6;
            --texto:      #D6E6F5;
            --apagado:    #7F96B2;
            --alerta:     #FF5C6C;
            --campo:      #0A1529;
        }

        /* ── Fondo: nebulosa + campo de estrellas ───── */
        .stApp {
            background:
                radial-gradient(ellipse at 15% 0%, rgba(139, 92, 246, .28), transparent 55%),
                radial-gradient(ellipse at 95% 35%, rgba(53, 224, 242, .13), transparent 50%),
                radial-gradient(ellipse at 40% 100%, rgba(255, 79, 216, .10), transparent 55%),
                var(--espacio);
            color: var(--texto);
            font-family: 'Rajdhani', sans-serif;
        }
        .stApp::before, .stApp::after {
            content: ""; position: fixed; inset: 0;
            pointer-events: none; z-index: 0;
        }
        .stApp::before {
            background-image:
                radial-gradient(1px 1px at 20px 30px, #fff, transparent),
                radial-gradient(1px 1px at 90px 140px, #cfe8ff, transparent),
                radial-gradient(1.5px 1.5px at 160px 70px, #fff, transparent),
                radial-gradient(1px 1px at 230px 190px, #b9d4ff, transparent);
            background-size: 260px 220px;
            opacity: .55;
        }
        .stApp::after {
            background-image:
                radial-gradient(1px 1px at 60px 90px, #fff, transparent),
                radial-gradient(1.5px 1.5px at 190px 20px, #ffe9ff, transparent),
                radial-gradient(1px 1px at 120px 200px, #fff, transparent);
            background-size: 340px 280px;
            animation: titilar 7s ease-in-out infinite alternate;
        }
        @keyframes titilar { from { opacity: .2; } to { opacity: .75; } }

        [data-testid="stHeader"] { background: transparent; }
        .block-container {
            position: relative; z-index: 1;
            padding-top: 2.5rem; max-width: 780px;
        }

        /* ── Texto base ─────────────────────────────── */
        .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3,
        [data-testid="stWidgetLabel"] p, summary p {
            color: var(--texto) !important;
            font-family: 'Rajdhani', sans-serif;
            font-size: 1.05rem;
        }
        .stApp h2, .stApp h3 {
            font-family: 'Orbitron', sans-serif !important;
            font-size: 1.05rem !important;
            letter-spacing: .12em;
            text-transform: uppercase;
        }
        [data-testid="stCaptionContainer"] p {
            color: var(--apagado) !important; font-size: .95rem;
        }

        /* ── Encabezado con radar ───────────────────── */
        .encabezado { display: flex; align-items: center; gap: 1.2rem; }
        .radar {
            flex: none; width: 66px; height: 66px; border-radius: 50%;
            position: relative; overflow: hidden;
            border: 1px solid var(--cian);
            background: repeating-radial-gradient(
                circle, transparent 0 9px, rgba(53, 224, 242, .22) 9px 10px);
            box-shadow: 0 0 20px rgba(53, 224, 242, .4),
                        inset 0 0 14px rgba(53, 224, 242, .25);
        }
        .radar::before {
            content: ""; position: absolute; inset: 0; border-radius: 50%;
            background: conic-gradient(
                from 0deg, rgba(53, 224, 242, .6), transparent 30%);
            animation: barrido 4s linear infinite;
        }
        .radar::after {
            content: ""; position: absolute; top: 17px; left: 41px;
            width: 4px; height: 4px; border-radius: 50%;
            background: #fff; box-shadow: 0 0 6px #fff;
        }
        @keyframes barrido { to { transform: rotate(360deg); } }

        .titulo {
            font-family: 'Orbitron', sans-serif; font-weight: 900;
            font-size: 1.9rem; letter-spacing: .1em; text-transform: uppercase;
            color: #fff; margin: 0; line-height: 1.1;
            text-shadow: 0 0 18px rgba(53, 224, 242, .65);
        }
        .subtitulo {
            color: var(--apagado); font-size: 1.1rem; font-weight: 500;
            letter-spacing: .04em; margin: .25rem 0 0 0;
        }

        /* ── Indicador de enlace ────────────────────── */
        .enlace {
            display: inline-flex; align-items: center; gap: .6rem;
            margin: 1.4rem 0 .4rem 0; padding: .4rem 1rem;
            background: var(--panel); border: 1px solid var(--cian-tenue);
            font-weight: 600; letter-spacing: .06em; color: var(--texto);
            clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px,
                               100% 100%, 10px 100%, 0 calc(100% - 10px));
        }
        .enlace .estado { color: var(--apagado); }
        .punto {
            width: 9px; height: 9px; border-radius: 50%;
            background: var(--apagado);
        }
        .punto.activo {
            background: #3DFFB0; box-shadow: 0 0 10px #3DFFB0;
            animation: pulso 1.8s ease-in-out infinite;
        }
        .punto.error { background: var(--alerta); box-shadow: 0 0 10px var(--alerta); }
        @keyframes pulso { 50% { opacity: .35; } }

        /* ── Carga de imagen ────────────────────────── */
        [data-testid="stFileUploaderDropzone"] {
            background: var(--panel);
            border: 1.5px dashed var(--cian-tenue); border-radius: 2px;
        }
        [data-testid="stFileUploaderDropzone"]:hover { border-color: var(--cian); }
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] span {
            color: var(--apagado) !important;
        }
        [data-testid="stFileUploaderDropzone"] button {
            background: transparent; border: 1px solid var(--cian);
            color: var(--cian); border-radius: 2px;
        }
        [data-testid="stImage"] img { border: 1px solid var(--cian-tenue); }
        [data-testid="stImageCaption"] { color: var(--apagado) !important; }

        /* ── Campos de texto ────────────────────────── */
        [data-baseweb="input"], [data-baseweb="base-input"],
        [data-baseweb="textarea"] {
            background: var(--campo) !important;
            border-color: var(--cian-tenue) !important;
            border-radius: 2px !important;
        }
        [data-baseweb="input"] input, [data-baseweb="base-input"] input,
        [data-baseweb="textarea"] textarea {
            color: var(--texto) !important; background: var(--campo) !important;
            font-family: 'Rajdhani', sans-serif; font-size: 1.05rem;
        }
        [data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within {
            border-color: var(--cian) !important;
            box-shadow: 0 0 10px rgba(53, 224, 242, .4);
        }

        /* ── Informe de análisis ────────────────────── */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(160deg,
                rgba(18, 36, 70, .85), rgba(7, 14, 30, .92));
            border: 1px solid var(--cian-tenue) !important;
            border-radius: 2px !important;
            box-shadow: inset 0 0 28px rgba(53, 224, 242, .07);
        }

        /* ── Sin señal / falla ──────────────────────── */
        .vacio, .falla {
            padding: 2rem 1.5rem; text-align: center;
            color: var(--apagado); font-size: 1.1rem;
            background: var(--panel); border: 1px dashed var(--cian-tenue);
        }
        .vacio strong, .falla strong {
            display: block; margin-bottom: .35rem;
            font-family: 'Orbitron', sans-serif; letter-spacing: .12em;
            text-transform: uppercase; font-size: 1rem; color: var(--texto);
        }
        .falla { border: 1px solid rgba(255, 92, 108, .55);
                 background: rgba(255, 92, 108, .08); }
        .falla strong { color: var(--alerta); }

        /* ── Botón principal ────────────────────────── */
        .stButton > button {
            background: linear-gradient(90deg,
                rgba(53, 224, 242, .18), rgba(139, 92, 246, .32));
            border: 1px solid var(--cian); border-radius: 2px;
            padding: .85rem 1rem;
            box-shadow: 0 0 18px rgba(53, 224, 242, .25);
            transition: box-shadow .2s ease, background .2s ease;
        }
        .stButton > button p {
            color: #E8FBFF !important;
            font-family: 'Orbitron', sans-serif; font-weight: 700;
            letter-spacing: .16em; text-transform: uppercase;
            font-size: .95rem;
        }
        .stButton > button:hover {
            border-color: #fff;
            background: linear-gradient(90deg,
                rgba(53, 224, 242, .32), rgba(139, 92, 246, .5));
            box-shadow: 0 0 28px rgba(53, 224, 242, .55);
        }
        .stButton > button:focus-visible { outline: 2px solid #fff; outline-offset: 3px; }

        /* ── Barra lateral, expanders y avisos ──────── */
        section[data-testid="stSidebar"] {
            background: rgba(5, 10, 22, .96);
            border-right: 1px solid var(--cian-tenue);
        }
        [data-testid="stExpander"] {
            background: var(--panel); border: 1px solid var(--cian-tenue);
            border-radius: 2px;
        }
        [data-testid="stAlert"] {
            background: rgba(53, 224, 242, .07);
            border: 1px solid var(--cian-tenue); border-radius: 2px;
        }
        [data-testid="stSpinner"] p { color: var(--cian) !important; }

        @media (prefers-reduced-motion: reduce) {
            .radar::before, .stApp::after, .punto.activo { animation: none; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# ESTADO DE LA SESIÓN
# ═════════════════════════════════════════════════════════════════════════════
def inicializar_estado() -> None:
    st.session_state.setdefault("informe", None)
    st.session_state.setdefault("error", None)


# ═════════════════════════════════════════════════════════════════════════════
# LÓGICA DE ANÁLISIS
# ═════════════════════════════════════════════════════════════════════════════
def codificar_imagen(archivo) -> str:
    """Convierte la imagen subida en un data URL listo para la API."""
    mime = archivo.type or "image/jpeg"
    b64 = base64.b64encode(archivo.getvalue()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def construir_prompt(contexto: str) -> str:
    prompt = PROMPT_BASE
    if contexto:
        prompt += f"\n\nContexto adicional del usuario:\n{contexto}"
    return prompt


def transmitir_analisis(api_key: str, prompt: str, data_url: str):
    """Envía la imagen al modelo y devuelve el texto por fragmentos."""
    client = OpenAI(api_key=api_key)
    mensajes = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]
    flujo = client.chat.completions.create(
        model=MODELO,
        messages=mensajes,
        max_tokens=MAX_TOKENS,
        stream=True,
    )
    for fragmento in flujo:
        if not fragmento.choices:
            continue
        texto = fragmento.choices[0].delta.content
        if texto:
            yield texto


# ═════════════════════════════════════════════════════════════════════════════
# COMPONENTES DE INTERFAZ
# ═════════════════════════════════════════════════════════════════════════════
def render_sidebar() -> str:
    """Dibuja la barra lateral y devuelve la clave de API."""
    with st.sidebar:
        st.subheader("Credenciales")
        api_key = st.text_input(
            "Clave de OpenAI",
            type="password",
            placeholder="sk-…",
            help="Se usa solo para esta consulta y no se guarda en disco.",
        )
        st.caption(f"Modelo de análisis: {MODELO}")
    return api_key.strip()


def render_encabezado(api_key: str) -> None:
    st.markdown(
        """
        <div class="encabezado">
            <div class="radar"></div>
            <div>
                <h1 class="titulo">Centro de comando</h1>
                <div class="subtitulo">Reconocimiento de imagen con inteligencia artificial</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    clase, texto = ("activo", "Clave lista") if api_key else ("", "Falta la clave")
    st.markdown(
        f"""
        <div class="enlace">
            <span class="punto {clase}"></span>
            <span>{MODELO}</span>
            <span class="estado">{texto}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_carga():
    """Panel de carga de imagen. Devuelve el archivo subido (o None)."""
    st.subheader("Carga de imagen")
    archivo = st.file_uploader(
        "Sube una imagen para analizar",
        type=TIPOS_IMAGEN,
        label_visibility="collapsed",
    )
    if archivo:
        with st.expander("Vista previa", expanded=True):
            st.image(archivo, caption=archivo.name, use_container_width=True)
    return archivo


def render_consulta() -> str:
    """Panel de consulta opcional. Devuelve el contexto escrito."""
    st.subheader("Consulta")
    quiere_detalle = st.toggle("Preguntar algo específico sobre la imagen", value=False)
    if not quiere_detalle:
        return ""
    return st.text_area(
        "Contexto o pregunta",
        placeholder="Por ejemplo: ¿qué objetos hay sobre la mesa?",
    ).strip()


def render_estado_vacio() -> None:
    st.markdown(
        """
        <div class="vacio">
            <strong>Sin informe</strong>
            Sube una imagen y pulsa «Iniciar análisis» para recibir la descripción.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_falla(mensaje: str) -> None:
    st.markdown(
        f"""
        <div class="falla">
            <strong>No se pudo completar el análisis</strong>
            {escape(mensaje)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def ejecutar_analisis(api_key: str, archivo, contexto: str) -> None:
    """Valida, lanza el análisis y guarda el resultado en la sesión."""
    if not api_key:
        st.warning("Ingresa tu clave de OpenAI en la barra lateral.")
        return
    if archivo is None:
        st.warning("Sube una imagen para analizar.")
        return

    st.session_state.informe = None
    st.session_state.error = None

    st.subheader("Informe de análisis")
    with st.container(border=True):
        espacio = st.empty()
        texto = ""
        try:
            with st.spinner("Analizando imagen…"):
                prompt = construir_prompt(contexto)
                for fragmento in transmitir_analisis(
                    api_key, prompt, codificar_imagen(archivo)
                ):
                    texto += fragmento
                    espacio.markdown(texto + "▌")
            espacio.markdown(texto)
            st.session_state.informe = texto
        except Exception as e:
            espacio.empty()
            st.session_state.error = str(e)
            render_falla(st.session_state.error)


def render_resultado_guardado() -> None:
    """Muestra el último informe (o error) cuando no se está analizando."""
    st.subheader("Informe de análisis")
    if st.session_state.error:
        render_falla(st.session_state.error)
    elif st.session_state.informe:
        with st.container(border=True):
            st.markdown(st.session_state.informe)
    else:
        render_estado_vacio()


# ═════════════════════════════════════════════════════════════════════════════
# FLUJO PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════
def main() -> None:
    configurar_pagina()
    inyectar_estilos()
    inicializar_estado()

    api_key = render_sidebar()
    render_encabezado(api_key)
    st.write("")

    archivo = render_carga()
    contexto = render_consulta()
    st.write("")

    analizar = st.button("Iniciar análisis", use_container_width=True, type="primary")
    st.write("")

    if analizar:
        ejecutar_analisis(api_key, archivo, contexto)
    else:
        render_resultado_guardado()


if __name__ == "__main__":
    main()
