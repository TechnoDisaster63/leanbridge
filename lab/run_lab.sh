#!/usr/bin/env bash
# One-command wrapper for the documented lab steps A-D. UNREVIEWED until an independent review
# clears this exact version AND the owner says to run it. It adds no new network actions: it only
# chains the existing, already-gated commands of cake_netns_lab.py and keeps its refusals.
#
#   sudo bash lab/run_lab.sh --i-confirm-disposable-vm ARM [ARM ...]      (from the repo root)
#   bash lab/run_lab.sh --plan ARM [ARM ...]                              (no root, prints only)
#
# Not automated, still yours: fresh VM snapshot, all VM network adapters detached, no shared
# folders/clipboard, iperf3 installed beforehand. The flag below is your statement, not verified.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DEST=/opt/leanbridge-lab
VALID="none static heuristic leanbridge recovery recovery_cap10"

# ---- helpers (also sourced by tests with LB_SOURCE_ONLY=1) ----
extract_rid() {  # last anchored "run id: xxxxxx" line of the log; digits/lowercase only, else empty
  local r; r="$(grep -E '^run id: [a-z0-9]{6}( |$)' "$1" 2>/dev/null | tail -1 | awk '{print $3}')"
  case "$r" in [a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9]) printf '%s' "$r";; esac
}
CHILD=""; LOG=""
stop_child() {  # ask the lab to stop and WAIT for it, so cleanup never races network setup
  [ -n "$CHILD" ] || return 0
  kill -INT "$CHILD" 2>/dev/null
  local i=0; while kill -0 "$CHILD" 2>/dev/null && [ $i -lt "${LB_STOP_WAIT:-90}" ]; do sleep 1; i=$((i+1)); done
  kill -0 "$CHILD" 2>/dev/null && { kill -TERM "$CHILD" 2>/dev/null; sleep 2; }
  kill -0 "$CHILD" 2>/dev/null && { kill -KILL "$CHILD" 2>/dev/null; }
  wait "$CHILD" 2>/dev/null; CHILD=""
}
cleanup_from_log() {  # run explicit cleanup unless the log already shows it verified
  local rid; rid="$(extract_rid "$1")"
  if grep -q 'cleanup verified: True' "$1" 2>/dev/null; then return 0; fi
  if [ -n "$rid" ]; then echo "cleaning up run $rid"; $LAB --cleanup --run-id "$rid"; return $?; fi
  echo "no run id printed yet: nothing to clean up"; return 0
}
on_int() { echo; echo "interrupted"; stop_child; [ -n "$LOG" ] && cleanup_from_log "$LOG"; echo "results so far: $OUT"; exit 130; }
run_arm() {  # sets ARM_RC; output goes to a file (no pipeline, so the lab's own exit status is kept)
  LOG="$OUT/$1.txt"; : > "$LOG"
  $LAB --execute --i-confirm-disposable-vm --code-dir "$DEST" --arm "$1" > "$LOG" 2>&1 &
  CHILD=$!
  tail -n +1 -f "$LOG" --pid="$CHILD" 2>/dev/null &
  local t=$!
  wait "$CHILD"; ARM_RC=$?; CHILD=""
  wait "$t" 2>/dev/null
  return 0
}
[ "${LB_SOURCE_ONLY:-0}" = 1 ] && return 0 2>/dev/null
confirm=0; plan=0
while [ $# -gt 0 ]; do
  case "$1" in
    --i-confirm-disposable-vm) confirm=1; shift;;
    --plan) plan=1; shift;;
    --*) echo "unknown option $1" >&2; exit 2;;
    *) break;;
  esac
done
[ $# -ge 1 ] || { echo "usage: run_lab.sh [--plan | --i-confirm-disposable-vm] ARM [ARM ...]  (arms: $VALID)" >&2; exit 2; }
for a in "$@"; do
  case " $VALID " in *" $a "*) ;; *) echo "unknown arm: $a (valid: $VALID)" >&2; exit 2;; esac
done
[ -f "$ROOT/lab/cake_netns_lab.py" ] && [ -d "$ROOT/src" ] || { echo "run from a full repo checkout (needs lab/ and src/)" >&2; exit 2; }
if [ "$plan" = 1 ]; then
  for a in "$@"; do python3 -I "$ROOT/lab/cake_netns_lab.py" --plan --arm "$a" || exit 1; done
  echo "plan only: nothing was changed"; exit 0
fi
[ "$confirm" = 1 ] || { echo "refusing: add --i-confirm-disposable-vm (your statement that this is a snapshotted, network-detached VM)" >&2; exit 2; }
[ "$(id -u)" = 0 ] || { echo "refusing: run with sudo" >&2; exit 2; }
echo "== source fingerprint (send this back with results) =="
( cd "$ROOT" && sha256sum lab/cake_netns_lab.py && find src -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum )
# A: root-owned immutable copy, rebuilt fresh each time so stale files cannot linger
rm -rf "$DEST" && mkdir -p "$DEST" || exit 1
cp -r "$ROOT/lab/cake_netns_lab.py" "$ROOT/src" "$DEST/" || exit 1
find "$DEST" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
chown -R root:root "$DEST" && chmod -R go-w "$DEST" || exit 1
LAB="python3 -I $DEST/cake_netns_lab.py"
# B: preflight (creates and deletes one throwaway namespace); stop on any problem
$LAB --check --i-confirm-disposable-vm || { echo "preflight failed: nothing was run" >&2; exit 1; }
# C: arms one at a time. D: interrupt handler stops the lab, waits, then cleans up from the log.
OUT="$(mktemp -d /tmp/leanbridge-lab-results.XXXXXX)"
trap on_int INT TERM HUP
rc=0
for a in "$@"; do
  echo "== arm: $a =="
  run_arm "$a"
  if [ "$ARM_RC" != 0 ]; then echo "lab exited with status $ARM_RC for $a" >&2; rc=1; fi
  if ! grep -q 'cleanup verified: True' "$LOG"; then
    echo "cleanup not confirmed for $a; trying explicit cleanup" >&2
    cleanup_from_log "$LOG" || { echo "cleanup failed: run $LAB --cleanup --run-id $(extract_rid "$LOG")" >&2; rc=1; break; }
  fi
  [ "$rc" = 0 ] || break
done
echo "== all output saved in $OUT (send the files back) =="; exit $rc
