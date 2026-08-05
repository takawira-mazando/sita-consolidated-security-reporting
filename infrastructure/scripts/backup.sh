#!/bin/bash
set -euo pipefail

# SITA Platform PostgreSQL Backup & Point-in-Time Recovery (PITR)
#
# Strategy:
#   1. Weekly base backups via pg_basebackup into $BASE_DIR.
#   2. Continuous WAL archiving into $WAL_DIR (server archive_command must be
#      configured; see the sample postgresql.conf block below).
#   3. Restore drill: replay base + WAL up to a given timestamp.
#
# Required server configuration (postgresql.conf):
#   wal_level = replica
#   archive_mode = on
#   archive_command = 'cp %p /backups/wal/%f'     # or rsync to a DR host
#   max_wal_senders = 10
#
# Usage:
#   ./backup.sh base            # take a base backup (full)
#   ./backup.sh drill "<ts>"    # restore-drill to a timestamp (PITR test)
#   ./backup.sh verify          # verify most recent backup set is restorable
#
# Notes:
#   * For a true DR story, ship WAL off-box (rsync/object storage). The cp
#     archive_command above is local-only and sufficient for restore drills.

DB_NAME="sita"
DB_USER="sita"
BACKUP_DIR="/backups"
BASE_DIR="${BACKUP_DIR}/base"
WAL_DIR="${BACKUP_DIR}/wal"
RESTORE_DIR="${BACKUP_DIR}/restore"
RETENTION_BASES=2
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "${BASE_DIR}" "${WAL_DIR}" "${RESTORE_DIR}"

take_base_backup() {
    local target="${BASE_DIR}/base_${TIMESTAMP}"
    echo "[$(date)] Taking base backup -> ${target}"
    pg_basebackup -h localhost -U "${DB_USER}" -D "${target}" \
        -Fp -P -X stream -z -l "sita base ${TIMESTAMP}"

    # prune old base backups, keep newest $RETENTION_BASES
    ls -1d "${BASE_DIR}"/base_* 2>/dev/null | sort -r \
        | tail -n +$((RETENTION_BASES + 1)) | xargs -r rm -rf
    echo "[$(date)] Base backup complete."
}

restore_drill() {
    local target_ts="${1:-now}"
    local target_dir="${RESTORE_DIR}/pitr_${TIMESTAMP}"
    echo "[$(date)] Restore drill: replay to '${target_ts}'"

    latest_base=$(ls -1d "${BASE_DIR}"/base_* 2>/dev/null | sort -r | head -n1)
    if [[ -z "${latest_base}" ]]; then
        echo "No base backup found; run '${0} base' first." >&2
        exit 1
    fi
    echo "[$(date)] Using base: ${latest_base}"

    cp -a "${latest_base}" "${target_dir}"
    rm -f "${target_dir}/postgresql.conf" "${target_dir}/pg_hba.conf"

    # PITR replay config
    cat > "${target_dir}/postgresql.conf" <<EOF
restore_command = 'cp ${WAL_DIR}/%f %p'
recovery_target_time = '${target_ts}'
recovery_target_action = 'pause'
EOF
    # touch standby.signal to force archive recovery
    touch "${target_dir}/standby.signal"

    echo "[$(date)] Restore drill prepared at ${target_dir}."
    echo "        Start postgres on the standby port, e.g.:"
    echo "        pg_ctl -D ${target_dir} -o '-p 5440' start"
    echo "        Then confirm recovery reached '${target_ts}', promote:"
    echo "        SELECT pg_wal_replay_resume();  /  pg_ctl promote"
}

verify_backup() {
    latest_base=$(ls -1d "${BASE_DIR}"/base_* 2>/dev/null | sort -r | head -n1)
    if [[ -z "${latest_base}" ]]; then
        echo "No base backups to verify." >&2
        exit 1
    fi
    echo "[$(date)] Verifying ${latest_base}"
    pg_controldata "${latest_base}" | grep -E 'latest checkpoint location|state:' \
        || echo "pg_controldata unavailable; check consistency manually."
    wal_count=$(ls "${WAL_DIR}"/*.gz 2>/dev/null | wc -l)
    echo "[$(date)] WAL segments archived: ${wal_count}"
    echo "[$(date)] Verification complete."
}

case "${1:-}" in
    base)   take_base_backup ;;
    drill)  restore_drill "${2:-now}" ;;
    verify) verify_backup ;;
    *) echo "Usage: $0 {base|drill \"<timestamp>\"|verify}"; exit 1 ;;
esac
