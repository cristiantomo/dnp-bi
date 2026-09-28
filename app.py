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
    """Municipios sin áreas no municipalizadas. Cada fila incluye mdm para TOPSIS."""
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
    categorias_sel = st.pills(
        "Categoría",
        categorias,
        selection_mode="multi",
        default=[],
        help="Puedes marcar varias. Si no marcas ninguna, entran todas las categorías.",
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
        help="Elige el componente urbano, rural o total. Ese mismo entra en el filtro, en el peso de TOPSIS y en el mapa.",
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
    st.divider()
    st.header("Priorización TOPSIS")
    st.caption(
        "Se calcula sobre los municipios que pasan el filtro. "
        "ICEE es costo: menor cobertura, más prioridad. "
        "VSS, NBI y MDM son beneficio: un valor más alto, más prioridad. "
        f"El peso de VSS se aplica a VSS {serie_vss.lower()}."
    )
    peso_icee = st.number_input(
        "Peso ICEE",
        min_value=0.0,
        max_value=1.0,
        value=0.25,
        step=0.01,
        format="%.2f",
        key="peso_icee",
        help="Costo. Una cobertura más baja aumenta la prioridad.",
    )
    peso_vss = st.number_input(
        f"Peso VSS {serie_vss.lower()}",
        min_value=0.0,
        max_value=1.0,
        value=0.25,
        step=0.01,
        format="%.2f",
        key="peso_vss",
        help=f"Beneficio. Se aplica a las viviendas sin servicio {serie_vss.lower()}.",
    )
    peso_nbi = st.number_input(
        "Peso NBI",
        min_value=0.0,
        max_value=1.0,
        value=0.25,
        step=0.01,
        format="%.2f",
        key="peso_nbi",
        help="Beneficio. Más necesidades básicas insatisfechas aumentan la prioridad.",
    )
    peso_mdm = st.number_input(
        "Peso MDM",
        min_value=0.0,
        max_value=1.0,
        value=0.25,
        step=0.01,
        format="%.2f",
        key="peso_mdm",
        help="Beneficio. MDM es el puntaje de la Medición de Desempeño Municipal: un puntaje más alto aumenta la prioridad.",
    )
    pesos_ingresados = (peso_icee, peso_vss, peso_nbi, peso_mdm)
    suma_pesos = None if any(peso is None for peso in pesos_ingresados) else sum(pesos_ingresados)
    st.caption(
        "Suma de pesos: —"
        if suma_pesos is None
        else f"Suma de pesos: {datos.formato_decimal(suma_pesos)}"
    )
    calcular_topsis = st.button(
        "Calcular TOPSIS",
        type="primary",
        icon=":material/calculate:",
        width="stretch",
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

if calcular_topsis:
    if suma_pesos is None:
        st.sidebar.error("Cada peso debe tener un valor entre 0 y 1. No se calculó la priorización.")
    elif abs(suma_pesos - 1) > datos.TOLERANCIA_PESOS:
        st.sidebar.error(
            f"Los pesos suman {datos.formato_decimal(suma_pesos)} y deben sumar 1,00. "
            "No se calculó la priorización."
        )
    else:
        try:
            puntajes = datos.topsis(
                filtradas,
                [
                    ("icee", "ICEE", False, peso_icee),
                    (campo_vss, f"VSS {serie_vss.lower()}", True, peso_vss),
                    ("nbi", "NBI", True, peso_nbi),
                    ("mdm", "MDM", True, peso_mdm),
                ],
            )
        except datos.TopsisError as error:
            st.sidebar.error(str(error))
        else:
            st.session_state.topsis = {
                "puntajes": puntajes,
                "serie": serie_vss,
                "pesos": {
                    "icee": peso_icee,
                    "vss": peso_vss,
                    "nbi": peso_nbi,
                    "mdm": peso_mdm,
                },
                "divipolas": tuple(sorted(puntajes)),
            }
            st.sidebar.success(
                f"Priorización calculada para {len(puntajes)} municipios con VSS {serie_vss.lower()}."
            )

resultado_topsis = st.session_state.get("topsis")
if resultado_topsis:
    pesos_guardados = resultado_topsis["pesos"]
    st.sidebar.caption(
        "Último cálculo: "
        f"{len(resultado_topsis['puntajes'])} municipios, "
        f"VSS {resultado_topsis['serie'].lower()}, "
        f"pesos ICEE {datos.formato_decimal(pesos_guardados['icee'])}, "
        f"VSS {datos.formato_decimal(pesos_guardados['vss'])}, "
        f"NBI {datos.formato_decimal(pesos_guardados['nbi'])}, "
        f"MDM {datos.formato_decimal(pesos_guardados['mdm'])}."
    )

puntajes_topsis = resultado_topsis["puntajes"] if resultado_topsis else {}
filas_vista = []
for fila in filtradas:
    vista = dict(fila)
    vista["priorizacion"] = puntajes_topsis.get(fila["divipola"])
    filas_vista.append(vista)

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
coeficientes = [fila["priorizacion"] for fila in filas_vista if fila["priorizacion"] is not None]

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
    st.metric(
        "Priorización máxima",
        datos.formato_coeficiente(max(coeficientes)) if coeficientes else "—",
        border=True,
        help="Mayor coeficiente TOPSIS entre los municipios del filtro que entraron en el último cálculo.",
    )

if resultado_topsis:
    completos = tuple(
        sorted(
            fila["divipola"]
            for fila in filtradas
            if None not in (fila["icee"], fila[campo_vss], fila["nbi"], fila["mdm"])
        )
    )
    pesos_actuales = (peso_icee, peso_vss, peso_nbi, peso_mdm)
    pesos_previos = (
        resultado_topsis["pesos"]["icee"],
        resultado_topsis["pesos"]["vss"],
        resultado_topsis["pesos"]["nbi"],
        resultado_topsis["pesos"]["mdm"],
    )
    if (
        resultado_topsis["serie"] != serie_vss
        or resultado_topsis["divipolas"] != completos
        or pesos_previos != pesos_actuales
    ):
        st.warning(
            "Los filtros, la serie de VSS o los pesos cambiaron después del cálculo. "
            f"El coeficiente que se muestra es el de VSS {resultado_topsis['serie'].lower()} "
            "con el filtro y los pesos de ese momento. "
            "Pulsa Calcular TOPSIS para actualizarlo."
        )

with st.container(border=True):
    opciones_mapa = datos.variables_mapa(serie_vss)
    if "variable_mapa" not in st.session_state:
        variable = st.segmented_control(
            "Variable del mapa",
            opciones_mapa,
            default="Priorización",
            key="variable_mapa",
            required=True,
        )
    else:
        if st.session_state["variable_mapa"] not in opciones_mapa:
            st.session_state["variable_mapa"] = opciones_mapa[-1]
        variable = st.segmented_control(
            "Variable del mapa",
            opciones_mapa,
            key="variable_mapa",
            required=True,
        )
    campo = datos.CAMPO[variable]
    if variable == "Priorización":
        minimo, maximo = 0.0, 1.0
        logaritmica = False
        if not coeficientes:
            st.info("Calcula TOPSIS en el panel izquierdo para ver el coeficiente en el mapa.")
    else:
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

    poligonos = datos.poligonos_filtrados(filas_vista, indice_geo, variable, minimo, maximo)
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
                "MDM {mdm}\n"
                "VSS urbano {vss_urbano}\n"
                "VSS rural {vss_rural}\n"
                "VSS total {vss_total}\n"
                "Priorización {priorizacion}"
            )
        },
    )
    st.pydeck_chart(mapa, height=640)
    if variable == "Priorización":
        nota_escala = " El coeficiente va de 0 a 1: más color, más prioridad."
    elif logaritmica:
        nota_escala = " En viviendas sin servicio la escala de color es logarítmica."
    else:
        nota_escala = ""
    st.caption(
        "En color, los municipios del filtro. En gris, el resto de municipios del DANE "
        "y, en priorización, los que no tienen coeficiente. "
        "Geometría generalizada a 0,002 grados, WGS84."
        + nota_escala
    )

tabla_df = pd.DataFrame(
    [
        {
            "DIVIPOLA": fila["divipola"],
            "Departamento": fila["departamento"],
            "Municipio": fila["municipio"],
            "Priorización": fila["priorizacion"],
            "Categoría": fila["categoria"],
            "ZOMAC": "Sí" if fila["zomac"] else "No",
            "VSS urbano": fila["vss_urbano"],
            "VSS rural": fila["vss_rural"],
            "VSS total": fila["vss_total"],
            "NBI": fila["nbi"],
            "ICEE": fila["icee"],
            "MDM": fila["mdm"],
            "Área km²": fila["area_km2"],
        }
        for fila in filas_vista
    ]
)
if not tabla_df.empty:
    if tabla_df["Priorización"].notna().any():
        tabla_df = tabla_df.sort_values(["Priorización", "ICEE"], ascending=[False, True])
    else:
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
            "MDM": st.column_config.NumberColumn("MDM", format="%.2f"),
            "Priorización": st.column_config.ProgressColumn(
                "Priorización",
                min_value=0,
                max_value=1,
                format="%.3f",
                help="Coeficiente TOPSIS. Más alto, más prioridad.",
            ),
            "Área km²": st.column_config.NumberColumn(format="%.1f"),
        },
        hide_index=True,
        height=480,
    )
