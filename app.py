"""Mapa de municipios con ICEE menor a 95%."""

from __future__ import annotations

import pandas as pd
import pydeck as pdk
import streamlit as st
import altair as alt

import municipios as datos

st.set_page_config(
    page_title="ICEE municipal",
    page_icon=":material/map:",
    layout="wide",
)

ORDEN_CATEGORIA = {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "ESP": 7}


@st.cache_data
def tabla():
    filas = [fila for fila in datos.cargar_tabla() if not fila["anm"]]
    indice, contexto = datos.cargar_geo()
    contexto = [
        feature
        for feature in contexto
        if feature["properties"].get("tipo") == "MUNICIPIO"
    ]
    for fila in filas:
        feature = indice.get(fila["divipola"])
        fila["area_km2"] = feature["properties"]["area_km2"] if feature else None
        fila["en_mapa"] = feature is not None
    return filas, indice, contexto


filas, indice_geo, contexto = tabla()
icee_min, icee_max = datos.limites(filas, "icee")
nbi_min, nbi_max = datos.limites(filas, "nbi")
departamentos = sorted({fila["departamento"] for fila in filas})
categorias = sorted(
    {fila["categoria"] for fila in filas if fila["categoria"]},
    key=lambda valor: ORDEN_CATEGORIA.get(valor, 99),
)

with st.sidebar:
    st.header("Filtros")
    st.caption("Solo municipios. Las áreas no municipalizadas quedan por fuera.")
    icee = st.slider(
        "ICEE",
        min_value=icee_min,
        max_value=icee_max,
        value=(icee_min, icee_max),
        help="Índice de cobertura de energía eléctrica. Un valor más alto es más cobertura.",
    )
    departamentos_sel = st.multiselect(
        "Departamento",
        departamentos,
        placeholder="Todos los departamentos",
    )
    candidatos = [
        fila
        for fila in filas
        if not departamentos_sel or fila["departamento"] in departamentos_sel
    ]
    etiquetas = {
        fila["divipola"]: f"{fila['municipio']} · {fila['departamento']} · {fila['divipola']}"
        for fila in candidatos
    }
    municipios_sel = st.multiselect(
        "Municipio",
        sorted(etiquetas, key=lambda codigo: etiquetas[codigo]),
        format_func=lambda codigo: etiquetas[codigo],
        placeholder="Todos los municipios",
        key="municipios-" + "|".join(departamentos_sel),
    )
    categorias_sel = st.multiselect(
        "Categoría",
        categorias,
        placeholder="Todas las categorías",
    )
    zomac = st.segmented_control(
        "ZOMAC",
        ["Todas", "Sí", "No"],
        default="Todas",
        required=True,
        help="Zonas más afectadas por el conflicto armado.",
    )
    serie_vss = st.segmented_control(
        "Viviendas sin servicio",
        list(datos.SERIES_VSS),
        default="Total",
        required=True,
        help="Elige si el rango se aplica al componente urbano, al rural o al total.",
    )
    campo_vss = datos.SERIES_VSS[serie_vss]
    vss_min, vss_max = datos.limites(filas, campo_vss)
    vss_min, vss_max = int(vss_min), int(vss_max)
    if vss_max <= vss_min:
        vss_max = vss_min + 1
    vss = st.slider(
        f"VSS {serie_vss.lower()}",
        min_value=vss_min,
        max_value=vss_max,
        value=(vss_min, vss_max),
        key=f"vss-{serie_vss}",
    )
    nbi = st.slider(
        "NBI",
        min_value=nbi_min,
        max_value=nbi_max,
        value=(nbi_min, nbi_max),
        help="Necesidades básicas insatisfechas, en porcentaje.",
    )

filtradas = datos.filtrar(
    filas,
    icee,
    departamentos_sel,
    municipios_sel,
    campo_vss,
    vss,
    nbi,
    categorias_sel,
    zomac,
)

st.title("Municipios con ICEE menor a 95%")
st.caption(
    "Cada municipio se ubica con su código DIVIPOLA sobre el Marco Geoestadístico Nacional 2025 del DANE. "
    "Las áreas no municipalizadas no entran en los filtros, el mapa ni la tabla."
)

vss_total = sum(fila[campo_vss] or 0 for fila in filtradas)
icee_ponderado = (
    sum((fila["icee"] or 0) * (fila[campo_vss] or 0) for fila in filtradas) / vss_total
    if vss_total
    else None
)
nbi_valores = [fila["nbi"] for fila in filtradas if fila["nbi"] is not None]
nbi_promedio = sum(nbi_valores) / len(nbi_valores) if nbi_valores else None

with st.container(horizontal=True):
    st.metric("Municipios", f"{len(filtradas):,}".replace(",", "."), border=True)
    st.metric(
        f"VSS {serie_vss.lower()}",
        f"{int(round(vss_total)):,}".replace(",", "."),
        border=True,
    )
    st.metric(
        "ICEE promedio",
        datos.formato_decimal(icee_ponderado) if icee_ponderado is not None else "—",
        border=True,
        help=f"Promedio ponderado por VSS {serie_vss.lower()}.",
    )
    st.metric(
        "NBI promedio",
        datos.formato_decimal(nbi_promedio) if nbi_promedio is not None else "—",
        border=True,
    )

with st.container(border=True):
    variable = st.segmented_control(
        "Variable del mapa",
        datos.VARIABLES,
        default="ICEE",
        required=True,
    )
    campo = datos.CAMPO[variable]
    minimo, maximo = datos.limites(filas, campo)
    logaritmica = variable.startswith("VSS")
    if logaritmica:
        minimo_eje = max(minimo, 1)
        maximo_eje = max(maximo, minimo_eje + 1)
    else:
        minimo_eje, maximo_eje = minimo, maximo
    leyenda = pd.DataFrame(
        {"valor": datos.muestra_leyenda(minimo_eje, maximo_eje, logaritmica), "banda": 1}
    )
    escala_x = alt.Scale(type="log" if logaritmica else "linear", domain=[minimo_eje, maximo_eje])
    escala_color = alt.Scale(
        type="log" if logaritmica else "linear",
        domain=[minimo_eje, maximo_eje],
        range=datos.COLORES_LEYENDA[variable],
    )
    grafico = (
        alt.Chart(leyenda)
        .mark_bar(size=18)
        .encode(
            x=alt.X("valor:Q", title=variable, scale=escala_x),
            y=alt.Y("banda:Q", axis=None),
            color=alt.Color("valor:Q", scale=escala_color, legend=None),
            tooltip=[alt.Tooltip("valor:Q", title=variable, format=",.2f")],
        )
        .properties(height=88)
        .configure_view(strokeWidth=0)
        .configure_axis(grid=False)
    )
    st.altair_chart(grafico)

    poligonos = datos.poligonos_filtrados(filtradas, indice_geo, variable, minimo, maximo)
    vista = datos.vista_para(poligonos)
    mapa = pdk.Deck(
        layers=[
            pdk.Layer(
                "GeoJsonLayer",
                {"type": "FeatureCollection", "features": contexto},
                id="contexto",
                stroked=True,
                filled=True,
                pickable=False,
                get_fill_color=[226, 232, 230, 255],
                get_line_color=[186, 198, 196, 255],
                line_width_min_pixels=0.4,
            ),
            pdk.Layer(
                "GeoJsonLayer",
                {"type": "FeatureCollection", "features": poligonos},
                id="municipios",
                stroked=True,
                filled=True,
                pickable=True,
                auto_highlight=True,
                get_fill_color="properties.fill_color",
                get_line_color=[30, 41, 40, 180],
                line_width_min_pixels=0.8,
            ),
        ],
        initial_view_state=pdk.ViewState(
            latitude=vista["latitude"],
            longitude=vista["longitude"],
            zoom=vista["zoom"],
            min_zoom=3.2,
            max_zoom=12,
        ),
        map_provider="carto",
        map_style="light",
        tooltip={
            "text": (
                "{municipio} · {departamento}\n"
                "DIVIPOLA {divipola}\n"
                "ICEE {icee}\n"
                "NBI {nbi}\n"
                "VSS urbano {vss_urbano}\n"
                "VSS rural {vss_rural}\n"
                "VSS total {vss_total}"
            )
        },
    )
    st.pydeck_chart(mapa, height=640)
    st.caption(
        "En color, los municipios del filtro. En gris, el resto de municipios del DANE. "
        "Geometría generalizada a 0,002 grados, WGS84. "
        "En viviendas sin servicio la escala de color es logarítmica."
        if logaritmica
        else "En color, los municipios del filtro. En gris, el resto de municipios del DANE. "
        "Geometría generalizada a 0,002 grados, WGS84."
    )

tabla_df = pd.DataFrame(
    [
        {
            "DIVIPOLA": fila["divipola"],
            "Departamento": fila["departamento"],
            "Municipio": fila["municipio"],
            "Categoría": fila["categoria"],
            "ZOMAC": "Sí" if fila["zomac"] else "No",
            "VSS urbano": fila["vss_urbano"],
            "VSS rural": fila["vss_rural"],
            "VSS total": fila["vss_total"],
            "NBI": fila["nbi"],
            "ICEE": fila["icee"],
            "Área km²": fila["area_km2"],
        }
        for fila in filtradas
    ]
)
if not tabla_df.empty:
    tabla_df = tabla_df.sort_values(["ICEE", f"VSS {serie_vss.lower()}"], ascending=[True, False])

with st.container(border=True):
    st.subheader("Municipios filtrados")
    st.download_button(
        "Descargar tabla filtrada",
        data=tabla_df.to_csv(index=False, sep=";", decimal=",").encode("utf-8"),
        file_name="municipios_icee_filtrado.csv",
        mime="text/csv",
        icon=":material/download:",
    )
    st.dataframe(
        tabla_df,
        column_config={
            "VSS urbano": st.column_config.NumberColumn(format="localized"),
            "VSS rural": st.column_config.NumberColumn(format="localized"),
            "VSS total": st.column_config.NumberColumn(format="localized"),
            "NBI": st.column_config.NumberColumn(format="%.2f"),
            "ICEE": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.2f"),
            "Área km²": st.column_config.NumberColumn(format="%.1f"),
        },
        hide_index=True,
        height=480,
    )
