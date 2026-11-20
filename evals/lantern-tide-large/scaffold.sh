#!/usr/bin/env bash
# Copies the fixture research folder into the empty workspace.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p research
cp -R "$here/../fixtures/lantern-tide-large" research/lantern-tide
