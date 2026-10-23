#!/usr/bin/env bash
# Sauvegarde quotidienne PostgreSQL (format custom, compressé). Exemple cron : 0 2 * * * /chemin/backup.sh
set -euo pipefail
: "${DATABASE_URL:?DATABASE_URL manquante}"
DIR="${BACKUP_DIR:-./backups}"; mkdir -p "$DIR"
FILE="$DIR/djamil_hijab_$(date +%Y%m%d_%H%M%S).dump"
pg_dump --format=custom --no-owner "$DATABASE_URL" -f "$FILE"
echo "Sauvegarde : $FILE"
# Conserver 30 jours ; copier ensuite le fichier hors du serveur (S3/R2, autre machine)
find "$DIR" -name 'djamil_hijab_*.dump' -mtime +30 -delete
# Restauration : pg_restore --clean --no-owner -d "$DATABASE_URL" fichier.dump
