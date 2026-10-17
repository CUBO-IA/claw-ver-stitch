#!/usr/bin/env python3
"""EPS -> SVG -> cli-anything-inkstitch -> PES. POC, one monochrome thread.

Idempotence: inputs + settings yield a stable job folder; re-runs reuse a
validated, previously completed job. Does not modify the incoming EPS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

VERSION = "0.1.0"
MAX_MM = 60.0  # 6 cm = 60 mm
NS = "{http://www.w3.org/2000/svg}"
DRAWABLE = {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line"}
IGNORED_CONTAINERS = {"defs", "clipPath", "mask", "pattern", "marker", "symbol"}


class POCError(Exception):
    pass


def run(argv: list[str], timeout: int = 180) -> str:
    try:
        p = subprocess.run(argv, text=True, encoding="utf-8", errors="replace",
                           capture_output=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise POCError(f"Comando no encontrado: {argv[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise POCError(f"Tiempo de espera agotado: {' '.join(argv[:3])}") from exc
    if p.returncode:
        raise POCError(f"Falló comando (exit={p.returncode}): {' '.join(argv)}\n"
                       f"STDOUT: {p.stdout[-1500:]}\nSTDERR: {p.stderr[-3500:]}")
    return p.stdout


def mm_number(value: str) -> float:
    m = re.fullmatch(r"\s*([+]?(?:\d+(?:\.\d*)?|\.\d+))(mm|cm|in|pt|px|pc|Q)?\s*", value)
    if not m:
        raise POCError(f"Unidad/dimensión SVG no compatible: {value!r}")
    number, unit = float(m.group(1)), m.group(2) or "px"
    factors = {"mm": 1, "cm": 10, "in": 25.4, "pt": 25.4 / 72,
               "px": 25.4 / 96, "pc": 25.4 / 6, "Q": 0.25}
    return number * factors[unit]


def normalize_svg(source: Path, target: Path, color: str, margin_mm: float) -> dict:
    """Keep SVG viewBox, set physical page to <=60mm, recolor drawable items.

    Does NOT reduce physical complexity: strokes become black, fills become black,
    and multi-color overlaps remain separate objects. This is deliberate.
    """
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise POCError("El color debe ser hexadecimal #RRGGBB")
    if not 0 <= margin_mm < 30:
        raise POCError("margin-mm debe estar entre 0 y menos de 30")
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree = ET.parse(source)
    root = tree.getroot()
    if root.tag != f"{NS}svg":
        raise POCError("El conversor no produjo un SVG válido")
    raw_box = root.get("viewBox")
    if raw_box:
        vals = [float(v) for v in re.split(r"[\s,]+", raw_box.strip())]
        if len(vals) != 4:
            raise POCError("viewBox SVG incorrecto")
        x, y, vw, vh = vals
    else:
        vw = mm_number(root.attrib["width"])
        vh = mm_number(root.attrib["height"])
        x = y = 0
    if not (0 < vw < 1e9 and 0 < vh < 1e9):
        raise POCError("viewBox vacío o demasiado grande")
    usable = MAX_MM - 2 * margin_mm
    scale = min(usable / vw, usable / vh)
    actual_w, actual_h = vw * scale, vh * scale
    # Page matches art aspect ratio. svg viewBox units may be px or mm: preserve
    # viewBox to let the renderer map units without changing coordinates.
    root.set("width", f"{actual_w:.6f}mm")
    root.set("height", f"{actual_h:.6f}mm")
    root.set("viewBox", f"{x:g} {y:g} {vw:g} {vh:g}")
    root.set("preserveAspectRatio", "xMidYMid meet")

    count = 0
    def visit(elem, excluded=False):
        nonlocal count
        tag = elem.tag.split("}")[-1]
        if tag in IGNORED_CONTAINERS or excluded:
            return
        if tag in {"image", "foreignObject", "text", "use"}:
            raise POCError(f"SVG contiene elemento no admitido ({tag}). Convierte texto y clones a trazados; elimina ráster.")
        if tag in DRAWABLE:
            style = dict(item.strip().split(":", 1) for item in elem.get("style", "").split(";") if ":" in item)
            # CSS inline is overwritten; external stylesheets/classes aren't handled
            # safely, hence reject them rather than silently converting colors.
            if elem.get("class"):
                raise POCError("SVG contiene clases CSS: convierte estilos a atributos antes de procesar")
            fill = style.get("fill", elem.get("fill", "black")).strip().lower()
            stroke = style.get("stroke", elem.get("stroke", "none")).strip().lower()
            if any(v.startswith("url(") for v in (fill, stroke)):
                raise POCError("SVG contiene gradientes/patrones no admitidos")
            # Fill and stroke semantics remain unchanged (none stays none).
            style["fill"] = "none" if fill == "none" else color
            style["stroke"] = "none" if stroke == "none" else color
            if style.get("display", "").strip() == "none":
                return
            # strip semi-transparency: thread cannot encode alpha.
            for k in ("opacity", "fill-opacity", "stroke-opacity", "filter"):
                style.pop(k, None)
                elem.attrib.pop(k, None)
            elem.set("style", ";".join(f"{k}:{v}" for k, v in style.items()))
            elem.set("fill", style["fill"])
            elem.set("stroke", style["stroke"])
            count += 1
        for child in elem:
            visit(child)
    visit(root)
    if count == 0:
        raise POCError("SVG sin elementos dibujables")
    target.parent.mkdir(parents=True, exist_ok=True)
    tree.write(target, encoding="utf-8", xml_declaration=True)
    return {"page_width_mm": round(actual_w, 3), "page_height_mm": round(actual_h, 3),
            "drawable_count": count, "single_color": color, "max_hoop_mm": [60, 60],
            "warning": "Dimensiones basadas en página/viewBox, no en caja exacta del dibujo."}


def verify_pes(path: Path) -> dict:
    try:
        from pyembroidery import read_pes
        p = read_pes(str(path))
    except Exception as exc:
        raise POCError(f"PES no pudo abrirse con pyembroidery: {exc}") from exc
    if p is None or not p.stitches:
        raise POCError("PES vacío: no contiene puntadas")
    bounds = p.bounds()  # PES coordinates in 0.1 mm (embroidery units)
    if bounds is None:
        raise POCError("PES sin límites de puntadas")
    x0, y0, x1, y1 = bounds
    w, h = (x1 - x0) / 10, (y1 - y0) / 10
    if w > 60.01 or h > 60.01:
        raise POCError(f"PES excede 60×60mm: {w:.2f}×{h:.2f}mm")
    # Number of distinct physical colors, not number of PES color table entries.
    colors = {getattr(t, 'hex_color', lambda: None)() for t in p.threadlist}
    if len(colors - {None}) > 1:
        raise POCError(f"PES declara varios colores de hilo: {colors}")
    return {"stitch_records": len(p.stitches), "stitch_bounds_mm": [round(w, 2), round(h, 2)],
            "thread_entries": len(p.threadlist), "distinct_thread_colors": len(colors - {None})}


def execute(args):
    eps = args.eps.expanduser().resolve()
    if not eps.is_file() or eps.suffix.lower() != ".eps":
        raise POCError("Se necesita un archivo .eps existente")
    if eps.stat().st_size > args.max_input_mb * 1024 * 1024:
        raise POCError("Archivo EPS supera el tamaño permitido")
    # We do not render PostScript ourselves: Ghostscript/Inkscape must be
    # provisioned on a sandboxed worker for untrusted input.
    for binary in (args.inkscape, args.cli):
        if not shutil.which(binary) and not Path(binary).is_file():
            raise POCError(f"Falta ejecutable: {binary}")
    if not args.skip_engine_check:
        if not (shutil.which("inkstitch") or os.environ.get("INKSTITCH_BINARY")):
            raise POCError("Ink/Stitch no está configurado. Instala el binario y define INKSTITCH_BINARY (o pon inkstitch en PATH).")
    out = args.output.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    checksum = hashlib.sha256(eps.read_bytes() + json.dumps({
        "version": VERSION, "color": args.color, "margin_mm": args.margin_mm},
        sort_keys=True).encode()).hexdigest()[:16]
    destination = out / f"{eps.stem}-{checksum}"
    manifest = destination / "result.json"
    if manifest.exists() and not args.force:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if (destination / "design.pes").is_file() and (destination / "design.svg").is_file():
            data["cached"] = True
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return
    with tempfile.TemporaryDirectory(prefix="embroidery-", dir=out) as stage:
        work = Path(stage)
        converted = work / "converted.svg"
        normalized = work / "design.svg"
        project = work / "project.json"
        pes = work / "design.pes"
        # Keep Ghostscript and Inkscape sandboxed; SVG conversion should expand text.
        run([args.inkscape, str(eps), "--export-text-to-path", "--export-plain-svg",
             f"--export-filename={converted}"], timeout=args.timeout)
        if not converted.is_file():
            raise POCError("Inkscape no produjo converted.svg")
        stats = normalize_svg(converted, normalized, args.color, args.margin_mm)
        base = [args.cli]
        run(base + ["document", "open", "--project", str(project), "--svg", str(normalized)], args.timeout)
        run(base + ["document", "prep", "--project", str(project), "--illustrator-rings", "detect"], args.timeout)
        run(base + ["document", "set-hoop", "--project", str(project), "--width-mm", "60", "--height-mm", "60"], args.timeout)
        run(base + ["document", "set-machine-target", "--project", str(project), "--format", "pes"], args.timeout)
        # No universal satin conversion: Ink/Stitch determines fill and stroke
        # from prepared geometry. This is an explicit baseline, not commercial QA.
        run(base + ["document", "save", "--project", str(project)], args.timeout)
        if args.strict:
            run(base + ["validate", "run", "--project", str(project), "--strict"], args.timeout)
        else:
            run(base + ["validate", "static", "--project", str(project)], args.timeout)
        run(base + ["export", "file", "--project", str(project), "--format", "pes",
                    "--out", str(pes)], args.timeout)
        if not pes.is_file() or pes.stat().st_size == 0:
            raise POCError("La exportación no produjo un PES válido")
        qa = verify_pes(pes)
        # Final preview represents actual stitches, not the EPS artwork.
        preview = work / "preview.png"
        run(base + ["preview", "stitch-sim", "--dst", str(pes), "--out", str(preview),
                    "--thread-color", args.color], args.timeout)
        if not preview.is_file():
            raise POCError("No se produjo preview.png")
        data = {"status": "completed", "version": VERSION, "cached": False,
                "job_id": checksum, "source_name": eps.name, "output_directory": str(destination),
                "files": ["design.svg", "design.pes", "preview.png", "project.json"],
                "svg": stats, "pes": qa,
                "limitations": ["Monocromo sin deduplicar objetos superpuestos",
                                "La validación física de costura todavía es obligatoria",
                                "Escala por viewBox, que puede incluir margen del EPS"]}
        (work / "result.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        converted.unlink(missing_ok=True)
        # CLI may produce undo history and other intermediates; preserve them.
        if destination.exists():
            if not args.force:
                raise POCError(f"Salida incompleta previa en {destination}; usa --force")
            shutil.rmtree(destination)
        os.replace(work, destination)
        print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description="Prueba de concepto EPS -> PES, monocromo, 60 x 60 mm")
    p.add_argument("eps", type=Path)
    p.add_argument("--output", type=Path, default=Path("./outputs"))
    p.add_argument("--color", default="#000000", help="Color único #RRGGBB")
    p.add_argument("--margin-mm", type=float, default=2.0,
                   help="Reserva óptica; página máxima por defecto 56x56mm")
    p.add_argument("--inkscape", default="inkscape")
    p.add_argument("--cli", default="cli-anything-inkstitch")
    p.add_argument("--timeout", type=int, default=240)
    p.add_argument("--max-input-mb", type=int, default=20)
    p.add_argument("--strict", action="store_true", help="Abortar con errores de validación de Ink/Stitch")
    p.add_argument("--force", action="store_true", help="Recrear un trabajo anterior")
    p.add_argument("--skip-engine-check", action="store_true", help="Solo depuración: omitir verificación del binario")
    args = p.parse_args()
    try:
        execute(args)
    except (POCError, ET.ParseError, ValueError, OSError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
