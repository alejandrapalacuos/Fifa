import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Configuración para móviles
st.set_page_config(
    page_title="Liga FIFA - Apuestas",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Jugadores predeterminados (10 jugadores)
JUGADORES_PREDETERMINADOS = [
    "Tomás", "Lezcano", "Bawe", "Juanda", "Fili", 
    "Higinio", "David", "Anto", "Cata", "Aleja"
]

# Cargar datos del torneo
def load_tournament_data():
    try:
        with open('data/tournament_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Asegurar que todos los jugadores predeterminados existan
            for jugador in JUGADORES_PREDETERMINADOS:
                if jugador not in data["players"]:
                    data["players"][jugador] = {
                        "dinero": 1000,
                        "apuestas_ganadas": 0,
                        "apuestas_perdidas": 0
                    }
            
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        # Si no existe el archivo o está corrupto, crear uno nuevo
        return {
            "groups": {
                "Grupo A": ["Liverpool", "Atlético Nacional", "Barcelona"],  # Quitamos Bayern
                "Grupo B": ["Real Madrid", "AC Milán", "Independiente Medellín"]
            },
            "players": {
                jugador: {
                    "dinero": 1000,
                    "apuestas_ganadas": 0,
                    "apuestas_perdidas": 0
                } for jugador in JUGADORES_PREDETERMINADOS
            },
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
def obtener_partidos_para_apostar():
    """Obtiene partidos que aún no han comenzado (sin resultado)"""
    partidos_para_apostar = []
    partidos_con_resultado = [f"{p['local']} vs {p['visitante']}" 
                            for p in st.session_state.tournament_data["matches"]]
    
    for grupo, equipos in st.session_state.tournament_data["groups"].items():
        for i, local in enumerate(equipos):
            for j, visitante in enumerate(equipos):
                if i != j:
                    partido_key = f"{local} vs {visitante}"
                    if partido_key not in partidos_con_resultado:
                        partidos_para_apostar.append({
                            "local": local,
                            "visitante": visitante,
                            "fase": "groups",
                            "grupo": grupo
                        })
    
    return partidos_para_apostar

def calcular_tabla(grupo):
    """Calcula la tabla de posiciones de un grupo"""
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
    """Obtiene los clasificados a semifinales"""
    clasificados = []
    for grupo in ["Grupo A", "Grupo B"]:
        df = calcular_tabla(grupo)
        top2 = df.head(2)["Equipo"].tolist()
        clasificados.extend(top2)
    return clasificados

def procesar_apuestas_partido(partido):
    """Procesa las apuestas de un partido"""
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
        if not apuesta.get("procesada", False) and apuesta["partido"] == partido_key:
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

# Funciones de UI
def mostrar_panel_apuestas_movil():
    """Muestra el panel de apuestas en el sidebar"""
    st.markdown("### 🎯 Hacer Apuesta")

    # Verificar si hay un jugador seleccionado
    if 'jugador_seleccionado' not in st.session_state or not st.session_state.jugador_seleccionado:
        st.info("👤 Primero selecciona tu nombre arriba")
        return

    jugador = st.session_state.jugador_seleccionado

    # Mostrar dinero disponible
    dinero_actual = st.session_state.tournament_data["players"][jugador]["dinero"]
    st.markdown(f"**Dinero disponible:** `${dinero_actual}`")

    # Partidos disponibles para apostar
    partidos_disponibles = obtener_partidos_para_apostar()

    if not partidos_disponibles:
        st.info("⏳ No hay partidos para apostar")
        return

    partido_apostar = st.selectbox(
        "Partido:",
        partidos_disponibles,
        format_func=lambda x: f"{x['local']} vs {x['visitante']}",
        key="apuesta_partido"
    )

    # Opciones de apuesta en botones
    st.markdown("**Tu predicción:**")
    col1, col2, col3 = st.columns(3)

    def hacer_apuesta_rapida(prediccion):
        monto = min(200, dinero_actual)
        if monto > dinero_actual or dinero_actual < 10:
            st.error("❌ No tienes suficiente dinero")
            return
        
        nueva_apuesta = {
            "jugador": jugador,
            "partido": f"{partido_apostar['local']} vs {partido_apostar['visitante']}",
            "local": partido_apostar['local'],
            "visitante": partido_apostar['visitante'],
            "prediccion": prediccion,
            "monto": monto,
            "fase": partido_apostar.get('fase', 'groups'),
            "procesada": False
        }

        st.session_state.tournament_data["players"][jugador]["dinero"] -= monto
        st.session_state.tournament_data["bets"].append(nueva_apuesta)
        save_tournament_data(st.session_state.tournament_data)
        st.success(f"✅ Apostaste ${monto} por {prediccion}")
        st.rerun()

    with col1:
        if st.button(f"🏠 {partido_apostar['local']}", use_container_width=True, key="local_btn"):
            hacer_apuesta_rapida("Local")

    with col2:
        if st.button("🤝 Empate", use_container_width=True, key="empate_btn"):
            hacer_apuesta_rapida("Empate")

    with col3:
        if st.button(f"✈️ {partido_apostar['visitante']}", use_container_width=True, key="visitante_btn"):
            hacer_apuesta_rapida("Visitante")

    # Apuesta personalizada
    with st.expander("💰 Apuesta personalizada"):
        if dinero_actual < 10:
            st.warning("No tienes suficiente dinero para apostar")
        else:
            opcion_apuesta = st.selectbox("Predicción", ["Local", "Empate", "Visitante"], key="prediccion_select")
            
            monto_apuesta = st.number_input(
                "Monto", 
                min_value=10, 
                max_value=dinero_actual, 
                value=min(100, dinero_actual), 
                step=10, 
                key="monto_input"
            )

            if st.button("Apostar", type="primary", key="apostar_btn"):
                if monto_apuesta > dinero_actual:
                    st.error("❌ No tienes suficiente dinero")
                else:
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
                    st.success(f"✅ Apostaste ${monto_apuesta} por {opcion_apuesta}")
                    st.rerun()

def mostrar_torneo():
    """Muestra la información del torneo"""
    st.markdown("### 📊 Fase de Grupos")

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
    st.markdown("### ⏭️ Próximos Partidos")
    partidos_futuros = obtener_partidos_para_apostar()[:3]
    if partidos_futuros:
        for partido in partidos_futuros:
            st.write(f"**{partido['local']}** vs **{partido['visitante']}** - {partido['grupo']}")
    else:
        st.info("🎉 Todos los partidos han sido jugados")

def mostrar_apuestas():
    """Muestra el historial de apuestas"""
    st.markdown("### 📋 Tus Apuestas")

    # Verificar si hay un jugador seleccionado
    if 'jugador_seleccionado' not in st.session_state or not st.session_state.jugador_seleccionado:
        st.info("👤 Primero selecciona tu nombre en el panel de control")
        return

    jugador_actual = st.session_state.jugador_seleccionado

    apuestas_jugador = [a for a in st.session_state.tournament_data.get("bets", []) if a["jugador"] == jugador_actual]

    if not apuestas_jugador:
        st.info("📝 Aún no has hecho apuestas")
        return

    for apuesta in reversed(apuestas_jugador):
        estado = "✅ GANADA" if apuesta.get("resultado") == "GANADA" else "❌ PERDIDA" if apuesta.get("resultado") == "PERDIDA" else "⏳ PENDIENTE"
        color = "green" if apuesta.get("resultado") == "GANADA" else "red" if apuesta.get("resultado") == "PERDIDA" else "gray"
        
        st.markdown(f"""
        <div style='border: 1px solid {color}; padding: 10px; border-radius: 5px; margin: 5px 0;'>
            <h4>{apuesta['partido']}</h4>
            <p><strong>Predicción:</strong> {apuesta['prediccion']} - ${apuesta['monto']} - {estado}</p>
        """, unsafe_allow_html=True)
        
        if apuesta.get("ganancias"):
            st.write(f"**Ganancias:** ${apuesta['ganancias']}")
        st.markdown("</div>", unsafe_allow_html=True)

def mostrar_posiciones():
    """Muestra el ranking de apostadores"""
    st.markdown("### 🏆 Ranking de Apostadores")

    if not st.session_state.tournament_data.get("players"):
        st.info("👥 Aún no hay jugadores")
        return

    jugadores_data = []
    for jugador, datos in st.session_state.tournament_data["players"].items():
        jugadores_data.append({
            "Jugador": jugador,
            "Dinero": datos['dinero'],
            "Ganadas": datos.get("apuestas_ganadas", 0),
            "Perdidas": datos.get("apuestas_perdidas", 0),
            "Balance": datos.get("apuestas_ganadas", 0) - datos.get("apuestas_perdidas", 0)
        })

    df_jugadores = pd.DataFrame(jugadores_data)
    df_jugadores = df_jugadores.sort_values("Dinero", ascending=False)
    df_jugadores["Dinero"] = "$" + df_jugadores["Dinero"].astype(str)
    st.dataframe(df_jugadores, use_container_width=True, hide_index=True)

def mostrar_admin():
    """Muestra el panel de administración - SOLO PARA ALEJA"""
    st.markdown("### ⚙️ Panel de Administración")
    st.warning("🔒 Esta sección es solo para el administrador")

    # Registrar resultados
    st.markdown("#### 📝 Registrar Resultados")
    
    partidos_sin_resultado = obtener_partidos_para_apostar()

    if partidos_sin_resultado:
        partido_registrar = st.selectbox(
            "Seleccionar partido:",
            partidos_sin_resultado,
            format_func=lambda x: f"{x['local']} vs {x['visitante']} - {x['grupo']}",
            key="admin_partido"
        )

        st.markdown(f"**Partido seleccionado:** {partido_registrar['local']} vs {partido_registrar['visitante']}")

        col1, col2 = st.columns(2)
        with col1:
            goles_local = st.number_input("Goles local", min_value=0, value=0, key="admin_gl")
        with col2:
            goles_visitante = st.number_input("Goles visitante", min_value=0, value=0, key="admin_gv")

        # Mostrar apuestas existentes para este partido
        apuestas_partido = [a for a in st.session_state.tournament_data.get("bets", []) 
                           if a["partido"] == f"{partido_registrar['local']} vs {partido_registrar['visitante']}"]
        
        if apuestas_partido:
            st.markdown(f"**Apuestas en este partido:** {len(apuestas_partido)}")
        
        if st.button("Registrar Resultado", type="primary", key="registrar_btn"):
            registrar_resultado_admin(partido_registrar, goles_local, goles_visitante)
    else:
        st.info("✅ Todos los partidos tienen resultado registrado")

    # Avanzar fases
    st.markdown("#### 🚀 Control del Torneo")
    if st.session_state.tournament_data.get("phase") == "groups":
        if st.button("Avanzar a Semifinales", key="avanzar_btn"):
            clasificados = obtener_clasificados_semifinales()
            if len(clasificados) == 4:
                st.session_state.tournament_data["phase"] = "semifinals"
                save_tournament_data(st.session_state.tournament_data)
                st.success("🎉 Avanzando a Semifinales!")
                st.rerun()
            else:
                st.error("❌ No hay suficientes equipos clasificados")

    # Reiniciar
    st.markdown("#### 🔄 Reiniciar Sistema")
    if st.button("Reiniciar Todo el Sistema", type="secondary", key="reiniciar_btn"):
        st.session_state.tournament_data = load_tournament_data()
        if 'jugador_seleccionado' in st.session_state:
            del st.session_state.jugador_seleccionado
        save_tournament_data(st.session_state.tournament_data)
        st.success("🔄 Sistema reiniciado completamente")
        st.rerun()

def registrar_resultado_admin(partido, goles_local, goles_visitante):
    """Registra el resultado de un partido"""
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
    st.success("✅ Resultado registrado y apuestas procesadas!")
    st.rerun()

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
        color: #1f77b4;
        font-weight: bold;
    }
    .section-header {
        font-size: 18px !important;
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">⚽ LIGA FIFA - APUESTAS 🎯</div>', unsafe_allow_html=True)

# Sidebar móvil optimizado
with st.sidebar:
    st.markdown("### 🎮 Panel de Control")

    # Selección de jugador - LISTA PREDETERMINADA
    st.markdown("#### 👥 Selecciona Tu Nombre")
    
    # Inicializar jugador seleccionado si no existe
    if 'jugador_seleccionado' not in st.session_state:
        st.session_state.jugador_seleccionado = None
    
    jugador_seleccionado = st.selectbox(
        "Elige tu nombre:",
        [""] + JUGADORES_PREDETERMINADOS,
        key="selector_jugador"
    )
    
    if jugador_seleccionado and jugador_seleccionado != st.session_state.get('jugador_seleccionado'):
        st.session_state.jugador_seleccionado = jugador_seleccionado
        st.success(f"✅ Hola {jugador_seleccionado}!")
        st.rerun()
    
    # Mostrar información del jugador seleccionado
    if st.session_state.jugador_seleccionado:
        jugador = st.session_state.jugador_seleccionado
        dinero = st.session_state.tournament_data["players"][jugador]["dinero"]
        st.markdown(f"**Jugador activo:** {jugador}")
        st.markdown(f"**Dinero disponible:** ${dinero}")
        
        # Mostrar estadísticas rápidas
        ganadas = st.session_state.tournament_data["players"][jugador].get("apuestas_ganadas", 0)
        perdidas = st.session_state.tournament_data["players"][jugador].get("apuestas_perdidas", 0)
        st.markdown(f"**Apuestas ganadas:** {ganadas}")
        st.markdown(f"**Apuestas perdidas:** {perdidas}")

    # Panel de apuestas (solo visible si hay jugador seleccionado)
    if st.session_state.jugador_seleccionado:
        mostrar_panel_apuestas_movil()
    else:
        st.info("👆 Selecciona tu nombre para comenzar a apostar")

# Sección principal - Diseño móvil first
# Crear pestañas dinámicamente según el usuario
jugador_actual = st.session_state.get('jugador_seleccionado', '')

if jugador_actual == 'Aleja':
    # Aleja ve todas las pestañas incluyendo Admin
    tab1, tab2, tab3, tab4 = st.tabs(["🏆 Torneo", "📊 Apuestas", "📈 Posiciones", "⚙️ Admin"])
    
    with tab1:
        mostrar_torneo()
    with tab2:
        mostrar_apuestas()
    with tab3:
        mostrar_posiciones()
    with tab4:
        mostrar_admin()
else:
    # Los demás jugadores no ven la pestaña Admin
    tab1, tab2, tab3 = st.tabs(["🏆 Torneo", "📊 Apuestas", "📈 Posiciones"])
    
    with tab1:
        mostrar_torneo()
    with tab2:
        mostrar_apuestas()
    with tab3:
        mostrar_posiciones()
