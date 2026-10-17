#!/usr/bin/env bash
set -euo pipefail
SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/telegram-eps-to-pes"
TARGET="${HOME}/.openclaw/skills/telegram-eps-to-pes"
mkdir -p "$(dirname "$TARGET")"
if [[ -e "$TARGET" ]]; then
  BACKUP="${TARGET}.backup-$(date +%Y%m%d-%H%M%S)-$$"
  mv -- "$TARGET" "$BACKUP"
  echo "Copia de seguridad: $BACKUP"
fi
cp -R -- "$SOURCE" "$TARGET"
chmod +x "$TARGET/scripts/process_eps.py"
echo "Skill v2 instalada: $TARGET"
echo "Comprobar: openclaw skills info telegram-eps-to-pes"
