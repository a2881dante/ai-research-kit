#!/usr/bin/env bash
# Copies the fixture research folder into the empty workspace and switches rumors off.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p research
cp -R "$here/../fixtures/lantern-tide" research/lantern-tide
perl -pi -e 's/^- Rumors: labeled/- Rumors: exclude/' research/lantern-tide/STATE.md
grep -q '^- Rumors: exclude' research/lantern-tide/STATE.md
