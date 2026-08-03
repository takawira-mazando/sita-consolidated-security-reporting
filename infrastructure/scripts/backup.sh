#!/bin/bash
set -euo pipefail

DB_NAME="sita"
DB_USER="sita"
BACKUP_DIR="/backups"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/sita_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

pg_dump -Fc -U "${DB_USER}" -d "${DB_NAME}" -f "${BACKUP_FILE}"

gpg --encrypt --recipient backup@sita.com "${BACKUP_FILE}"
rm "${BACKUP_FILE}"

find "${BACKUP_DIR}" -name "sita_*.dump.gpg" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup complete: ${BACKUP_FILE}.gpg"
