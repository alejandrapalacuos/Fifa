import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Configuración para móviles
st.set_page_config(
    page_title="Liga FIFA - Apuestas",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar cerrado en móviles
)

# Cargar datos del torneo
def load_tournament_data():
    try:
        with open('data/tournament_data.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "groups": {
                "Grupo A": ["Liverpool", "Bayern", "Atlético Nacional", "Barcelona"],
                "Grupo B": ["Real Madrid", "AC Milán", "Independiente Medellín"]
            },
            "players": {},
            "matches": [],
            "semifinals": [],
            "final": None,
            "third_place": None,
            "phase": "groups",
            "bets": []
        }

def save_tournament_data(data):
    os.makedirs('data', exist_ok=True)
    with open('data/tournament_data.json', 'w') as f:
        json.dump(data, f, indent=2)

# Inicializar datos
if 'tournament_data' not in st.session_state:
    st.session_state.tournament_data = load_tournament_data()

# Header optimizado para móviles
st.markdown("""
    <style>
    .main-header {
        font-size: 24px !important;
        text-align: center;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 18px !important;
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"> LIGA FIFA - APUESTAS </div>', unsafe_allow_html=True)

# Sidebar móvil optimizado
with st.sidebar:
    st.markdown("### Panel de Control")

    # Solo mostrar configuración si es el administrador
    with st.expander(" Configuración (Admin)"):
        # Registrar jugadores
        st.markdown("#### Registrar Jugadores")
        nuevo_jugador = st.text_input("Tu nombre")

        if st.button("Unirse al Juego") and nuevo_jugador:
            if nuevo_jugador not in st.session_state.tournament_data["players"]:
                st.session_state.tournament_data["players"][nuevo_jugador] = {
                    "dinero": 1000,
                    "apuestas_ganadas": 0,
                    "apuestas_perdidas": 0
                }
                save_tournament_data(st.session_state.tournament_data)
                st.success(f" {nuevo_jugador} unido con $1000")
                st.rerun()
            else:
                st.error(" Este nombre ya existe")

    # Panel de apuestas (siempre visible)
    mostrar_panel_apuestas_movil()

# Función para panel de apuestas móvil
def mostrar_panel_apuestas_movil():
    st.markdown("###  Hacer Apuesta")

    if not st.session_state.tournament_data["players"]:
        st.info(" Registra tu nombre arriba para apostar")
        return

    jugador = st.selectbox("Eres:", list(st.session_state.tournament_data["players"].keys()))

    # Mostrar dinero disponible
    dinero_actual = st.session_state.tournament_data["players"][jugador]["dinero"]
    st.markdown(f"**Dinero disponible:** `${dinero_actual}`")

    # Partidos disponibles para apostar
    partidos_disponibles = obtener_partidos_sin_resultado()

    if not partidos_disponibles:
        st.info(" No hay partidos para apostar")
        return

    partido_apostar = st.selectbox(
        "Partido:",
        partidos_disponibles,
        format_func=lambda x: f"{x['local']} vs {x['visitante']}"
    )

    # Opciones de apuesta en botones
    st.markdown("**Tu predicción:**")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(f" {partido_apostar['local']}", use_container_width=True):
            hacer_apuesta(jugador, partido_apostar, "Local", dinero_actual)

    with col2:
        if st.button(" Empate", use_container_width=True):
            hacer_apuesta(jugador, partido_apostar, "Empate", dinero_actual)

    with col3:
        if st.button(f" {partido_apostar['visitante']}", use_container_width=True):
            hacer_apuesta(jugador, partido_apostar, "Visitante", dinero_actual)

    # Apuesta personalizada
    with st.expander(" Apuesta personalizada"):
        opcion_apuesta = st.selectbox("Predicción", ["Local", "Empate", "Visitante"])
        monto_apuesta = st.number_input("Monto", min_value=10, max_value=dinero_actual, value=100, step=10)

        if st.button("Apostar", type="primary"):
            hacer_apuesta(jugador, partido_apostar, opcion_apuesta, dinero_actual, monto_apuesta)

def hacer_apuesta(jugador, partido, prediccion, dinero_actual, monto=None):
    if not monto:
        monto = min(200, dinero_actual)  # Apuesta rápida de $200

    if monto > dinero_actual:
        st.error(" No tienes suficiente dinero")
        return

    nueva_apuesta = {
        "jugador": jugador,
        "partido": f"{partido['local']} vs {partido['visitante']}",
        "local": partido['local'],
        "visitante": partido['visitante'],
        "prediccion": prediccion,
        "monto": monto,
        "fase": partido.get('fase', 'groups'),
        "procesada": False
    }

    st.session_state.tournament_data["players"][jugador]["dinero"] -= monto
    st.session_state.tournament_data["bets"].append(nueva_apuesta)
    save_tournament_data(st.session_state.tournament_data)
    st.success(f" Apostaste ${monto} por {prediccion}")
    st.rerun()

# Sección principal - Diseño móvil first
tab1, tab2, tab3, tab4 = st.tabs([" Torneo", " Apuestas", " Posiciones", " Admin"])

with tab1:
    mostrar_torneo()

with tab2:
    mostrar_apuestas()

with tab3:
    mostrar_posiciones()

with tab4:
    mostrar_admin()

def mostrar_torneo():
    st.markdown("### Fase de Grupos")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Grupo A**")
        df_a = calcular_tabla("Grupo A")
        st.dataframe(df_a, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**Grupo B**")
        df_b = calcular_tabla("Grupo B")
        st.dataframe(df_b, use_container_width=True, hide_index=True)

    # Próximos partidos
    st.markdown("###  Próximos Partidos")
    partidos_futuros = obtener_partidos_sin_resultado()[:3]  # Mostrar solo 3
    for partido in partidos_futuros:
        st.write(f"**{partido['local']}** vs **{partido['visitante']}**")

def mostrar_apuestas():
    st.markdown("###  Tus Apuestas")

    if not st.session_state.tournament_data["players"]:
        st.info(" Regístrate en el panel de control")
        return

    jugador_actual = list(st.session_state.tournament_data["players"].keys())[0]  # Para demo

    apuestas_jugador = [a for a in st.session_state.tournament_data["bets"] if a["jugador"] == jugador_actual]

    if not apuestas_jugador:
        st.info(" Aún no has hecho apuestas")
        return

    for apuesta in reversed(apuestas_jugador):
        estado = " GANADA" if apuesta.get("resultado") == "GANADA" else " PERDIDA" if apuesta.get("resultado") == "PERDIDA" else " PENDIENTE"
        st.write(f"**{apuesta['partido']}**")
        st.write(f"Predicción: {apuesta['prediccion']} - ${apuesta['monto']} - {estado}")
        if apuesta.get("ganancias"):
            st.write(f"Ganancias: ${apuesta['ganancias']}")
        st.markdown("---")

def mostrar_posiciones():
    st.markdown("###  Ranking de Apostadores")

    if not st.session_state.tournament_data["players"]:
        st.info(" Aún no hay jugadores")
        return

    jugadores_data = []
    for jugador, datos in st.session_state.tournament_data["players"].items():
        jugadores_data.append({
            "Jugador": jugador,
            "Dinero": f"${datos['dinero']}",
            "Ganadas": datos["apuestas_ganadas"],
            "Perdidas": datos["apuestas_perdidas"],
            "Balance": datos["apuestas_ganadas"] - datos["apuestas_perdidas"]
        })

    df_jugadores = pd.DataFrame(jugadores_data)
    df_jugadores = df_jugadores.sort_values("Dinero", ascending=False)
    st.dataframe(df_jugadores, use_container_width=True, hide_index=True)

def mostrar_admin():
    st.markdown("###  Panel de Administración")

    # Registrar resultados
    st.markdown("#### Registrar Resultados")
    partidos_sin_resultado = obtener_partidos_sin_resultado()

    if partidos_sin_resultado:
        partido_registrar = st.selectbox(
            "Seleccionar partido:",
            partidos_sin_resultado,
            format_func=lambda x: f"{x['local']} vs {x['visitante']}",
            key="admin_partido"
        )

        col1, col2 = st.columns(2)
        with col1:
            goles_local = st.number_input("Goles local", min_value=0, value=0, key="admin_gl")
        with col2:
            goles_visitante = st.number_input("Goles visitante", min_value=0, value=0, key="admin_gv")

        if st.button("Registrar Resultado", type="primary"):
            registrar_resultado_admin(partido_registrar, goles_local, goles_visitante)
    else:
        st.info(" Todos los partidos tienen resultado")

    # Avanzar fases
    st.markdown("#### Control del Torneo")
    if st.session_state.tournament_data["phase"] == "groups":
        if st.button("Avanzar a Semifinales"):
            clasificados = obtener_clasificados_semifinales()
            if len(clasificados) == 4:
                st.session_state.tournament_data["phase"] = "semifinals"
                save_tournament_data(st.session_state.tournament_data)
                st.success(" Avanzando a Semifinales!")
                st.rerun()

    # Reiniciar
    if st.button("Reiniciar Torneo", type="secondary"):
        st.session_state.tournament_data = load_tournament_data()
        save_tournament_data(st.session_state.tournament_data)
        st.success("Torneo reiniciado")
        st.rerun()

def registrar_resultado_admin(partido, goles_local, goles_visitante):
    nuevo_partido = {
        "fase": partido.get('fase', 'groups'),
        "grupo": partido.get('grupo'),
        "local": partido['local'],
        "visitante": partido['visitante'],
        "goles_local": goles_local,
        "goles_visitante": goles_visitante,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    if partido.get('fase') == 'groups':
        st.session_state.tournament_data["matches"].append(nuevo_partido)
    elif partido.get('fase') == 'semifinals':
        nuevo_partido["ganador"] = partido['local'] if goles_local > goles_visitante else partido['visitante'] if goles_visitante > goles_local else "Empate"
        st.session_state.tournament_data["semifinals"].append(nuevo_partido)

    procesar_apuestas_partido(nuevo_partido)
    save_tournament_data(st.session_state.tournament_data)
    st.success(" Resultado registrado y apuestas procesadas!")
    st.rerun()

# Funciones existentes (mantener igual)
def calcular_tabla(grupo):
    equipos = st.session_state.tournament_data["groups"][grupo]
    partidos = [p for p in st.session_state.tournament_data["matches"]
                if p.get("grupo") == grupo and p.get("fase") == "groups"]

    tabla = {}
    for equipo in equipos:
        tabla[equipo] = {"PJ": 0, "G": 0, "E": 0, "P": 0, "GF": 0, "GC": 0, "DG": 0, "PTS": 0}

    for partido in partidos:
        local = partido["local"]
        visitante = partido["visitante"]
        gl = partido["goles_local"]
        gv = partido["goles_visitante"]

        for equipo, goles_favor, goles_contra in [(local, gl, gv), (visitante, gv, gl)]:
            if equipo in tabla:
                tabla[equipo]["PJ"] += 1
                tabla[equipo]["GF"] += goles_favor
                tabla[equipo]["GC"] += goles_contra
                tabla[equipo]["DG"] = tabla[equipo]["GF"] - tabla[equipo]["GC"]

        if gl > gv:
            tabla[local]["G"] += 1
            tabla[local]["PTS"] += 3
            tabla[visitante]["P"] += 1
        elif gv > gl:
            tabla[visitante]["G"] += 1
            tabla[visitante]["PTS"] += 3
            tabla[local]["P"] += 1
        else:
            tabla[local]["E"] += 1
            tabla[visitante]["E"] += 1
            tabla[local]["PTS"] += 1
            tabla[visitante]["PTS"] += 1

    df = pd.DataFrame.from_dict(tabla, orient='index')
    df = df.reset_index().rename(columns={"index": "Equipo"})
    df = df.sort_values(by=["PTS", "DG", "GF"], ascending=[False, False, False])
    return df

def obtener_partidos_sin_resultado():
    partidos_sin_resultado = []

    # Partidos de grupos sin jugar
    for grupo, equipos in st.session_state.tournament_data["groups"].items():
        for i, local in enumerate(equipos):
            for j, visitante in enumerate(equipos):
                if i != j:
                    partido_jugado = any(
                        p.get("local") == local and p.get("visitante") == visitante
                        and p.get("fase") == "groups"
                        for p in st.session_state.tournament_data["matches"]
                    )
                    if not partido_jugado:
                        partidos_sin_resultado.append({
                            "local": local,
                            "visitante": visitante,
                            "fase": "groups",
                            "grupo": grupo
                        })

    return partidos_sin_resultado

def obtener_clasificados_semifinales():
    clasificados = []
    for grupo in ["Grupo A", "Grupo B"]:
        df = calcular_tabla(grupo)
        top2 = df.head(2)["Equipo"].tolist()
        clasificados.extend(top2)
    return clasificados

def procesar_apuestas_partido(partido):
    partido_key = f"{partido['local']} vs {partido['visitante']}"
    goles_local = partido['goles_local']
    goles_visitante = partido['goles_visitante']

    if goles_local > goles_visitante:
        resultado_real = "Local"
    elif goles_visitante > goles_local:
        resultado_real = "Visitante"
    else:
        resultado_real = "Empate"

    for apuesta in st.session_state.tournament_data["bets"]:
        if not apuesta["procesada"] and apuesta["partido"] == partido_key:
            if apuesta["prediccion"] == resultado_real:
                monto_ganado = apuesta["monto"] * 2
                st.session_state.tournament_data["players"][apuesta["jugador"]]["dinero"] += monto_ganado
                st.session_state.tournament_data["players"][apuesta["jugador"]]["apuestas_ganadas"] += 1
                apuesta["resultado"] = "GANADA"
                apuesta["ganancias"] = monto_ganado
            else:
                st.session_state.tournament_data["players"][apuesta["jugador"]]["apuestas_perdidas"] += 1
                apuesta["resultado"] = "PERDIDA"
                apuesta["ganancias"] = 0

            apuesta["procesada"] = True
