import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Configuración de página
st.set_page_config(
    page_title="Liga FIFA - Sportsbook",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado para estilo profesional de casa de apuestas
st.markdown("""
<style>
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
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        font-weight: 700;
        font-size: 2rem;
        letter-spacing: 1px;
    }
    
    .section-header {
        background: var(--dark);
        color: white;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        margin: 1.5rem 0 1rem 0;
        font-weight: 600;
        font-size: 1.2rem;
        border-left: 4px solid var(--secondary);
    }
    
    .bet-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    
    .bet-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-2px);
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
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
        margin: 0.25rem 0;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    
    .odds-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .odds-button.local {
        background: linear-gradient(135deg, #1e40af 0%, #1e3a8a 100%);
    }
    
    .odds-button.draw {
        background: linear-gradient(135deg, #475569 0%, #334155 100%);
    }
    
    .odds-button.visitor {
        background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
    }
    
    .balance-card {
        background: linear-gradient(135deg, var(--success) 0%, #047857 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
    }
    
    .stats-card {
        background: var(--light);
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .team-badge {
        display: inline-block;
        background: var(--light);
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        margin: 0.25rem;
        border: 1px solid #e2e8f0;
    }
    
    .match-header {
        background: var(--dark);
        color: white;
        padding: 0.75rem;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        text-align: center;
    }
    
    .table-header {
        background: var(--primary);
        color: white;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: var(--light);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: var(--light);
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--primary);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Cargar datos del torneo
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

# Funciones auxiliares
def obtener_partidos_sin_resultado():
    partidos_sin_resultado = []

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

# Funciones de UI mejoradas
def mostrar_panel_apuestas_movil():
    st.markdown('<div class="section-header">HACER APUESTA</div>', unsafe_allow_html=True)

    if not st.session_state.tournament_data["players"]:
        st.info("Registra tu nombre para comenzar a apostar")
        return

    jugador = st.selectbox("SELECCIONAR JUGADOR", list(st.session_state.tournament_data["players"].keys()))

    # Tarjeta de balance
    dinero_actual = st.session_state.tournament_data["players"][jugador]["dinero"]
    st.markdown(f'''
    <div class="balance-card">
        <div style="font-size: 0.9rem; opacity: 0.9;">BALANCE DISPONIBLE</div>
        <div style="font-size: 1.8rem; font-weight: 700;">${dinero_actual:,}</div>
    </div>
    ''', unsafe_allow_html=True)

    # Partidos disponibles para apostar
    partidos_disponibles = obtener_partidos_sin_resultado()

    if not partidos_disponibles:
        st.info("No hay partidos disponibles para apostar")
        return

    # Selector de partido
    partido_apostar = st.selectbox(
        "SELECCIONAR PARTIDO",
        partidos_disponibles,
        format_func=lambda x: f"{x['local']} vs {x['visitante']} - {x['grupo']}",
        key="apuesta_partido"
    )

    # Cuotas de apuesta (simuladas)
    st.markdown('<div style="margin: 1rem 0; font-weight: 600; text-align: center;">CUOTAS DEL PARTIDO</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="odds-button local" onclick="alert(\'Apuesta local\')">'
                   f'<div>{partido_apostar["local"]}</div>'
                   '<div style="font-size: 1.2rem; margin-top: 0.5rem;">2.10</div>'
                   '</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="odds-button draw">'
                   '<div>EMPATE</div>'
                   '<div style="font-size: 1.2rem; margin-top: 0.5rem;">3.25</div>'
                   '</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="odds-button visitor">'
                   f'<div>{partido_apostar["visitante"]}</div>'
                   '<div style="font-size: 1.2rem; margin-top: 0.5rem;">2.80</div>'
                   '</div>', unsafe_allow_html=True)

    # Apuesta personalizada
    with st.expander("APUESTA PERSONALIZADA", expanded=False):
        col_pred, col_monto = st.columns(2)
        
        with col_pred:
            opcion_apuesta = st.selectbox("PREDICCIÓN", ["Local", "Empate", "Visitante"], key="prediccion_select")
        
        with col_monto:
            monto_apuesta = st.number_input("MONTO ($)", min_value=10, max_value=dinero_actual, value=100, step=10, key="monto_input")

        if st.button("CONFIRMAR APUESTA", type="primary", use_container_width=True):
            if monto_apuesta > dinero_actual:
                st.error("Fondos insuficientes")
                return

            nueva_apuesta = {
                "jugador": jugador,
                "partido": f"{partido_apostar['local']} vs {partido_apostar['visitante']}",
                "local": partido_apostar['local'],
                "visitante": partido_apostar['visitante'],
                "prediccion": opcion_apuesta,
                "monto": monto_apuesta,
                "fase": partido_apostar.get('fase', 'groups'),
                "procesada": False
            }

            st.session_state.tournament_data["players"][jugador]["dinero"] -= monto_apuesta
            st.session_state.tournament_data["bets"].append(nueva_apuesta)
            save_tournament_data(st.session_state.tournament_data)
            st.success(f"Apuesta confirmada: ${monto_apuesta} por {opcion_apuesta}")
            st.rerun()

def mostrar_torneo():
    st.markdown('<div class="section-header">FASE DE GRUPOS</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**GRUPO A**")
        df_a = calcular_tabla("Grupo A")
        st.dataframe(df_a, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**GRUPO B**")
        df_b = calcular_tabla("Grupo B")
        st.dataframe(df_b, use_container_width=True, hide_index=True)

    # Próximos partidos
    st.markdown('<div class="section-header">PRÓXIMOS PARTIDOS</div>', unsafe_allow_html=True)
    partidos_futuros = obtener_partidos_sin_resultado()[:4]
    
    if partidos_futuros:
        for partido in partidos_futuros:
            col1, col2, col3 = st.columns([2,1,2])
            with col1:
                st.markdown(f'<div style="text-align: right; font-weight: 600;">{partido["local"]}</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div style="text-align: center; color: var(--gray);">VS</div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div style="text-align: left; font-weight: 600;">{partido["visitante"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div style="text-align: center; color: var(--gray); font-size: 0.8rem;">{partido["grupo"]}</div>', unsafe_allow_html=True)
            st.markdown("---")
    else:
        st.info("Todos los partidos de grupos han sido jugados")

def mostrar_apuestas():
    st.markdown('<div class="section-header">HISTORIAL DE APUESTAS</div>', unsafe_allow_html=True)

    if not st.session_state.tournament_data["players"]:
        st.info("Regístrate para ver tu historial de apuestas")
        return

    jugador_actual = st.selectbox(
        "JUGADOR",
        list(st.session_state.tournament_data["players"].keys()),
        key="jugador_apuestas"
    )

    apuestas_jugador = [a for a in st.session_state.tournament_data["bets"] if a["jugador"] == jugador_actual]

    if not apuestas_jugador:
        st.info("No hay apuestas registradas")
        return

    # Estadísticas rápidas
    apuestas_ganadas = len([a for a in apuestas_jugador if a.get("resultado") == "GANADA"])
    apuestas_perdidas = len([a for a in apuestas_jugador if a.get("resultado") == "PERDIDA"])
    apuestas_pendientes = len([a for a in apuestas_jugador if not a.get("procesada", False)])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="stats-card">'
                   f'<div style="color: var(--success); font-size: 1.5rem; font-weight: 700;">{apuestas_ganadas}</div>'
                   f'<div>Ganadas</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stats-card">'
                   f'<div style="color: var(--secondary); font-size: 1.5rem; font-weight: 700;">{apuestas_perdidas}</div>'
                   f'<div>Perdidas</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stats-card">'
                   f'<div style="color: var(--warning); font-size: 1.5rem; font-weight: 700;">{apuestas_pendientes}</div>'
                   f'<div>Pendientes</div></div>', unsafe_allow_html=True)

    # Lista de apuestas
    for apuesta in reversed(apuestas_jugador):
        estado_clase = "won" if apuesta.get("resultado") == "GANADA" else "lost" if apuesta.get("resultado") == "PERDIDA" else "pending"
        estado_texto = "GANADA" if apuesta.get("resultado") == "GANADA" else "PERDIDA" if apuesta.get("resultado") == "PERDIDA" else "PENDIENTE"
        estado_color = "var(--success)" if estado_clase == "won" else "var(--secondary)" if estado_clase == "lost" else "var(--warning)"
        
        st.markdown(f'''
        <div class="bet-card {estado_clase}">
            <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 0.5rem;">
                <div style="font-weight: 600; font-size: 1.1rem;">{apuesta['partido']}</div>
                <div style="background: {estado_color}; color: white; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">
                    {estado_texto}
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; color: var(--gray); font-size: 0.9rem;">
                <div>Predicción: <strong>{apuesta['prediccion']}</strong></div>
                <div>Monto: <strong>${apuesta['monto']}</strong></div>
            </div>
        ''', unsafe_allow_html=True)
        
        if apuesta.get("ganancias"):
            st.markdown(f'<div style="color: var(--success); font-weight: 600; margin-top: 0.5rem;">Ganancias: ${apuesta["ganancias"]}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def mostrar_posiciones():
    st.markdown('<div class="section-header">RANKING DE APOSTADORES</div>', unsafe_allow_html=True)

    if not st.session_state.tournament_data["players"]:
        st.info("No hay jugadores registrados")
        return

    jugadores_data = []
    for jugador, datos in st.session_state.tournament_data["players"].items():
        jugadores_data.append({
            "Jugador": jugador,
            "Dinero": datos['dinero'],
            "Ganadas": datos["apuestas_ganadas"],
            "Perdidas": datos["apuestas_perdidas"],
            "Balance": datos["apuestas_ganadas"] - datos["apuestas_perdidas"]
        })

    df_jugadores = pd.DataFrame(jugadores_data)
    df_jugadores = df_jugadores.sort_values("Dinero", ascending=False)
    
    # Formatear dinero
    df_jugadores["Dinero"] = "$" + df_jugadores["Dinero"].astype(str)
    
    # Aplicar estilo a la tabla
    st.dataframe(
        df_jugadores,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Jugador": st.column_config.TextColumn(width="medium"),
            "Dinero": st.column_config.TextColumn(width="small"),
            "Ganadas": st.column_config.NumberColumn(width="small"),
            "Perdidas": st.column_config.NumberColumn(width="small"),
            "Balance": st.column_config.NumberColumn(width="small")
        }
    )

def mostrar_admin():
    st.markdown('<div class="section-header">PANEL DE ADMINISTRACIÓN</div>', unsafe_allow_html=True)

    # Registrar resultados
    st.markdown("**REGISTRAR RESULTADOS**")
    partidos_sin_resultado = obtener_partidos_sin_resultado()

    if partidos_sin_resultado:
        partido_registrar = st.selectbox(
            "SELECCIONAR PARTIDO",
            partidos_sin_resultado,
            format_func=lambda x: f"{x['local']} vs {x['visitante']} - {x['grupo']}",
            key="admin_partido"
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**{partido_registrar['local']}**")
            goles_local = st.number_input("Goles local", min_value=0, value=0, key="admin_gl")
        with col2:
            st.markdown("**VS**")
            st.markdown("")  # Espacio vacío para alineación
        with col3:
            st.markdown(f"**{partido_registrar['visitante']}**")
            goles_visitante = st.number_input("Goles visitante", min_value=0, value=0, key="admin_gv")

        if st.button("REGISTRAR RESULTADO", type="primary", use_container_width=True):
            registrar_resultado_admin(partido_registrar, goles_local, goles_visitante)
    else:
        st.info("Todos los partidos tienen resultado registrado")

    # Avanzar fases
    st.markdown("**CONTROL DEL TORNEO**")
    if st.session_state.tournament_data["phase"] == "groups":
        if st.button("AVANZAR A SEMIFINALES", use_container_width=True):
            clasificados = obtener_clasificados_semifinales()
            if len(clasificados) == 4:
                st.session_state.tournament_data["phase"] = "semifinals"
                save_tournament_data(st.session_state.tournament_data)
                st.success("Torneo avanzado a semifinales")
                st.rerun()
            else:
                st.error("No hay suficientes equipos clasificados")

    # Reiniciar
    if st.button("REINICIAR TORNEO", type="secondary", use_container_width=True):
        st.session_state.tournament_data = load_tournament_data()
        save_tournament_data(st.session_state.tournament_data)
        st.success("Torneo reiniciado exitosamente")
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
    st.success("Resultado registrado y apuestas procesadas")
    st.rerun()

# Inicializar datos
if 'tournament_data' not in st.session_state:
    st.session_state.tournament_data = load_tournament_data()

# Header principal
st.markdown('<div class="main-header">LIGA FIFA SPORTSBOOK</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown('<div class="section-header">PANEL DE CONTROL</div>', unsafe_allow_html=True)

    # Registro de jugadores
    with st.expander("REGISTRO DE JUGADORES"):
        nuevo_jugador = st.text_input("NOMBRE DEL JUGADOR", key="nuevo_jugador")

        if st.button("REGISTRAR JUGADOR", key="unirse_btn") and nuevo_jugador:
            if nuevo_jugador.strip() and nuevo_jugador not in st.session_state.tournament_data["players"]:
                st.session_state.tournament_data["players"][nuevo_jugador] = {
                    "dinero": 1000,
                    "apuestas_ganadas": 0,
                    "apuestas_perdidas": 0
                }
                save_tournament_data(st.session_state.tournament_data)
                st.success(f"Jugador {nuevo_jugador} registrado con $1000")
                st.rerun()
            elif nuevo_jugador in st.session_state.tournament_data["players"]:
                st.error("Este nombre ya está registrado")
            else:
                st.error("El nombre no puede estar vacío")

    # Panel de apuestas
    mostrar_panel_apuestas_movil()

# Navegación principal
tab1, tab2, tab3, tab4 = st.tabs(["TORNEO", "MIS APUESTAS", "RANKING", "ADMIN"])

with tab1:
    mostrar_torneo()

with tab2:
    mostrar_apuestas()

with tab3:
    mostrar_posiciones()

with tab4:
    mostrar_admin()
