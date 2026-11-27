#!/usr/bin/env bash
# Self-check for install.sh with stub agents in a throwaway HOME: bash tests/test_install.sh
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/home"
cat > "$T/bin/claude" <<'STUB'
#!/bin/bash
echo "$*" >> "$HOME/claude.log"
case "$*" in
  "plugin list") cat "$HOME/plugins" 2>/dev/null || true;;
  "plugin marketplace list") cat "$HOME/markets" 2>/dev/null || true;;
  "plugin install "*) echo "$3" >> "$HOME/plugins";;
  "plugin marketplace add"*) echo research-kit >> "$HOME/markets";;
esac
STUB
printf '#!/bin/sh\n' > "$T/bin/codex"; chmod +x "$T/bin/"*
run() { env -i HOME="$T/home" PATH="$T/bin:/usr/bin:/bin" RESEARCH_KIT_REPO="file://$ROOT" bash "$ROOT/install.sh" "$@" >/dev/null 2>&1; }
LINK="$T/home/.agents/skills/research"

run; run  # install, then update
[ -f "$LINK/SKILL.md" ] || { echo "FAIL: skill not linked"; exit 1; }
grep -qx "plugin install research-kit@research-kit" "$T/home/claude.log" || { echo "FAIL: no install"; exit 1; }
grep -qx "plugin update research-kit@research-kit" "$T/home/claude.log" || { echo "FAIL: no update on rerun"; exit 1; }
run --uninstall
[ ! -e "$LINK" ] && [ ! -e "$T/home/.local/share/research-kit" ] || { echo "FAIL: uninstall left files"; exit 1; }
mkdir -p "$LINK"  # someone else's skill: refuse, clone nothing
! run || { echo "FAIL: overwrote an existing skill dir"; exit 1; }
[ ! -e "$T/home/.local/share/research-kit" ] || { echo "FAIL: cloned despite conflict"; exit 1; }
rm "$T/bin/"*
! run || { echo "FAIL: succeeded with no agent"; exit 1; }
echo ok
