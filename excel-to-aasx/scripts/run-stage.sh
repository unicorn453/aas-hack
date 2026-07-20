#!/usr/bin/env bash
set -u

if [ "$#" -lt 3 ]; then
  echo "usage: scripts/run-stage.sh STAGE_NAME OUTPUT_ROOT COMMAND [ARG ...]" >&2
  exit 2
fi

stage_name="$1"
output_root="$2"
shift 2

log_dir="${output_root}/logs"
mkdir -p "$log_dir"

timestamp="$(date '+%Y%m%d_%H%M%S_%Z')"
log_file="${log_dir}/${timestamp}_${stage_name}.log"
latest_file="${log_dir}/${stage_name}.latest.log"

{
  printf 'stage: %s\n' "$stage_name"
  printf 'output_root: %s\n' "$output_root"
  printf 'started_at: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
  printf 'cwd: %s\n' "$PWD"
  printf 'cmd:'
  printf ' %q' "$@"
  printf '\n\n'
} > "$log_file"

printf '\033[36m==> %s\033[0m\n' "$stage_name" | tee -a "$log_file"

set -o pipefail
"$@" > >(tee -a "$log_file") 2> >(tee -a "$log_file" >&2)
status=$?
set +o pipefail

{
  printf '\nexit_code: %s\n' "$status"
  printf 'finished_at: %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
} >> "$log_file"

cp "$log_file" "$latest_file"

if [ "$status" -ne 0 ]; then
  printf '\033[31mFAILED %s; see %s\033[0m\n' "$stage_name" "$log_file" >&2
else
  printf '\033[32mcompleted %s; log: %s\033[0m\n' "$stage_name" "$log_file"
fi

exit "$status"
