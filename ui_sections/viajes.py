import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import pydeck as pdk
import pytz
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from google_sheets_client import get_sheet, get_sheet_data, refresh_data, update_cell_by_id

# --- Constantes ---
SHEET_VEHICULOS = "Vehiculos"
SHEET_VIAJES = "Viajes"
SHEET_VIAJES_UPDATES = "ViajesUpdates"
SHEET_DESTINOS = "Destinos"
TZ_DEFAULT = "America/Argentina/Buenos_Aires"

# --- Utilidades de tiempo ---
def now_iso(tz_name: str = TZ_DEFAULT) -> str:
    tz = pytz.timezone(tz_name)
    return datetime.now(tz).isoformat()

def _parse_coord(val: Any) -> Optional[float]:
    """Acepta string o número y devuelve float, tolerando coma decimal y separadores de miles.
    Reglas:
    - Si contiene coma y no punto, usamos coma como decimal.
    - Si contiene ambos, tomamos el último separador como decimal y quitamos el otro como miles.
    - Quitamos espacios.
    - Si el valor absoluto es >= 1000, asumimos microgrados y dividimos por 1.000.000.
    """
    if val is None:
        return None
    
    num = None
    
    if isinstance(val, (int, float)):
        num = float(val)
    else:
        s = str(val).strip()
        if not s:
            return None
        s = s.replace(" ", "")
        if "," in s and "." not in s:
            s = s.replace(",", ".")
        elif "," in s and "." in s:
            # último separador es el decimal
            last_dot = s.rfind('.')
            last_comma = s.rfind(',')
            if last_comma > last_dot:
                # coma decimal, punto miles -> quitar puntos, coma a punto
                s = s.replace('.', '')
                s = s.replace(',', '.')
            else:
                # punto decimal, coma miles -> quitar comas
                s = s.replace(',', '')
        try:
            num = float(s)
        except Exception:
            return None

    # Normalizar magnitudes típicas de microgrados (e.g., -34620000 -> -34.62)
    if num is not None and abs(num) >= 1000:
        num = num / 1_000_000.0
        
    return num

# --- Funciones de Datos ---
def get_vehicles(client) -> pd.DataFrame:
    """Obtiene vehículos como DataFrame (ID, Nombre, Tipo)."""
    df = st.session_state.get("df_vehiculos", pd.DataFrame())
    if df.empty:
        df = get_sheet_data(client, SHEET_VEHICULOS)
    expected = ["ID", "Nombre", "Tipo"]
    for col in expected:
        if col not in df.columns:
            df[col] = ""
    return df[expected].copy()

def _hex_to_rgb(hex_str: str) -> Optional[list]:
    try:
        s = str(hex_str).strip()
        # Support for common names
        names = {
            "rojo": [255, 0, 0], "red": [255, 0, 0],
            "azul": [0, 0, 255], "blue": [0, 0, 255],
            "verde": [0, 128, 0], "green": [0, 128, 0],
            "blanco": [255, 255, 255], "white": [255, 255, 255],
            "negro": [0, 0, 0], "black": [0, 0, 0],
            "gris": [128, 128, 128], "grey": [128, 128, 128], "gray": [128, 128, 128],
            "amarillo": [255, 255, 0], "yellow": [255, 255, 0],
            "naranja": [255, 165, 0], "orange": [255, 165, 0],
            "violeta": [238, 130, 238], "violet": [238, 130, 238],
            "plateado": [192, 192, 192], "silver": [192, 192, 192],
        }
        if s.lower() in names:
            return names[s.lower()]

        s = s.lstrip('#')
        if len(s) == 3:
            s = ''.join([c*2 for c in s])
        if len(s) != 6:
            return None
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        return [r, g, b]
    except Exception:
        return None

def get_vehicle_color_map(client) -> Dict[str, list]:
    """Devuelve map VehiculoID -> [r,g,b]. Usa columna 'Color' (hex) si existe; si no, asigna paleta fallback."""
    df = st.session_state.get("df_vehiculos", pd.DataFrame())
    if df.empty:
        df = get_sheet_data(client, SHEET_VEHICULOS)
    color_map: Dict[str, list] = {}
    palette = [
        [230, 25, 75], [60, 180, 75], [255, 225, 25], [0, 130, 200], [245, 130, 48], [145, 30, 180],
        [70, 240, 240], [240, 50, 230], [210, 245, 60], [250, 190, 190], [0, 128, 128], [230, 190, 255],
        [170, 110, 40], [255, 250, 200], [128, 0, 0], [170, 255, 195], [128, 128, 0], [255, 215, 180], [0, 0, 128]
    ]
    idx = 0
    if not df.empty:
        # Normalizar columnas
        cols = {c.lower().strip(): c for c in df.columns}
        id_col = cols.get('id')
        color_col = cols.get('color')
        if id_col:
            for _, row in df.iterrows():
                vid = str(row[id_col]).strip()
                rgb = None
                if color_col and pd.notna(row[color_col]) and str(row[color_col]).strip():
                    rgb = _hex_to_rgb(str(row[color_col]))
                if not rgb:
                    rgb = palette[idx % len(palette)]
                    idx += 1
                color_map[vid] = rgb
    return color_map

def get_destinos_map(client) -> Dict[str, Dict[str, float]]:
    """Retorna un dict {Nombre: {"lat": float, "lon": float}} desde la hoja Destinos."""
    df = st.session_state.get("df_destinos", pd.DataFrame())
    if df.empty:
        df = get_sheet_data(client, SHEET_DESTINOS)
    if df.empty:
        return {}
    # Normalizar encabezados esperados
    rename_map = {}
    for c in df.columns:
        c_clean = str(c).strip().lower()
        if c_clean in ("nombre", "destino", "lugar"):
            rename_map[c] = "Nombre"
        elif c_clean in ("lat", "latitud"):
            rename_map[c] = "Lat"
        elif c_clean in ("lon", "lng", "longitud"):
            rename_map[c] = "Lon"
    if rename_map:
        df = df.rename(columns=rename_map)
    for col in ["Nombre", "Lat", "Lon"]:
        if col not in df.columns:
            return {}
    # Filtrar filas válidas
    out: Dict[str, Dict[str, float]] = {}
    for _, row in df.iterrows():
        try:
            name = str(row["Nombre"]).strip()
            lat = _parse_coord(row["Lat"]) if pd.notna(row["Lat"]) else None
            lon = _parse_coord(row["Lon"]) if pd.notna(row["Lon"]) else None
            if name and lat is not None and lon is not None:
                out[name] = {"lat": float(lat), "lon": float(lon)}
        except Exception:
            continue
    return out

def _ensure_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def create_trip(client, vehicle_id: str, people: List[str], destino_principal: str,
                destinos_intermedios: List[str], salida_dt: datetime, tz_name: str = TZ_DEFAULT) -> Optional[str]:
    """Crea un viaje y devuelve su trip_id."""
    sheet = get_sheet(client, SHEET_VIAJES)
    if sheet is None:
        return None
    trip_id = _ensure_id("trip")
    salida_str = salida_dt.astimezone(pytz.timezone(tz_name)).isoformat() if salida_dt.tzinfo else pytz.timezone(tz_name).localize(salida_dt).isoformat()
    payload = [
        trip_id,
        vehicle_id or "",
        json.dumps(people or []),
        salida_str,
        destino_principal or "",
        json.dumps(destinos_intermedios or []),
        "active",
        now_iso(tz_name)
    ]
    sheet.append_row(payload)
    refresh_data(client, SHEET_VIAJES)
    return trip_id

def add_trip_update(client, trip_id: str, lat: float, lon: float, notes: str = "", tz_name: str = TZ_DEFAULT) -> bool:
    """Agrega una actualización de ubicación al viaje."""
    sheet = get_sheet(client, SHEET_VIAJES_UPDATES)
    if sheet is None:
        return False
    ts = now_iso(tz_name)
    sheet.append_row([trip_id, ts, lat, lon, notes or ""]) 
    refresh_data(client, SHEET_VIAJES_UPDATES)
    return True

def get_active_trips(client) -> pd.DataFrame:
    """Retorna viajes con estado active."""
    df = st.session_state.get("df_viajes", pd.DataFrame())
    if df.empty:
        df = get_sheet_data(client, SHEET_VIAJES)
    if "Estado" not in df.columns:
        return pd.DataFrame()
    return df[df["Estado"].str.lower() == "active"].copy()

def complete_trip(client, trip_id: str) -> bool:
    """Marca un viaje como completed."""
    return update_cell_by_id(client, SHEET_VIAJES, trip_id, "Estado", "completed")

def update_trip_destination(client, trip_id: str, new_dest: str) -> bool:
    """Actualiza el destino principal de un viaje."""
    return update_cell_by_id(client, SHEET_VIAJES, trip_id, "DestinoPrincipal", new_dest)

def get_trip_updates_df(client, trip_id: Optional[str] = None) -> pd.DataFrame:
    df = st.session_state.get("df_viajesupdates", pd.DataFrame())
    if df.empty:
        df = get_sheet_data(client, SHEET_VIAJES_UPDATES)
    if not df.empty and trip_id:
        if "TripID" in df.columns:
            df = df[df["TripID"].astype(str) == str(trip_id)]
        elif "trip_id" in df.columns:
            df = df[df["trip_id"].astype(str) == str(trip_id)]
    return df.copy()

# --- UI Principal ---
def seccion_viajes(client, personal_list: List[str]):
    st.subheader("🚗 Gestión de Salidas al Campo")

    # Ensure DataFrame schemas exist in Sheets
    # _show_schema_info()

    tab_gestion, tab_registro, tab_seguimiento, tab_mapa, tab_destinos = st.tabs([
        "🚙 Vehículos",
        "📝 Registro de Viajes",
        "📍 Seguimiento",
        "🗺️ Mapa",
        "📚 Destinos"
    ])

    with tab_gestion:
        _tab_vehiculos(client)

    with tab_registro:
        _tab_registro_viaje(client, personal_list)

    with tab_seguimiento:
        _tab_seguimiento(client)

    with tab_mapa:
        _tab_mapa(client)

    with tab_destinos:
        _tab_destinos(client)

# --- Sub-secciones ---
def _tab_vehiculos(client):
    st.markdown("#### Gestión de Vehículos")
    df = get_vehicles(client)
    if df.empty:
        st.info("No hay vehículos registrados.")
    else:
        st.dataframe(df, hide_index=True, width='stretch')

    with st.form("vehiculos_form", clear_on_submit=True):
        st.markdown("##### Registrar nuevo vehículo")
        nombre = st.text_input("Nombre")
        tipo = st.selectbox("Tipo", ["Auto", "Camioneta", "Camión", "Otro"])
        color_hex = st.color_picker("Color (para mapa)", value="#007AFF")
        if st.form_submit_button("Registrar Vehículo"):
            sheet = get_sheet(client, SHEET_VEHICULOS)
            if sheet is None:
                st.error("No se pudo acceder a la hoja de Vehículos.")
                return
            vid = _ensure_id("veh")
            sheet.append_row([vid, nombre.strip(), tipo, color_hex])
            refresh_data(client, SHEET_VEHICULOS)
            st.success("Vehículo registrado.")
            st.rerun()

def _tab_registro_viaje(client, personal_list: List[str]):
    st.markdown("#### Registro de Viaje")
    vehiculos_df = get_vehicles(client)
    veh_map = {f"{row['Nombre']} ({row['Tipo']})": row['ID'] for _, row in vehiculos_df.iterrows()}
    veh_options = list(veh_map.keys())

    col1, col2 = st.columns(2)
    veh_label = col1.selectbox("Vehículo", options=["Seleccionar..."] + veh_options)

    people_options = personal_list or []
    selected_people = col2.multiselect("Ocupantes (desde Personal)", options=people_options)
    extra_people = st.text_input("Ocupantes adicionales (separados por coma)")

    col3, col4 = st.columns(2)
    salida_fecha = col3.date_input("Fecha de salida", value=datetime.now().date())
    salida_hora = col3.time_input("Hora de salida", value=datetime.now().time())

    destinos_map = get_destinos_map(client)
    destinos_options = sorted(list(destinos_map.keys())) + ["Otro"]
    destino_principal = col4.selectbox("Destino principal", options=destinos_options, index=(destinos_options.index("Oficina") if "Oficina" in destinos_options else 0))
    destino_principal_manual = st.text_input("Destino principal manual (si aplica)")
    if destino_principal != "Otro" and destino_principal in destinos_map:
        coords = destinos_map[destino_principal]
        st.caption(f"Coordenadas destino principal: lat={coords['lat']}, lon={coords['lon']}")

    # Destinos intermedios eliminados por simplificación
    # destinos_intermedios_sel = st.multiselect("Seleccionar desde catálogo", options=sorted(list(destinos_map.keys())))
    # destinos_intermedios_text = st.text_area("Adicionales manuales (separados por coma)")

    if st.button("Iniciar Viaje"):
        if veh_label == "Seleccionar...":
            st.warning("Seleccione un vehículo.")
            return
        vehicle_id = veh_map.get(veh_label)
        final_people = [p for p in selected_people if p] + [p.strip() for p in (extra_people.split(',') if extra_people else []) if p.strip()]
        principal = destino_principal_manual.strip() if destino_principal == "Otro" and destino_principal_manual.strip() else destino_principal
        intermedios = [] # Simplificado: sin intermedios
        salida_dt = datetime.combine(salida_fecha, salida_hora)
        trip_id = create_trip(client, vehicle_id, final_people, principal, intermedios, salida_dt)
        if trip_id:
            st.success(f"Viaje iniciado. ID: {trip_id}")
            st.session_state["ultimo_trip_id"] = trip_id
            # Primer seguimiento automático con destino principal si está en catálogo
            if principal and principal in destinos_map:
                coords = destinos_map[principal]
                try:
                    add_trip_update(client, trip_id, float(coords["lat"]), float(coords["lon"]), "Inicio: destino principal")
                    refresh_data(client, SHEET_VIAJES_UPDATES)
                    st.toast("Primer seguimiento creado con destino principal.")
                except Exception:
                    pass
        else:
            st.error("No se pudo crear el viaje.")

def _tab_seguimiento(client):
    st.markdown("#### Seguimiento en tiempo real")
    df_active = get_active_trips(client)
    if df_active.empty:
        st.info("No hay viajes activos.")
        return

    # Nombres de vehículos
    df_veh = st.session_state.get("df_vehiculos", pd.DataFrame())
    if df_veh.empty:
        df_veh = get_sheet_data(client, SHEET_VEHICULOS)
    vcols = {c.lower().strip(): c for c in df_veh.columns}
    v_id_col = vcols.get('id') or 'ID'
    v_name_col = vcols.get('nombre') or 'Nombre'
    veh_names = {str(r[v_id_col]).strip(): str(r[v_name_col]).strip() for _, r in df_veh.iterrows()} if (not df_veh.empty and v_id_col in df_veh.columns and v_name_col in df_veh.columns) else {}

    # Personas por viaje
    vcols_a = {c.lower().strip(): c for c in df_active.columns}
    id_col = vcols_a.get('id') or 'ID'
    veh_col = vcols_a.get('vehiculoid') or vcols_a.get('vehicleid') or 'VehiculoID'
    personas_col = vcols_a.get('personas(json)') or vcols_a.get('personas') or 'Personas(JSON)'
    trip_map = {}
    for _, row in df_active.iterrows():
        tid = str(row.get(id_col, '')).strip()
        vid = str(row.get(veh_col, '')).strip()
        vname = veh_names.get(vid, vid)
        ppl_raw = row.get(personas_col, '[]')
        ppl_list = []
        try:
            if isinstance(ppl_raw, str):
                ppl_list = json.loads(ppl_raw)
            elif isinstance(ppl_raw, list):
                ppl_list = ppl_raw
        except Exception:
            if isinstance(ppl_raw, str) and ppl_raw.strip():
                ppl_list = [p.strip() for p in ppl_raw.split(',') if p.strip()]
        ppl_txt = ", ".join([str(p).strip() for p in ppl_list if p])
        label = f"{vname} - {ppl_txt}" if ppl_txt else f"{vname}"
        trip_map[label] = tid

    trip_label = st.selectbox("Viaje activo", options=list(trip_map.keys()))
    trip_id = trip_map.get(trip_label)

    # Última ubicación del viaje seleccionado (solo lectura)
    last_text = "Sin ubicaciones reportadas"
    last_lat, last_lon = None, None
    try:
        if trip_id:
            df_last = get_trip_updates_df(client, trip_id)
            if not df_last.empty:
                ucols = {c.lower().strip(): c for c in df_last.columns}
                lat_c = ucols.get('lat') or ucols.get('latitud') or 'Lat'
                lon_c = ucols.get('lon') or ucols.get('longitud') or 'Lon'
                ts_c = ucols.get('timestampiso') or ucols.get('timestamp') or ucols.get('fecha') or 'TimestampISO'
                if ts_c in df_last.columns:
                    df_last = df_last.sort_values(by=ts_c)
                rlast = df_last.tail(1).iloc[0]
                lat_v = _parse_coord(rlast.get(lat_c))
                lon_v = _parse_coord(rlast.get(lon_c))
                ts_v = str(rlast.get(ts_c, '')).strip() if ts_c in df_last.columns else ''
                if lat_v is not None and lon_v is not None:
                    last_lat, last_lon = lat_v, lon_v
                    # Buscar nombre del lugar
                    destinos_map = get_destinos_map(client)
                    loc_name = None
                    thr = 0.002
                    for dname, dcoords in destinos_map.items():
                        if abs(dcoords['lat'] - lat_v) <= thr and abs(dcoords['lon'] - lon_v) <= thr:
                            loc_name = dname
                            break
                    
                    if loc_name:
                        last_text = f"{loc_name} ({ts_v})" if ts_v else loc_name
                    else:
                        last_text = f"{lat_v:.6f}, {lon_v:.6f}  {('('+ts_v+')') if ts_v else ''}"
    except Exception:
        pass
    st.text_input("Última ubicación", value=last_text, disabled=True)

    st.markdown("##### Reportar Estado / Ubicación")

    # Unified Reporting UI
    destinos_map = get_destinos_map(client)
    dest_opts = [""] + sorted(list(destinos_map.keys()))
    
    # 1. Select Location/Destination
    sel_location = st.selectbox("Ubicación actual / Nuevo destino", options=dest_opts, key="seg_ubicacion_sel")
    
    notes = st.text_input("Notas")

    if st.button("Reportar"):
        if not sel_location:
            st.error("Seleccione una ubicación.")
            return
        
        coords = destinos_map.get(sel_location)
        if not coords:
            st.error("Ubicación inválida.")
            return

        # Always update destination AND report location (Simplified workflow)
        # User requested removing the checkbox, so we assume any report from this tab 
        # implies a location update that should be reflected as the current destination/state.
        # However, to avoid overwriting the "official" destination if they just want to report a checkpoint,
        # we might need to be careful. But the user said "removerlo" (the checkbox).
        # If we remove the checkbox, we have two options:
        # A) Always update destination.
        # B) Never update destination (only location report).
        # Given the previous request "quiero visualizar... en base al ultimo (o unico) destino reportado",
        # option A seems closer to "the map shows where I am".
        # Let's do: Always update destination if it's different.
        
        # Update Trip Destination (Implicit)
        update_trip_destination(client, trip_id, sel_location)
        
        # Report Location
        if add_trip_update(client, trip_id, float(coords['lat']), float(coords['lon']), notes):
            st.toast(f"Reportado en {sel_location}")
            refresh_data(client, SHEET_VIAJES)
            refresh_data(client, SHEET_VIAJES_UPDATES)
            st.success("Ubicación actualizada.")
            st.rerun()
        else:
            st.error("No se pudo realizar la actualización.")

    st.divider()
    if st.button("Finalizar Viaje", type="primary"):
        if trip_id and complete_trip(client, trip_id):
            refresh_data(client, SHEET_VIAJES)
            st.success("Viaje finalizado.")
            st.rerun()
        else:
            st.error("No se pudo finalizar el viaje.")

def _tab_mapa(client):
    st.markdown("#### Visualización en mapa (todos los viajes activos)")
    # Depuración deshabilitada

    df_active = get_active_trips(client)
    if df_active.empty:
        st.info("No hay viajes activos.")
        return

    # Preparar colores y nombres por vehículo
    veh_colors = get_vehicle_color_map(client)
    df_veh = st.session_state.get("df_vehiculos", pd.DataFrame())
    if df_veh.empty:
        df_veh = get_sheet_data(client, SHEET_VEHICULOS)
    vcols = {c.lower().strip(): c for c in df_veh.columns}
    v_id_col = vcols.get('id') or 'ID'
    v_name_col = vcols.get('nombre') or 'Nombre'
    veh_names = {}
    if not df_veh.empty and v_id_col in df_veh.columns and v_name_col in df_veh.columns:
        veh_names = {str(r[v_id_col]).strip(): str(r[v_name_col]).strip() for _, r in df_veh.iterrows()}

    # Reunir todas las ubicaciones reportadas de viajes activos
    updates = st.session_state.get("df_viajesupdates", pd.DataFrame())
    if updates.empty:
        updates = get_sheet_data(client, SHEET_VIAJES_UPDATES)

    # Normalizar nombres de columnas de updates
    up_cols = {c.lower().strip(): c for c in updates.columns}
    lat_col = up_cols.get('lat') or up_cols.get('latitud') or 'Lat'
    lon_col = up_cols.get('lon') or up_cols.get('longitud') or 'Lon'
    tripid_col = up_cols.get('tripid') or up_cols.get('trip_id') or 'TripID'
    ts_col = up_cols.get('timestampiso') or up_cols.get('timestamp') or up_cols.get('fecha') or 'TimestampISO'
    notes_col = up_cols.get('notas') or up_cols.get('nota') or up_cols.get('notes') or 'Notas'
    if lat_col not in updates.columns or lon_col not in updates.columns or tripid_col not in updates.columns:
        updates = pd.DataFrame(columns=[tripid_col, lat_col, lon_col])

    # Mapear TripID -> VehiculoID
    v_cols = {c.lower().strip(): c for c in df_active.columns}
    id_col = v_cols.get('id') or 'ID'
    veh_col = v_cols.get('vehiculoid') or v_cols.get('vehicleid') or 'VehiculoID'
    active_trip_to_veh = {}
    for _, row in df_active.iterrows():
        active_trip_to_veh[str(row[id_col]).strip()] = str(row.get(veh_col, '')).strip()

    # Filtrar updates solo de viajes activos
    updates_active = updates[updates[tripid_col].astype(str).isin(active_trip_to_veh.keys())].copy()

    # Construir DataFrame para pydeck
    def _norm(v):
        v = _parse_coord(v)
        if v is None:
            return None
        # Simple safety clamp to valid geo range
        return max(min(v, 180.0), -180.0)

    # Mapas auxiliares: destino principal y personas por trip
    trip_to_dest = {}
    trip_to_people = {}
    try:
        df_vinfo = st.session_state.get("df_viajes", pd.DataFrame())
        if df_vinfo.empty:
            df_vinfo = get_sheet_data(client, SHEET_VIAJES)
        if not df_vinfo.empty:
            vcols_i = {c.lower().strip(): c for c in df_vinfo.columns}
            id_v_col = vcols_i.get('id') or 'ID'
            principal_col = vcols_i.get('destinoprincipal') or 'DestinoPrincipal'
            personas_col = vcols_i.get('personas(json)') or vcols_i.get('personas') or 'Personas(JSON)'
            for _, rr in df_vinfo.iterrows():
                tid = str(rr.get(id_v_col, '')).strip()
                if not tid:
                    continue
                trip_to_dest[tid] = str(rr.get(principal_col, '')).strip()
                ppl_raw = rr.get(personas_col, '[]')
                ppl_list = []
                try:
                    if isinstance(ppl_raw, str):
                        ppl_list = json.loads(ppl_raw)
                    elif isinstance(ppl_raw, list):
                        ppl_list = ppl_raw
                except Exception:
                    if isinstance(ppl_raw, str) and ppl_raw.strip():
                        ppl_list = [p.strip() for p in ppl_raw.split(',') if p.strip()]
                trip_to_people[tid] = ", ".join([str(p).strip() for p in ppl_list if p])
    except Exception:
        pass

    # --- ARCS LOGIC ---
    destinos_map = get_destinos_map(client)
    # Buscar Estación Central
    estacion_central = None
    for k, v in destinos_map.items():
        if "estacion central" in k.lower() or "estación central" in k.lower():
            estacion_central = v
            break
    
    arc_rows = []
    vehicle_rows = []
    
    # Pre-calcular secuencia de puntos por viaje
    # Estructura: [Estación Central] -> [Update 1] -> [Update 2] -> ...
    
    # Agrupar updates por trip
    trip_updates_map = {}
    if not updates_active.empty:
        if ts_col in updates_active.columns:
            updates_active = updates_active.sort_values(by=ts_col)
        for tid, group in updates_active.groupby(tripid_col):
            pts = []
            for _, r in group.iterrows():
                lat = _norm(r.get(lat_col))
                lon = _norm(r.get(lon_col))
                if lat is not None and lon is not None:
                    pts.append({"lat": lat, "lon": lon})
            trip_updates_map[str(tid).strip()] = pts

    # Cargar viajes activos para iterar
    df_v = st.session_state.get("df_viajes", pd.DataFrame())
    if df_v.empty:
        df_v = get_sheet_data(client, SHEET_VIAJES)
    
    if not df_v.empty:
        v_cols2 = {c.lower().strip(): c for c in df_v.columns}
        id_v_col = v_cols2.get('id') or 'ID'
        veh_v_col = v_cols2.get('vehiculoid') or v_cols2.get('vehicleid') or 'VehiculoID'
        principal_col = v_cols2.get('destinoprincipal') or 'DestinoPrincipal'
        estado_col = v_cols2.get('estado') or 'Estado'
        
        for _, row in df_v.iterrows():
            if str(row.get(estado_col, '')).lower() != 'active':
                continue
            trip_id = str(row.get(id_v_col, '')).strip()
            veh_id = str(row.get(veh_v_col, '')).strip()
            color = veh_colors.get(veh_id) or [120, 120, 120]
            
            # Construir secuencia de puntos
            points = []
            if estacion_central:
                points.append(estacion_central)
            
            # Agregar updates reportados
            if trip_id in trip_updates_map:
                points.extend(trip_updates_map[trip_id])
            else:
                # Si no hay updates, usar destino principal si existe
                principal = str(row.get(principal_col, '')).strip()
                if principal and principal in destinos_map:
                    points.append(destinos_map[principal])
            
            # Generar Arcos
            if len(points) > 1:
                for i in range(len(points) - 1):
                    start = points[i]
                    end = points[i+1]
                    # Evitar arcos de longitud 0
                    if abs(start['lat'] - end['lat']) < 0.0001 and abs(start['lon'] - end['lon']) < 0.0001:
                        continue
                    arc_rows.append({
                        "source": [start['lon'], start['lat']],
                        "target": [end['lon'], end['lat']],
                        "color": color,
                        "trip_id": trip_id
                    })
            
            # Posición del vehículo (último punto)
            if points:
                last_pt = points[-1]
                source_type = "realtime" if trip_id in trip_updates_map else "planned"
                
                destino_name = trip_to_dest.get(trip_id, '')
                personas_txt = trip_to_people.get(trip_id, '')
                label_txt = f"Vehículo: {veh_names.get(veh_id, veh_id)}\nDestino: {destino_name}\nPersonas: {personas_txt}".strip()
                
                vehicle_rows.append({
                    "lat": last_pt['lat'],
                    "lon": last_pt['lon'],
                    "color": color,
                    "trip_id": trip_id,
                    "veh_id": veh_id,
                    "veh_name": veh_names.get(veh_id, veh_id),
                    "tipo": source_type,
                    "label": label_txt,
                })

    # Construir data_rows para layer_updates (Trail)
    data_rows = []
    for _, r in updates_active.iterrows():
        lat = _norm(r[lat_col])
        lon = _norm(r[lon_col])
        if lat is None or lon is None:
            continue
        trip_id = str(r[tripid_col]).strip()
        veh_id = active_trip_to_veh.get(trip_id, '')
        base_color = veh_colors.get(veh_id) or [0, 122, 255]
        # Add transparency (alpha = 140/255)
        color = (base_color[:3] if len(base_color) >= 3 else base_color) + [140]
        
        ts = str(r.get(ts_col, '')).strip()
        note = str(r.get(notes_col, '')).strip()
        destino_name = trip_to_dest.get(trip_id, '')
        personas_txt = trip_to_people.get(trip_id, '')
        label_txt = f"Vehículo: {veh_names.get(veh_id, veh_id)}\nDestino: {destino_name}\nPersonas: {personas_txt}".strip()
        data_rows.append({
            "lat": lat,
            "lon": lon,
            "color": color,
            "trip_id": trip_id,
            "veh_id": veh_id,
            "veh_name": veh_names.get(veh_id, veh_id),
            "timestamp": ts,
            "notes": note,
            "destino": destino_name,
            "personas": personas_txt,
            "label": label_txt,
        })

    df_plot = pd.DataFrame(data_rows) if data_rows else pd.DataFrame(columns=["lat","lon","color","trip_id","veh_id","veh_name","timestamp","notes"])

    # Capa de puntos de trail (updates)
    layer_updates = None
    if not df_plot.empty:
        layer_updates = pdk.Layer(
            "ScatterplotLayer",
            df_plot,
            get_position='[lon, lat]',
            get_fill_color='color',
            get_radius=10,
            radius_units='meters',
            radius_min_pixels=2,
            radius_max_pixels=10,
            pickable=True,
        )

    # Capa de Arcos
    layer_arcs = None
    if arc_rows:
        df_arcs = pd.DataFrame(arc_rows)
        layer_arcs = pdk.Layer(
            "ArcLayer",
            df_arcs,
            get_source_position="source",
            get_target_position="target",
            get_source_color="color",
            get_target_color="color",
            get_width=3,
            pickable=True,
        )

    # Capa de Vehículos
    layer_vehicles = None
    if vehicle_rows:
        df_veh_plot = pd.DataFrame(vehicle_rows)
        layer_vehicles = pdk.Layer(
            "ScatterplotLayer",
            df_veh_plot,
            get_position='[lon, lat]',
            get_fill_color='color',
            get_radius=15,
            radius_units='meters',
            radius_min_pixels=6,
            radius_max_pixels=15,
            pickable=True,
            stroked=True,
            get_line_color=[255, 255, 255],
            line_width_min_pixels=1,
        )

    # Normalizar coordenadas a grados y asegurar floats antes de centrar
    def _ensure_deg_series(s: pd.Series) -> pd.Series:
        def _f(v):
            try:
                v = float(v)
                if abs(v) >= 1000:
                    v = v / 1_000_000.0
                return v
            except Exception:
                return None
        return s.apply(_f)

    # Calcular centro
    center_lat, center_lon = -34.603722, -58.381592 # Default
    if vehicle_rows:
        lats = [r['lat'] for r in vehicle_rows]
        lons = [r['lon'] for r in vehicle_rows]
        if lats and lons:
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)

    # Vista fija perpendicular (top-down)
    pitch_val = 0
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=11,
        pitch=pitch_val,
        bearing=0,
    )
    # Capa de puntos de referencia (siempre visibles) desde hoja Destinos con bandera booleana
    layer_reference = None
    try:
        df_dest = st.session_state.get("df_destinos", pd.DataFrame())
        if df_dest.empty:
            df_dest = get_sheet_data(client, SHEET_DESTINOS)
        if not df_dest.empty:
            dcols = {c.lower().strip(): c for c in df_dest.columns}
            name_c = dcols.get('nombre') or dcols.get('destino') or 'Nombre'
            lat_c = dcols.get('lat') or dcols.get('latitud') or 'Lat'
            lon_c = dcols.get('lon') or dcols.get('longitud') or 'Lon'
            flag_c = dcols.get('mostrarsiempre') or dcols.get('mostrar_siempre') or dcols.get('always') or dcols.get('mostrar')
            reference_rows = []
            if name_c in df_dest.columns and lat_c in df_dest.columns and lon_c in df_dest.columns and flag_c in df_dest.columns:
                for _, r in df_dest.iterrows():
                    flag_val = str(r.get(flag_c, '')).strip().lower()
                    is_true = flag_val in ('true','1','si','sí','yes','y','t')
                    if not is_true:
                        continue
                    lat = _parse_coord(r.get(lat_c))
                    lon = _parse_coord(r.get(lon_c))
                    if lat is None or lon is None:
                        continue
                    reference_rows.append({
                        'lat': lat,
                        'lon': lon,
                        'color': [255, 215, 0],
                        'destino': str(r.get(name_c, '')).strip(),
                        'tipo': 'referencia',
                        'veh_name': '',
                        'trip_id': '',
                        'notes': '',
                        'timestamp': '',
                        'label': str(r.get(name_c, '')).strip(),
                    })
            if reference_rows:
                df_ref = pd.DataFrame(reference_rows)
                layer_reference = pdk.Layer(
                    'ScatterplotLayer',
                    df_ref,
                    get_position='[lon, lat]',
                    get_fill_color='color',
                    get_radius=5,
                    radius_units='meters',
                    radius_min_pixels=6,
                    radius_max_pixels=40,
                    stroked=True,
                    get_line_color=[0,0,0,200],
                    line_width_min_pixels=1,
                    pickable=True,
                )
    except Exception:
        pass

    # Orden de capas: Arcos (fondo), Referencias, Updates (trail), Vehículos (top)
    layers = ([layer_arcs] if layer_arcs is not None else []) + \
             ([layer_reference] if layer_reference is not None else []) + \
             ([layer_updates] if layer_updates is not None else []) + \
             ([layer_vehicles] if layer_vehicles is not None else [])
    if not layers:
        st.info("Sin puntos para mostrar (ni trail ni destinos planificados).")
        return
    tooltip = {"text": "{label}"}
    # Estilo de mapa fijo: Dark Matter (oscuro)
    map_style_url = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"

    # Layout: mapa ancho + lista angosta de viajes activos
    col_map, col_list = st.columns([5, 2])
    r = pdk.Deck(map_style=map_style_url, layers=layers, initial_view_state=view_state, tooltip=tooltip)
    with col_map:
        st.caption(f"Centro del mapa: lat={center_lat:.5f}, lon={center_lon:.5f}")
        st.pydeck_chart(r, use_container_width=True, height=520)

    # Lista de viajes activos: Vehículo - Personas - Destino/Ubicación actual
    with col_list:
        st.markdown("##### Viajes activos")
        if st.button("Actualizar", use_container_width=True):
            refresh_data(client, SHEET_VIAJES_UPDATES)
            refresh_data(client, SHEET_VIAJES)
            st.rerun()
        # Última ubicación por TripID
        last_by_trip = {}
        try:
            if not updates_active.empty:
                # Orden por timestamp si existe
                if ts_col in updates_active.columns:
                    updates_active_sorted = updates_active.sort_values(by=ts_col)
                else:
                    updates_active_sorted = updates_active
                last_rows = updates_active_sorted.groupby(tripid_col).tail(1)
                for _, rr in last_rows.iterrows():
                    last_by_trip[str(rr[tripid_col]).strip()] = {
                        'lat': _parse_coord(rr.get(lat_col)),
                        'lon': _parse_coord(rr.get(lon_col)),
                        'ts': str(rr.get(ts_col, '')).strip()
                    }
        except Exception:
            pass

        # Construir líneas
        vcols_i = {c.lower().strip(): c for c in df_active.columns}
        id_v_col = vcols_i.get('id') or 'ID'
        veh_v_col = vcols_i.get('vehiculoid') or vcols_i.get('vehicleid') or 'VehiculoID'
        principal_col = vcols_i.get('destinoprincipal') or 'DestinoPrincipal'
        personas_col = vcols_i.get('personas(json)') or vcols_i.get('personas') or 'Personas(JSON)'
        lines = []
        def _nearest_dest_name(lat, lon):
            if lat is None or lon is None or not destinos_map:
                return None
            best = None
            thr = 0.002
            for name, coords in destinos_map.items():
                dlat = abs(float(coords['lat']) - float(lat))
                dlon = abs(float(coords['lon']) - float(lon))
                if dlat <= thr and dlon <= thr:
                    best = name
                    break
            return best
        for _, row in df_active.iterrows():
            tid = str(row.get(id_v_col, '')).strip()
            vid = str(row.get(veh_v_col, '')).strip()
            vname = veh_names.get(vid, vid)
            ppl_raw = row.get(personas_col, '[]')
            ppl_list = []
            try:
                if isinstance(ppl_raw, str):
                    ppl_list = json.loads(ppl_raw)
                elif isinstance(ppl_raw, list):
                    ppl_list = ppl_raw
            except Exception:
                if isinstance(ppl_raw, str) and ppl_raw.strip():
                    ppl_list = [p.strip() for p in ppl_raw.split(',') if p.strip()]
            ppl_txt = ", ".join([str(p).strip() for p in ppl_list if p])
            destino = str(row.get(principal_col, '')).strip()
            loc = last_by_trip.get(tid)
            loc_name = _nearest_dest_name(loc.get('lat') if loc else None, loc.get('lon') if loc else None)
            loc_txt = f"Ubicación: {loc_name}" if loc_name else (f"Destino: {destino}" if destino else "Sin ubicación")
            line = f"- {vname} - {ppl_txt} - {loc_txt}" if ppl_txt else f"- {vname} - {loc_txt}"
            lines.append(line)
        st.markdown("\n".join(lines) if lines else "Sin viajes para listar")

# --- Info de esquema ---
def _show_schema_info():
    with st.expander("Estructura de hojas (necesaria)"):
        st.markdown("""
- **Vehiculos**: ID, Nombre, Tipo, Color
- **Viajes**: ID, VehiculoID, Personas(JSON), SalidaISO, DestinoPrincipal, DestinosIntermedios(JSON), Estado, CreatedAt
- **ViajesUpdates**: TripID, TimestampISO, Lat, Lon, Notas
- **Destinos**: Nombre, Lat, Lon
        """)

def _tab_destinos(client):
    st.markdown("#### Catálogo de Destinos")
    df = st.session_state.get("df_destinos", pd.DataFrame())
    if not df.empty:
        # Mostrar normalizado
        df_display = df.copy()
        # Intentar renombrar
        rename_map = {}
        for c in df_display.columns:
            c_clean = str(c).strip().lower()
            if c_clean in ("nombre", "destino", "lugar"):
                rename_map[c] = "Nombre"
            elif c_clean in ("lat", "latitud"):
                rename_map[c] = "Lat"
            elif c_clean in ("lon", "lng", "longitud"):
                rename_map[c] = "Lon"
        if rename_map:
            df_display = df_display.rename(columns=rename_map)
        for col in ["Nombre", "Lat", "Lon"]:
            if col not in df_display.columns:
                df_display[col] = ""
        # Normalizar con _parse_coord para vista
        df_display["Lat"] = df_display["Lat"].apply(_parse_coord)
        df_display["Lon"] = df_display["Lon"].apply(_parse_coord)
        st.dataframe(df_display[["Nombre", "Lat", "Lon"]], hide_index=True, width='stretch')

    with st.form("destinos_form", clear_on_submit=True):
        st.markdown("##### Agregar destino")
        nombre = st.text_input("Nombre del destino")
        col1, col2 = st.columns(2)
        lat_text = col1.text_input("Latitud (ej: -34.603722 o -34,603722)")
        lon_text = col2.text_input("Longitud (ej: -58.381592 o -58,381592)")
        if st.form_submit_button("Agregar Destino"):
            lat = _parse_coord(lat_text)
            lon = _parse_coord(lon_text)
            if not nombre.strip():
                st.warning("Ingrese un nombre de destino.")
                return
            if lat is None or lon is None:
                st.warning("Coordenadas inválidas.")
                return
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                st.warning("Rangos inválidos: lat ∈ [-90,90], lon ∈ [-180,180].")
                return
            sheet = get_sheet(client, SHEET_DESTINOS)
            if sheet is None:
                st.error("No se pudo acceder a la hoja 'Destinos'.")
                return
            # Guardar SIEMPRE con punto decimal y 6 decimales
            sheet.append_row([nombre.strip(), f"{lat:.6f}", f"{lon:.6f}"])
            refresh_data(client, SHEET_DESTINOS)
            st.success("Destino agregado correctamente.")
            st.rerun()
