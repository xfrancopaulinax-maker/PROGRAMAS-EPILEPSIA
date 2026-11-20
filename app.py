import datetime
import random
import time
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ==========================================
# CONFIGURACIÓN GENERAL DE LA APLICACIÓN
# ==========================================
st.set_page_config(
    page_title="Programa de Rehabilitación Cognitiva y Adherencia",
    page_icon="🧠",
    layout="wide",
)

# Significado práctico de fichas (Opción 2 - uso exclusivamente simulado)[cite: 1, 14]
FICHAS_OPCIONES = {
    "Azul — Rutina / toma simulada normal": "Azul (Rutina / toma normal)",
    "Verde — Sin ayuda o tras pausa/regulación": "Verde (Sin ayuda / tras pausa)",
    "Naranja — Tras interrupción o con apoyo/pista": "Naranja (Interrupción / con apoyo)",
    "Sin ficha": "Sin ficha",
}

# Inicializar estado de sesión
if "registros" not in st.session_state:
  st.session_state.registros = []
if "alarma_activa" not in st.session_state:
  st.session_state.alarma_activa = False
if "inicio_alarma" not in st.session_state:
  st.session_state.inicio_alarma = None
if "conteo_brujula" not in st.session_state:
  st.session_state.conteo_brujula = 0
if "matriz_regla" not in st.session_state:
  st.session_state.matriz_regla = (
      "Bloque 1: Tachar figuras geométricas por COLOR (ej. Azules/Verdes)"
  )  #[cite: 5, 29]
if "matriz_items" not in st.session_state:
  elementos = [
      "🔵",
      "🔴",
      "🟢",
      "🔺",
      "🟥",
      "🟩",
      "7",
      "4",
      "9",
      "2",
      "5",
      "8",
      "🔵",
      "🟢",
      "🔺",
      "🟥",
      "3",
      "6",
      "1",
      "8",
      "🟢",
      "🔵",
      "5",
      "9",
  ]
  st.session_state.matriz_items = elementos
if "sonar_alarma" not in st.session_state:
  st.session_state.sonar_alarma = False
if "sonar_senal" not in st.session_state:
  st.session_state.sonar_senal = False
if "secuencia_digital" not in st.session_state:
  st.session_state.secuencia_digital = []


def reproducir_tono(frecuencia=880, duracion_seg=0.45, repeticiones=2):
  """Genera un sonido de alarma o señal directamente en el navegador."""
  codigo_audio = f"""
    <script>
    (function() {{
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        const ctx = new AudioCtx();
        for (let i = 0; i < {repeticiones}; i++) {{
            const startTime = ctx.currentTime + i * ({duracion_seg} + 0.15);
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.setValueAtTime({frecuencia}, startTime);
            gain.gain.setValueAtTime(0.25, startTime);
            gain.gain.exponentialRampToValueAtTime(0.001, startTime + {duracion_seg});
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(startTime);
            osc.stop(startTime + {duracion_seg});
        }}
    }})();
    </script>
    """
  components.html(codigo_audio, height=0)


def registrar_evento(sesion_o_modulo, actividad, detalle, bateria_actual):
  hora = datetime.datetime.now().strftime("%H:%M:%S")
  st.session_state.registros.append({
      "Hora": hora,
      "Sesión / Módulo": sesion_o_modulo,
      "Actividad": actividad,
      "Detalle / Resultado": detalle,
      "Batería Mental": f"{bateria_actual}/10",
  })


def mostrar_tarjeta_registro(bateria_actual, ubicacion_key="sidebar"):
  """Ficha visual para registrar ficha, hora, señal y comprobación simulada."""  #[cite: 1, 15, 16]
  with st.container(border=True):
    st.markdown("### 🗂️ Tarjeta de Registro")
    st.caption(
        "🔵 Azul: rutina/toma normal | 🟢 Verde: sin ayuda o tras pausa |"
        " 🟠 Naranja: interrupción o con apoyo *(simulación)*"
    )  #[cite: 1, 14]

    c1, c2 = st.columns(2)
    with c1:
      hora_ficha = st.text_input(
          "Hora registrada:",
          value=datetime.datetime.now().strftime("%H:%M"),
          key=f"hora_ficha_{ubicacion_key}",
      )
    with c2:
      etiqueta_ficha = st.selectbox(
          "Ficha:",
          list(FICHAS_OPCIONES.keys()),
          key=f"color_ficha_{ubicacion_key}",
      )
      color_ficha = FICHAS_OPCIONES[etiqueta_ficha]

    senal_ficha = st.selectbox(
        "Señal o actividad:",
        [
            "Alarma ficticia",
            "Misión «brújula»",
            "Interrupción de tarea",
            "Rutina / agenda",
        ],
        key=f"senal_ficha_{ubicacion_key}",
    )

    verificado = st.checkbox(
        "Verifiqué la indicación y registré la toma/acción simulada",
        key=f"verificado_{ubicacion_key}",
    )
    observacion = st.text_input(
        "Nota / apoyo requerido:",
        placeholder="Ej. Sin ayuda / con pista",
        key=f"obs_ficha_{ubicacion_key}",
    )

    if st.button(
        "➕ Guardar Tarjeta",
        key=f"btn_guardar_ficha_{ubicacion_key}",
        use_container_width=True,
    ):
      registrar_evento(
          "Tarjeta de Registro",
          f"Ficha {color_ficha} ({senal_ficha})",
          (
              f"Hora: {hora_ficha} | Verificado: {verificado} | Nota:"
              f" {observacion}"
          ),
          bateria_actual,
      )
      st.success("Tarjeta guardada en la bitácora.")


# Disparar sonidos programados
if st.session_state.sonar_alarma:
  reproducir_tono(frecuencia=920, duracion_seg=0.35, repeticiones=3)
  st.session_state.sonar_alarma = False

if st.session_state.sonar_senal:
  reproducir_tono(frecuencia=620, duracion_seg=0.25, repeticiones=1)
  st.session_state.sonar_senal = False


# ==========================================
# ENCABEZADO Y PANEL TRANSVERSAL
# ==========================================
st.title("🧠 Programa de Entrenamiento Cognitivo y Adherencia (Sesiones 1–12)")  #[cite: 11, 41]
st.caption(
    "Actividad exclusivamente simulada con fines psicoeducativos y de"
    " entrenamiento funcional. No evalúa ni modifica dosis reales."
)  #[cite: 1, 11, 14]

col1, col2, col3 = st.columns([2.2, 1, 1.2])

with col1:
  bateria = st.slider(
      "🔋 Batería Mental / Termómetro de Fatiga (0 = Sin fatiga | 10 ="
      " Agotamiento extremo)",
      min_value=0,
      max_value=10,
      value=5,
  )  #[cite: 2, 18]
  if bateria < 4:
    st.warning(
        "📉 **Batería < 4 / Señales de fatiga:** Reducir demanda de estímulos,"
        " priorizar precisión y considerar pausa o apoyo."
    )  #[cite: 2, 18, 23]
  elif bateria <= 6:
    st.caption(
        "🟡 **Fatiga moderada:** Monitorear señales corporales/mentales y"
        " administrar pausas."
    )  #[cite: 18, 19]
  else:
    st.caption(
        "🟢 **Energía adecuada:** Mantener ritmo pausado y estrategias de"
        " organización."
    )  #[cite: 21, 23]

with col2:
  st.write("")
  if st.button("🔔 Activar Alarma Ficticia", use_container_width=True):
    st.session_state.alarma_activa = True
    st.session_state.sonar_alarma = True
    st.session_state.inicio_alarma = time.time()
    registrar_evento(
        "Transversal",
        "Alarma ficticia",
        "Alarma activada con señal sonora",
        bateria,
    )
    st.rerun()

with col3:
  st.write("")
  if st.session_state.alarma_activa:
    if st.button(
        "✅ Completar Cadena y Retomar",
        type="primary",
        use_container_width=True,
    ):
      tiempo_reaccion = round(time.time() - st.session_state.inicio_alarma, 1)
      st.session_state.alarma_activa = False
      registrar_evento(
          "Transversal",
          "Cadena de adherencia completada",
          f"Tiempo de respuesta: {tiempo_reaccion} seg",
          bateria,
      )
      st.toast(f"Cadena registrada en {tiempo_reaccion}s. ¡Retoma tu tarea!")
      st.rerun()

if st.session_state.alarma_activa:
  st.error(
      "🚨 **¡ALARMA FICTICIA ACTIVA!**\n\n"
      "1. Detén la actividad y marca dónde te quedaste (*Miro → Señalo →"
      " Compruebo*).\n"
      "2. Consulta la tarjeta de indicación simulada.\n"
      "3. Toma la ficha representativa y anota el marcaje en la bitácora.\n"
      "4. Pulsa *'Completar Cadena y Retomar'* para volver a la tarea."
  )  #[cite: 22, 33]

st.divider()

# ==========================================
# MENÚ LATERAL DE MÓDULOS Y TARJETA
# ==========================================
st.sidebar.header("📋 Módulos del Programa")
modulo = st.sidebar.radio(
    "Selecciona el módulo:",
    [
        "1. Atención, Señales y Rutina (S1, S2, S7)",
        "2. Fatiga y Autorregulación (S3, S11)",
        "3. Memoria de Trabajo y Ejecutivas (S4, S5, S6)",
        "4. Memoria Episódica y Comunicación (S8, S9)",
        "5. Circuito Integrador Final (S10, S12)",
        "📊 Bitácora y Descarga de Resultados",
    ],
)

st.sidebar.divider()
mostrar_tarjeta_registro(bateria, ubicacion_key="sidebar")


# ==========================================
# MÓDULO 1: ATENCIÓN, SEÑALES Y RUTINA
# ==========================================
if modulo == "1. Atención, Señales y Rutina (S1, S2, S7)":
  tab1, tab2, tab3 = st.tabs([
      "🚦 S1: Semáforo, Estrategias y Rutina",
      "🧭 S2: Misión del Explorador",
      "🔄 S7: Matrices de Alternancia",
  ])

  # --- SESIÓN 1 ---
  with tab1:
    st.subheader("Sesión 1: Mi rutina bajo la lupa")  #[cite: 11]
    st.caption(
        "Las clasificaciones no son correctas o incorrectas; reflejan la"
        " experiencia propia de la persona."
    )  #[cite: 1, 11]

    situaciones_s1 = [
        "Dormir bien toda la noche",
        "Sentir fatiga o cansancio acumulado",
        "Estar ocupado o en llamada cuando suena la alarma",
        "Tener recordatorios visibles o bitácora a la mano",
        "Experimentar estrés o prisa en la mañana",
        "Contar con un apoyo familiar respetuoso",
    ]
    clasif_s1 = {}
    justif_s1 = {}
    for i, sit in enumerate(situaciones_s1):
      c_a, c_b = st.columns([1.2, 2])
      with c_a:
        clasif_s1[sit] = st.selectbox(
            sit,
            [
                "Sin clasificar",
                "🟢 Verde (Me ayuda en mi rutina)",
                "🟡 Amarillo (Prestar atención especial)",
                "🔴 Rojo (Dificulta o interfiere)",
            ],
            key=f"s1_sit_{i}",
        )  #[cite: 12]
      with c_b:
        justif_s1[sit] = st.text_input(
            f"Justificación / experiencia similar ({sit}):", key=f"s1_just_{i}"
        )  #[cite: 12]

    st.markdown("#### Tarjetas de Estrategias Compensatorias")  #[cite: 12]
    herramientas_uso = st.multiselect(
        "¿Qué herramientas utiliza actualmente? (Alarma, Agenda, Registro,"
        " Rutina):",
        ["Alarma", "Agenda", "Registro", "Rutina"],
    )  #[cite: 12]
    que_hace_ocupado = st.text_input(
        "¿Qué hace si está ocupado al sonar una alarma?"
    )  #[cite: 13]
    como_verifica = st.text_input(
        "¿Cómo verifica si ya realizó una toma o pendiente?"
    )  #[cite: 13]

    st.markdown("#### Ordenar los 4 pasos de ejecución segura")  #[cite: 13]
    pasos_s1 = st.multiselect(
        "Selecciona en orden (1 a 4):",
        [
            "Recibir el recordatorio (alarma/nota)",
            "Revisar la indicación simulada",
            "Realizar la actividad o toma simulada",
            "Comprobar y registrar el cumplimiento en la bitácora",
        ],
    )  #[cite: 13]
    apoyo_semana_s1 = st.text_input(
        "Dificultad detectada y apoyo útil para mantener en la semana:"
    )  #[cite: 13, 14]

    if st.button("Guardar Sesión 1"):
      orden_ok = pasos_s1 == [
          "Recibir el recordatorio (alarma/nota)",
          "Revisar la indicación simulada",
          "Realizar la actividad o toma simulada",
          "Comprobar y registrar el cumplimiento en la bitácora",
      ]  #[cite: 13]
      registrar_evento(
          "Sesión 1",
          "Rutina, Estrategias y Pasos",
          (
              f"Herramientas: {', '.join(herramientas_uso)} | Pasos en orden:"
              f" {orden_ok} | Apoyo: {apoyo_semana_s1}"
          ),
          bateria,
      )
      st.success("Sesión 1 registrada.")

  # --- SESIÓN 2 ---
  with tab2:
    st.subheader(
        "Sesión 2: La misión del explorador — Escucha, presiona y registra"
    )  #[cite: 14]
    st.info(
        "**Relato guía (4 apariciones de «brújula»):** «Al iniciar la"
        " caminata, el explorador guardó su **brújula** (ficha **Azul**, **08:15**)."
        " A media mañana revisó el sendero y consultó su **brújula** (ficha"
        " **Verde**, **10:40**). Tras una pausa junto al río, volvió a mirar"
        " su **brújula** (ficha **Naranja**, **13:10**). Al caer la tarde,"
        " verificó el rumbo final con su **brújula** (ficha **Azul**, **16:50**).»"
    )  #[cite: 15, 16]

    c1, c2, c3 = st.columns(3)
    with c1:
      if st.button(
          "🔘 ¡ESCUCHÉ «BRÚJULA»!", type="primary", use_container_width=True
      ):
        st.session_state.conteo_brujula += 1
        registrar_evento(
            "Sesión 2",
            "Detección «brújula»",
            f"Presión #{st.session_state.conteo_brujula}",
            bateria,
        )
    with c2:
      st.metric("Presiones registradas", st.session_state.conteo_brujula)
    with c3:
      if st.button("Reiniciar contador"):
        st.session_state.conteo_brujula = 0
        st.rerun()

    st.markdown("#### Cronograma Ficticio (4 registros)")  #[cite: 15, 16]
    cronograma_df = pd.DataFrame([
        {"Evento": "1", "Hora anotada": "", "Ficha anotada": "Azul"},
        {"Evento": "2", "Hora anotada": "", "Ficha anotada": "Verde"},
        {"Evento": "3", "Hora anotada": "", "Ficha anotada": "Naranja"},
        {"Evento": "4", "Hora anotada": "", "Ficha anotada": "Azul"},
    ])
    cronograma_editado = st.data_editor(
        cronograma_df, num_rows="fixed", use_container_width=True
    )

    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
      omisiones_s2 = st.number_input("Omisiones:", min_value=0, max_value=4, step=1)  #[cite: 14, 16]
    with col_e2:
      falsas_s2 = st.number_input("Falsas alarmas:", min_value=0, step=1)  #[cite: 14, 16]
    with col_e3:
      estrategia_s2 = st.text_input("Estrategia para no distraerse:")  #[cite: 16]

    if st.button("Guardar Sesión 2"):
      registrar_evento(
          "Sesión 2",
          "Misión del Explorador y Cronograma",
          (
              f"Presiones: {st.session_state.conteo_brujula}/4 | Omisiones:"
              f" {omisiones_s2} | Falsas: {falsas_s2} | Estrategia:"
              f" {estrategia_s2}"
          ),
          bateria,
      )
      st.success("Sesión 2 guardada.")

    st.write("")
    mostrar_tarjeta_registro(bateria, ubicacion_key="sesion2")

  # --- SESIÓN 7 ---
  with tab3:
    st.subheader("Sesión 7: Mi atención en acción — Matrices de alternancia")  #[cite: 27]
    st.write(
        "Prioriza precisión sobre velocidad. Al cambiar de regla sonará una"
        " señal breve."
    )  #[cite: 28, 29]

    reglas_s7 = [
        (
            "Bloque 1: Tachar figuras geométricas por COLOR (ej. Azules/Verdes)"
        ),
        "Bloque 2: Cambiar criterio a NÚMEROS IMPARES (1, 3, 5, 7, 9)",
        "Bloque 3: Tachar CUADRADOS o TRIÁNGULOS (🟥, 🟩, 🔺)",
        (
            "Interrupción / Reorientación: Aplicar 'Miro → Señalo → Compruebo'"
            " tras distracción"
        ),
    ]  #[cite: 29]

    col_r1, col_r2 = st.columns([2.2, 1])
    with col_r1:
      st.warning(f"📌 **REGLA ACTUAL:** {st.session_state.matriz_regla}")
    with col_r2:
      if st.button("🔊 Cambiar Regla (Señal)"):
        otras = [r for r in reglas_s7 if r != st.session_state.matriz_regla]
        st.session_state.matriz_regla = random.choice(otras)
        st.session_state.sonar_senal = True
        st.rerun()

    marcados = []
    grid = st.columns(6)
    for idx, item in enumerate(st.session_state.matriz_items):
      with grid[idx % 6]:
        if st.checkbox(f"{item}", key=f"s7_grid_{idx}"):
          marcados.append(item)

    col_p1, col_p2 = st.columns(2)
    with col_p1:
      persev_s7 = st.number_input("Errores de perseveración:", min_value=0, step=1)  #[cite: 28, 29]
    with col_p2:
      retoma_s7 = st.selectbox(
          "Reorientación tras interrupción ('Miro → Señalo → Compruebo'):",
          ["Autónoma", "Con apoyo", "No requerida"],
      )  #[cite: 29]

    if st.button("Guardar Sesión 7"):
      registrar_evento(
          "Sesión 7",
          "Matrices de Alternancia",
          (
              f"Marcados: {len(marcados)} | Perseveraciones: {persev_s7} |"
              f" Reorientación: {retoma_s7}"
          ),
          bateria,
      )
      st.success("Sesión 7 guardada.")


# ==========================================
# MÓDULO 2: FATIGA Y AUTORREGULACIÓN
# ==========================================
elif modulo == "2. Fatiga y Autorregulación (S3, S11)":
  tab1, tab2 = st.tabs([
      "🔋 S3: Termómetro de Fatiga y Pausa",
      "🧘 S11: Pausa, Pienso y Sigo",
  ])

  with tab1:
    st.subheader("Sesión 3: Mi batería mental y pausa estratégica")  #[cite: 16, 17]
    senales_s3 = st.multiselect(
        "Señales cuando la batería baja de 4 (somáticas o mentales):",
        [
            "Pesadez palpebral / vista cansada",
            "Enlentecimiento del pensamiento / lectura lenta",
            "Tensión cefálica o cervical",
            "Irritabilidad",
            "Distracción fácil",
        ],
    )  #[cite: 17, 18]

    c_a, c_d = st.columns(2)
    with c_a:
      st.markdown("#### Lámina A (Antes de pausa de 3 min)")  #[cite: 18]
      fat_a = st.slider("Batería antes (0-10):", 0, 10, 5, key="s3_fa")
      ac_a = st.number_input("Aciertos Lámina A:", min_value=0, step=1, key="s3_aa")
    with c_d:
      st.markdown("#### Lámina B (Después de pausa de 3 min)")  #[cite: 18, 19]
      fat_d = st.slider("Batería después (0-10):", 0, 10, 3, key="s3_fd")
      ac_d = st.number_input("Aciertos Lámina B:", min_value=0, step=1, key="s3_ad")

    semaforo_fatiga = st.selectbox(
        "Tarjeta del Semáforo de Autorregulación seleccionada:",
        [
            "🟢 Verde: Continuar la actividad",
            "🟡 Amarillo: Pausa corta / Reducir exigencia del estímulo",
            "🔴 Rojo: Detener la tarea y solicitar apoyo externo",
        ],
    )  #[cite: 19]

    if st.button("Guardar Sesión 3"):
      registrar_evento(
          "Sesión 3",
          "Batería Mental y Pausa",
          (
              f"Antes: {ac_a} (Fat {fat_a}) -> Después: {ac_d} (Fat {fat_d}) |"
              f" Semáforo: {semaforo_fatiga} | Señales: {', '.join(senales_s3)}"
          ),
          bateria,
      )
      st.success("Sesión 3 guardada.")

  with tab2:
    st.subheader("Sesión 11: Pausa, pienso y sigo")  #[cite: 38]
    st.write("Secuencia cognitiva: **Pausa → Emoción → Prioridad → Respuesta**")  #[cite: 39]

    escena_s11 = st.selectbox(
        "Imprevisto o recordatorio simulado:",
        [
            "Perder temporalmente un objeto o nota",
            "Recibir un recordatorio imprevisto",
            "Sentir molestia o prisa ante una interrupción",
        ],
    )  #[cite: 38, 39]
    col_1, col_2 = st.columns(2)
    with col_1:
      emocion_s11 = st.selectbox(
          "Emoción identificada (sin juzgar):",
          ["Frustración", "Molestia / Irritabilidad", "Ansiedad", "Calma"],
      )  #[cite: 39]
      prioridad_s11 = st.text_input("Prioridad en este momento:")  #[cite: 39]
    with col_2:
      frase_s11 = st.text_area(
          "Frase de contención asertiva:",
          value="Gracias, dame un momento para comprobarlo en mi registro.",
      )  #[cite: 39]

    acuerdo_familiar = st.text_area(
        "Acuerdo con familiar/esposa para recordatorios neutrales (sin"
        " invalidación):"
    )  #[cite: 38, 39]

    if st.button("Guardar Sesión 11"):
      registrar_evento(
          "Sesión 11",
          "Autorregulación y Acuerdos",
          (
              f"Escena: {escena_s11} | Emoción: {emocion_s11} | Frase:"
              f" {frase_s11} | Acuerdo: {acuerdo_familiar}"
          ),
          bateria,
      )
      st.success("Sesión 11 guardada.")


# ==========================================
# MÓDULO 3: MEMORIA DE TRABAJO Y EJECUTIVAS
# ==========================================
elif modulo == "3. Memoria de Trabajo y Ejecutivas (S4, S5, S6)":
  tab1, tab2, tab3 = st.tabs([
      "🔐 S4: Escape de Instrucciones",
      "🛒 S5: Memoria de Trabajo",
      "🧩 S6: Soluciono Problemas",
  ])

  with tab1:
    st.subheader("Sesión 4: Escape de instrucciones")  #[cite: 19, 44]
    st.caption(
        "Agrupación: *Preparar → Hacer → Revisar*. No subir a 4 pasos si hay"
        " errores por fatiga."
    )  #[cite: 20, 21, 44]

    consigna_elegida = st.radio(
        "Consigna a practicar:",
        [
            (
                "3 pasos (Nivel 1): Tomar Tarjeta Azul → Colocar bajo Sobre 2 →"
                " Señalar Círculo Verde"
            ),
            (
                "4 pasos (si precisión es alta y batería > 5): Abrir Sobre 1 →"
                " Tomar Ficha Verde → Poner junto a Reloj → Marcar X"
            ),
        ],
        key="consigna_digital_s4",
    )  #[cite: 21, 44]

    st.markdown("### 🎮 Simulador Digital de Escape (3 o 4 pasos)")
    st.write(
        "Haz clic en los sobres, fichas y objetivos en el orden de la"
        " consigna:"
    )  #[cite: 21, 22]

    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    elementos_s4 = [
        ("Sobre 1", col_d1),
        ("Sobre 2", col_d2),
        ("Tarjeta Azul", col_d3),
        ("Ficha Verde", col_d4),
    ]
    for nombre, columna in elementos_s4:
      with columna:
        if st.button(f"📦 {nombre}", key=f"btn_s4_{nombre}"):
          st.session_state.secuencia_digital.append(nombre)

    col_o1, col_o2, col_o3 = st.columns(3)
    objetivos_s4 = [
        ("Círculo Verde", col_o1),
        ("Reloj", col_o2),
        ("Marca X", col_o3),
    ]
    for obj, columna in objetivos_s4:
      with columna:
        if st.button(f"🎯 {obj}", key=f"btn_s4_{obj}"):
          st.session_state.secuencia_digital.append(obj)

    st.info(
        "**Secuencia marcada hasta ahora (Miro → Señalo → Compruebo):** "
        + (
            " → ".join(st.session_state.secuencia_digital)
            if st.session_state.secuencia_digital
            else "Ningún paso aún"
        )
    )  #[cite: 22]

    c_b1, c_b2 = st.columns(2)
    with c_b1:
      if st.button("🔄 Limpiar secuencia"):
        st.session_state.secuencia_digital = []
        st.rerun()
    with c_b2:
      if st.button("✅ Verificar secuencia digital"):
        if consigna_elegida.startswith("3 pasos"):
          esperada = ["Tarjeta Azul", "Sobre 2", "Círculo Verde"]
        else:
          esperada = ["Sobre 1", "Ficha Verde", "Reloj", "Marca X"]

        aciertos_orden = sum(
            1
            for a, b in zip(st.session_state.secuencia_digital, esperada)
            if a == b
        )
        registrar_evento(
            "Sesión 4",
            "Escape Digital",
            (
                f"Marcados: {st.session_state.secuencia_digital} |"
                f" Coincidencias en orden:"
                f" {aciertos_orden}/{len(esperada)}"
            ),
            bateria,
        )
        st.success(
            f"Coincidencias en posición: {aciertos_orden} de {len(esperada)}."
        )

    st.markdown("#### Observación clínica de la ejecución")  #[cite: 19, 20, 22]
    col_a, col_b, col_c = st.columns(3)
    with col_a:
      pasos_ok_s4 = st.number_input("Pasos correctos:", 0, 4, 3)  #[cite: 19, 20]
    with col_b:
      rep_verbal = st.selectbox(
          "Repetición verbal previa:", ["Autónoma", "Con modelado", "No realizó"]
      )  #[cite: 19, 21]
    with col_c:
      retoma_s4 = st.selectbox(
          "Retoma tras interrupción ('Miro → Señalo → Compruebo'):",
          ["Retomó exacto sin reiniciar", "Con pista", "Reinició"],
      )  #[cite: 19, 22]

    if st.button("Guardar Observación Sesión 4"):
      registrar_evento(
          "Sesión 4",
          "Escape de Instrucciones (Observación)",
          (
              f"Pasos: {pasos_ok_s4} | Repetición: {rep_verbal} | Retoma:"
              f" {retoma_s4}"
          ),
          bateria,
      )
      st.success("Observación de Sesión 4 guardada.")

  with tab2:
    st.subheader("Sesión 5: Mi memoria de trabajo")  #[cite: 22]
    ver_compras = st.checkbox(
        "Mostrar lista de supermercado desordenada", value=True
    )  #[cite: 23]
    if ver_compras:
      st.warning(
          "🛒 **Lista:** Manzana • Detergente • Leche • Plátano • Jabón •"
          " Yogurt"
      )  #[cite: 23]

    c1, c2 = st.columns(2)
    with c1:
      cat_frutas = st.text_input("Categoría Frutas (de memoria):")  #[cite: 23, 24]
      cat_limpieza = st.text_input(
          "Categoría Artículos de limpieza (de memoria):"
      )  #[cite: 23, 24]
    with c2:
      interferente_s5 = st.text_input(
          "Tarea interferente breve (ej. ¿Qué día de la semana es o cómo está"
          " el clima?):"
      )  #[cite: 24]
      agenda_recordada = st.text_input(
          "Tareas de agenda simulada recordadas tras interferencia:"
      )  #[cite: 24]

    tecnica_s5 = st.text_input(
        "¿Qué técnica mental usó para retener la información?"
    )  #[cite: 24]

    if st.button("Guardar Sesión 5"):
      registrar_evento(
          "Sesión 5",
          "Memoria de Trabajo Funcional",
          (
              f"Frutas: {cat_frutas} | Limpieza: {cat_limpieza} | Agenda:"
              f" {agenda_recordada} | Técnica: {tecnica_s5}"
          ),
          bateria,
      )
      st.success("Sesión 5 guardada.")

  with tab3:
    st.subheader("Sesión 6: Soluciono problemas")  #[cite: 25]
    caso_s6 = st.selectbox(
        "Situación problemática cotidiana:",
        [
            (
                "Olvidaste llevar un documento que tenías que entregar a las"
                " 10:00 AM"
            ),
            (
                "Suena la alarma de actividad/medicamento durante una reunión"
                " importante"
            ),
            "Otro imprevisto referido por el consultante",
        ],
    )  #[cite: 26]
    p1 = st.text_input("1. ¿Qué está ocurriendo exactamente?")  #[cite: 26]
    p2 = st.text_input(
        "2. ¿Requiere solución inmediata o puede esperar unos minutos?"
    )  #[cite: 26]
    p3 = st.text_input("3. ¿Qué herramientas, notas o apoyos tengo a la mano?")  #[cite: 26]
    alt_s6 = st.text_area("4. 2 o 3 alternativas y elección final:")  #[cite: 26, 27]
    regla_s6 = st.text_input(
        "5. Resumen en regla: Detenerme → Analizar → Decidir:"
    )  #[cite: 27]

    if st.button("Guardar Sesión 6"):
      registrar_evento(
          "Sesión 6",
          "Resolución de Problemas",
          (
              f"Caso: {caso_s6} | Urgencia: {p2} | Elección: {alt_s6} |"
              f" Regla: {regla_s6}"
          ),
          bateria,
      )
      st.success("Sesión 6 guardada.")


# ==========================================
# MÓDULO 4: MEMORIA EPISÓDICA Y COMUNICACIÓN
# ==========================================
elif modulo == "4. Memoria Episódica y Comunicación (S8, S9)":
  tab1, tab2 = st.tabs([
      "📖 S8: Recuerdo lo Importante",
      "💬 S9: Me Comunico Mejor",
  ])

  with tab1:
    st.subheader("Sesión 8: Recuerdo lo importante")  #[cite: 29]
    ver_relato_s8 = st.checkbox(
        "Mostrar relato episódico (leer 2 veces con visualización y"
        " categorización)",
        value=True,
    )  #[cite: 30, 31]
    if ver_relato_s8:
      st.info(
          "**Relato:** «El **martes a las 10:30 AM**, se acudió a la"
          " **farmacia del centro** para recoger una **libreta azul** de"
          " apuntes y después se tomó un café en la **plaza principal** antes"
          " de volver a casa a la **1:00 PM**.»"
      )  #[cite: 31]

    libre_s8 = st.text_area(
        "Recuerdo libre (tras demora de 5 min con actividad neutra):"
    )  #[cite: 31]
    c1, c2, c3 = st.columns(3)
    with c1:
      cl1 = st.selectbox(
          "Clave 1 (Día/Hora):",
          ["...", "Martes 10:30 AM", "Viernes 8:00 AM", "Domingo 6:00 PM"],
      )  #[cite: 31]
    with c2:
      cl2 = st.selectbox(
          "Clave 2 (Objeto):",
          ["...", "Libreta azul", "Paraguas gris", "Agenda roja"],
      )  #[cite: 31]
    with c3:
      cl3 = st.selectbox(
          "Clave 3 (Lugar café):",
          ["...", "Plaza principal", "Biblioteca", "Estación"],
      )  #[cite: 31]

    if st.button("Guardar Sesión 8"):
      puntos_s8 = sum([
          cl1 == "Martes 10:30 AM",
          cl2 == "Libreta azul",
          cl3 == "Plaza principal",
      ])
      registrar_evento(
          "Sesión 8",
          "Memoria Episódica",
          f"Claves: {puntos_s8}/3 | Libre: {libre_s8}",
          bateria,
      )
      st.success("Sesión 8 guardada.")

  with tab2:
    st.subheader("Sesión 9: Me comunico mejor")  #[cite: 31]
    st.write(
        "Estructura asertiva: **Lo que pasa + Cómo me siento + Lo que propongo**"
    )  #[cite: 32, 33]
    a1, a2, a3 = st.columns(3)
    with a1:
      lo_que_pasa = st.text_input(
          "Lo que pasa:",
          value="Cuando me repiten varias veces si ya cumplí la tarea",
      )
    with a2:
      como_me_siento = st.text_input(
          "Cómo me siento:", value="me siento presionado"
      )
    with a3:
      lo_que_propongo = st.text_input(
          "Lo que propongo:",
          value="prefiero que revisemos juntos el registro al final de la tarde.",
      )

    st.success(f"Frase construida: «{lo_que_pasa}, {como_me_siento}; {lo_que_propongo}»")

    roleplay_s9 = st.selectbox(
        "Escena de Role-Play practicada:",
        [
            "1. Pregunta en tono molesto sobre la toma/tarea",
            "2. Cansancio ante solicitud de reunión familiar esa misma tarde",
            "3. Olvido de lo que se iba a decir en una conversación",
        ],
    )  #[cite: 34]
    retro_s9 = st.text_input(
        "Retroalimentación (cómo se sintió, acierto y punto de mejora):"
    )  #[cite: 34]

    if st.button("Guardar Sesión 9"):
      registrar_evento(
          "Sesión 9",
          "Comunicación Asertiva y Role-Play",
          f"Escena: {roleplay_s9} | Retro: {retro_s9}",
          bateria,
      )
      st.success("Sesión 9 guardada.")


# ==========================================
# MÓDULO 5: CIRCUITO INTEGRADOR FINAL
# ==========================================
elif modulo == "5. Circuito Integrador Final (S10, S12)":
  st.subheader("🏆 Sesiones 10 y 12: Simulación de Día Completo y Circuito Final")  #[cite: 35, 41, 43]
  st.caption(
      "Ajusta la dificultad a la tolerancia real; interviene con pista solo si"
      " hay bloqueo > 1 min (en Sesión 12 la alarma es sin guía)."
  )  #[cite: 7, 35, 41, 43]

  st.markdown("### Simulación en 4 Momentos (Sesión 10)")  #[cite: 36, 43]
  m1, m2 = st.columns(2)
  with m1:
    m_manana = st.checkbox(
        "1. Mañana: Agenda con 3 actividades + horarios/alarmas"
    )  #[cite: 36, 43]
    m_tarde = st.checkbox(
        "3. Tarde: Fatiga simulada 7/10 + regulación + comunicación"
    )  #[cite: 36, 37, 43]
  with m2:
    m_mediodia = st.checkbox(
        "2. Mediodía: Lista/precios con alarma + 'Miro → Señalo → Compruebo'"
    )  #[cite: 36, 43]
    m_noche = st.checkbox(
        "4. Noche: Pastillero para 2 días + hoja de análisis + 3 eventos"
    )  #[cite: 37, 43]

  ajustes_s10 = st.text_input(
      "Revisión y ajustes acordados (ej. horario de alarma o lugar visible):"
  )  #[cite: 37, 43]

  st.divider()
  st.markdown("### Circuito Final Autónomo y Kit Definitivo (Sesión 12)")  #[cite: 41, 43]
  c_s12_1 = st.checkbox(
      "3 pistas en agenda + 4 datos de relato tras demora + 5 pendientes"
      " priorizados + 3 instrucciones"
  )  #[cite: 41, 43]
  c_s12_2 = st.checkbox(
      "Alarma sorpresiva sin guía: cadena completa y retoma exacta 100%"
      " autónoma"
  )  #[cite: 41, 43]
  kit_items = st.multiselect(
      "Elementos organizados en el Kit Definitivo:",
      [
          "Tarjeta de registro",
          "Tarjetas posictales / recordatorio",
          "Claves de memoria",
          "Semáforo de fatiga",
      ],
  )  #[cite: 41]
  pistas_totales = st.number_input(
      "Número total de pistas requeridas:", min_value=0, step=1
  )  #[cite: 35, 41]

  if st.button("Guardar Circuito Integrador", type="primary"):
    logros_s10 = sum([m_manana, m_mediodia, m_tarde, m_noche])
    registrar_evento(
        "Sesiones 10 y 12",
        "Circuito Integrador y Kit",
        (
            f"Momentos S10: {logros_s10}/4 | Pistas: {pistas_totales} |"
            f" Circuito S12 ({c_s12_1}, Alarma sin guía: {c_s12_2}) | Kit:"
            f" {', '.join(kit_items)} | Ajustes: {ajustes_s10}"
        ),
        bateria,
    )
    st.balloons()
    st.success("Circuito integrador registrado.")


# ==========================================
# BITÁCORA Y DESCARGA
# ==========================================
elif modulo == "📊 Bitácora y Descarga de Resultados":
  st.subheader("📊 Bitácora General de Observación y Resultados")

  if len(st.session_state.registros) == 0:
    st.info("Aún no hay registros en esta sesión.")
  else:
    df = pd.DataFrame(st.session_state.registros)
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="⬇️ Descargar Bitácora (CSV / Excel)",
        data=csv,
        file_name=f"bitacora_programa_{datetime.date.today()}.csv",
        mime="text/csv",
        type="primary",
    )