import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Configuración optimizada para móviles
st.set_page_config(
    page_title="Liga FIFA - Sportsbook",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS optimizado para móviles
st.markdown("""
<style>
    /* Optimizaciones móviles */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.5rem !important;
            padding: 1rem !important;
        }
        .section-header {
            font-size: 1.1rem !important;
            padding: 0.5rem !important;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem !important;
            font-size: 0.9rem !important;
        }
    }
    
    /* Prevenir scroll horizontal */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Mejorar rendimiento de elementos */
    .bet-card, .odds-button, .balance-card {
        transform: translateZ(0);
        backface-visibility: hidden;
        perspective: 1000;
    }
    
    /* Colores corporativos */
    :root {
        --primary: #1e40af;
        --primary-dark: #1e3a8a;
        --secondary: #dc2626;
        --success: #059669;
        --warning: #d97706;
        --dark: #0f172a;
        --light: #f8fafc;
        --gray: #64748b;
    }
    
    .main-header {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0 0 15px 15px;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 700;
        font-size: 2rem;
        letter-spacing: 1px;
    }
    
    .section-header {
        background: var(--dark);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-weight: 600;
        font-size: 1.2rem;
        border-left: 4px solid var(--secondary);
    }
    
    .bet-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 0.5rem 0;
    }
    
    .bet-card.won {
        border-left: 4px solid var(--success);
    }
    
    .bet-card.lost {
        border-left: 4px solid var(--secondary);
    }
    
    .bet-card.pending {
        border-left: 4px solid var(--warning);
    }
    
    .odds-button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white;
        border: none;
        padding: 0.75rem;
        border-radius: 6px;
        font-weight: 600;
        width: 100%;
        margin: 0.25rem 0;
        text-align: center;
    }
    
    .balance-card {
        background: linear-gradient(135deg, var(--success) 0%, #047857 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .stats-card {
        background: var(--light);
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 0.75rem;
        text-align: center;
        margin: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# Cache para mejorar rendimiento
@st.cache_data(ttl=60)
def load_tournament_data():
    try:
        with open('data/tournament_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "groups": {
                "Grupo A": ["Liverpool", "Bayern Munich", "Atlético Nacional", "Barcelona"],
                "Grupo B": ["Real Madrid", "AC Milan", "Independiente Medellín", "Paris SG"]
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
    with open('data/tournament_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Inicialización optimizada
if 'tournament_data' not in st.session_state:
    st.session_state.tournament_data = load_tournament_data()
if 'initialized' not in st.session_state:
    st.session_state.initialized = True

# Funciones auxiliares con cache
@st.cache_data(ttl=30)
def calcular_tabla(grupo):
    data = st.session_state.tournament_data
    equipos = data["groups"][grupo]
    partidos = [p for p in data["matches"] if p.get("grupo") == grupo and p.get("fase") == "groups"]

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
    data = st.session_state.tournament_data
    partidos_sin_resultado = []

    for grupo, equipos in data["groups"].items():
        for i, local in enumerate(equipos):
            for j, visitante in enumerate(equipos):
                if i != j:
                    partido_jugado = any(
                        p.get("local") == local and p.get("visitante") == visitante
                        and p.get("fase") == "groups"
                        for p in data["matches"]
                    )
                    if not partido_jugado:
                        partidos_sin_resultado.append({
                            "local": local,
                            "visitante": visitante,
                            "fase": "groups",
                            "grupo": grupo
                        })
    return partidos_sin_resultado

def procesar_apuestas_partido(partido):
    data = st.session_state.tournament_data
    partido_key = f"{partido['local']} vs {partido['visitante']}"
    goles_local = partido['goles_local']
    goles_visitante = partido['goles_visitante']

    if goles_local > goles_visitante:
        resultado_real = "Local"
    elif goles_visitante > goles_local:
        resultado_real = "Visitante"
    else:
        resultado_real = "Empate"

    for apuesta in data["bets"]:
        if not apuesta["procesada"] and apuesta["partido"] == partido_key:
            if apuesta["prediccion"] == resultado_real:
                monto_ganado = apuesta["monto"] * 2
                data["players"][apuesta["jugador"]]["dinero"] += monto_ganado
                data["players"][apuesta["jugador"]]["apuestas_ganadas"] += 1
                apuesta["resultado"] = "GANADA"
                apuesta["ganancias"] = monto_ganado
            else:
                data["players"][apuesta["jugador"]]["apuestas_perdidas"] += 1
                apuesta["resultado"] = "PERDIDA"
                apuesta["ganancias"] = 0
            apuesta["procesada"] = True

# UI Functions simplificadas
def mostrar_panel_apuestas():
    st.markdown("**HACER APUESTA**")

    if not st.session_state.tournament_data["players"]:
        st.info("Registra tu nombre para comenzar")
        return

    jugador = st.selectbox("Jugador", list(st.session_state.tournament_data["players"].keys()))
    dinero_actual = st.session_state.tournament_data["players"][jugador]["dinero"]
    
    st.markdown(f'<div class="balance-card">Balance: ${dinero_actual}</div>', unsafe_allow_html=True)

    partidos_disponibles = obtener_partidos_sin_resultado()
    if not partidos_disponibles:
        st.info("No hay partidos disponibles")
        return

    partido_apostar = st.selectbox(
        "Partido",
        partidos_disponibles,
        format_func=lambda x: f"{x['local']} vs {x['visitante']}"
    )

    # Botones de apuesta simplificados
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(partido_apostar['local'], use_container_width=True):
            hacer_apuesta_simple(jugador, partido_apostar, "Local", dinero_actual)
    with col2:
        if st.button("EMPATE", use_container_width=True):
            hacer_apuesta_simple(jugador, partido_apostar, "Empate", dinero_actual)
    with col3:
        if st.button(partido_apostar['visitante'], use_container_width=True):
            hacer_apuesta_simple(jugador, partido_apostar, "Visitante", dinero_actual)

def hacer_apuesta_simple(jugador, partido, prediccion, dinero_actual):
    monto = min(100, dinero_actual)
    if monto > dinero_actual:
        st.error("Fondos insuficientes")
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
    st.success(f"Apuesta confirmada: ${monto}")
    st.rerun()

def mostrar_torneo():
    st.markdown("**FASE DE GRUPOS**")
    
    # Usar columns responsivas
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Grupo A**")
        df_a = calcular_tabla("Grupo A")
        st.dataframe(df_a, use_container_width=True, hide_index=True)
    
    with col2:
        st.write("**Grupo B**")
        df_b = calcular_tabla("Grupo B")
        st.dataframe(df_b, use_container_width=True, hide_index=True)

def mostrar_apuestas():
    st.markdown("**MIS APUESTAS**")

    if not st.session_state.tournament_data["players"]:
        st.info("Regístrate para ver apuestas")
        return

    jugador_actual = st.selectbox(
        "Jugador",
        list(st.session_state.tournament_data["players"].keys()),
        key="apuestas_jugador"
    )

    apuestas_jugador = [a for a in st.session_state.tournament_data["bets"] if a["jugador"] == jugador_actual]

    if not apuestas_jugador:
        st.info("No hay apuestas")
        return

    for apuesta in apuestas_jugador[-5:]:  # Mostrar solo las últimas 5
        estado = "GANADA" if apuesta.get("resultado") == "GANADA" else "PERDIDA" if apuesta.get("resultado") == "PERDIDA" else "PENDIENTE"
        st.write(f"**{apuesta['partido']}**")
        st.write(f"{apuesta['prediccion']} - ${apuesta['monto']} - {estado}")
        if apuesta.get("ganancias"):
            st.write(f"Ganancias: ${apuesta['ganancias']}")
        st.divider()

def mostrar_posiciones():
    st.markdown("**RANKING**")

    if not st.session_state.tournament_data["players"]:
        st.info("No hay jugadores")
        return

    jugadores_data = []
    for jugador, datos in st.session_state.tournament_data["players"].items():
        jugadores_data.append({
            "Jugador": jugador,
            "Dinero": f"${datos['dinero']}",
            "Ganadas": datos["apuestas_ganadas"],
            "Perdidas": datos["apuestas_perdidas"]
        })

    df_jugadores = pd.DataFrame(jugadores_data)
    df_jugadores = df_jugadores.sort_values("Dinero", ascending=False)
    st.dataframe(df_jugadores, use_container_width=True, hide_index=True)

def mostrar_admin():
    st.markdown("**ADMINISTRACIÓN**")

    partidos_sin_resultado = obtener_partidos_sin_resultado()
    if partidos_sin_resultado:
        partido = st.selectbox(
            "Partido a registrar",
            partidos_sin_resultado,
            format_func=lambda x: f"{x['local']} vs {x['visitante']}"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            goles_local = st.number_input("Goles local", 0, 10, 0)
        with col2:
            goles_visitante = st.number_input("Goles visitante", 0, 10, 0)

        if st.button("Registrar Resultado"):
            nuevo_partido = {
                "fase": partido.get('fase', 'groups'),
                "grupo": partido.get('grupo'),
                "local": partido['local'],
                "visitante": partido['visitante'],
                "goles_local": goles_local,
                "goles_visitante": goles_visitante,
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            st.session_state.tournament_data["matches"].append(nuevo_partido)
            procesar_apuestas_partido(nuevo_partido)
            save_tournament_data(st.session_state.tournament_data)
            st.success("Resultado registrado")
            st.rerun()
    else:
        st.info("Todos los partidos registrados")

    if st.button("Reiniciar Torneo"):
        st.session_state.tournament_data = load_tournament_data()
        save_tournament_data(st.session_state.tournament_data)
        st.success("Torneo reiniciado")
        st.rerun()

# Header principal simplificado
st.markdown('<div class="main-header">LIGA FIFA SPORTSBOOK</div>', unsafe_allow_html=True)

# Sidebar optimizado
with st.sidebar:
    st.markdown("**CONTROL**")
    
    with st.expander("Registro"):
        nuevo_jugador = st.text_input("Nombre jugador")
        if st.button("Registrar") and nuevo_jugador:
            if nuevo_jugador not in st.session_state.tournament_data["players"]:
                st.session_state.tournament_data["players"][nuevo_jugador] = {
                    "dinero": 1000,
                    "apuestas_ganadas": 0,
                    "apuestas_perdidas": 0
                }
                save_tournament_data(st.session_state.tournament_data)
                st.success("Jugador registrado")
                st.rerun()
    
    mostrar_panel_apuestas()

# Navegación principal optimizada
tab1, tab2, tab3, tab4 = st.tabs(["Torneo", "Apuestas", "Ranking", "Admin"])

with tab1:
    mostrar_torneo()

with tab2:
    mostrar_apuestas()

with tab3:
    mostrar_posiciones()

with tab4:
    mostrar_admin()

# Limpiar cache periódicamente
if 'cache_clear' not in st.session_state:
    st.session_state.cache_clear = 0

st.session_state.cache_clear += 1
if st.session_state.cache_clear > 10:
    st.cache_data.clear()
    st.session_state.cache_clear = 0
