"""
Observatorio de imágenes
------------------------
App de Streamlit que envía una imagen a un modelo de visión de OpenAI y
muestra la descripción en tiempo real. Tema: observatorio astronómico, con
un planeta anillado, órbitas de fondo y paleta inspirada en Neptuno,
Saturno y Marte.

Ejecutar:  streamlit run app_observatorio.py
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
        page_title="Observatorio de imágenes",
        page_icon="🪐",
        layout="centered",
        initial_sidebar_state="expanded",
    )


def inyectar_estilos() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Hanken+Grotesk:wght@400;500;600;700&display=swap');

        :root {
            --noche:     #0D1230;
            --panel:     rgba(23, 31, 72, 0.72);
            --campo:     #11183B;
            --oro:       #E9C46A;
            --oro-claro: #F3DDA3;
            --oro-tenue: rgba(233, 196, 106, 0.30);
            --neptuno:   #5B8DEF;
            --marte:     #F0705A;
            --texto:     #EDE6D6;
            --apagado:   #A3A9C9;
        }

        /* ── Fondo: noche azul + órbitas ────────────── */
        .stApp {
            background:
                radial-gradient(ellipse at 100% 0%, rgba(91, 141, 239, .28), transparent 55%),
                radial-gradient(ellipse at 0% 100%, rgba(233, 196, 106, .10), transparent 50%),
                var(--noche);
            color: var(--texto);
            font-family: 'Hanken Grotesk', sans-serif;
        }
        .stApp::before, .stApp::after {
            content: ""; position: fixed; inset: 0;
            pointer-events: none; z-index: 0;
        }
        /* órbitas concéntricas que nacen de la esquina superior derecha */
        .stApp::before {
            background: repeating-radial-gradient(
                circle at 108% -8%,
                transparent 0 170px,
                rgba(233, 196, 106, .08) 170px 171px);
        }
        /* estrellas dispersas */
        .stApp::after {
            background-image:
                radial-gradient(1px 1px at 30px 50px, #fff, transparent),
                radial-gradient(1.5px 1.5px at 170px 120px, #dfe8ff, transparent),
                radial-gradient(1px 1px at 280px 220px, #fff, transparent);
            background-size: 320px 260px;
            opacity: .4;
        }

        [data-testid="stHeader"] { background: transparent; }
        .block-container {
            position: relative; z-index: 1;
            padding-top: 2.5rem; max-width: 760px;
        }

        /* ── Texto base ─────────────────────────────── */
        .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3,
        [data-testid="stWidgetLabel"] p, summary p {
            color: var(--texto) !important;
            font-family: 'Hanken Grotesk', sans-serif;
            font-size: 1.02rem;
        }
        .stApp h2, .stApp h3 {
            font-family: 'Fraunces', serif !important;
            font-weight: 700 !important;
            font-size: 1.35rem !important;
            letter-spacing: -0.01em;
        }
        [data-testid="stCaptionContainer"] p {
            color: var(--apagado) !important; font-size: .92rem;
        }

        /* ── Encabezado con planeta anillado ────────── */
        .encabezado { display: flex; align-items: center; gap: 1.3rem; }
        .planeta { position: relative; flex: none; width: 92px; height: 92px; }
        .planeta .esfera {
            position: absolute; inset: 20px; border-radius: 50%; z-index: 1;
            background:
                radial-gradient(circle at 30% 26%, rgba(255,255,255,.38), transparent 42%),
                linear-gradient(#E9C46A 0 18%, #C99A4B 18% 32%, #F3DDA3 32% 40%,
                                #B97E3F 40% 58%, #E9C46A 58% 72%, #C99A4B 72% 100%);
            box-shadow: inset -12px -10px 18px rgba(8, 10, 32, .62),
                        0 0 26px rgba(233, 196, 106, .28);
        }
        .planeta .anillo {
            position: absolute; left: 0; right: 0; top: 50%;
            height: 30px; margin-top: -15px; border-radius: 50%;
            border: 3px solid rgba(243, 221, 163, .9);
            box-shadow: inset 0 0 0 5px rgba(233, 196, 106, .18);
            transform: rotate(-18deg);
        }
        .planeta .atras  { z-index: 0; }
        .planeta .frente { z-index: 2; clip-path: inset(50% 0 0 0); }

        .titulo {
            font-family: 'Fraunces', serif; font-weight: 700;
            font-size: 2.15rem; line-height: 1.1; letter-spacing: -0.02em;
            color: var(--texto); margin: 0;
        }
        .subtitulo {
            color: var(--apagado); font-size: 1.08rem; margin: .35rem 0 0 0;
        }

        /* ── Indicador de clave ─────────────────────── */
        .estado-clave {
            display: inline-flex; align-items: center; gap: .6rem;
            margin: 1.4rem 0 .4rem 0; padding: .35rem 1rem;
            background: var(--panel); border: 1px solid var(--oro-tenue);
            border-radius: 999px; font-weight: 600; color: var(--texto);
        }
        .estado-clave .detalle { color: var(--apagado); font-weight: 500; }
        .punto { width: 9px; height: 9px; border-radius: 50%; background: var(--apagado); }
        .punto.activo { background: var(--oro); box-shadow: 0 0 10px var(--oro); }

        /* ── Carga de imagen ────────────────────────── */
        [data-testid="stFileUploaderDropzone"] {
            background: var(--panel);
            border: 1.5px dashed var(--oro-tenue); border-radius: 18px;
        }
        [data-testid="stFileUploaderDropzone"]:hover { border-color: var(--oro); }
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] span {
            color: var(--apagado) !important;
        }
        [data-testid="stFileUploaderDropzone"] button {
            background: transparent; border: 1px solid var(--oro);
            color: var(--oro); border-radius: 999px;
        }
        /* la vista previa se ve como la mira de un telescopio */
        [data-testid="stImage"] img {
            border: 1px solid var(--oro);
            border-radius: 16px;
            outline: 1px solid var(--oro-tenue);
            outline-offset: 7px;
        }
        [data-testid="stImageCaption"] { color: var(--apagado) !important; }

        /* ── Campos de texto ────────────────────────── */
        [data-baseweb="input"], [data-baseweb="base-input"],
        [data-baseweb="textarea"] {
            background: var(--campo) !important;
            border-color: var(--oro-tenue) !important;
            border-radius: 12px !important;
        }
        [data-baseweb="input"] input, [data-baseweb="base-input"] input,
        [data-baseweb="textarea"] textarea {
            color: var(--texto) !important; background: var(--campo) !important;
            font-family: 'Hanken Grotesk', sans-serif; font-size: 1.02rem;
        }
        [data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within {
            border-color: var(--oro) !important;
            box-shadow: 0 0 0 3px rgba(233, 196, 106, .22);
        }

        /* ── Informe: franja de bandas tipo Júpiter ─── */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(165deg,
                rgba(28, 38, 86, .88), rgba(13, 18, 48, .94));
            border: 1px solid var(--oro-tenue) !important;
            border-radius: 18px !important;
            overflow: hidden;
        }
        [data-testid="stVerticalBlockBorderWrapper"]::before {
            content: ""; display: block; height: 8px;
            background: linear-gradient(#E9C46A 0 25%, #B97E3F 25% 50%,
                                        #F3DDA3 50% 62%, #C99A4B 62% 100%);
        }

        /* ── Sin informe / falla ────────────────────── */
        .vacio, .falla {
            padding: 2rem 1.5rem; text-align: center;
            color: var(--apagado); font-size: 1.05rem;
            background: var(--panel); border: 1.5px dashed var(--oro-tenue);
            border-radius: 18px;
        }
        .vacio strong, .falla strong {
            display: block; margin-bottom: .3rem;
            font-family: 'Fraunces', serif; font-size: 1.2rem; color: var(--texto);
        }
        .falla { border: 1px solid rgba(240, 112, 90, .6);
                 background: rgba(240, 112, 90, .08); }
        .falla strong { color: var(--marte); }

        /* ── Botón principal: oro de Saturno ────────── */
        .stButton > button {
            background: linear-gradient(135deg, #F3DDA3, #E9C46A 55%, #C99A4B);
            border: none; border-radius: 999px; padding: .8rem 1rem;
            box-shadow: 0 6px 22px rgba(233, 196, 106, .28);
            transition: transform .15s ease, box-shadow .15s ease;
        }
        .stButton > button p {
            color: #1A1535 !important;
            font-family: 'Hanken Grotesk', sans-serif;
            font-weight: 700; font-size: 1.08rem; letter-spacing: .01em;
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 28px rgba(233, 196, 106, .42);
        }
        .stButton > button:focus-visible { outline: 3px solid #fff; outline-offset: 3px; }

        /* ── Barra lateral, expanders y avisos ──────── */
        section[data-testid="stSidebar"] {
            background: #0A0E27; border-right: 1px solid var(--oro-tenue);
        }
        [data-testid="stExpander"] {
            background: var(--panel); border: 1px solid var(--oro-tenue);
            border-radius: 14px;
        }
        [data-testid="stAlert"] {
            background: rgba(233, 196, 106, .08);
            border: 1px solid var(--oro-tenue); border-radius: 12px;
        }
        [data-testid="stSpinner"] p { color: var(--oro) !important; }
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
        st.subheader("Acceso")
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
            <div class="planeta">
                <div class="anillo atras"></div>
                <div class="esfera"></div>
                <div class="anillo frente"></div>
            </div>
            <div>
                <h1 class="titulo">Observatorio de imágenes</h1>
                <div class="subtitulo">Apunta a una imagen y recibe una descripción detallada.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    clase, texto = ("activo", "Clave lista") if api_key else ("", "Falta la clave")
    st.markdown(
        f"""
        <div class="estado-clave">
            <span class="punto {clase}"></span>
            <span>{MODELO}</span>
            <span class="detalle">{texto}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_carga():
    """Panel de carga de imagen. Devuelve el archivo subido (o None)."""
    st.subheader("Muestra")
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
    st.subheader("Pregunta")
    quiere_detalle = st.toggle("Hacer una pregunta específica sobre la imagen", value=False)
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
            <strong>Aún no hay observaciones</strong>
            Sube una imagen y pulsa «Observar imagen» para recibir la descripción.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_falla(mensaje: str) -> None:
    st.markdown(
        f"""
        <div class="falla">
            <strong>No se pudo completar la observación</strong>
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

    st.subheader("Observaciones")
    with st.container(border=True):
        espacio = st.empty()
        texto = ""
        try:
            with st.spinner("Observando la imagen…"):
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
    st.subheader("Observaciones")
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

    observar = st.button("Observar imagen", use_container_width=True, type="primary")
    st.write("")

    if observar:
        ejecutar_analisis(api_key, archivo, contexto)
    else:
        render_resultado_guardado()


if __name__ == "__main__":
    main()
