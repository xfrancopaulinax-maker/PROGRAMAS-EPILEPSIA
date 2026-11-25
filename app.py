import datetime
import io
import json
import os
import random
import re
import time
import unicodedata

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# CONFIGURACIÓN GENERAL DE LA APLICACIÓN
# ==========================================
st.set_page_config(
    page_title="Programa de Rehabilitación Cognitiva y Adherencia",
    page_icon="🧠",
    layout="wide",
)

# Significado práctico de fichas (uso exclusivamente simulado)
FICHAS_OPCIONES = {
    "Azul — Rutina / toma simulada normal": "Azul (Rutina / toma normal)",
    "Verde — Sin ayuda o tras pausa/regulación": "Verde (Sin ayuda / tras pausa)",
    "Naranja — Tras interrupción o con apoyo/pista": "Naranja (Interrupción / con apoyo)",
    "Sin ficha": "Sin ficha",
}

# Niveles según la batería mental (1 = muy fatigado, 10 = sin fatiga)
ETIQUETAS_NIVEL = {
    "bajo": (
        "🟠 Batería 1–4 (muy fatigado): hoy trabajaremos en modo SUAVE, con"
        " menos ejercicios y más fáciles."
    ),
    "medio": "🟡 Batería 5–7 (fatiga media): hoy trabajaremos en modo ESTÁNDAR.",
    "alto": (
        "🟢 Batería 8–10 (sin fatiga): hoy trabajaremos en modo RETO, con más"
        " ejercicios y más difíciles."
    ),
}


def _init_estado():
    ahora = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    valores = {
        "registros": [],
        "alarma_activa": False,
        "alarma_sin_guia": False,
        "inicio_alarma": None,
        "sonar_alarma": False,
        "sonar_senal": False,
        "bateria_actual": 5,
        "archivo_resultados": f"resultados_terapeuta/resultados_{ahora}.csv",
    }
    for clave, valor in valores.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


_init_estado()


# ==========================================
# UTILIDADES
# ==========================================
def nivel_de_bateria(b):
    """1-4 muy fatigado (bajo) | 5-7 medio | 8-10 sin fatiga (alto)."""
    if b <= 4:
        return "bajo"
    if b <= 7:
        return "medio"
    return "alto"


def por_nivel(nivel, bajo, medio, alto):
    return {"bajo": bajo, "medio": medio, "alto": alto}[nivel]


def normalizar(texto):
    t = unicodedata.normalize("NFD", str(texto).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def contiene(respuesta, *requisitos):
    """True si la respuesta contiene TODOS los requisitos.

    Cada requisito puede traer alternativas separadas por '|'.
    """
    r = normalizar(respuesta)
    if not r:
        return False
    for req in requisitos:
        alternativas = [normalizar(a) for a in str(req).split("|")]
        encontrada = False
        for a in alternativas:
            if not a:
                continue
            if re.search(r"\d", a):
                patron = rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])"
                if re.search(patron, r):
                    encontrada = True
            elif a in r:
                encontrada = True
        if not encontrada:
            return False
    return True


def normalizar_hora(h):
    m = re.search(r"(\d{1,2})\s*[:.hH]\s*(\d{2})", str(h))
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else str(h).strip()


def _guardar_respaldo():
    """Respaldo automático de los resultados para el terapeuta."""
    try:
        ruta = st.session_state.archivo_resultados
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        pd.DataFrame(st.session_state.registros).to_csv(
            ruta, index=False, encoding="utf-8-sig"
        )
    except Exception:
        pass


def registrar_evento(sesion_o_modulo, actividad, detalle):
    ahora = datetime.datetime.now()
    st.session_state.registros.append({
        "Fecha": ahora.strftime("%Y-%m-%d"),
        "Hora": ahora.strftime("%H:%M:%S"),
        "Paciente": st.session_state.get("paciente", ""),
        "Sesión / Módulo": sesion_o_modulo,
        "Actividad": actividad,
        "Detalle / Resultado": detalle,
        "Batería Mental": f"{st.session_state.bateria_actual}/10",
    })
    _guardar_respaldo()


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


def mostrar_temporizado(html_contenido, segundos, mensaje_final=None, alto=240):
    """Muestra un contenido que DESAPARECE solo después de N segundos."""
    if mensaje_final is None:
        mensaje_final = (
            "⏳ Se acabó el tiempo: el contenido desapareció. Ahora responde"
            " de memoria."
        )
    msg = json.dumps(
        "<div style='padding:14px;background:#FFF4E5;color:#222;"
        "border-radius:8px;font-size:18px;font-family:sans-serif;'>"
        f"{mensaje_final}</div>"
    )
    codigo = f"""
    <div style="font-family:sans-serif;">
      <div id="cont" style="background:#EAF2FB;color:#111;padding:14px;
           border-radius:8px;font-size:18px;line-height:1.5;">{html_contenido}</div>
      <p id="cuenta" style="color:#666;font-size:14px;margin-top:8px;">
        ⏱️ Desaparece en <b id="seg">{int(segundos)}</b> s</p>
    </div>
    <script>
      let t = {int(segundos)};
      const seg = document.getElementById("seg");
      const timer = setInterval(function() {{
        t -= 1;
        seg.textContent = t;
        if (t <= 0) {{
          clearInterval(timer);
          document.getElementById("cont").outerHTML = {msg};
          document.getElementById("cuenta").style.display = "none";
        }}
      }}, 1000);
    </script>
    """
    components.html(codigo, height=alto)


def cuenta_regresiva(segundos, titulo="⏸️ Pausa"):
    codigo = f"""
    <div style="font-family:sans-serif;text-align:center;padding:12px;
         background:#EAF7EE;color:#111;border-radius:8px;">
      <div style="font-size:18px;">{titulo}</div>
      <div id="reloj" style="font-size:48px;font-weight:bold;">--:--</div>
    </div>
    <script>
      let t = {int(segundos)};
      const reloj = document.getElementById("reloj");
      function pintar() {{
        const m = Math.floor(t / 60), s = t % 60;
        reloj.textContent = String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
      }}
      pintar();
      const timer = setInterval(function() {{
        t -= 1;
        if (t <= 0) {{
          clearInterval(timer);
          reloj.textContent = "¡Pausa terminada!";
          reloj.style.fontSize = "30px";
        }} else {{
          pintar();
        }}
      }}, 1000);
    </script>
    """
    components.html(codigo, height=135)


def leer_en_voz_alta(texto, repeticiones=2, pausa_seg=3):
    """Lee un texto con la voz del navegador (Web Speech API), N veces."""
    limpio = re.sub(r"[*_]", "", texto)
    codigo = f"""
    <div style="font-family:sans-serif;padding:12px;background:#EAF2FB;color:#111;
         border-radius:8px;">
      <button id="play" style="font-size:16px;padding:8px 14px;cursor:pointer;">
        ▶️ Escuchar el relato ({repeticiones} veces)</button>
      <button id="stop" style="font-size:16px;padding:8px 14px;cursor:pointer;">
        ⏹️ Detener</button>
      <span id="estado" style="margin-left:12px;font-size:15px;"></span>
    </div>
    <script>
      const texto = {json.dumps(limpio)};
      const total = {int(repeticiones)};
      const pausa = {int(pausa_seg)} * 1000;
      const synth = window.speechSynthesis;
      const estado = document.getElementById("estado");
      let activo = false;

      function elegirVoz() {{
        const voces = synth.getVoices();
        return voces.find(v => v.lang === "es-MX")
            || voces.find(v => v.lang.toLowerCase().startsWith("es"))
            || null;
      }}
      function leer(k) {{
        if (!activo) return;
        estado.textContent = "🔊 Lectura " + (k + 1) + " de " + total;
        const u = new SpeechSynthesisUtterance(texto);
        u.lang = "es-MX";
        u.rate = 0.9;
        const voz = elegirVoz();
        if (voz) u.voice = voz;
        u.onend = function() {{
          if (!activo) return;
          if (k + 1 < total) {{
            estado.textContent = "⏳ Pausa breve...";
            setTimeout(function() {{ leer(k + 1); }}, pausa);
          }} else {{
            activo = false;
            estado.textContent = "✅ Terminó la lectura";
          }}
        }};
        u.onerror = function() {{
          activo = false;
          estado.textContent = "⚠️ Tu navegador no pudo reproducir la voz";
        }};
        synth.speak(u);
      }}
      document.getElementById("play").onclick = function() {{
        if (!synth) {{ estado.textContent = "⚠️ Este navegador no tiene voz"; return; }}
        synth.cancel();
        activo = true;
        leer(0);
      }};
      document.getElementById("stop").onclick = function() {{
        activo = false;
        if (synth) synth.cancel();
        estado.textContent = "⏹️ Detenido";
      }};
    </script>
    """
    components.html(codigo, height=75)


def reiniciar_sesion(n):
    prefijo = f"s{n}_"
    for clave in list(st.session_state.keys()):
        if clave.startswith(prefijo):
            del st.session_state[clave]


def abrir_sesion(n):
    """Batería mental INICIAL. Devuelve el nivel (bajo/medio/alto) o None."""
    inicio = st.session_state.get(f"s{n}_inicio")
    if inicio is None:
        st.markdown("### 🔋 Antes de empezar: ¿cómo está tu batería mental?")
        st.caption(
            "1–4 = muy fatigado · 5–7 = fatiga media · 8–10 = sin fatiga. El"
            " programa ajustará la dificultad y la cantidad de ejercicios."
        )
        valor = st.slider(
            "Batería mental al INICIO de la sesión:",
            1,
            10,
            st.session_state.bateria_actual,
            key=f"s{n}_sl_ini",
        )
        if st.button(
            "✅ Registrar y comenzar", key=f"s{n}_btn_ini", type="primary"
        ):
            st.session_state[f"s{n}_inicio"] = valor
            st.session_state.bateria_actual = valor
            registrar_evento(
                f"Sesión {n}",
                "Batería mental inicial",
                f"{valor}/10 — nivel {nivel_de_bateria(valor)}",
            )
            st.rerun()
        return None

    nivel = nivel_de_bateria(inicio)
    st.info(f"🔋 Batería inicial: {inicio}/10 — {ETIQUETAS_NIVEL[nivel]}")
    if inicio <= 4:
        st.caption(
            "Si lo necesitas, toma una pausa antes de comenzar. Prioriza la"
            " precisión sobre la velocidad."
        )
    st.button(
        "🔄 Reiniciar esta sesión",
        key=f"s{n}_btn_reiniciar",
        on_click=reiniciar_sesion,
        args=(n,),
    )
    return nivel


def cerrar_sesion(n, actividad, detalle, resumen_paciente=""):
    """Batería mental FINAL y guardado de la sesión."""
    st.divider()
    if st.session_state.get(f"s{n}_guardada"):
        ini = st.session_state.get(f"s{n}_inicio")
        fin = st.session_state.get(f"s{n}_fin")
        st.success(f"✅ Sesión {n} guardada. Batería: {ini}/10 → {fin}/10.")
        resumen = st.session_state.get(f"s{n}_resumen", "")
        if resumen:
            st.info(resumen)
        return

    st.markdown("### 🔋 Al terminar: ¿cómo quedó tu batería mental?")
    fin = st.slider(
        "Batería mental al FINAL de la sesión:",
        1,
        10,
        st.session_state.bateria_actual,
        key=f"s{n}_sl_fin",
    )
    if fin <= 4:
        st.warning(
            "Tu batería quedó baja. Descansa y toma agua antes de seguir con"
            " otra actividad."
        )
    if st.button(
        f"💾 Guardar Sesión {n}", key=f"s{n}_btn_guardar", type="primary"
    ):
        ini = st.session_state.get(f"s{n}_inicio")
        st.session_state[f"s{n}_fin"] = fin
        st.session_state.bateria_actual = fin
        registrar_evento(
            f"Sesión {n}", "Batería mental final", f"{ini}/10 → {fin}/10"
        )
        registrar_evento(f"Sesión {n}", actividad, detalle)
        st.session_state[f"s{n}_guardada"] = True
        st.session_state[f"s{n}_resumen"] = resumen_paciente
        st.rerun()


def boton_pista(prefijo, clave, texto):
    """Botón de pista: cuenta cuántas pistas se piden."""
    if st.button("💡 Necesito una pista", key=f"{prefijo}_pista_{clave}"):
        st.session_state[f"{prefijo}_pistas"] = (
            st.session_state.get(f"{prefijo}_pistas", 0) + 1
        )
        st.session_state[f"{prefijo}_pv_{clave}"] = True
    if st.session_state.get(f"{prefijo}_pv_{clave}"):
        st.info(texto)


def mostrar_tarjeta_registro(ubicacion_key="sidebar"):
    """Ficha visual para registrar ficha, hora, señal y comprobación simulada."""
    with st.container(border=True):
        st.markdown("### 🗂️ Tarjeta de Registro")
        st.caption(
            "🔵 Azul: rutina/toma normal | 🟢 Verde: sin ayuda o tras pausa |"
            " 🟠 Naranja: interrupción o con apoyo *(simulación)*"
        )
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
# SESIÓN 1
# ==========================================
def sesion_1():
    st.subheader("Sesión 1: Mi rutina bajo la lupa")
    nivel = abrir_sesion(1)
    if nivel is None:
        return
    st.caption(
        "Las clasificaciones no son correctas o incorrectas; reflejan tu"
        " experiencia propia."
    )
    st.markdown(
        "**Instrucciones:** 1) Clasifica cada situación según cómo influye en"
        " tu rutina. 2) Escribe por qué, con un ejemplo tuyo. 3) Contesta las"
        " preguntas de estrategias. 4) Ordena los 4 pasos de ejecución segura."
    )

    todas = [
        "Dormir bien toda la noche",
        "Sentir fatiga o cansancio acumulado",
        "Estar ocupado o en llamada cuando suena la alarma",
        "Tener recordatorios visibles o bitácora a la mano",
        "Experimentar estrés o prisa en la mañana",
        "Contar con un apoyo familiar respetuoso",
        "Hacer una pausa corta a media mañana",
        "Que alguien me interrumpa mientras hago una actividad",
    ]
    situaciones = todas[: por_nivel(nivel, 4, 6, 8)]
    clasif, justif = {}, {}
    for i, sit in enumerate(situaciones):
        c_a, c_b = st.columns([1.2, 2])
        with c_a:
            clasif[sit] = st.selectbox(
                sit,
                [
                    "Sin clasificar",
                    "🟢 Verde (Me ayuda en mi rutina)",
                    "🟡 Amarillo (Prestar atención especial)",
                    "🔴 Rojo (Dificulta o interfiere)",
                ],
                key=f"s1_sit_{i}",
            )
        with c_b:
            justif[sit] = st.text_input(
                f"Justificación / experiencia similar ({sit}):",
                key=f"s1_just_{i}",
            )

    st.markdown("#### Tarjetas de Estrategias Compensatorias")
    herramientas_uso = st.multiselect(
        "¿Qué herramientas utiliza actualmente? (Alarma, Agenda, Registro,"
        " Rutina):",
        ["Alarma", "Agenda", "Registro", "Rutina"],
        key="s1_herr",
    )
    que_hace_ocupado = st.text_input(
        "¿Qué hace si está ocupado al sonar una alarma?", key="s1_ocupado"
    )
    como_verifica = st.text_input(
        "¿Cómo verifica si ya realizó una toma o pendiente?", key="s1_verifica"
    )

    st.markdown("#### Ordenar los 4 pasos de ejecución segura")
    orden_correcto = [
        "Recibir el recordatorio (alarma/nota)",
        "Revisar la indicación simulada",
        "Realizar la actividad o toma simulada",
        "Comprobar y registrar el cumplimiento en la bitácora",
    ]
    pasos = st.multiselect(
        "Selecciona en orden (1 a 4):", orden_correcto, key="s1_pasos"
    )
    apoyo_semana = st.text_input(
        "Dificultad detectada y apoyo útil para mantener en la semana:",
        key="s1_apoyo",
    )

    orden_ok = pasos == orden_correcto
    clasificadas = sum(1 for v in clasif.values() if v != "Sin clasificar")
    detalle = (
        f"Situaciones clasificadas: {clasificadas}/{len(situaciones)} |"
        f" Clasificación: "
        + "; ".join(f"{s}: {c} ({justif[s]})" for s, c in clasif.items())
        + f" | Herramientas: {', '.join(herramientas_uso)} | Ocupado:"
        f" {que_hace_ocupado} | Verifica: {como_verifica} | Pasos en orden:"
        f" {orden_ok} | Apoyo: {apoyo_semana}"
    )
    resumen = "Pasos en orden correcto." if orden_ok else (
        "Recuerda el orden: Recibir → Revisar → Realizar → Comprobar."
    )
    cerrar_sesion(1, "Rutina, Estrategias y Pasos", detalle, resumen)


# ==========================================
# SESIÓN 2
# ==========================================
RELATOS_S2 = {
    "bajo": (
        "Al iniciar la caminata, el explorador guardó su **brújula** (ficha"
        " **Azul**, **08:15**). A media mañana revisó el sendero y consultó su"
        " **brújula** (ficha **Verde**, **10:40**). Al caer la tarde, verificó"
        " el rumbo final con su **brújula** (ficha **Naranja**, **16:50**)."
    ),
    "medio": (
        "Al iniciar la caminata, el explorador guardó su brújula (ficha"
        " **Azul**, **08:15**). A media mañana revisó el sendero y consultó su"
        " brújula (ficha **Verde**, **10:40**). Tras una pausa junto al río,"
        " volvió a mirar su brújula (ficha **Naranja**, **13:10**). Al caer la"
        " tarde, verificó el rumbo final con su brújula (ficha **Azul**,"
        " **16:50**)."
    ),
    "alto": (
        "Al iniciar la caminata, el explorador revisó su mapa y guardó su"
        " brújula (ficha **Azul**, **07:50**). A media mañana encendió la"
        " linterna para cruzar un túnel y consultó su brújula (ficha"
        " **Verde**, **09:25**). Después comparó el mapa con los binoculares,"
        " sin soltar la cantimplora. Al llegar al río, volvió a mirar su"
        " brújula (ficha **Naranja**, **11:40**). Tras comer, anotó el rumbo"
        " en su bitácora y verificó con la brújula (ficha **Azul**,"
        " **13:15**). Subiendo la colina escuchó un ruido, guardó los"
        " binoculares y comprobó su brújula (ficha **Verde**, **15:05**). Al"
        " caer la tarde, ya sin linterna, hizo la última lectura de su"
        " brújula (ficha **Naranja**, **17:30**)."
    ),
}
EVENTOS_S2 = {
    "bajo": [("08:15", "Azul"), ("10:40", "Verde"), ("16:50", "Naranja")],
    "medio": [
        ("08:15", "Azul"),
        ("10:40", "Verde"),
        ("13:10", "Naranja"),
        ("16:50", "Azul"),
    ],
    "alto": [
        ("07:50", "Azul"),
        ("09:25", "Verde"),
        ("11:40", "Naranja"),
        ("13:15", "Azul"),
        ("15:05", "Verde"),
        ("17:30", "Naranja"),
    ],
}


def sesion_2():
    st.subheader(
        "Sesión 2: La misión del explorador — Escucha, presiona y registra"
    )
    nivel = abrir_sesion(2)
    if nivel is None:
        return

    eventos = EVENTOS_S2[nivel]
    st.markdown(
        "**Instrucciones:** 1) Pulsa «Escuchar el relato»: una voz lo leerá"
        " **dos veces**. 2) Cada vez que escuches la palabra «brújula», pulsa"
        " el botón de abajo. 3) Después anota en la tabla la hora y la ficha"
        " de cada vez que apareció."
    )
    # El relato NUNCA se muestra escrito: solo se escucha (sin apoyo visual).
    leer_en_voz_alta(RELATOS_S2[nivel], repeticiones=2)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            "🔘 ¡ESCUCHÉ «BRÚJULA»!",
            type="primary",
            use_container_width=True,
            key="s2_btn_press",
        ):
            st.session_state.s2_conteo = st.session_state.get("s2_conteo", 0) + 1
            registrar_evento(
                "Sesión 2",
                "Detección «brújula»",
                f"Presión #{st.session_state.s2_conteo}",
            )
    with c2:
        st.metric("Presiones registradas", st.session_state.get("s2_conteo", 0))
    with c3:
        if st.button("Reiniciar contador", key="s2_btn_reset"):
            st.session_state.s2_conteo = 0
            st.rerun()

    st.markdown("#### Cronograma ficticio")
    st.caption(
        "Agrega una fila por cada vez que apareció «brújula» (usa el + al"
        " final de la tabla). Anota la hora (hh:mm) y elige la ficha."
    )
    base = pd.DataFrame({"Hora anotada": [""], "Ficha anotada": [None]})
    editado = st.data_editor(
        base,
        num_rows="dynamic",
        use_container_width=True,
        key="s2_crono",
        column_config={
            "Hora anotada": st.column_config.TextColumn("Hora anotada (hh:mm)"),
            "Ficha anotada": st.column_config.SelectboxColumn(
                "Ficha anotada", options=["Azul", "Verde", "Naranja"]
            ),
        },
    )
    estrategia = st.text_input(
        "Estrategia para no distraerse:", key="s2_estrategia"
    )

    filas = []
    for h, f in zip(editado["Hora anotada"], editado["Ficha anotada"]):
        h = "" if pd.isna(h) else str(h).strip()
        f = "" if pd.isna(f) else str(f)
        if h or f:
            filas.append((normalizar_hora(h), f))
    pendientes = list(eventos)
    datos_ok = 0
    for fila in filas:
        if fila in pendientes:
            pendientes.remove(fila)
            datos_ok += 1

    presiones = st.session_state.get("s2_conteo", 0)
    reales = len(eventos)
    omisiones = max(0, reales - presiones)
    falsas = max(0, presiones - reales)

    st.write("")
    mostrar_tarjeta_registro(ubicacion_key="sesion2")

    detalle = (
        f"Nivel {nivel} | Apariciones reales: {reales} | Presiones:"
        f" {presiones} | Omisiones: {omisiones} | Falsas alarmas: {falsas} |"
        f" Cronograma correcto: {datos_ok}/{reales} (anotadas {len(filas)}) |"
        f" Estrategia: {estrategia}"
    )
    resumen = (
        f"Registraste {presiones} presiones y {datos_ok} datos correctos en tu"
        " cronograma."
    )
    cerrar_sesion(2, "Misión del Explorador y Cronograma", detalle, resumen)


# ==========================================
# SESIÓN 3
# ==========================================
SENALES_S3 = [
    "Pesadez palpebral / vista cansada",
    "Enlentecimiento del pensamiento / lectura lenta",
    "Tensión cefálica o cervical",
    "Irritabilidad",
    "Distracción fácil",
    "Otros",
]


def _fuente(tam):
    for nombre in (
        "arial.ttf",
        "Arial.ttf",
        "DejaVuSans.ttf",
        "LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(nombre, tam)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=tam)
    except Exception:
        return ImageFont.load_default()


@st.cache_data(show_spinner=False)
def generar_lamina(nivel, nombre):
    """Genera la imagen de la Lámina A o B (cuadrícula de letras y números)."""
    filas, cols = por_nivel(nivel, (6, 10), (8, 12), (10, 16))
    objetivos = por_nivel(nivel, ["A"], ["A", "7"], ["A", "7", "K"])
    rango = por_nivel(nivel, (3, 5), (4, 7), (5, 9))
    rng_c = random.Random(f"s3-conteos-{nivel}")
    conteos = {o: rng_c.randint(*rango) for o in objetivos}

    rng = random.Random(f"s3-lamina-{nivel}-{nombre}")
    distractores = list("HVXMNTEFLZBDPRGU") + list("2345689")
    total = filas * cols
    celdas = [rng.choice(distractores) for _ in range(total)]
    posiciones = rng.sample(range(total), sum(conteos.values()))
    i = 0
    for objetivo, cantidad in conteos.items():
        for _ in range(cantidad):
            celdas[posiciones[i]] = objetivo
            i += 1

    celda, margen = 46, 20
    ancho, alto = cols * celda + 2 * margen, filas * celda + 2 * margen
    img = Image.new("RGB", (ancho, alto), "white")
    d = ImageDraw.Draw(img)
    fuente = _fuente(28)
    d.rectangle([4, 4, ancho - 5, alto - 5], outline=(120, 120, 120), width=2)
    for idx, ch in enumerate(celdas):
        r, c = divmod(idx, cols)
        cx = margen + c * celda + celda / 2
        cy = margen + r * celda + celda / 2
        bbox = d.textbbox((0, 0), ch, font=fuente)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(
            (cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]),
            ch,
            font=fuente,
            fill=(30, 30, 30),
        )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), conteos


def sesion_3():
    st.subheader("Sesión 3: Mi batería mental y pausa estratégica")
    nivel = abrir_sesion(3)
    if nivel is None:
        return
    st.markdown(
        "**Instrucciones:** 1) Repasa lo aprendido antes. 2) Marca las señales"
        " que notas cuando tu batería baja. 3) Cuenta los símbolos de la"
        " Lámina A. 4) Haz una pausa de 3 minutos. 5) Cuenta los símbolos de"
        " la Lámina B."
    )

    # ---- 1. Repaso
    st.markdown("#### 🔁 1. Repaso: lo que aprendimos antes")
    st.info(
        "**Sesión 1:** los 4 pasos de ejecución segura (Recibir → Revisar →"
        " Realizar → Comprobar) y la estrategia **Miro → Señalo → Compruebo**."
        "\n\n**Sesión 2:** las fichas Azul (rutina), Verde (sin ayuda o tras"
        " pausa) y Naranja (interrupción o con apoyo), y registrar la hora."
    )
    repaso = [
        (
            "¿Qué significa «Miro → Señalo → Compruebo»?",
            "Mirar dónde me quedé, señalarlo y comprobar antes de seguir.",
        ),
        (
            "¿Qué significa cada ficha (Azul, Verde, Naranja)?",
            "Azul: rutina normal · Verde: sin ayuda o tras pausa · Naranja:"
            " tras interrupción o con apoyo.",
        ),
        (
            "Nombra los 4 pasos de ejecución segura.",
            "Recibir el recordatorio, revisar la indicación, realizar la"
            " actividad y comprobar/registrar.",
        ),
        (
            "¿Qué haces si suena una alarma y estás ocupado?",
            "Detengo la actividad, marco dónde me quedé, atiendo la alarma,"
            " registro y retomo.",
        ),
    ]
    n_rep = por_nivel(nivel, 2, 3, 4)
    respuestas_repaso = []
    for i, (preg, _) in enumerate(repaso[:n_rep]):
        respuestas_repaso.append(st.text_input(preg, key=f"s3_rep_{i}"))
    if st.checkbox("Ver respuestas de referencia del repaso", key="s3_rep_ver"):
        for preg, ref in repaso[:n_rep]:
            st.caption(f"• {preg} → {ref}")

    # ---- 2. Señales
    st.markdown("#### 🔎 2. Mis señales de fatiga")
    senales = st.multiselect(
        "Señales cuando la batería baja de 4 (somáticas o mentales):",
        SENALES_S3,
        key="s3_senales",
    )
    otros = ""
    if "Otros" in senales:
        otros = st.text_input("Otros: ¿cuáles?", key="s3_otros")

    # ---- 3. Lámina A
    st.markdown("#### 🖼️ 3. Lámina A (antes de la pausa de 3 min)")
    st.caption(
        "Cuenta cuántas veces aparece cada símbolo indicado y escribe tu"
        " respuesta."
    )
    png_a, conteos_a = generar_lamina(nivel, "A")
    st.image(png_a, width=720)
    objetivos = list(conteos_a.keys())
    fat_a = st.slider(
        "Batería mental justo ANTES de la pausa:",
        1,
        10,
        st.session_state.bateria_actual,
        key="s3_fa",
    )
    resp_a = {
        o: st.number_input(
            f"Lámina A — ¿cuántas veces aparece «{o}»?",
            0,
            99,
            0,
            key=f"s3_a_{o}",
        )
        for o in objetivos
    }
    ac_a = sum(1 for o in objetivos if resp_a[o] == conteos_a[o])

    # ---- 4. Pausa
    st.markdown("#### ⏸️ 4. Pausa de 3 minutos")
    pausa = st.session_state.get("s3_pausa", 0)
    if pausa == 0:
        st.write(
            "Cuando estés listo, pulsa el botón. Descansa los ojos, respira"
            " lento y no uses el celular."
        )
        if st.button("▶️ Iniciar pausa de 3 minutos", key="s3_btn_pausa"):
            st.session_state.s3_pausa = 1
            st.rerun()
        return
    if pausa == 1:
        cuenta_regresiva(180, "⏸️ Pausa estratégica: respira y descansa")
        if st.button("✅ Terminé la pausa", key="s3_btn_fin_pausa"):
            st.session_state.s3_pausa = 2
            st.rerun()
        return

    # ---- 5. Lámina B
    st.markdown("#### 🖼️ 5. Lámina B (después de la pausa)")
    png_b, conteos_b = generar_lamina(nivel, "B")
    st.image(png_b, width=720)
    fat_d = st.slider(
        "Batería mental DESPUÉS de la pausa:",
        1,
        10,
        st.session_state.bateria_actual,
        key="s3_fd",
    )
    resp_b = {
        o: st.number_input(
            f"Lámina B — ¿cuántas veces aparece «{o}»?",
            0,
            99,
            0,
            key=f"s3_b_{o}",
        )
        for o in objetivos
    }
    ac_b = sum(1 for o in objetivos if resp_b[o] == conteos_b[o])

    semaforo = st.selectbox(
        "Tarjeta del Semáforo de Autorregulación seleccionada:",
        [
            "🟢 Verde: Continuar la actividad",
            "🟡 Amarillo: Pausa corta / Reducir exigencia del estímulo",
            "🔴 Rojo: Detener la tarea y solicitar apoyo externo",
        ],
        key="s3_semaforo",
    )

    detalle = (
        f"Nivel {nivel} | Repaso respondido:"
        f" {sum(1 for r in respuestas_repaso if r.strip())}/{n_rep} |"
        f" Lámina A: {ac_a}/{len(objetivos)} (Batería {fat_a}) → Lámina B:"
        f" {ac_b}/{len(objetivos)} (Batería {fat_d}) | Semáforo: {semaforo} |"
        f" Señales: {', '.join(senales)}"
        + (f" | Otros: {otros}" if otros else "")
    )
    resumen = (
        f"Lámina A: {ac_a} de {len(objetivos)} correctas. Lámina B: {ac_b} de"
        f" {len(objetivos)} correctas."
    )
    cerrar_sesion(3, "Batería Mental y Pausa", detalle, resumen)


# ==========================================
# SESIÓN 4
# ==========================================
OBJETOS_S4 = ["Sobre 1", "Sobre 2", "Tarjeta Azul", "Ficha Verde"]
OBJETIVOS_S4 = ["Círculo Verde", "Reloj", "Marca X"]
CONSIGNAS_S4 = {
    1: (
        "Tomar la Tarjeta Azul → Colocarla bajo el Sobre 2 → Señalar el"
        " Círculo Verde",
        ["Tarjeta Azul", "Sobre 2", "Círculo Verde"],
    ),
    2: (
        "Abrir el Sobre 1 → Tomar la Ficha Verde → Ponerla junto al Reloj →"
        " Marcar la X",
        ["Sobre 1", "Ficha Verde", "Reloj", "Marca X"],
    ),
    3: (
        "Tomar la Ficha Verde → Colocarla en el Sobre 2 → Mirar el Reloj →"
        " Tomar la Tarjeta Azul → Señalar el Círculo Verde",
        ["Ficha Verde", "Sobre 2", "Reloj", "Tarjeta Azul", "Círculo Verde"],
    ),
}
RONDAS_S4 = {"bajo": [1], "medio": [1, 2], "alto": [2, 3]}
SEGUNDOS_S4 = {"bajo": 25, "medio": 15, "alto": 10}


def sesion_4():
    st.subheader("Sesión 4: Escape de instrucciones")
    nivel = abrir_sesion(4)
    if nivel is None:
        return
    rondas = RONDAS_S4[nivel]
    segundos = SEGUNDOS_S4[nivel]
    st.session_state.setdefault("s4_seq", [])
    st.session_state.setdefault("s4_ronda", 0)
    st.session_state.setdefault("s4_res", [])
    ronda = st.session_state.s4_ronda

    st.markdown(
        "**Instrucciones:** 1) Pulsa «Ver consigna»: aparecerá unos segundos y"
        " luego **desaparecerá**. 2) Memoriza el orden (Preparar → Hacer →"
        " Revisar). 3) Reproduce la consigna en el simulador pulsando en el"
        " mismo orden. 4) Pulsa «Verificar»."
    )

    if st.session_state.s4_res:
        ultima = st.session_state.s4_res[-1]
        st.info(
            f"Ronda anterior: {ultima['coinc']} de {ultima['total']} pasos en"
            " la posición correcta."
        )

    if ronda >= len(rondas):
        st.success("🎉 Terminaste todas las rondas.")
        detalle = f"Nivel {nivel} | " + " || ".join(
            f"R{i + 1}: consigna {r['consigna']} | marcado {r['marcado']} |"
            f" coincidencias {r['coinc']}/{r['total']} | exacta {r['exacta']}"
            f" | veces que vio la consigna {r['vistas']}"
            for i, r in enumerate(st.session_state.s4_res)
        )
        aciertos = sum(r["coinc"] for r in st.session_state.s4_res)
        total = sum(r["total"] for r in st.session_state.s4_res)
        cerrar_sesion(
            4,
            "Escape de Instrucciones (simulador digital)",
            detalle,
            f"Pasos correctos: {aciertos} de {total}.",
        )
        return

    texto, esperada = CONSIGNAS_S4[rondas[ronda]]
    st.markdown(f"#### Ronda {ronda + 1} de {len(rondas)}")
    if st.button(f"👁️ Ver consigna ({segundos} s)", key=f"s4_ver_{ronda}"):
        st.session_state[f"s4_vistas_{ronda}"] = (
            st.session_state.get(f"s4_vistas_{ronda}", 0) + 1
        )
        mostrar_temporizado(
            f"<b>Consigna ({len(esperada)} pasos):</b><br>{texto}",
            segundos,
            mensaje_final=(
                "⏳ La consigna desapareció. Reprodúcela en el simulador de"
                " abajo."
            ),
            alto=200,
        )
    st.caption(
        "Veces que has visto esta consigna:"
        f" {st.session_state.get(f's4_vistas_{ronda}', 0)}"
    )

    st.markdown("### 🎮 Simulador Digital de Escape")
    st.write("Haz clic en los sobres, fichas y objetivos en el orden correcto:")
    cols = st.columns(4)
    for nombre, col in zip(OBJETOS_S4, cols):
        with col:
            if st.button(
                f"📦 {nombre}", key=f"s4_btn_{ronda}_{nombre}"
            ):
                st.session_state.s4_seq.append(nombre)
    cols = st.columns(3)
    for nombre, col in zip(OBJETIVOS_S4, cols):
        with col:
            if st.button(
                f"🎯 {nombre}", key=f"s4_btn_{ronda}_{nombre}"
            ):
                st.session_state.s4_seq.append(nombre)

    st.info(
        "**Secuencia marcada hasta ahora (Miro → Señalo → Compruebo):** "
        + (
            " → ".join(st.session_state.s4_seq)
            if st.session_state.s4_seq
            else "Ningún paso aún"
        )
    )
    b1, b2 = st.columns(2)
    with b1:
        if st.button("🔄 Limpiar secuencia", key=f"s4_limpiar_{ronda}"):
            st.session_state.s4_seq = []
            st.rerun()
    with b2:
        if st.button("✅ Verificar secuencia", key=f"s4_verif_{ronda}"):
            seq = list(st.session_state.s4_seq)
            coinc = sum(1 for a, b in zip(seq, esperada) if a == b)
            st.session_state.s4_res.append({
                "consigna": rondas[ronda],
                "marcado": " > ".join(seq),
                "coinc": coinc,
                "total": len(esperada),
                "exacta": seq == esperada,
                "vistas": st.session_state.get(f"s4_vistas_{ronda}", 0),
            })
            st.session_state.s4_seq = []
            st.session_state.s4_ronda += 1
            st.rerun()


# ==========================================
# SESIÓN 5
# ==========================================
LISTAS_S5 = {
    "bajo": {
        "Frutas": ["Manzana", "Plátano"],
        "Artículos de limpieza": ["Detergente", "Jabón"],
        "Lácteos": ["Leche", "Yogurt"],
    },
    "medio": {
        "Frutas": ["Manzana", "Plátano", "Uva"],
        "Artículos de limpieza": ["Detergente", "Jabón", "Cloro"],
        "Lácteos": ["Leche", "Yogurt", "Queso"],
    },
    "alto": {
        "Frutas": ["Manzana", "Plátano", "Uva"],
        "Artículos de limpieza": ["Detergente", "Jabón", "Cloro"],
        "Lácteos": ["Leche", "Yogurt", "Queso"],
        "Verduras": ["Zanahoria", "Jitomate", "Espinaca"],
    },
}
AGENDA_S5 = [
    ("Llamar al banco a las 11:00", "banco"),
    ("Recoger el paquete a las 14:30", "paquete"),
    ("Enviar el informe a las 16:00", "informe"),
]
SEGUNDOS_S5 = {"bajo": 30, "medio": 25, "alto": 25}
CUENTOS_S5 = {
    "bajo": {
        "texto": (
            "Don Ernesto salió temprano a trabajar. En la esquina saludó a su"
            " vecina, que regaba unas plantas. En la oficina, una compañera le"
            " pidió ayuda con una carpeta azul. Al mediodía comieron juntos en"
            " el comedor."
        ),
        "preguntas": [(
            "¿Qué le pidió la compañera a Don Ernesto?",
            ["Prestarle dinero", "Ayuda con una carpeta azul", "Cambiar de turno"],
            "Ayuda con una carpeta azul",
        )],
    },
    "medio": {
        "texto": (
            "Lucía llevó a su hijo a la escuela y después fue al taller a"
            " recoger el coche. El mecánico le explicó que el cambio de aceite"
            " costaba 850 pesos. Mientras esperaba, recibió una llamada de su"
            " hermana, que le pidió pasar por un pastel antes de las seis."
            " Lucía anotó el encargo en su libreta verde."
        ),
        "preguntas": [
            (
                "¿Cuánto costaba el cambio de aceite?",
                ["650 pesos", "580 pesos", "850 pesos"],
                "850 pesos",
            ),
            (
                "¿Qué le pidió su hermana?",
                ["Pasar por un pastel", "Recoger a su sobrino", "Llevar un paraguas"],
                "Pasar por un pastel",
            ),
        ],
    },
    "alto": {
        "texto": (
            "Martín tenía una reunión a las nueve con tres clientes. Salió de"
            " casa a las 8:10, pero el tráfico de la avenida principal estaba"
            " detenido por una obra, así que tomó la calle del mercado. Llegó"
            " a las 8:55 y notó que había dejado su cartera con las tarjetas"
            " en el escritorio de su casa. Llamó a su esposa, quien se la"
            " llevó en un taxi y la dejó con el vigilante a las 9:20. Martín"
            " agradeció el gesto y, al terminar la reunión, le compró flores."
        ),
        "preguntas": [
            (
                "¿A qué hora era la reunión?",
                ["8:30", "10:00", "9:00"],
                "9:00",
            ),
            (
                "¿Qué había dejado olvidado?",
                ["Su celular", "Su cartera con las tarjetas", "Las llaves"],
                "Su cartera con las tarjetas",
            ),
            (
                "¿Con quién la dejó su esposa?",
                ["Con un cliente", "Con la recepcionista", "Con el vigilante"],
                "Con el vigilante",
            ),
        ],
    },
}


def sesion_5():
    st.subheader("Sesión 5: Mi memoria de trabajo")
    nivel = abrir_sesion(5)
    if nivel is None:
        return
    lista = LISTAS_S5[nivel]
    agenda = AGENDA_S5[: por_nivel(nivel, 1, 2, 3)]
    segundos = SEGUNDOS_S5[nivel]
    cuento = CUENTOS_S5[nivel]
    paso = st.session_state.setdefault("s5_paso", 0)

    st.markdown(
        "**Instrucciones:** 1) Memoriza la lista de supermercado y tu agenda:"
        " desaparecerán solos. 2) Lee el cuento breve y contesta (es una"
        " distracción). 3) Escribe de memoria lo que recuerdes."
    )
    st.progress(
        min(paso, 2) / 2,
        text=f"Paso {min(paso, 2) + 1} de 3",
    )

    if paso == 0:
        st.markdown("#### Paso 1: Memoriza la lista y la agenda")
        todos = [x for v in lista.values() for x in v]
        random.Random(f"s5-{nivel}").shuffle(todos)
        if st.button(
            f"👁️ Ver la lista y la agenda ({segundos} s)", key="s5_btn_ver"
        ):
            st.session_state.s5_visto = True
            html = (
                "<b>🛒 Lista de supermercado:</b><br>"
                + " • ".join(todos)
                + "<br><br><b>📅 Agenda:</b><br>"
                + "<br>".join(t for t, _ in agenda)
            )
            mostrar_temporizado(
                html,
                segundos,
                mensaje_final=(
                    "⏳ La lista y la agenda desaparecieron. Pulsa «Continuar»."
                ),
                alto=300,
            )
        if st.session_state.get("s5_visto"):
            if st.button("➡️ Continuar al cuento", key="s5_btn_cont1"):
                st.session_state.s5_paso = 1
                st.rerun()
        return

    if paso == 1:
        st.markdown("#### Paso 2: Cuento breve (distractor)")
        st.info(cuento["texto"])
        for i, (preg, opciones, _) in enumerate(cuento["preguntas"]):
            st.radio(preg, opciones, index=None, key=f"s5_cuento_{i}")
        if st.button("➡️ Pasar al recuerdo", key="s5_btn_cont2"):
            ok = sum(
                1
                for i, (_, _, correcta) in enumerate(cuento["preguntas"])
                if st.session_state.get(f"s5_cuento_{i}") == correcta
            )
            st.session_state.s5_cuento_ok = ok
            st.session_state.s5_paso = 2
            st.rerun()
        return

    st.markdown("#### Paso 3: Escribe de memoria")
    st.caption("Escribe los artículos separados por comas.")
    total_items, ok_items = 0, 0
    detalle_cat = []
    for i, (cat, items) in enumerate(lista.items()):
        resp = st.text_input(f"Categoría {cat}:", key=f"s5_cat_{i}")
        aciertos = sum(1 for it in items if contiene(resp, it))
        total_items += len(items)
        ok_items += aciertos
        detalle_cat.append(f"{cat}: {aciertos}/{len(items)} ('{resp}')")
    resp_agenda = st.text_area(
        "Tareas de la agenda que recuerdas:", key="s5_agenda"
    )
    ok_agenda = sum(1 for _, clave in agenda if contiene(resp_agenda, clave))
    tecnica = st.text_input(
        "¿Qué técnica mental usó para retener la información?", key="s5_tecnica"
    )

    cuento_ok = st.session_state.get("s5_cuento_ok", 0)
    detalle = (
        f"Nivel {nivel} | Lista: {ok_items}/{total_items} | "
        + " | ".join(detalle_cat)
        + f" | Agenda: {ok_agenda}/{len(agenda)} ('{resp_agenda}') | Cuento:"
        f" {cuento_ok}/{len(cuento['preguntas'])} | Técnica: {tecnica}"
    )
    resumen = (
        f"Recordaste {ok_items} de {total_items} artículos y {ok_agenda} de"
        f" {len(agenda)} tareas de agenda."
    )
    cerrar_sesion(5, "Memoria de Trabajo Funcional", detalle, resumen)


# ==========================================
# SESIÓN 6
# ==========================================
def sesion_6():
    st.subheader("Sesión 6: Soluciono problemas")
    nivel = abrir_sesion(6)
    if nivel is None:
        return
    st.markdown(
        "**Instrucciones:** Elige una situación y respóndela paso a paso:"
        " Detenerme → Analizar → Decidir."
    )
    caso = st.selectbox(
        "Situación problemática cotidiana:",
        [
            "Olvidaste llevar un documento que tenías que entregar a las 10:00 AM",
            "Suena la alarma de actividad/medicamento durante una reunión importante",
            "Otro imprevisto referido por el consultante",
        ],
        key="s6_caso",
    )
    p1 = st.text_input("1. ¿Qué está ocurriendo exactamente?", key="s6_p1")
    p2 = st.text_input(
        "2. ¿Requiere solución inmediata o puede esperar unos minutos?",
        key="s6_p2",
    )
    p3 = st.text_input(
        "3. ¿Qué herramientas, notas o apoyos tengo a la mano?", key="s6_p3"
    )
    alt = st.text_area("4. 2 o 3 alternativas y elección final:", key="s6_alt")
    regla = ""
    if nivel != "bajo":
        regla = st.text_input(
            "5. Resumen en regla: Detenerme → Analizar → Decidir:",
            key="s6_regla",
        )
    reto = ""
    if nivel == "alto":
        st.markdown("#### 🔥 Reto adicional")
        reto = st.text_area(
            "Un familiar te pide ayuda con un trámite justo cuando debes"
            " entregar un reporte a las 12:00. ¿Qué haces y qué le dices?",
            key="s6_reto",
        )
        reto += " | Con batería 3/10: " + st.text_input(
            "¿Qué cambiarías si estuvieras con la batería en 3/10?",
            key="s6_reto2",
        )

    detalle = (
        f"Nivel {nivel} | Caso: {caso} | Qué ocurre: {p1} | Urgencia: {p2} |"
        f" Apoyos: {p3} | Elección: {alt} | Regla: {regla}"
        + (f" | Reto: {reto}" if reto else "")
    )
    cerrar_sesion(6, "Resolución de Problemas", detalle)


# ==========================================
# SESIÓN 7
# ==========================================
REGLAS_S7 = [
    (
        "Bloque de COLOR: tacha las figuras AZULES o VERDES (🔵 🟦 🟢 🟩)",
        {"🔵", "🟦", "🟢", "🟩"},
        "Color",
    ),
    (
        "Bloque de NÚMEROS IMPARES: tacha 1, 3, 5, 7, 9",
        {"1", "3", "5", "7", "9"},
        "Impares",
    ),
    (
        "Bloque de FORMAS: tacha CUADRADOS o TRIÁNGULOS (🟥 🟩 🟦 🔺 🔻)",
        {"🟥", "🟩", "🟦", "🔺", "🔻"},
        "Formas",
    ),
]
SIMBOLOS_S7 = [
    "🔵", "🔴", "🟢", "🟡", "🟣", "🟦", "🟥", "🟩", "🟨", "🔺", "🔻", "⭐",
] + list("0123456789")
# (bloques, bloques con distracción, cantidad de símbolos)
SEC_S7 = {
    "bajo": ([0, 1], {0}, 24),
    "medio": ([0, 1, 2], {1}, 36),
    "alto": ([0, 1, 2, 0], {1, 2}, 48),
}
LLAMADAS_S7 = [
    ("¿Cuánto es 9 + 6?", "15"),
    ("¿Cuánto es 20 − 7?", "13"),
    ("¿Cuánto es 8 + 7?", "15"),
]


@st.cache_data(show_spinner=False)
def generar_grid_s7(nivel, pos, n_items, regla_idx):
    rng = random.Random(f"s7-{nivel}-{pos}")
    pred = REGLAS_S7[regla_idx][1]
    minimo, maximo = max(4, int(n_items * 0.15)), int(n_items * 0.5)
    items = []
    for _ in range(300):
        items = [rng.choice(SIMBOLOS_S7) for _ in range(n_items)]
        objetivos = sum(1 for x in items if x in pred)
        if minimo <= objetivos <= maximo:
            break
    return items


def sesion_7():
    st.subheader("Sesión 7: Mi atención en acción — Matrices de alternancia")
    nivel = abrir_sesion(7)
    if nivel is None:
        return
    bloques, distraer, n_items = SEC_S7[nivel]
    st.markdown(
        "**Instrucciones:** Prioriza la precisión sobre la velocidad. Cada"
        " bloque tiene una regla: marca SOLO las figuras que la cumplen. Al"
        " cambiar de regla sonará una señal breve. En algunos bloques sonará"
        " una **alarma** y te llamarán por teléfono: atiende y retoma con"
        " **Miro → Señalo → Compruebo**."
    )
    pos = st.session_state.setdefault("s7_pos", 0)
    fase = st.session_state.setdefault("s7_fase", "A")
    resultados = st.session_state.setdefault("s7_res", [])
    reorient = st.session_state.setdefault("s7_reorient", [])

    # ---- Fin de la sesión
    if pos >= len(bloques):
        st.success("🎉 Terminaste todos los bloques.")
        st.dataframe(pd.DataFrame(resultados), use_container_width=True)
        total_a = sum(r["Aciertos"] for r in resultados)
        total_o = sum(r["Omisiones"] for r in resultados)
        total_e = sum(r["Errores"] for r in resultados)
        total_p = sum(r["Perseveraciones"] for r in resultados)
        detalle = (
            f"Nivel {nivel} | Aciertos: {total_a} | Omisiones: {total_o} |"
            f" Errores: {total_e} | Perseveraciones: {total_p} | Por bloque: "
            + "; ".join(
                f"B{i + 1} {r['Regla']} A{r['Aciertos']}/O{r['Omisiones']}/"
                f"E{r['Errores']}/P{r['Perseveraciones']}"
                for i, r in enumerate(resultados)
            )
            + " | Reorientación: "
            + (
                "; ".join(
                    f"{r['reorientacion']} ({r['intentos']} intento(s),"
                    f" {r['segundos']} s, llamada correcta: {r['llamada_ok']})"
                    for r in reorient
                )
                or "No hubo distracción"
            )
        )
        cerrar_sesion(
            7,
            "Matrices de Alternancia",
            detalle,
            f"Aciertos: {total_a} · Omisiones: {total_o} · Errores:"
            f" {total_e}.",
        )
        return

    regla_idx = bloques[pos]
    texto_regla, pred, nombre_regla = REGLAS_S7[regla_idx]
    items = generar_grid_s7(nivel, pos, n_items, regla_idx)
    hay_distr = pos in distraer
    mitad = n_items // 2
    st.markdown(f"#### Bloque {pos + 1} de {len(bloques)}")

    # ---- Fase de distracción (alarma + llamada)
    if fase == "dist":
        st.error(
            "🚨 **¡ALARMA!** Suena el teléfono: un familiar te llama. Atiende"
            " la llamada y después retoma tu tarea."
        )
        pregunta, correcta = LLAMADAS_S7[pos % len(LLAMADAS_S7)]
        resp = st.text_input(
            f"📞 Tu familiar pregunta: {pregunta}", key=f"s7_llam_{pos}"
        )
        st.markdown(
            "Ahora retoma con **Miro → Señalo → Compruebo**: mira dónde te"
            " quedaste, señala la última figura que marcaste y comprueba la"
            " regla antes de seguir."
        )
        sel = st.selectbox(
            "¿Qué regla estabas aplicando?",
            ["Elige..."] + [r[0] for r in REGLAS_S7],
            key=f"s7_reo_{pos}",
        )
        if st.session_state.get("s7_intentos", 0) >= 2:
            st.info(f"Pista: la regla era «{texto_regla}»")
        if st.button("▶️ Retomar tarea", key=f"s7_retomar_{pos}"):
            st.session_state.s7_intentos = (
                st.session_state.get("s7_intentos", 0) + 1
            )
            if sel == texto_regla:
                intentos = st.session_state.s7_intentos
                reorient.append({
                    "reorientacion": "Autónoma" if intentos == 1 else "Con apoyo",
                    "intentos": intentos,
                    "segundos": round(
                        time.time() - st.session_state.get("s7_t_alarma", time.time()),
                        1,
                    ),
                    "llamada_ok": contiene(resp, correcta),
                })
                st.session_state.s7_fase = "B"
                st.rerun()
            else:
                st.warning(
                    "Esa no es la regla que estabas aplicando. Piensa de nuevo"
                    " e inténtalo."
                )
        return

    # ---- Fase de resultados del bloque
    if fase == "chk":
        r = resultados[-1]
        st.markdown(f"**Resultado del bloque ({r['Regla']})**")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("✅ Aciertos", r["Aciertos"])
        m2.metric("⚪ Omisiones", r["Omisiones"])
        m3.metric("❌ Errores", r["Errores"])
        m4.metric("🔁 Perseveraciones", r["Perseveraciones"])
        if r["Errores"] == 0 and r["Omisiones"] == 0:
            st.success("¡Bloque perfecto!")
        elif r["Perseveraciones"] > 0:
            st.warning(
                "Marcaste figuras de la regla anterior. Revisa bien la regla"
                " nueva antes de empezar."
            )
        else:
            st.warning("Revisa con calma: algunas figuras no coincidieron.")
        ultimo = pos + 1 >= len(bloques)
        etiqueta = (
            "🏁 Finalizar bloques"
            if ultimo
            else "🔊 Siguiente bloque (cambio de regla)"
        )
        if st.button(etiqueta, key=f"s7_sig_{pos}"):
            st.session_state.s7_pos = pos + 1
            st.session_state.s7_fase = "A"
            if not ultimo:
                st.session_state.sonar_senal = True
            st.rerun()
        return

    # ---- Fase de tarea
    st.warning(f"📌 **REGLA ACTUAL:** {texto_regla}")
    if hay_distr:
        rango = range(0, mitad) if fase == "A" else range(mitad, n_items)
    else:
        rango = range(n_items)
    cols = st.columns(6)
    for idx in rango:
        with cols[idx % 6]:
            st.checkbox(items[idx], key=f"s7_g_{pos}_{idx}")

    if hay_distr and fase == "A":
        if st.button("➡️ Terminé esta parte", key=f"s7_parteA_{pos}"):
            st.session_state[f"s7_marksA_{pos}"] = [
                idx
                for idx in range(mitad)
                if st.session_state.get(f"s7_g_{pos}_{idx}")
            ]
            st.session_state.s7_fase = "dist"
            st.session_state.s7_intentos = 0
            st.session_state.s7_t_alarma = time.time()
            st.session_state.sonar_alarma = True
            st.rerun()
    else:
        if st.button("✅ Comprobar bloque", key=f"s7_comp_{pos}"):
            marcados = set(st.session_state.get(f"s7_marksA_{pos}", [])) | {
                idx
                for idx in rango
                if st.session_state.get(f"s7_g_{pos}_{idx}")
            }
            objetivos = {i for i, x in enumerate(items) if x in pred}
            errores = marcados - objetivos
            persev = 0
            if pos > 0:
                pred_prev = REGLAS_S7[bloques[pos - 1]][1]
                persev = sum(1 for i in errores if items[i] in pred_prev)
            resultados.append({
                "Bloque": pos + 1,
                "Regla": nombre_regla,
                "Aciertos": len(marcados & objetivos),
                "Omisiones": len(objetivos - marcados),
                "Errores": len(errores),
                "Perseveraciones": persev,
            })
            st.session_state.s7_fase = "chk"
            st.rerun()


# ==========================================
# SESIÓN 8
# ==========================================
HISTORIAS_S8 = [
    {
        "id": "breve",
        "titulo": "Historia breve",
        "texto": (
            "El **martes a las 10:30 AM**, se acudió a la **farmacia del"
            " centro** para recoger una **libreta azul** de apuntes y después"
            " se tomó un café en la **plaza principal** antes de volver a casa"
            " a la **1:00 PM**."
        ),
        "claves": [
            ("¿Qué día y a qué hora fue?", ["martes", "10 30"]),
            ("¿Qué objeto recogió?", ["libreta"]),
            ("¿En qué lugar tomó el café?", ["plaza"]),
        ],
    },
    {
        "id": "larga1",
        "titulo": "Historia larga 1 (trabajo)",
        "texto": (
            "El jueves a las 8:45 AM, Roberto llegó a la oficina de la calle"
            " Hidalgo y encontró que el elevador estaba descompuesto, así que"
            " subió al tercer piso por las escaleras. Su jefa, la licenciada"
            " Paredes, le pidió preparar un informe de ventas con cuatro"
            " gráficas para la junta de las 12:00. Roberto trabajó con su"
            " compañero Iván y, a las 10:15, se dieron cuenta de que faltaban"
            " los datos de la sucursal norte. Llamó a la encargada, Marisol,"
            " quien le mandó el archivo por correo. A la hora de la comida fue"
            " a una fonda cercana y pidió caldo de pollo. Antes de salir,"
            " imprimió seis copias del informe y las guardó en una carpeta"
            " roja. La junta terminó a las 2:30 PM y Roberto regresó a casa en"
            " autobús."
        ),
        "claves": [
            ("¿Qué día y a qué hora llegó a la oficina?", ["jueves", "8 45"]),
            ("¿Qué documento le pidió preparar su jefa?", ["informe"]),
            ("¿A qué hora era la junta?", ["12"]),
            ("¿Cómo se llamaba la encargada de la sucursal norte?", ["marisol"]),
            ("¿Qué pidió de comer?", ["caldo"]),
            ("¿Cuántas copias imprimió?", ["6|seis"]),
        ],
    },
    {
        "id": "larga2",
        "titulo": "Historia larga 2 (familia)",
        "texto": (
            "El sábado por la tarde, la familia de Carmen se reunió en casa de"
            " su mamá para celebrar el cumpleaños número 70 de la abuela Rosa."
            " Carmen llegó a las 4:00 PM con un pastel de zarzamora y dos"
            " botellas de agua de jamaica. Su hermano Luis llevó una guitarra"
            " y su sobrina Daniela preparó un cartel con letras moradas."
            " Alrededor de las 5:30 comieron mole con arroz y, después, la"
            " abuela contó cómo conoció a su esposo en el pueblo de San"
            " Miguel. Antes de despedirse, Luis acordó con Carmen que el"
            " domingo la ayudaría a mover un librero de la sala. Regresaron a"
            " sus casas a las 9:00 PM."
        ),
        "claves": [
            ("¿Qué día y a qué hora llegó Carmen?", ["sabado", "4"]),
            ("¿Cuántos años cumplía la abuela Rosa?", ["70|setenta"]),
            ("¿De qué sabor era el pastel?", ["zarzamora"]),
            ("¿Qué llevó Luis?", ["guitarra"]),
            ("¿De qué color eran las letras del cartel?", ["morad"]),
            ("¿Qué mueble ayudaría a mover Luis el domingo?", ["librero"]),
        ],
    },
]


def sesion_8():
    st.subheader("Sesión 8: Recuerdo lo importante")
    nivel = abrir_sesion(8)
    if nivel is None:
        return
    historias = HISTORIAS_S8[: por_nivel(nivel, 1, 2, 3)]
    st.markdown(
        "**Instrucciones:** 1) Lee cada historia **dos veces**, imaginándola y"
        " agrupando los datos (día, lugar, objetos, personas). 2) Cuando estés"
        " listo, desmarca «Mostrar historia» para ocultarla. 3) Escribe todo lo"
        " que recuerdes. 4) Responde las claves escribiendo tu propia"
        " respuesta."
    )

    total_ok, total = 0, 0
    for h in historias:
        for j, (_, reqs) in enumerate(h["claves"]):
            total += 1
            if contiene(st.session_state.get(f"s8_{h['id']}_c{j}", ""), *reqs):
                total_ok += 1
    st.metric("✅ Contador de aciertos (claves correctas)", f"{total_ok} / {total}")

    detalle_h = []
    for h in historias:
        with st.container(border=True):
            st.markdown(f"### 📖 {h['titulo']}")
            if st.checkbox(
                "Mostrar historia", value=True, key=f"s8_ver_{h['id']}"
            ):
                st.info(h["texto"])
            libre = st.text_area(
                "Recuerdo libre (tras una demora de 5 min con actividad"
                " neutra):",
                key=f"s8_libre_{h['id']}",
            )
            ok_h = 0
            respuestas = []
            for j, (preg, reqs) in enumerate(h["claves"]):
                r = st.text_input(f"Clave {j + 1}: {preg}", key=f"s8_{h['id']}_c{j}")
                respuestas.append(r)
                if contiene(r, *reqs):
                    ok_h += 1
            st.caption(f"Aciertos en esta historia: {ok_h} de {len(h['claves'])}")
            detalle_h.append(
                f"{h['titulo']}: {ok_h}/{len(h['claves'])} | Claves:"
                f" {respuestas} | Libre: {libre}"
            )

    detalle = f"Nivel {nivel} | Total: {total_ok}/{total} | " + " || ".join(
        detalle_h
    )
    cerrar_sesion(
        8,
        "Memoria Episódica",
        detalle,
        f"Claves correctas: {total_ok} de {total}.",
    )


# ==========================================
# SESIÓN 9
# ==========================================
ESCENAS_S9 = [
    "1. Un familiar te pregunta en tono molesto si ya cumpliste tu tarea o actividad",
    "2. Estás cansado y te piden asistir a una reunión familiar esa misma tarde",
    "3. Olvidaste lo que ibas a decir en medio de una conversación",
    "4. En el trabajo, un compañero te interrumpe varias veces mientras terminas un pendiente",
]


def sesion_9():
    st.subheader("Sesión 9: Me comunico mejor")
    nivel = abrir_sesion(9)
    if nivel is None:
        return
    st.markdown(
        "**Instrucciones:** 1) Construye tu frase asertiva con 3 partes: **Lo"
        " que pasa + Cómo me siento + Lo que propongo**. 2) Practica cada"
        " escena en voz alta con el psicólogo. 3) Márcala como practicada."
        " 4) El psicólogo te dará su retroalimentación. 5) Anota cómo te"
        " sentiste."
    )
    a1, a2, a3 = st.columns(3)
    with a1:
        lo_que_pasa = st.text_input(
            "Lo que pasa:",
            value="Cuando me repiten varias veces si ya cumplí la tarea",
            key="s9_pasa",
        )
    with a2:
        como_me_siento = st.text_input(
            "Cómo me siento:", value="me siento presionado", key="s9_siento"
        )
    with a3:
        lo_que_propongo = st.text_input(
            "Lo que propongo:",
            value="prefiero que revisemos juntos el registro al final de la tarde.",
            key="s9_propongo",
        )
    st.caption("Los textos de arriba son un ejemplo: cámbialos con tus palabras.")
    st.success(
        f"Frase construida: «{lo_que_pasa}, {como_me_siento}; {lo_que_propongo}»"
    )

    st.markdown("#### Escenas de role-play")
    escenas = ESCENAS_S9[: por_nivel(nivel, 1, 2, 4)]
    practicadas = []
    for i, escena in enumerate(escenas):
        if st.checkbox(f"{escena} — ✔ practicada", key=f"s9_esc_{i}"):
            practicadas.append(escena)

    st.markdown("#### 🧑‍⚕️ Retroalimentación del psicólogo")
    st.info(
        "**Instrucciones para el psicólogo:** 1) Observa la práctica sin"
        " interrumpir. 2) Redacta tres partes breves (máximo 3 frases cada"
        " una): **a)** un acierto concreto que observaste, **b)** un solo"
        " punto de mejora, **c)** una sugerencia para la próxima práctica."
        " 3) Usa un tono amable y específico (ejemplo: «Mantuviste un tono"
        " calmado y dijiste claramente lo que propones»). 4) Léela en voz alta"
        " al paciente y pregúntale cómo la recibe."
    )
    retro_acierto = st.text_area("a) Acierto observado:", key="s9_r_acierto")
    retro_mejora = st.text_area("b) Punto de mejora:", key="s9_r_mejora")
    retro_sugerencia = st.text_area(
        "c) Sugerencia para la próxima práctica:", key="s9_r_sug"
    )
    sentir = st.text_input(
        "Paciente: ¿cómo me sentí practicando y qué haré distinto?",
        key="s9_sentir",
    )

    detalle = (
        f"Nivel {nivel} | Escenas practicadas: {len(practicadas)}/{len(escenas)}"
        f" ({'; '.join(practicadas)}) | Frase: {lo_que_pasa}, {como_me_siento};"
        f" {lo_que_propongo} | Retro psicólogo — Acierto: {retro_acierto} |"
        f" Mejora: {retro_mejora} | Sugerencia: {retro_sugerencia} |"
        f" Paciente: {sentir}"
    )
    cerrar_sesion(9, "Comunicación Asertiva y Role-Play", detalle)


# ==========================================
# SESIÓN 10
# ==========================================
PRECIOS_S10 = [("Pan", 18), ("Leche", 27), ("Jabón", 35), ("Fruta", 42), ("Café", 64)]


def sesion_10():
    st.subheader("Sesión 10: Simulación de un día completo")
    nivel = abrir_sesion(10)
    if nivel is None:
        return
    momentos = por_nivel(nivel, [1, 2], [1, 2, 3], [1, 2, 3, 4])
    st.markdown(
        "**Instrucciones generales:** Vas a practicar un día completo en"
        f" {len(momentos)} momentos. En cada momento: 1) lee las"
        " instrucciones, 2) haz lo que se pide, 3) marca «Terminé este"
        " momento». Si te bloqueas, pide una 💡 pista (se contarán). Todo es"
        " una simulación: no se usan medicamentos reales."
    )
    st.session_state.setdefault("s10_pistas", 0)
    completos = 0
    detalle = []

    if 1 in momentos:
        with st.container(border=True):
            st.markdown("### 🌅 Momento 1: Mañana — Mi agenda del día")
            st.markdown(
                "1. Escribe tus actividades del día con su hora.\n"
                "2. Elige a qué hora sonará tu alarma.\n"
                "3. Marca «Terminé este momento»."
            )
            n_act = por_nivel(nivel, 2, 3, 4)
            agenda = []
            for i in range(n_act):
                c1, c2 = st.columns([3, 1])
                act = c1.text_input(f"Actividad {i + 1}:", key=f"s10_act_{i}")
                hora = c2.text_input("Hora:", key=f"s10_hora_{i}")
                agenda.append(f"{act} ({hora})")
            alarma = st.text_input("Hora de mi alarma:", key="s10_alarma")
            boton_pista(
                "s10", 1, "Pista: pon primero la actividad que tiene hora fija."
            )
            ok = st.checkbox("Terminé este momento", key="s10_m1_ok")
            completos += int(ok)
            detalle.append(f"M1 agenda: {agenda} alarma: {alarma}")

    if 2 in momentos:
        with st.container(border=True):
            st.markdown("### 🕛 Momento 2: Mediodía — Lista, precios y alarma")
            st.markdown(
                "1. Calcula el total de la compra.\n"
                "2. Pulsa 🔔 **Activar Alarma Ficticia** (arriba). Cuando suene,"
                " detén lo que haces, marca dónde te quedaste y pulsa"
                " **Completar Cadena y Retomar**.\n"
                "3. Revisa tu cuenta con **Miro → Señalo → Compruebo** y marca"
                " «Terminé este momento»."
            )
            compra = PRECIOS_S10[: por_nivel(nivel, 2, 3, 5)]
            st.write(" • ".join(f"{n}: ${p}" for n, p in compra))
            total_real = sum(p for _, p in compra)
            total = st.number_input(
                "Total de la compra ($):", 0, 9999, 0, key="s10_total"
            )
            revise = st.checkbox(
                "Revisé mi cuenta con Miro → Señalo → Compruebo",
                key="s10_revise",
            )
            boton_pista("s10", 2, "Pista: suma de dos en dos.")
            ok = st.checkbox("Terminé este momento", key="s10_m2_ok")
            completos += int(ok)
            detalle.append(
                f"M2 total {total} (correcto {total_real}: {total == total_real})"
                f" revisó: {revise}"
            )

    if 3 in momentos:
        with st.container(border=True):
            st.markdown("### 🌇 Momento 3: Tarde — Fatiga y comunicación")
            st.markdown(
                "1. Imagina que tu batería mental bajó a **3/10**.\n"
                "2. Escribe qué señales notarías y qué pausa tomarías.\n"
                "3. Escribe una frase asertiva para un familiar que te pide"
                " algo en ese momento.\n"
                "4. Marca «Terminé este momento»."
            )
            senales = st.text_input(
                "Señales que notaría:", key="s10_senales"
            )
            pausa = st.selectbox(
                "Pausa que tomaría:",
                [
                    "Elige...",
                    "Pausa de 5 minutos con respiración lenta",
                    "Beber agua y descansar la vista",
                    "Pedir apoyo a un familiar",
                ],
                key="s10_pausa",
            )
            frase = st.text_area("Mi frase asertiva:", key="s10_frase")
            boton_pista(
                "s10",
                3,
                "Pista: usa la estructura Lo que pasa + Cómo me siento + Lo"
                " que propongo.",
            )
            ok = st.checkbox("Terminé este momento", key="s10_m3_ok")
            completos += int(ok)
            detalle.append(f"M3 señales: {senales} pausa: {pausa} frase: {frase}")

    if 4 in momentos:
        with st.container(border=True):
            st.markdown("### 🌙 Momento 4: Noche — Pastillero y análisis")
            st.markdown(
                "1. Prepara un pastillero **simulado** para 2 días (usa fichas"
                " de colores, no medicamentos reales) y marca cada"
                " compartimento listo.\n"
                "2. Escribe 3 eventos del día y cómo los resolviste.\n"
                "3. Marca «Terminé este momento»."
            )
            listos = 0
            c1, c2 = st.columns(2)
            for d, col in zip(["Día 1", "Día 2"], [c1, c2]):
                with col:
                    for franja in ["Mañana", "Noche"]:
                        listos += int(
                            st.checkbox(
                                f"{d} – {franja} (listo)",
                                key=f"s10_pill_{d}_{franja}",
                            )
                        )
            eventos = [
                st.text_area(
                    f"Evento {i + 1}: ¿qué pasó y cómo lo resolví?",
                    key=f"s10_ev_{i}",
                )
                for i in range(3)
            ]
            boton_pista("s10", 4, "Pista: Día 1 primero, luego Día 2.")
            ok = st.checkbox("Terminé este momento", key="s10_m4_ok")
            completos += int(ok)
            detalle.append(f"M4 compartimentos: {listos}/4 eventos: {eventos}")

    ajustes = st.text_input(
        "Ajustes que haré para mañana (ej. horario de alarma o lugar visible):",
        key="s10_ajustes",
    )
    pistas = st.session_state.get("s10_pistas", 0)
    detalle_txt = (
        f"Nivel {nivel} | Momentos completos: {completos}/{len(momentos)} |"
        f" Pistas: {pistas} | " + " | ".join(detalle) + f" | Ajustes: {ajustes}"
    )
    cerrar_sesion(
        10,
        "Simulación de Día Completo",
        detalle_txt,
        f"Completaste {completos} de {len(momentos)} momentos.",
    )


# ==========================================
# SESIÓN 11
# ==========================================
EMOCIONES_S11 = [
    "Frustración",
    "Molestia / Irritabilidad",
    "Ansiedad",
    "Preocupación",
    "Cansancio",
    "Calma",
]
ESCENAS_S11 = [
    {
        "titulo": "Se perdió la nota antes de la junta (trabajo)",
        "relato": (
            "Son las 9:40 AM. A las 10:00 tienes junta con tu jefa y necesitas"
            " la nota donde anotaste los datos del informe. Buscas en tu"
            " escritorio y en tu mochila, pero no la encuentras. Sientes que el"
            " tiempo se acaba y un compañero te apura: «¡Date prisa, ya vamos"
            " tarde!»."
        ),
        "pendientes": [
            "Encontrar la nota o reconstruir los datos (9:40)",
            "Avisar a tu jefa si te retrasas (9:45)",
            "Imprimir el informe (9:50)",
            "Llamar al proveedor (11:00)",
            "Responder el correo del banco (13:00)",
        ],
        "ej_prioridad": (
            "Primero avisar a mi jefa que llegaré unos minutos tarde y luego"
            " reconstruir los datos con el informe impreso."
        ),
        "ej_frase": (
            "Gracias por avisarme; dame un momento para revisar mi registro y"
            " te alcanzo en la sala."
        ),
        "ej_bitacora": (
            "Hoy se me perdió una nota antes de la junta. Me sentí presionado"
            " y ansioso. Hice tres respiraciones lentas, avisé a mi jefa y"
            " reconstruí los datos desde el informe."
        ),
    },
    {
        "titulo": "El recordatorio repetido en casa (familia)",
        "relato": (
            "Son las 4:30 PM. Un familiar te recuerda por tercera vez que hoy"
            " debes recoger un paquete antes de las 6:00 PM. Lo dice con buena"
            " intención, pero te molesta que te lo repitan y sientes que dudan"
            " de ti. Además, empiezas a sentirte cansado."
        ),
        "pendientes": [
            "Recoger el paquete (antes de las 6:00 PM)",
            "Pasar por pan (6:30 PM)",
            "Llamar a tu hermana (7:00 PM)",
            "Revisar tu agenda de mañana (8:30 PM)",
            "Preparar la ropa de mañana (9:00 PM)",
        ],
        "ej_prioridad": (
            "Primero recoger el paquete porque es lo que tiene hora límite más"
            " cercana; después el pan."
        ),
        "ej_frase": (
            "Gracias por recordármelo; ya lo tengo anotado en mi registro y lo"
            " reviso juntos contigo al final de la tarde."
        ),
        "ej_bitacora": (
            "Me recordaron tres veces un pendiente y me molesté. Hice una pausa,"
            " revisé mi bitácora, vi que el paquete era la prioridad y se lo"
            " expliqué con calma a mi familiar."
        ),
    },
    {
        "titulo": "Interrupción mientras reviso mi agenda (trabajo y casa)",
        "relato": (
            "Son las 11:15 AM. Estás revisando tu agenda del día cuando un"
            " compañero te interrumpe con una duda urgente y, al mismo tiempo,"
            " suena tu teléfono: es un familiar que te pregunta si ya hiciste"
            " un pendiente. Sientes prisa y se te mezclan las ideas."
        ),
        "pendientes": [
            "Responder la duda urgente del compañero (11:20)",
            "Devolver la llamada al familiar (11:45)",
            "Entregar el reporte semanal (12:00)",
            "Comer (14:00)",
            "Pagar el recibo de la luz (17:00)",
        ],
        "ej_prioridad": (
            "Primero entregar el reporte de las 12:00, avisando al compañero"
            " que lo atiendo en 10 minutos, y luego devolver la llamada."
        ),
        "ej_frase": (
            "Dame diez minutos para terminar esto y con gusto te ayudo; te"
            " devuelvo la llamada en cuanto termine."
        ),
        "ej_bitacora": (
            "Me interrumpieron dos veces a la vez. Sentí prisa. Respiré, ordené"
            " mis pendientes por hora y avisé a ambos cuándo les respondería."
        ),
    },
]


def sesion_11():
    st.subheader("Sesión 11: Pausa, pienso y sigo")
    nivel = abrir_sesion(11)
    if nivel is None:
        return
    st.write("Secuencia cognitiva: **Pausa → Emoción → Prioridad → Respuesta**")
    st.markdown(
        "**Instrucciones:** Para cada escena: 1) Lee el relato. 2) **Pausa:**"
        " respira lento tres veces y marca la casilla. 3) **Emoción:** elige"
        " cómo te sientes, sin juzgarte. 4) **Prioridad:** elige qué pendiente"
        " haces primero. 5) **Respuesta:** escribe una frase de contención"
        " asertiva. 6) **Bitácora:** escribe con tus palabras qué pasó, cómo te"
        " sentiste y qué decidiste. Si te trabas, abre el ejemplo."
    )
    escenas = ESCENAS_S11[: por_nivel(nivel, 1, 2, 3)]
    n_pend = por_nivel(nivel, 3, 4, 5)
    detalle = []
    completas = 0

    for i, e in enumerate(escenas):
        with st.container(border=True):
            st.markdown(f"### Escena {i + 1}: {e['titulo']}")
            st.info(f"📖 **Relato:** {e['relato']}")
            pendientes = e["pendientes"][:n_pend]
            st.markdown(
                "**Mis pendientes del momento:**\n"
                + "\n".join(f"- {p}" for p in pendientes)
            )
            pausa = st.checkbox(
                "1) Hice mi pausa (3 respiraciones lentas)", key=f"s11_pausa_{i}"
            )
            emocion = st.selectbox(
                "2) Emoción identificada (sin juzgar):",
                EMOCIONES_S11,
                index=None,
                placeholder="Elige una emoción",
                key=f"s11_emo_{i}",
            )
            prioridad = st.radio(
                "3) ¿Qué hago primero?", pendientes, index=None, key=f"s11_pri_{i}"
            )
            frase = st.text_area(
                "4) Mi frase de contención asertiva:", key=f"s11_frase_{i}"
            )
            bitacora = st.text_area(
                "5) Escribo en mi bitácora (qué pasó, cómo me sentí, qué"
                " decidí):",
                key=f"s11_bit_{i}",
            )
            if st.checkbox("💡 Ver ejemplo de respuesta", key=f"s11_ej_{i}"):
                st.success(
                    f"**Prioridad:** {e['ej_prioridad']}\n\n**Frase:**"
                    f" «{e['ej_frase']}»\n\n**Bitácora:** {e['ej_bitacora']}"
                )
            if pausa and emocion and prioridad and frase.strip() and bitacora.strip():
                completas += 1
            detalle.append(
                f"E{i + 1} ({e['titulo']}): pausa {pausa} | emoción {emocion} |"
                f" prioridad {prioridad} | frase {frase} | bitácora {bitacora}"
            )

    acuerdo = st.text_area(
        "Acuerdo con un familiar para recordatorios neutrales (sin"
        " invalidación): ¿cómo me gustaría que me lo recuerden?",
        key="s11_acuerdo",
    )
    detalle_txt = (
        f"Nivel {nivel} | Escenas completas: {completas}/{len(escenas)} | "
        + " || ".join(detalle)
        + f" | Acuerdo: {acuerdo}"
    )
    cerrar_sesion(
        11,
        "Autorregulación y Acuerdos",
        detalle_txt,
        f"Completaste {completas} de {len(escenas)} escenas.",
    )


# ==========================================
# SESIÓN 12
# ==========================================
NOMBRES_PASOS_S12 = [
    "Agenda con pistas",
    "Relato",
    "Pendientes priorizados",
    "Instrucciones",
    "Recuerdo del relato",
    "Kit definitivo",
]
RELATOS_S12 = {
    "bajo": (
        "El miércoles, Elena fue a la panadería a recoger un pan de elote para"
        " su sobrino Pablo.",
        [
            ("¿Qué día fue?", ["miercoles"]),
            ("¿Qué recogió en la panadería?", ["elote"]),
            ("¿Para quién era?", ["pablo"]),
        ],
    ),
    "medio": (
        "El miércoles, Elena fue a la panadería a recoger un pan de elote para"
        " su sobrino Pablo. Después compró una bufanda gris en la tienda de"
        " regalos.",
        [
            ("¿Qué día fue?", ["miercoles"]),
            ("¿Qué recogió en la panadería?", ["elote"]),
            ("¿Para quién era?", ["pablo"]),
            ("¿Qué compró en la tienda de regalos?", ["bufanda"]),
        ],
    ),
    "alto": (
        "El miércoles, Elena fue a la panadería a recoger un pan de elote para"
        " su sobrino Pablo. Después compró una bufanda gris en la tienda de"
        " regalos y pagó con un billete de 100 pesos. Su vecino Hugo la ayudó"
        " a cargar las bolsas y llegó a su casa a las 7:30 PM.",
        [
            ("¿Qué día fue?", ["miercoles"]),
            ("¿Qué recogió en la panadería?", ["elote"]),
            ("¿Para quién era?", ["pablo"]),
            ("¿Qué compró en la tienda de regalos?", ["bufanda"]),
            ("¿A qué hora llegó a su casa?", ["7 30"]),
        ],
    ),
}
PENDIENTES_S12 = [
    ("Entregar el informe en la oficina", "10:00"),
    ("Llamar a mi mamá", "12:30"),
    ("Pagar el recibo de la luz", "14:00"),
    ("Recoger el paquete", "16:30"),
    ("Comprar pan para la cena", "18:15"),
    ("Revisar mi agenda de mañana", "20:00"),
]
INSTRUCCIONES_S12 = [
    "Abrir el Sobre 2",
    "Colocar la Tarjeta Azul junto al Reloj",
    "Marcar la X en la hoja",
    "Guardar la Ficha Verde en el Kit",
]
KIT_S12 = [
    "Tarjeta de registro",
    "Tarjetas posictales / recordatorio",
    "Claves de memoria",
    "Semáforo de fatiga",
]
PISTAS_S12 = {
    1: "Pista: escribe la actividad y su hora, por ejemplo «Llamar al banco – 11:00».",
    2: "Pista: fíjate en el día, el lugar y las personas.",
    3: "Pista: ordena por hora, de la más temprana a la más tarde.",
    4: "Pista: repítelas en voz baja: Preparar → Hacer → Revisar.",
    5: "Pista: piensa en la panadería y en quién era el pan.",
    6: "Pista: el kit debe tener todo para registrar y para regularte.",
}


def _continuar_s12(paso):
    """Botón de avance. En el paso sorpresa dispara la alarma SIN guía."""
    pendiente = st.session_state.get("s12_alarma_disparada") and not (
        st.session_state.get("s12_retoma_hecha")
    )
    if pendiente:
        st.error("🔔 ¡Suena una alarma!")
        sel = st.selectbox(
            "¿En qué punto de la tarea te habías quedado?",
            ["Elige..."] + NOMBRES_PASOS_S12,
            key="s12_retoma_sel",
        )
        if st.button("Confirmar mi retoma", key="s12_retoma_btn"):
            ok = sel == NOMBRES_PASOS_S12[paso - 1]
            st.session_state.s12_retoma_ok = ok
            st.session_state.s12_retoma_hecha = True
            registrar_evento(
                "Sesión 12",
                "Retoma tras alarma sorpresiva",
                f"Retoma exacta: {ok}",
            )
            st.rerun()
        return
    if st.button("➡️ Continuar", key=f"s12_cont_{paso}", type="primary"):
        if paso == st.session_state.s12_paso_alarma and not st.session_state.get(
            "s12_alarma_disparada"
        ):
            st.session_state.alarma_activa = True
            st.session_state.alarma_sin_guia = True
            st.session_state.sonar_alarma = True
            st.session_state.inicio_alarma = time.time()
            st.session_state.s12_alarma_disparada = True
            registrar_evento(
                "Sesión 12", "Alarma sorpresiva", "Alarma activada sin guía"
            )
        else:
            st.session_state.s12_paso = paso + 1
        st.rerun()


def sesion_12():
    st.subheader("Sesión 12: Circuito final autónomo y Kit definitivo")
    nivel = abrir_sesion(12)
    if nivel is None:
        return
    datos = st.session_state.setdefault("s12_datos", {})
    paso = st.session_state.setdefault("s12_paso", 1)
    st.session_state.setdefault("s12_paso_alarma", random.choice([3, 4]))
    segundos = por_nivel(nivel, 25, 20, 15)

    st.markdown(
        "**Instrucciones generales:** Este es el circuito final: son 6 pasos"
        " y lo harás con la mayor autonomía posible. En cada paso lee la"
        " indicación y pulsa «Continuar». Puedes pedir una 💡 pista, pero se"
        " contará. Durante el circuito **puede sonar una alarma sorpresa**:"
        " actúa con lo que aprendiste, sin ayuda."
    )
    st.progress(
        min(paso - 1, 6) / 6,
        text=f"Paso {min(paso, 6)} de 6: {NOMBRES_PASOS_S12[min(paso, 6) - 1]}",
    )
    st.markdown(f"#### Paso {paso}: {NOMBRES_PASOS_S12[paso - 1]}")

    if paso == 1:
        n = por_nivel(nivel, 2, 3, 4)
        st.write(
            f"Escribe en tu agenda **{n} pistas** (recordatorios cortos) para"
            " mañana, cada una con su hora. Ejemplo: «Llamar al banco – 11:00»."
        )
        datos["agenda"] = [
            st.text_input(f"Pista {i + 1}:", key=f"s12_ag_{i}") for i in range(n)
        ]
        boton_pista("s12", 1, PISTAS_S12[1])
        _continuar_s12(1)

    elif paso == 2:
        texto, _ = RELATOS_S12[nivel]
        st.write(
            f"Pulsa «Ver relato». Aparecerá {segundos} segundos y"
            " desaparecerá. Más adelante te preguntaré por sus datos."
        )
        if st.button("👁️ Ver relato", key="s12_ver_rel"):
            st.session_state.s12_rel_visto = True
            mostrar_temporizado(
                texto,
                segundos,
                mensaje_final="⏳ El relato desapareció. Pulsa «Continuar».",
                alto=200,
            )
        boton_pista("s12", 2, PISTAS_S12[2])
        if st.session_state.get("s12_rel_visto"):
            _continuar_s12(2)

    elif paso == 3:
        n = por_nivel(nivel, 3, 5, 6)
        lista = PENDIENTES_S12[:n]
        mezclados = [f"{t} — {h}" for t, h in lista]
        random.Random(f"s12-pend-{n}").shuffle(mezclados)
        st.write(
            "Estos son tus pendientes de mañana. Selecciónalos **en orden, del"
            " más urgente (hora más cercana) al menos urgente**:"
        )
        st.markdown("\n".join(f"- {m}" for m in mezclados))
        orden = st.multiselect(
            "Orden de prioridad:", mezclados, key="s12_orden"
        )
        datos["orden"] = list(orden)
        datos["orden_esperado"] = [f"{t} — {h}" for t, h in lista]
        boton_pista("s12", 3, PISTAS_S12[3])
        _continuar_s12(3)

    elif paso == 4:
        n = por_nivel(nivel, 2, 3, 4)
        instr = INSTRUCCIONES_S12[:n]
        st.write(
            f"Pulsa «Ver instrucciones»: verás {n} instrucciones durante"
            f" {segundos} segundos. Después selecciónalas en el orden en que"
            " las viste."
        )
        if st.button("👁️ Ver instrucciones", key="s12_ver_ins"):
            mostrar_temporizado(
                "<br>".join(f"{i + 1}. {t}" for i, t in enumerate(instr)),
                segundos,
                mensaje_final=(
                    "⏳ Las instrucciones desaparecieron. Ordénalas abajo."
                ),
                alto=220,
            )
        mezcladas = list(instr)
        random.Random(f"s12-ins-{n}").shuffle(mezcladas)
        orden_i = st.multiselect(
            "Instrucciones en el orden en que las viste:",
            mezcladas,
            key="s12_orden_ins",
        )
        datos["instr"] = list(orden_i)
        datos["instr_esperado"] = instr
        boton_pista("s12", 4, PISTAS_S12[4])
        _continuar_s12(4)

    elif paso == 5:
        _, preguntas = RELATOS_S12[nivel]
        st.write("Después de la demora, escribe los datos del relato:")
        resp = [
            st.text_input(p, key=f"s12_dato_{i}")
            for i, (p, _) in enumerate(preguntas)
        ]
        datos["datos_ok"] = sum(
            1
            for r, (_, reqs) in zip(resp, preguntas)
            if contiene(r, *reqs)
        )
        datos["datos_total"] = len(preguntas)
        datos["datos_resp"] = resp
        boton_pista("s12", 5, PISTAS_S12[5])
        _continuar_s12(5)

    else:
        st.write("Organiza tu **Kit definitivo**: elige los elementos que lo componen.")
        kit = st.multiselect("Elementos del kit:", KIT_S12, key="s12_kit")
        boton_pista("s12", 6, PISTAS_S12[6])

        n_ag = len(datos.get("agenda", []))
        ag_ok = sum(1 for a in datos.get("agenda", []) if a.strip())
        orden_ok = datos.get("orden") == datos.get("orden_esperado")
        instr_ok = datos.get("instr") == datos.get("instr_esperado")
        pistas = st.session_state.get("s12_pistas", 0)
        retoma = st.session_state.get("s12_retoma_ok")
        cadena = st.session_state.get("s12_alarma_disparada") and (
            not st.session_state.alarma_activa
        )
        detalle = (
            f"Nivel {nivel} | Agenda: {ag_ok}/{n_ag} {datos.get('agenda')} |"
            f" Pendientes en orden: {orden_ok} | Instrucciones en orden:"
            f" {instr_ok} | Datos del relato: {datos.get('datos_ok', 0)}/"
            f"{datos.get('datos_total', 0)} {datos.get('datos_resp')} | Alarma"
            f" sin guía — retoma exacta: {retoma} | cadena completada:"
            f" {bool(cadena)} | Pistas: {pistas} | Kit: {', '.join(kit)}"
        )
        resumen = (
            f"Datos del relato: {datos.get('datos_ok', 0)} de"
            f" {datos.get('datos_total', 0)}. Pistas usadas: {pistas}."
        )
        cerrar_sesion(12, "Circuito Final y Kit Definitivo", detalle, resumen)


# ==========================================
# ENCABEZADO Y PANEL TRANSVERSAL
# ==========================================
st.title("🧠 Programa de Entrenamiento Cognitivo y Adherencia (Sesiones 1–12)")
st.caption(
    "Equipo Epilepsia · Actividad exclusivamente simulada con fines"
    " psicoeducativos y de entrenamiento funcional. No evalúa ni modifica dosis"
    " reales."
)

col1, col2, col3 = st.columns([2.2, 1, 1.2])

with col1:
    bat = st.session_state.bateria_actual
    st.metric("🔋 Batería mental actual (1 = muy fatigado · 10 = sin fatiga)", f"{bat}/10")
    st.caption(
        "Se registra al inicio y al final de cada sesión; según su valor, el"
        " programa ajusta la dificultad y la cantidad de ejercicios."
    )

with col2:
    st.write("")
    if st.button("🔔 Activar Alarma Ficticia", use_container_width=True):
        st.session_state.alarma_activa = True
        st.session_state.alarma_sin_guia = False
        st.session_state.sonar_alarma = True
        st.session_state.inicio_alarma = time.time()
        registrar_evento(
            "Transversal", "Alarma ficticia", "Alarma activada con señal sonora"
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
            tiempo = round(time.time() - st.session_state.inicio_alarma, 1)
            st.session_state.alarma_activa = False
            st.session_state.alarma_sin_guia = False
            registrar_evento(
                "Transversal",
                "Cadena de adherencia completada",
                f"Tiempo de respuesta: {tiempo} seg",
            )
            st.toast(f"Cadena registrada en {tiempo}s. ¡Retoma tu tarea!")
            st.rerun()

if st.session_state.alarma_activa:
    if st.session_state.alarma_sin_guia:
        st.error("🚨 **¡ALARMA!**")
    else:
        st.error(
            "🚨 **¡ALARMA FICTICIA ACTIVA!**\n\n"
            "1. Detén la actividad y marca dónde te quedaste (*Miro → Señalo →"
            " Compruebo*).\n"
            "2. Consulta la tarjeta de indicación simulada.\n"
            "3. Toma la ficha representativa y anota el marcaje en la"
            " bitácora.\n"
            "4. Pulsa *'Completar Cadena y Retomar'* para volver a la tarea."
        )

st.divider()

# ==========================================
# MENÚ LATERAL DE MÓDULOS Y TARJETA
# ==========================================
MOD1 = "1. Atención, Señales y Rutina (S1, S2, S7)"
MOD2 = "2. Fatiga y Autorregulación (S3, S11)"
MOD3 = "3. Memoria de Trabajo y Ejecutivas (S4, S5, S6)"
MOD4 = "4. Memoria Episódica y Comunicación (S8, S9)"
MOD5 = "5. Circuito Integrador Final (S10, S12)"
MOD6 = "📊 Resultados para el terapeuta"

st.sidebar.text_input("Nombre o ID del paciente:", key="paciente")
st.sidebar.header("📋 Módulos del Programa")
modulo = st.sidebar.radio(
    "Selecciona el módulo:", [MOD1, MOD2, MOD3, MOD4, MOD5, MOD6]
)
progreso = [
    ("✅" if st.session_state.get(f"s{n}_guardada") else "⬜") + f"S{n}"
    for n in range(1, 13)
]
st.sidebar.caption("Progreso: " + " ".join(progreso))
st.sidebar.divider()
mostrar_tarjeta_registro(ubicacion_key="sidebar")

# ==========================================
# MÓDULOS
# ==========================================
if modulo == MOD1:
    tab1, tab2, tab3 = st.tabs([
        "🚦 S1: Semáforo, Estrategias y Rutina",
        "🧭 S2: Misión del Explorador",
        "🔄 S7: Matrices de Alternancia",
    ])
    with tab1:
        sesion_1()
    with tab2:
        sesion_2()
    with tab3:
        sesion_7()

elif modulo == MOD2:
    tab1, tab2 = st.tabs([
        "🔋 S3: Termómetro de Fatiga y Pausa",
        "🧘 S11: Pausa, Pienso y Sigo",
    ])
    with tab1:
        sesion_3()
    with tab2:
        sesion_11()

elif modulo == MOD3:
    tab1, tab2, tab3 = st.tabs([
        "🔐 S4: Escape de Instrucciones",
        "🛒 S5: Memoria de Trabajo",
        "🧩 S6: Soluciono Problemas",
    ])
    with tab1:
        sesion_4()
    with tab2:
        sesion_5()
    with tab3:
        sesion_6()

elif modulo == MOD4:
    tab1, tab2 = st.tabs([
        "📖 S8: Recuerdo lo Importante",
        "💬 S9: Me Comunico Mejor",
    ])
    with tab1:
        sesion_8()
    with tab2:
        sesion_9()

elif modulo == MOD5:
    tab1, tab2 = st.tabs([
        "🏆 S10: Simulación de Día Completo",
        "🎯 S12: Circuito Final y Kit",
    ])
    with tab1:
        sesion_10()
    with tab2:
        sesion_12()

else:
    st.subheader("📊 Resultados para el terapeuta")
    st.caption(
        "Los resultados se guardan automáticamente en la carpeta"
        f" `{os.path.dirname(st.session_state.archivo_resultados)}`. También"
        " puedes descargarlos aquí."
    )
    filas_bat = []
    for n in range(1, 13):
        ini = st.session_state.get(f"s{n}_inicio")
        fin = st.session_state.get(f"s{n}_fin")
        if ini is not None:
            filas_bat.append({
                "Sesión": n,
                "Batería inicial": ini,
                "Nivel aplicado": nivel_de_bateria(ini),
                "Batería final": fin if fin is not None else "—",
                "Guardada": "Sí" if st.session_state.get(f"s{n}_guardada") else "No",
            })
    if filas_bat:
        st.markdown("#### Batería mental por sesión")
        st.dataframe(pd.DataFrame(filas_bat), use_container_width=True)

    if len(st.session_state.registros) == 0:
        st.info("Aún no hay registros en esta sesión.")
    else:
        df = pd.DataFrame(st.session_state.registros)
        st.markdown("#### Bitácora general")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="⬇️ Descargar resultados (CSV / Excel)",
            data=csv,
            file_name=f"resultados_programa_{datetime.date.today()}.csv",
            mime="text/csv",
            type="primary",
        )
