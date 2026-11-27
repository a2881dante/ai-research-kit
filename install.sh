#!/usr/bin/env bash
# Install or update research-kit for the agents found on this machine.
#
#   curl -fsSL https://raw.githubusercontent.com/a2881dante/ai-research-kit/main/install.sh | bash
#   bash install.sh --uninstall
#
# Claude Code: installs the plugin from this repo's marketplace.
# Codex, Gemini CLI: clones the repo to ~/.local/share/research-kit and links the skill into
# ~/.agents/skills/research, which both read. Running it again updates everything.
set -euo pipefail

REPO=${RESEARCH_KIT_REPO:-https://github.com/a2881dante/ai-research-kit.git}
DIR=${RESEARCH_KIT_DIR:-$HOME/.local/share/research-kit}
LINK=$HOME/.agents/skills/research
PLUGIN=research-kit@research-kit

have() { command -v "$1" >/dev/null 2>&1; }
lists() { [[ "$(claude plugin $1 list 2>/dev/null)" == *"$2"* ]]; }  # no grep -q: SIGPIPE + pipefail

if [ "${1:-}" = "--uninstall" ]; then
  if have claude && lists "" "$PLUGIN"; then
    claude plugin uninstall "$PLUGIN"
    claude plugin marketplace remove research-kit || true
  fi
  if [ -L "$LINK" ] && [ "$(readlink "$LINK")" = "$DIR/skills/research" ]; then
    rm "$LINK" && echo "Removed $LINK"
  fi
  if [ -f "$DIR/skills/research/SKILL.md" ]; then  # only a clone made by this script
    rm -rf "$DIR" && echo "Removed $DIR"
  fi
  echo "Research folders (./research/) are yours and were not touched."
  exit 0
fi

have python3 && python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' \
  || { echo "research-kit needs python3 3.9 or newer." >&2; exit 1; }
have pdftotext || python3 -c 'import pypdf' 2>/dev/null \
  || echo "Note: to read PDFs, install poppler (brew install poppler / apt install poppler-utils) or pypdf."

done_any=
if have claude; then
  if lists marketplace research-kit; then
    claude plugin marketplace update research-kit
  else
    claude plugin marketplace add a2881dante/ai-research-kit
  fi
  if lists "" "$PLUGIN"; then
    claude plugin update "$PLUGIN"
  else
    claude plugin install "$PLUGIN"
  fi
  echo "Claude Code: plugin $PLUGIN installed (restart Claude Code to load it)."
  done_any=1
fi

if have codex || have gemini; then
  have git || { echo "git is needed to install the skill for Codex/Gemini." >&2; exit 1; }
  if [ -e "$LINK" ] && [ "$(readlink "$LINK" || true)" != "$DIR/skills/research" ]; then
    echo "$LINK already exists and isn't this install; leaving it alone." >&2
    exit 1
  fi
  if [ -d "$DIR/.git" ]; then
    git -C "$DIR" pull --ff-only --quiet
  else
    git clone --quiet --depth 1 "$REPO" "$DIR"
  fi
  mkdir -p "$(dirname "$LINK")"
  ln -sfn "$DIR/skills/research" "$LINK"
  echo "Codex/Gemini: skill linked at $LINK -> $DIR/skills/research"
  done_any=1
fi

if [ -z "$done_any" ]; then
  echo "No supported agent found (claude, codex or gemini on PATH)." >&2
  exit 1
fi
echo "Done. Ask your agent to research something, e.g. \"research the history of X for an essay\"."
