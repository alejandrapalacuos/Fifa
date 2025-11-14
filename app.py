import streamlit as st
import pandas as pd
import json
import os
import time
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración para móviles
st.set_page_config(
    page_title="Liga FIFA - Apuestas",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Datos por defecto del torneo
DEFAULT_TOURNAMENT_DATA = {
    "groups": {
        "Grupo A": ["Liverpool", "Bayern", "Atlético Nacional", "Barcelona"],
        "Grupo B": ["Real Madrid", "AC Milán", "Independiente Medellín", "PSG"]
    },
    "players": {},
    "matches": [],
    "semifinals": [],
    "final": None,
    "third_place": None,
    "phase": "groups",
    "bets": []
}

def load_tournament_data():
    """Carga los datos del torneo de forma robusta"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Verificar si el archivo existe y tiene contenido
            if not os.path.exists('data/tournament_data.json'):
                logger.info("Archivo no encontrado, creando datos por defecto")
                return DEFAULT_TOURNAMENT_DATA.copy()
            
            with open('data/tournament_data.json', 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    logger.warning("Archivo vacío, usando datos por defecto")
                    return DEFAULT_TOURNAMENT_DATA.copy()
                
                data = json.loads(content)
                
                # Validar estructura básica
                required_keys = ["groups", "players", "matches", "bets", "phase"]
                if all(key in data for key in required_keys):
                    logger.info("Datos cargados exitosamente")
                    return data
                else:
                    logger.warning("Estructura de datos inválida, usando datos por defecto")
                    return DEFAULT_TOURNAMENT_DATA.copy()
                    
        except json.JSONDecodeError as e:
            logger.error(f"Error JSON (intento {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(0.1)  # Esperar antes de reintentar
            else:
                logger.error("Todos los intentos fallaron, usando datos por defecto")
                return DEFAULT_TOURNAMENT_DATA.copy()
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return DEFAULT_TOURNAMENT_DATA.copy()
    
    return DEFAULT_TOURNAMENT_DATA.copy()

def save_tournament_data(data):
    """Guarda los datos del torneo de forma segura"""
    try:
        os.makedirs('data', exist_ok=True)
        
        # Guardar en archivo temporal primero
        temp_file = 'data/tournament_data_temp.json'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Reemplazar archivo original
        if os.path.exists(temp_file):
            os.replace(temp_file, 'data/tournament_data.json')
            logger.info("Datos guardados exitosamente")
            
    except Exception as e:
        logger.error(f"Error guardando datos: {e}")
        st.error("Error al guardar los datos. Intenta nuevamente.")

# Funciones auxiliares
def obtener_partidos_para_apostar():
    """Obtiene partidos que aún no han comenzado (sin resultado)"""
    try:
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
    except Exception as e:
        logger.error(f"Error obteniendo partidos: {e}")
        return []

def calcular_tabla(grupo):
    """Calcula la tabla de posiciones de un grupo"""
    try:
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
    except Exception as e:
        logger.error(f"Error calculando tabla: {e}")
        return pd.DataFrame()

def obtener_clasificados_semifinales():
    """Obtiene los clasificados a semifinales"""
    try:
        clasificados = []
        for grupo in ["Grupo A", "Grupo B"]:
            df = calcular_tabla(grupo)
            if not df.empty:
                top2 = df.head(2)["Equipo"].tolist()
                clasificados.extend(top2)
        return clasificados
    except Exception as e:
        logger.error(f"Error obteniendo clasificados: {e}")
        return []

def procesar_apuestas_partido(partido):
    """Procesa las apuestas de un partido"""
    try:
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
    except Exception as e:
        logger.error(f"Error procesando apuestas: {e}")

# Funciones de UI
def mostrar_panel_apuestas_movil():
    """Muestra el panel de apuestas en el sidebar"""
    st.markdown("### 🎯 Hacer Apuesta")

    if not st.session_state.tournament_data.get("players"):
        st.info("👤 Registra tu nombre arriba para apostar")
        return

    # Selector de jugador
    jugadores = list(st.session_state.tournament_data["players"].keys())
    if not jugadores:
        st.info("👤 Registra tu nombre primero")
        return

    jugador = st.selectbox("Eres:", jugadores)

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
        try:
            monto = min(200, dinero_actual)
            if monto > dinero_actual:
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
        except Exception as e:
            logger.error(f"Error haciendo apuesta: {e}")
            st.error("❌ Error al realizar la apuesta")

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
        opcion_apuesta = st.selectbox("Predicción", ["Local", "Empate", "Visitante"], key="prediccion_select")
        monto_apuesta = st.number_input("Monto", min_value=10, max_value=dinero_actual, value=100, step=10, key="monto_input")

        if st.button("Apostar", type="primary", key="apostar_btn"):
            try:
                if monto_apuesta > dinero_actual:
                    st.error("❌ No tienes suficiente dinero")
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
                st.success(f"✅ Apostaste ${monto_apuesta} por {opcion_apuesta}")
                st.rerun()
            except Exception as e:
                logger.error(f"Error en apuesta personalizada: {e}")
                st.error("❌ Error al realizar la apuesta")

def mostrar_torneo():
    """Muestra la información del torneo"""
    st.markdown("### 📊 Fase de Grupos")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Grupo A**")
        df_a = calcular_tabla("Grupo A")
        if not df_a.empty:
            st.dataframe(df_a, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos del grupo A")

    with col2:
        st.markdown("**Grupo B**")
        df_b = calcular_tabla("Grupo B")
        if not df_b.empty:
            st.dataframe(df_b, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos del grupo B")

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

    if not st.session_state.tournament_data.get("players"):
        st.info("👤 Regístrate en el panel de control")
        return

    # Selector de jugador
    jugadores = list(st.session_state.tournament_data["players"].keys())
    if not jugadores:
        st.info("👤 No hay jugadores registrados")
        return

    jugador_actual = st.selectbox(
        "Selecciona tu jugador:",
        jugadores,
        key="jugador_apuestas"
    )

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
    """Muestra el panel de administración - SOLO PARA CONTROLAR RESULTADOS"""
    st.markdown("### ⚙️ Panel de Administración")
    st.warning("🔒 Esta sección es solo para registrar resultados de partidos")

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
            try:
                registrar_resultado_admin(partido_registrar, goles_local, goles_visitante)
            except Exception as e:
                logger.error(f"Error registrando resultado: {e}")
                st.error("❌ Error al registrar resultado")
    else:
        st.info("✅ Todos los partidos tienen resultado registrado")

    # Avanzar fases
    st.markdown("#### 🚀 Control del Torneo")
    if st.session_state.tournament_data.get("phase") == "groups":
        if st.button("Avanzar a Semifinales", key="avanzar_btn"):
            try:
                clasificados = obtener_clasificados_semifinales()
                if len(clasificados) == 4:
                    st.session_state.tournament_data["phase"] = "semifinals"
                    save_tournament_data(st.session_state.tournament_data)
                    st.success("🎉 Avanzando a Semifinales!")
                    st.rerun()
                else:
                    st.error("❌ No hay suficientes equipos clasificados")
            except Exception as e:
                logger.error(f"Error avanzando fases: {e}")
                st.error("❌ Error al avanzar fases")

    # Reiniciar
    st.markdown("#### 🔄 Reiniciar Sistema")
    if st.button("Reiniciar Todo el Sistema", type="secondary", key="reiniciar_btn"):
        try:
            st.session_state.tournament_data = DEFAULT_TOURNAMENT_DATA.copy()
            save_tournament_data(st.session_state.tournament_data)
            st.success("🔄 Sistema reiniciado completamente")
            st.rerun()
        except Exception as e:
            logger.error(f"Error reiniciando sistema: {e}")
            st.error("❌ Error al reiniciar el sistema")

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

# Inicializar datos de forma segura
if 'tournament_data' not in st.session_state:
    try:
        st.session_state.tournament_data = load_tournament_data()
    except Exception as e:
        logger.error(f"Error crítico inicializando datos: {e}")
        st.session_state.tournament_data = DEFAULT_TOURNAMENT_DATA.copy()
        st.error("⚠️ Se cargaron datos por defecto debido a un error")

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

    # Registro de jugadores - VISIBLE PARA TODOS
    st.markdown("#### 👥 Registro de Jugadores")
    nuevo_jugador = st.text_input("Tu nombre", key="nuevo_jugador", placeholder="Ingresa tu nombre aquí")

    if st.button("Unirse al Juego", key="unirse_btn") and nuevo_jugador:
        try:
            if nuevo_jugador.strip() and nuevo_jugador not in st.session_state.tournament_data["players"]:
                st.session_state.tournament_data["players"][nuevo_jugador] = {
                    "dinero": 1000,
                    "apuestas_ganadas": 0,
                    "apuestas_perdidas": 0
                }
                save_tournament_data(st.session_state.tournament_data)
                st.success(f"✅ {nuevo_jugador} unido con $1000")
                st.rerun()
            elif nuevo_jugador in st.session_state.tournament_data["players"]:
                st.error("❌ Este nombre ya existe")
            else:
                st.error("❌ El nombre no puede estar vacío")
        except Exception as e:
            logger.error(f"Error registrando jugador: {e}")
            st.error("❌ Error al registrar jugador")

    # Mostrar jugadores registrados
    if st.session_state.tournament_data.get("players"):
        st.markdown("#### 👤 Jugadores Registrados")
        for jugador in list(st.session_state.tournament_data["players"].keys())[:10]:  # Mostrar solo primeros 10
            st.write(f"• {jugador}")
        if len(st.session_state.tournament_data["players"]) > 10:
            st.write(f"... y {len(st.session_state.tournament_data['players']) - 10} más")

    # Panel de apuestas (siempre visible)
    mostrar_panel_apuestas_movil()

# Sección principal - Diseño móvil first
tab1, tab2, tab3, tab4 = st.tabs(["🏆 Torneo", "📊 Apuestas", "📈 Posiciones", "⚙️ Admin"])

with tab1:
    mostrar_torneo()

with tab2:
    mostrar_apuestas()

with tab3:
    mostrar_posiciones()

with tab4:
    mostrar_admin()
    
