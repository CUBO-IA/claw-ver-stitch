# claw-ver-stitch

Proyecto de digitalización de bordado máquina con [Ink/Stitch](https://inkstitch.org/).

Contiene un CLI stateful para manipular SVGs con atributos `inkstitch:*` y delegar la generación de puntadas, preview y exportación a formatos de máquina (DST, PES, JEF, VP3, EXP) al binario de Ink/Stitch.

## Estructura

```
claw-ver-stitch/
├── vendor/
│   └── cli-anything-inkstitch/   # CLI principal (Python, Click, lxml, pyembroidery)
│       ├── src/cli_anything_inkstitch/   # Código fuente del CLI
│       │   ├── commands/          # Grupos de comandos: document, element, params, tools, export, font, artifact
│       │   ├── artifact/          # Loop de corrección con editor en navegador
│       │   ├── embroidery/        # Lógica pura: I/O de archivos de bordado + análisis
│       │   ├── font_format/       # Formato de directorio de fuentes Ink/Stitch
│       │   ├── svg/               # Helpers lxml (namespace, atributos, geometría)
│       │   └── schema/            # Extracción y caché de esquemas INX/params
│       ├── tools/                 # Scripts Python: rde_to_inkstitch, rde_regress, rde_decode, svg_scale
│       ├── skills/                # Skills de agente: cli-anything-inkstitch, embroidery-digitization, chroma-rde-import
│       ├── docs/                  # Especificación técnica y auditoría de cobertura
│       └── tests/                 # Suite de pruebas (pytest)
├── Prueba concepto/
│   ├── embroidery-poc/            # POC: outputs de diseños (SVG, PES, preview), scripts y skills
│   └── embroidery-poc-phase1.zip  # Empaquetado fase 1
├── LICENSE                        # Apache-2.0
└── .venv/                         # Entorno virtual Python local
```

## Requisitos

- Python 3.10+
- [Ink/Stitch](https://inkstitch.org/docs/install/) instalado y en `PATH` (o definir `INKSTITCH_BINARY`)

## Instalación

```bash
cd vendor/cli-anything-inkstitch
pip install -e '.[dev]'
```

## Uso rápido

```bash
# Abrir un SVG y crear proyecto
cli-anything-inkstitch document open --project /tmp/logo.inkstitch-cli.json --svg /tmp/logo.svg

# Inspeccionar elementos
cli-anything-inkstitch --json element list --project /tmp/logo.inkstitch-cli.json --refresh

# Asignar tipo de puntada y parámetros
cli-anything-inkstitch params set --project /tmp/logo.inkstitch-cli.json --id logo_outline \
    --stitch-type satin_column --pull-compensation-mm 0.4 --zigzag-spacing-mm 0.35

# Validar y exportar
cli-anything-inkstitch --json validate run --project /tmp/logo.inkstitch-cli.json --strict
cli-anything-inkstitch export file --project /tmp/logo.inkstitch-cli.json --format dst --out /tmp/logo.dst

# Preview stitch-sim (post-export, antes de coser)
cli-anything-inkstitch preview stitch-sim --dst /tmp/logo.dst --out /tmp/logo-sim.png
```

## Documentación

- **CLI completo:** `vendor/cli-anything-inkstitch/skills/cli-anything-inkstitch/SKILL.md`
- **Sabiduría de digitalización:** `vendor/cli-anything-inkstitch/skills/embroidery-digitization/SKILL.md`
- **Conversión Chroma RDE:** `vendor/cli-anything-inkstitch/skills/chroma-rde-import/SKILL.md`
- **Especificación técnica:** `vendor/cli-anything-inkstitch/SPEC.md`
- **Namespace Ink/Stitch:** https://inkstitch.org/namespace/

## Licencia

Apache-2.0. Ver [LICENSE](LICENSE).
