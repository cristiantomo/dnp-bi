# Manual de usuario de SIMPLE

La versión para compartir es el archivo Word `MANUAL_USUARIO.docx`. Este Markdown es el borrador del texto.

SIMPLE es el Simulador de Priorización Municipal para la Energización.

Sirve para ver los municipios de Colombia, filtrarlos y ordenarlos según la prioridad de energización. La prioridad se calcula con el método TOPSIS.

Solo entran municipios. Las áreas no municipalizadas quedan fuera de los filtros, del mapa y de la tabla.

## Cómo abrirlo

En la carpeta del proyecto, con las dependencias instaladas:

```bash
streamlit run app.py
```

Se abre en el navegador. Si ya tienes un enlace de la aplicación, ábrelo directo.

## La pantalla

A la izquierda está el panel de filtros y de priorización.

Arriba, al centro, hay cinco cifras de los municipios que pasan el filtro:

- **Municipios.** Cuántos municipios quedan.
- **VSS.** Suma de viviendas sin servicio. Usa la serie que elegiste: urbano, rural o total.
- **ICEE promedio.** Promedio del índice de cobertura, ponderado por esas viviendas sin servicio.
- **NBI promedio.** Promedio simple del NBI de esos municipios.
- **Priorización máxima.** El puntaje TOPSIS más alto del último cálculo, entre los municipios que siguen en el filtro. Si aún no calculas, sale un guion.

Debajo está el mapa. Al final está la tabla.

## Filtrar municipios

Los filtros están en el panel izquierdo. Si no tocas un filtro, entran todos los municipios.

Puedes combinarlos. Un municipio entra solo si cumple todos a la vez.

- **ICEE.** Rango del índice de cobertura. Se mueve con dos puntos.
- **Departamento.** Puedes marcar varios. Si no marcas ninguno, entran todos.
- **Municipio.** La lista muestra municipio, departamento y código DIVIPOLA. Si elegiste departamentos, solo ves municipios de esos departamentos. Si cambias el departamento, vuelve a elegir el municipio.
- **Categoría.** De 1 a 6, o ESP (especial). Puedes marcar varias. Si no marcas ninguna, entran todas.
- **ZOMAC.** Zonas más afectadas por el conflicto armado. Elige Todas, Sí o No.
- **Viviendas sin servicio.** Elige Urbano, Rural o Total. Esa misma serie se usa en el filtro de VSS, en el peso de TOPSIS, en el mapa y en las cifras de arriba.
- **VSS.** Rango de viviendas sin servicio de la serie elegida.
- **NBI.** Rango de necesidades básicas insatisfechas.
- **Valor agregado per cápita.** Rango de ese indicador.

Los rangos se ajustan a los demás filtros. El mínimo y el máximo de cada barra son los de los municipios que pasan el resto de filtros.

Si dejas una barra en sus extremos, sigue ajustándose sola. Si la estrechas, se conserva tu elección.

Un municipio sin dato de viviendas sin servicio, o sin valor agregado per cápita, no entra en el filtro.

## Calcular la priorización

El cálculo está al final del panel izquierdo. No corre solo. Pulsa **Calcular TOPSIS**.

Hay cinco pesos. Cada uno va de 0 a 1. Al abrir la aplicación, cada peso vale 0,20. La suma debe ser 1,00. La suma se ve debajo de los pesos.

| Peso | Qué hace un valor más alto |
| --- | --- |
| ICEE | Baja la prioridad. Es un costo: menos cobertura, más prioridad. |
| VSS urbano, rural o total | Sube la prioridad. Más viviendas sin servicio, más prioridad. |
| NBI | Sube la prioridad. Más necesidades básicas insatisfechas, más prioridad. |
| MDM | Sube la prioridad. Más puntaje de desempeño municipal, más prioridad. |
| Valor agregado per cápita | Sube la prioridad. Más valor agregado por habitante, más prioridad. |

El peso de VSS se aplica a la serie que esté elegida en ese momento.

El puntaje va de 0 a 1. Más alto, más prioridad. Se calcula solo con los municipios del filtro que tienen los cinco datos: ICEE, VSS de la serie elegida, NBI, MDM y valor agregado per cápita. Hacen falta al menos dos municipios con esos datos.

El orden es relativo a ese grupo. Si cambias el filtro y vuelves a calcular, los puntajes cambian.

Si después del cálculo cambias filtros, la serie de VSS o los pesos, aparece un aviso. El puntaje que ves sigue siendo el del cálculo anterior. Pulsa **Calcular TOPSIS** otra vez para actualizarlo.

Estos mensajes impiden el cálculo:

- Algún peso está vacío o fuera de 0 a 1.
- Los pesos no suman 1,00.
- Hay menos de dos municipios con los cinco datos.
- Un criterio vale cero en todos los municipios del filtro.

Cuando el cálculo sale bien, el panel dice para cuántos municipios se hizo y con qué serie de VSS.

## Leer el mapa

Sobre el mapa eliges la variable del color:

- Priorización
- ICEE
- NBI
- MDM
- VSS de la serie elegida
- Valor agregado per cápita

La barra de color muestra la escala. En viviendas sin servicio y en valor agregado per cápita la escala es logarítmica: los valores bajos se distinguen mejor y los muy altos no dominan el color.

Cómo leer el color:

- **Priorización, NBI, viviendas sin servicio y valor agregado per cápita.** El color oscuro es un valor alto.
- **ICEE y MDM.** El verde es un valor alto. El rojo es un valor bajo. En estos dos, el valor alto es mejor cobertura o mejor desempeño.
- **Priorización.** El coeficiente va de 0 a 1. Más color, más prioridad. Si aún no calculas, el mapa lo indica.

En color están los municipios del filtro. En gris está el resto del país. En priorización, también quedan en gris los municipios del filtro que no tienen puntaje.

El mapa se centra en los municipios del filtro. Puedes acercar, alejar y moverlo. Al pasar el cursor sobre un municipio ves su nombre, departamento, DIVIPOLA, ICEE, NBI, MDM, VSS urbano, rural y total, valor agregado per cápita y priorización.

La geometría es el Marco Geoestadístico Nacional 2025 del DANE.

## Leer la tabla y descargar

La tabla se llama **Municipios filtrados**. Muestra solo los municipios que pasan el filtro.

Columnas: DIVIPOLA, departamento, municipio, priorización, categoría, ZOMAC, VSS urbano, VSS rural, VSS total, NBI, ICEE, MDM, valor agregado per cápita y área en km².

Orden:

- Si ya hay puntaje, primero el de mayor priorización. Si empatan, primero el de menor ICEE.
- Si no hay puntaje, primero el de menor ICEE y luego el de más viviendas sin servicio de la serie elegida.

ICEE y priorización se ven como barra. La priorización vacía significa que ese municipio no entró en el último cálculo.

**Descargar tabla filtrada** baja un archivo CSV llamado `municipios_icee_filtrado.csv`. Usa punto y coma entre columnas y coma decimal, para abrirlo en Excel en español. El archivo trae las filas del filtro, no todos los municipios del país.

## Qué significa cada dato

- **DIVIPOLA.** Código de cinco dígitos del municipio, del DANE.
- **ICEE.** Índice de Cobertura de Energía Eléctrica. Porcentaje de viviendas del municipio con servicio de energía eléctrica. Año 2024, entregado por el DNP.
- **VSS.** Viviendas sin servicio de energía eléctrica. Puede ser el área urbana, el área rural o el total. Se calcula con el ICEE de 2024.
- **NBI.** Necesidades Básicas Insatisfechas. Porcentaje de personas sin cubrir vivienda, servicios, espacio para vivir, escuela o ingresos del hogar. Fuente: DANE.
- **MDM.** Medición de Desempeño Municipal. Junta la gestión de la alcaldía y los resultados en educación, salud, servicios públicos y seguridad. Fuente: DNP, TerriData.
- **Valor agregado per cápita.** Lo que se produce en el municipio, dividido por su población. En la aplicación se muestra en millones de pesos por habitante. Fuentes: DANE, cuentas nacionales departamentales y proyecciones de población.
- **Categoría.** Categoría municipal, de 1 a 6, o ESP si es especial.
- **ZOMAC.** Sí, si el municipio es zona más afectada por el conflicto armado.
- **Área km².** Área del municipio según el mapa del DANE.

## Ejemplo corto

1. Deja los filtros como están, o elige un departamento.
2. En viviendas sin servicio, deja **Total** o cambia a **Rural** si quieres priorizar el área rural.
3. Revisa que los cinco pesos sumen 1,00.
4. Pulsa **Calcular TOPSIS**.
5. En el mapa, elige **Priorización**.
6. Mira la tabla: el primer municipio es el de mayor prioridad en ese filtro.
7. Si cambias un filtro o un peso, pulsa **Calcular TOPSIS** otra vez.
8. Descarga la tabla si necesitas llevarte el resultado.
