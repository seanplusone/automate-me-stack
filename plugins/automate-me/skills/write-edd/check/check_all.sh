#!/bin/sh
# Run every step 9 check on one EDD run.
# Usage: sh check/check_all.sh <input dir with map.txt, gaps.txt, pm-answers.md, optional layout.json> <run dir> <repo[,repo...]>
# The layout is <input dir>/layout.json when it exists, else rules/edd-sections.json.
# The run dir holds edd.md, delta.txt, arch.txt, current.txt, blast-*.txt and evidence/.
[ $# -ge 3 ] || { echo "usage: check_all.sh <input dir> <run dir> <repo>" >&2; exit 2; }
IN=$1 RUN=$2 REPO=$3
HERE=$(cd "$(dirname "$0")" && pwd)
RULES=$HERE/../rules/edd-sections.json
[ -f "$IN/layout.json" ] && RULES=$IN/layout.json
C="python3 $HERE/check_edd.py"
mkdir -p "$RUN/evidence"
{
  $C delta "$RUN/delta.txt" "$IN/map.txt" "$IN/gaps.txt" "$IN/pm-answers.md" "$RUN/arch.txt" "$RUN/current.txt" "$RUN"/blast-*.txt "$RUN"/evidence/*.md
  $C sections "$RUN/edd.md" "$RULES"
  $C coverage "$RUN/edd.md" "$IN/map.txt" "$IN/gaps.txt" "$IN/pm-answers.md" "$RULES" "$RUN"/blast-*.txt "$RUN/arch.txt" "$RUN/delta.txt" "$RUN"/evidence/*.md
  $C hazards "$RUN/edd.md" "$RULES"
  $C spikes "$RUN/edd.md" "$RUN/evidence" "$RULES"
  $C diagrams "$RUN/edd.md" "$RUN/delta.txt" "$RULES"
  $C names "$REPO" "$RUN/edd.md"
  $C writing "$RUN/edd.md"
  if command -v mmdc >/dev/null; then
    T=$(mktemp -d)
    awk -v d="$T" '/^```mermaid/{n++; f=d"/"n".mmd"; on=1; next} /^```/{on=0} on{print > f}' "$RUN/edd.md"
    for f in "$T"/*.mmd; do mmdc -q -i "$f" -o "$f.svg" >/dev/null 2>&1 && echo "PASS render: $(basename "$f")" || echo "FAIL render: $(basename "$f")"; done
  else
    echo "SKIP render: mmdc not installed (npm i -g @mermaid-js/mermaid-cli)"
  fi
} 2>&1 | tee "$RUN/checks.txt"
! grep -q '^FAIL\|Traceback' "$RUN/checks.txt"
