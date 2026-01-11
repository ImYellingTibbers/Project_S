#!/bin/bash
set -e

ROOT="/home/jcpix/projects/Project_S/Project_S_v1.2"
CONF="$ROOT/upload_channels.conf"

if [ ! -f "$CONF" ]; then
  echo "Missing upload_channels.conf"
  exit 1
fi

TMP_CRON=$(mktemp)

# Remove all existing uploader jobs
(crontab -l 2>/dev/null || true) | grep -v "queued_youtube_uploader.py" > "$TMP_CRON" || true

while IFS="|" read -r NAME TIMES; do
  [[ -z "$NAME" || "$NAME" =~ ^# ]] && continue

  CHANNEL_ROOT="$ROOT/$NAME"

  if [ ! -d "$CHANNEL_ROOT" ]; then
    echo "Channel path does not exist: $CHANNEL_ROOT"
    exit 1
  fi


  IFS="," read -ra TIME_LIST <<< "$TIMES"

  for T in "${TIME_LIST[@]}"; do
    if ! [[ "$T" =~ ^([01][0-9]|2[0-3]):[0-5][0-9]$ ]]; then
      echo "Invalid time '$T' for channel '$NAME'"
      exit 1
    fi

    HOUR="${T%%:*}"
    MIN="${T##*:}"

    echo "$MIN $HOUR * * * cd $CHANNEL_ROOT && python3 src/uploader/queued_youtube_uploader.py >> upload.log 2>&1" >> "$TMP_CRON"
  done
done < "$CONF"

crontab "$TMP_CRON"
rm "$TMP_CRON"

echo "Upload schedules applied successfully."
