# Fase 1 — EPS a PES monocromático (prueba de concepto)

- **Un hilo, un color**, color por defecto `#000000`.
- **Área máxima: 6 cm × 6 cm = 60 mm × 60 mm**.
- Por defecto se reserva un margen de 2 mm por lado: lienzo escalado máximo de 56 × 56 mm.
- No cambia el EPS original.
- Repetir una entrada con iguales parámetros devuelve el resultado previo (idempotencia por SHA-256).
- Se conserva la proporción; no se amplía obligatoriamente hasta 60 × 60.

## Requisitos Ubuntu

```bash
sudo apt update
sudo apt install -y inkscape ghostscript git python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pyembroidery lxml
# Instalar CLI desde el código del proyecto (el README oficial sugiere pip editable):
git clone https://github.com/bobbymarko/cli-anything-inkstitch.git vendor/cli-anything-inkstitch
pip install -e ./vendor/cli-anything-inkstitch
```

**Instalar Ink/Stitch aparte**, desde https://inkstitch.org/docs/install/ . No basta con instalar `cli-anything-inkstitch`: el CLI llama al motor nativo de Ink/Stitch. Verifica cuál es su ubicación real y configura, por ejemplo:

```bash
export INKSTITCH_BINARY="/ruta/real/al/ejecutable/inkstitch"
cli-anything-inkstitch --help
inkscape --version
```

Si `inkstitch` está en tu `PATH`, no necesitas la variable. No se recomienda ejecutar EPS de usuarios desconocidos fuera de un contenedor aislado; **este MVP es solo para EPS locales confiables**.

## Ejecutar

```bash
python embroidery_poc.py ./samples/logo.eps --output ./outputs
```

Color distinto (sigue siendo un solo hilo):

```bash
python embroidery_poc.py ./samples/logo.eps --color '#003366' --margin-mm 2
```

Forzar recomputar y aplicar comprobación estricta del motor:

```bash
python embroidery_poc.py ./samples/logo.eps --strict --force
```

Salida por trabajo:

```text
outputs/logo-<hash>/
  design.svg       SVG normalizado y preparado para Ink/Stitch
  design.pes       Patrón PES
  preview.png      Simulación de puntadas (no foto de bordado)
  project.json     Estado de cli-anything-inkstitch
  result.json      Metadatos/medidas/validación
```

## Límites de esta primera iteración

1. **No hay digitalización inteligente por elementos**: Ink/Stitch clasifica rellenos y líneas según su geometría. En particular, no convierte automáticamente cualquier letra o figura en satén.
2. El EPS puede contener imágenes, gradientes, fuentes ausentes o construcciones que se aplanan al convertir. El script rechaza explícitamente parte de los SVG problemáticos, pero no detecta todos.
3. Los objetos solapados en el mismo color pueden producir bordado excesivamente denso: todavía no hay operación de unión/deduplicación geométrica.
4. La escala usa el `viewBox` (área de página), no un cálculo exacto de la caja del dibujo. Un EPS con grandes márgenes tendrá bordado menor al esperado.
5. `pyembroidery` vuelve a abrir el PES para verificar que exista contenido, que tenga **como máximo 60 × 60 mm** y no declare más de un color de hilo. Esto no garantiza que los parámetros sean adecuados para el material.
6. No se garantiza ejecución sin ajustes locales: la instalación y la interfaz de `cli-anything-inkstitch` y Ink/Stitch deben probarse conjuntamente sobre tu Ubuntu.

## Fallos esperables

- `Falta ejecutable`: instala el programa faltante o usa `--inkscape` / `--cli` con su ruta.
- `Ink/Stitch no está configurado`: instala el motor y fija `INKSTITCH_BINARY`.
- `PES vacío`: el SVG no contiene elementos que Ink/Stitch pueda digitalizar.
- `clases CSS`: convierte el estilo a atributos, o crea un SVG plano sin CSS complejos.
- `PES excede 60×60mm`: revisar `viewBox`, offset geométrico, compensaciones de bordado o transformaciones del motor.

## Siguiente iteración

Cuando nos compartas un EPS representativo y el resultado de ejecución, añadiremos clasificación por elementos, estrategias de puntada (relleno, contorno, satén cuando sea geométricamente viable), unión de áreas superpuestas y perfiles de densidad por tela.

**Referencias:** https://github.com/bobbymarko/cli-anything-inkstitch y https://inkstitch.org/docs/command-line/
