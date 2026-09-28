"""Carga de la tabla ICEE y de los polígonos municipales del DANE."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "datos" / "Municipio con ICEE menor a 95 por ciento.csv"
GEO_PATH = ROOT / "datos" / "geo" / "municipios_mgn2025.geojson"

VARIABLES = ("ICEE", "NBI", "VSS urbano", "VSS rural", "VSS total")
CAMPO = {
    "ICEE": "icee",
    "NBI": "nbi",
    "VSS urbano": "vss_urbano",
    "VSS rural": "vss_rural",
    "VSS total": "vss_total",
}
SERIES_VSS = {
    "Urbano": "vss_urbano",
    "Rural": "vss_rural",
    "Total": "vss_total",
}

# Bajo, medio y alto. En ICEE el valor alto es mejor cobertura.
# En NBI y en viviendas sin servicio el valor alto es la situación más grave.
PALETAS = {
    "ICEE": ((159, 18, 57), (217, 119, 6), (15, 118, 110)),
    "NBI": ((15, 118, 110), (217, 119, 6), (159, 18, 57)),
    "VSS urbano": ((153, 246, 228), (217, 119, 6), (159, 18, 57)),
    "VSS rural": ((153, 246, 228), (217, 119, 6), (159, 18, 57)),
    "VSS total": ((153, 246, 228), (217, 119, 6), (159, 18, 57)),
}
COLORES_LEYENDA = {
    "ICEE": ["#9F1239", "#D97706", "#0F766E"],
    "NBI": ["#0F766E", "#D97706", "#9F1239"],
    "VSS urbano": ["#99F6E4", "#D97706", "#9F1239"],
    "VSS rural": ["#99F6E4", "#D97706", "#9F1239"],
    "VSS total": ["#99F6E4", "#D97706", "#9F1239"],
}
GRIS_SIN_DATO = [148, 163, 184, 170]
VISTA_COLOMBIA = {"latitude": 4.57, "longitude": -73.9, "zoom": 4.55}


def limpiar_nombre(valor: str) -> str:
    texto = " ".join(valor.strip().split())
    return texto.replace("D,C,", "D.C.").replace("D,C", "D.C.")


def _numero(valor: str) -> float | None:
    texto = valor.strip()
    if not texto:
        return None
    return float(texto.replace(".", "").replace(",", "."))


def _texto(registro: dict, columna: str) -> str:
    return (registro.get(columna) or "").strip()


def cargar_tabla(path: Path = CSV_PATH) -> list[dict]:
    filas = []
    with path.open(newline="", encoding="utf-8") as archivo:
        for registro in csv.DictReader(archivo, delimiter=";"):
            codigo = _texto(registro, "DIVIPOLA MUNICIPIO")
            if not codigo:
                continue
            filas.append(
                {
                    "divipola": codigo.zfill(5),
                    "departamento": limpiar_nombre(_texto(registro, "NOMBRE DEPARTAMENTO")),
                    "municipio": limpiar_nombre(_texto(registro, "NOMBRE MUNICIPIO")),
                    "nbi": _numero(_texto(registro, "NBI")),
                    "icee": _numero(_texto(registro, "ICEE")),
                    "categoria": _texto(registro, "CATEGORIA"),
                    "zomac": _texto(registro, "ZOMAC") == "1",
                    "vss_urbano": _numero(_texto(registro, "VSS Urbano")),
                    "vss_rural": _numero(_texto(registro, "VSS Rural")),
                    "vss_total": _numero(_texto(registro, "VSS Total")),
                    "anm": _texto(registro, "ANM") == "1",
                }
            )
    return filas


def cargar_geo(path: Path = GEO_PATH) -> tuple[dict, list[dict]]:
    coleccion = json.loads(path.read_text(encoding="utf-8"))
    indice = {}
    for feature in coleccion["features"]:
        indice[feature["properties"]["divipola"]] = feature
    return indice, coleccion["features"]


def filtrar(
    filas: list[dict],
    icee: tuple[float, float],
    departamentos: list[str],
    divipolas: list[str],
    campo_vss: str,
    vss: tuple[float, float],
    nbi: tuple[float, float],
    categorias: list[str],
    zomac: str,
) -> list[dict]:
    departamentos = set(departamentos)
    divipolas = set(divipolas)
    categorias = set(categorias)
    resultado = []
    for fila in filas:
        if fila["anm"]:
            continue
        if not (icee[0] <= fila["icee"] <= icee[1]):
            continue
        if departamentos and fila["departamento"] not in departamentos:
            continue
        if divipolas and fila["divipola"] not in divipolas:
            continue
        if categorias and fila["categoria"] not in categorias:
            continue
        if zomac == "Sí" and not fila["zomac"]:
            continue
        if zomac == "No" and fila["zomac"]:
            continue
        valor_vss = fila[campo_vss]
        if valor_vss is None or not (vss[0] <= valor_vss <= vss[1]):
            continue
        if fila["nbi"] is not None and not (nbi[0] <= fila["nbi"] <= nbi[1]):
            continue
        resultado.append(fila)
    return resultado


def _mezcla(color_a: tuple[int, int, int], color_b: tuple[int, int, int], peso: float) -> list[int]:
    return [int(color_a[canal] + (color_b[canal] - color_a[canal]) * peso) for canal in range(3)]


def color_valor(variable: str, valor: float | None, minimo: float, maximo: float) -> list[int]:
    if valor is None or maximo <= minimo:
        return GRIS_SIN_DATO
    if variable.startswith("VSS"):
        piso = max(minimo, 1)
        techo = max(maximo, piso + 1)
        posicion = (math.log(max(valor, piso)) - math.log(piso)) / (math.log(techo) - math.log(piso))
    else:
        posicion = (valor - minimo) / (maximo - minimo)
    posicion = min(1.0, max(0.0, posicion))
    bajo, medio, alto = PALETAS[variable]
    if posicion <= 0.5:
        rgb = _mezcla(bajo, medio, posicion / 0.5)
    else:
        rgb = _mezcla(medio, alto, (posicion - 0.5) / 0.5)
    return [*rgb, 210]


def formato_decimal(valor: float | None) -> str:
    if valor is None:
        return "Sin dato"
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formato_entero(valor: float | None) -> str:
    if valor is None:
        return "Sin dato"
    return f"{int(round(valor)):,}".replace(",", ".")


def poligonos_filtrados(
    filas: list[dict],
    indice_geo: dict,
    variable: str,
    minimo: float,
    maximo: float,
) -> list[dict]:
    campo = CAMPO[variable]
    features = []
    for fila in filas:
        base = indice_geo.get(fila["divipola"])
        if base is None:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "divipola": fila["divipola"],
                    "municipio": fila["municipio"],
                    "departamento": fila["departamento"],
                    "icee": formato_decimal(fila["icee"]),
                    "nbi": formato_decimal(fila["nbi"]),
                    "vss_urbano": formato_entero(fila["vss_urbano"]),
                    "vss_rural": formato_entero(fila["vss_rural"]),
                    "vss_total": formato_entero(fila["vss_total"]),
                    "fill_color": color_valor(variable, fila[campo], minimo, maximo),
                },
                "geometry": base["geometry"],
            }
        )
    return features


def _recorrer(coordenadas, xs: list[float], ys: list[float]) -> None:
    if isinstance(coordenadas[0], (int, float)):
        xs.append(coordenadas[0])
        ys.append(coordenadas[1])
        return
    for parte in coordenadas:
        _recorrer(parte, xs, ys)


def vista_para(features: list[dict]) -> dict:
    if not features:
        return dict(VISTA_COLOMBIA)
    xs: list[float] = []
    ys: list[float] = []
    for feature in features:
        _recorrer(feature["geometry"]["coordinates"], xs, ys)
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    extension = max(maxx - minx, (maxy - miny) * 1.2, 0.15)
    if extension > 10:
        return dict(VISTA_COLOMBIA)
    zoom = 5.15 - math.log2(extension / 4.0)
    return {
        "latitude": (miny + maxy) / 2,
        "longitude": (minx + maxx) / 2,
        "zoom": max(4.0, min(10.5, zoom)),
    }


def limites(filas: list[dict], campo: str) -> tuple[float, float]:
    valores = [fila[campo] for fila in filas if fila[campo] is not None]
    return min(valores), max(valores)


def muestra_leyenda(minimo: float, maximo: float, logaritmica: bool, n: int = 48) -> list[float]:
    if logaritmica:
        piso = max(minimo, 1)
        techo = max(maximo, piso + 1)
        return [math.exp(math.log(piso) + (math.log(techo) - math.log(piso)) * i / (n - 1)) for i in range(n)]
    return [minimo + (maximo - minimo) * i / (n - 1) for i in range(n)]
