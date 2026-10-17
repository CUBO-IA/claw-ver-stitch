#!/usr/bin/env python3
"""Puente mínimo OpenClaw -> POC existente; salida JSON, sin envío directo a Telegram."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path('/home/felicito/cubo_ai/openclaw/claw-ver-stitch/Prueba concepto/embroidery-poc')
MAX_BYTES = 20 * 1024 * 1024


def error(message, code=2):
    print(json.dumps({'ok': False, 'error': message}, ensure_ascii=False))
    return code


def header_ok(path):
    with path.open('rb') as f:
        start = f.read(512)
    # EPSF identification; EPS can be binary preview wrapper (C5 D0 D3 C6)
    if start.startswith(b'\xc5\xd0\xd3\xc6'):
        return True
    return start.startswith(b'%!PS-Adobe-') and b'EPSF-' in start[:120]


def main(argv=None):
    ap = argparse.ArgumentParser(description='Ejecuta POC de bordado EPS -> PES de forma controlada')
    ap.add_argument('--input', required=True, help='Ruta absoluta del EPS descargado por OpenClaw')
    ap.add_argument('--output', default=str(PROJECT / 'outputs'))
    ap.add_argument('--python', default=str(PROJECT / '.venv' / 'bin' / 'python'))
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args(argv)

    eps = Path(args.input).expanduser().resolve()
    if not eps.is_file():
        return error('No existe el archivo recibido o no es accesible')
    if eps.suffix.lower() != '.eps':
        return error('Extensión no admitida: se requiere .eps')
    if not 0 < eps.stat().st_size <= MAX_BYTES:
        return error('EPS vacío o superior a 20 MiB')
    if not header_ok(eps):
        return error('El contenido no presenta una cabecera EPS reconocible')
    script = PROJECT / 'embroidery_poc.py'
    if not script.is_file():
        return error(f'No existe el motor: {script}')
    python = Path(args.python).expanduser().resolve()
    if not python.is_file():
        return error(f'Python del entorno virtual no encontrado: {python}')

    output = Path(args.output).expanduser().resolve()
    # Never honor arbitrary output dirs in Telegram instructions: fixed to project.
    if output != (PROJECT / 'outputs').resolve():
        return error('Directorio de salida distinto del directorio autorizado')
    output.mkdir(parents=True, exist_ok=True)
    command = [str(python), str(script), str(eps), '--output', str(output),
               '--color', '#000000', '--margin-mm', '2', '--max-input-mb', '20']
    if args.force:
        command.append('--force')
    try:
        proc = subprocess.run(command, cwd=PROJECT, capture_output=True,
                              text=True, timeout=900, check=False)
    except subprocess.TimeoutExpired:
        return error('El motor excedió el tiempo límite de 15 minutos', 3)
    except OSError as exc:
        return error(f'No fue posible iniciar el motor: {exc}', 3)
    if proc.returncode:
        return error('El motor EPS→PES falló: ' + (proc.stderr or proc.stdout)[-2500:], 3)
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return error('El motor no devolvió JSON válido: ' + proc.stdout[-1000:], 3)
    if result.get('status') != 'completed':
        return error('El motor no confirmó el estado completed', 3)
    target = Path(result.get('output_directory', '')).resolve()
    # Only accept a direct child of outputs, no path traversal / outside dirs.
    if target.parent != output or not target.is_dir():
        return error('El motor devolvió un directorio de resultados no permitido', 3)
    pes = target / 'design.pes'
    if not pes.is_file() or pes.stat().st_size == 0:
        return error('El motor no produjo design.pes', 3)
    manifest = target / 'result.json'
    if not manifest.is_file():
        return error('El motor no produjo result.json', 3)
    preview = target / 'preview.png'
    # PNG es requerido en v2: evitar anunciar un resultado sin su previsualización.
    if not preview.is_file() or preview.stat().st_size == 0:
        return error('El PES existe, pero falta preview.png o está vacío', 3)
    with preview.open('rb') as f:
        if f.read(8) != b'\x89PNG\r\n\x1a\n':
            return error('preview.png no tiene una cabecera PNG válida', 3)
    payload = {'ok': True, 'version': '2.0.0', 'pes_path': str(pes), 'output_directory': str(target),
               'preview_path': str(preview),
               'job_id': result.get('job_id'), 'cached': result.get('cached', False),
               'dimensions_mm': result.get('pes', {}).get('stitch_bounds_mm'),
               'stitches': result.get('pes', {}).get('stitch_records')}
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
