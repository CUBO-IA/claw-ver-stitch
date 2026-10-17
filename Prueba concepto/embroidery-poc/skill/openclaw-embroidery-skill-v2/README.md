# Skill v2 de OpenClaw: Telegram EPS → PNG + PES

Actualización sobre v1: **el agente envía primero `preview.png` y luego `design.pes`**, ambos desde el directorio `outputs` que genera el motor original. No se modifica `embroidery_poc.py` ni se recalcula la simulación.

## Instalación / actualización

Descomprime el ZIP, entra en su carpeta y ejecuta:

```bash
bash install.sh
openclaw skills info telegram-eps-to-pes
openclaw skills check
```

El instalador hace copia de la versión anterior, si existe, en `~/.openclaw/skills/telegram-eps-to-pes.backup-<fecha>` y actualiza la skill. Puedes deshacer la actualización restaurando esa carpeta.

## Prueba local

```bash
python3 ~/.openclaw/skills/telegram-eps-to-pes/scripts/process_eps.py --input '/ruta/real/logo.eps'
```

Salida JSON esperada en éxito:

```json
{
  "ok": true,
  "version": "2.0.0",
  "pes_path": "/home/felicito/.../outputs/logo-hash/design.pes",
  "preview_path": "/home/felicito/.../outputs/logo-hash/preview.png",
  "output_directory": "/home/felicito/.../outputs/logo-hash"
}
```

`pes_path` y `preview_path` son rutas absolutas reales, no URLs; el agente las adjunta mediante la herramienta `message` al mismo chat de Telegram. El puente comprueba que el PNG existe, no está vacío y tiene cabecera PNG válida. Si falta, da error sin afirmar que el trabajo está completo. Este cambio también funciona con trabajos cacheados.

## Prueba en Telegram

Adjunta `logo.eps` como **documento**, no como imagen, al bot autorizado. OpenClaw deberá responder con dos envíos: PNG visualizable en el chat y PES descargable. Si falla el segundo, informará del éxito parcial. El proceso sigue siendo un solo color y máximo 60 × 60 mm.

## Consideraciones

- El agente requiere `exec`, herramienta `message` con permisos para enviar medios y acceso de lectura a los archivos generados en el host. En Docker hay que montar las rutas.
- Para el envío, OpenClaw puede aplicar restricciones de rutas de archivos locales: revisa la configuración de medios del canal y no desactives controles de seguridad globales.
- El PNG es una simulación de puntadas, no garantía del resultado físico.
- Si tu `.venv` está en otro lugar, actualiza el parámetro `--python` o la configuración del puente.
