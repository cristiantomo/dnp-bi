"""Carga de la tabla ICEE y de los polígonos municipales del DANE."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "datos" / "Municipio con ICEE menor a 95 por ciento.csv"
GEO_PATH = ROOT / "datos" / "geo" / "municipios_mgn2025.geojson"

CAMPO = {
    "Priorización": "priorizacion",
    "ICEE": "icee",
    "NBI": "nbi",
    "MDM": "mdm",
    "VSS urbano": "vss_urbano",
    "VSS rural": "vss_rural",
    "VSS total": "vss_total",
}
SERIES_VSS = {
    "Urbano": "vss_urbano",
    "Rural": "vss_rural",
    "Total": "vss_total",
}


def variables_mapa(serie_vss: str) -> list[str]:
    """Orden del mapa: priorización, ICEE, NBI, MDM y la serie de VSS elegida."""
    return ["Priorización", "ICEE", "NBI", "MDM", f"VSS {serie_vss.lower()}"]

# Bajo, medio y alto. En ICEE y en MDM el valor alto es mejor.
# En NBI, viviendas sin servicio y priorización el valor alto es la situación más grave.
PALETAS = {
    "Priorización": ((153, 246, 228), (217, 119, 6), (159, 18, 57)),
    "ICEE": ((159, 18, 57), (217, 119, 6), (15, 118, 110)),
    "NBI": ((15, 118, 110), (217, 119, 6), (159, 18, 57)),
    "MDM": ((159, 18, 57), (217, 119, 6), (15, 118, 110)),
    "VSS urbano": ((153, 246, 228), (217, 119, 6), (159, 18, 57)),
    "VSS rural": ((153, 246, 228), (217, 119, 6), (159, 18, 57)),
    "VSS total": ((153, 246, 228), (217, 119, 6), (159, 18, 57)),
}
COLORES_LEYENDA = {
    "Priorización": ["#99F6E4", "#D97706", "#9F1239"],
    "ICEE": ["#9F1239", "#D97706", "#0F766E"],
    "NBI": ["#0F766E", "#D97706", "#9F1239"],
    "MDM": ["#9F1239", "#D97706", "#0F766E"],
    "VSS urbano": ["#99F6E4", "#D97706", "#9F1239"],
    "VSS rural": ["#99F6E4", "#D97706", "#9F1239"],
    "VSS total": ["#99F6E4", "#D97706", "#9F1239"],
}
TOLERANCIA_PESOS = 1e-4
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
                    "mdm": _numero(_texto(registro, "mdm")),
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


class TopsisError(ValueError):
    """El cálculo TOPSIS no se puede hacer con estos datos o estos pesos."""


def topsis(
    filas: list[dict],
    criterios: list[tuple[str, str, bool, float]],
) -> dict[str, float]:
    """Coeficiente de priorización TOPSIS por DIVIPOLA.

    Cada criterio es (campo, etiqueta, es_beneficio, peso). En un beneficio,
    el valor alto se acerca al ideal positivo. En un costo, el valor bajo.
    El coeficiente va de 0 a 1: más alto, más cerca del ideal positivo.
    """
    if len(criterios) < 2:
        raise TopsisError("TOPSIS necesita al menos dos criterios.")
    pesos = [peso for _, _, _, peso in criterios]
    if any(peso < 0 for peso in pesos):
        raise TopsisError("Los pesos no pueden ser negativos.")
    if abs(sum(pesos) - 1) > TOLERANCIA_PESOS:
        raise TopsisError("Los pesos deben sumar 1.")

    campos = [campo for campo, _, _, _ in criterios]
    utiles: list[tuple[str, list[float]]] = []
    for fila in filas:
        valores = [fila[campo] for campo in campos]
        if any(valor is None for valor in valores):
            continue
        utiles.append((fila["divipola"], valores))
    if len(utiles) < 2:
        raise TopsisError(
            "Se necesitan al menos dos municipios con ICEE, VSS, NBI y mdm. "
            f"En el filtro hay {len(filas)} y {len(utiles)} tienen los cuatro datos."
        )

    normas = []
    for indice, (_, etiqueta, _, _) in enumerate(criterios):
        norma = math.sqrt(sum(valores[indice] ** 2 for _, valores in utiles))
        if norma == 0:
            raise TopsisError(
                f"{etiqueta} vale cero en todos los municipios del filtro, "
                "así que no se puede normalizar."
            )
        normas.append(norma)

    matriz = [
        [peso * valores[indice] / normas[indice] for indice, peso in enumerate(pesos)]
        for _, valores in utiles
    ]
    ideal_positivo = []
    ideal_negativo = []
    for indice, (_, _, es_beneficio, _) in enumerate(criterios):
        columna = [fila[indice] for fila in matriz]
        if es_beneficio:
            ideal_positivo.append(max(columna))
            ideal_negativo.append(min(columna))
        else:
            ideal_positivo.append(min(columna))
            ideal_negativo.append(max(columna))

    puntajes = {}
    for (codigo, _), ponderada in zip(utiles, matriz):
        distancia_positiva = math.sqrt(
            sum((ponderada[indice] - ideal_positivo[indice]) ** 2 for indice in range(len(criterios)))
        )
        distancia_negativa = math.sqrt(
            sum((ponderada[indice] - ideal_negativo[indice]) ** 2 for indice in range(len(criterios)))
        )
        if distancia_positiva == 0:
            puntajes[codigo] = 1.0
        else:
            puntajes[codigo] = distancia_negativa / (distancia_positiva + distancia_negativa)
    return puntajes


def formato_decimal(valor: float | None) -> str:
    if valor is None:
        return "Sin dato"
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formato_coeficiente(valor: float | None) -> str:
    if valor is None:
        return "Sin cálculo"
    return f"{valor:.3f}".replace(".", ",")


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
                    "mdm": formato_decimal(fila.get("mdm")),
                    "priorizacion": formato_coeficiente(fila.get("priorizacion")),
                    "fill_color": color_valor(variable, fila.get(campo), minimo, maximo),
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
