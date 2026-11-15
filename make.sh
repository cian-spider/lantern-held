#!/bin/sh
# Rebuild the piece from source, then verify the rebuild is byte-identical to
# the submitted export. This is the regression check the brief asks for.
#
#   ./make.sh            rebuild lantern-held.wav + .mp3 + .mid in this folder
#   ./make.sh --verify   rebuild into a temp dir and compare sha256 to the
#                        submitted exports, printing PASS/FAIL per file
#
# Requirements: python3 with numpy and lameenc. Nothing else. No DAW, no
# plugins, no sample library, no network access.

set -eu
cd "$(dirname "$0")"

MODE="${1:-build}"

if [ "$MODE" = "--verify" ]; then
    OUT="$(mktemp -d)"
    trap 'rm -rf "$OUT"' EXIT
    echo "== rebuilding into $OUT"
    python3 score.py "$OUT/score.json"
    python3 render.py "$OUT/score.json" "$OUT/lantern-held.wav" --mp3 "$OUT/lantern-held.mp3"
    python3 midi_export.py "$OUT/score.json" "$OUT/lantern-held.mid"
    echo
    echo "== comparing to the submitted exports"
    FAIL=0
    for f in lantern-held.wav lantern-held.mp3 lantern-held.mid; do
        a=$(sha256sum "$OUT/$f" | cut -d' ' -f1)
        b=$(sha256sum "$f" | cut -d' ' -f1)
        if [ "$a" = "$b" ]; then
            echo "PASS  $f  $a"
        else
            echo "FAIL  $f"
            echo "        rebuilt  $a"
            echo "        shipped  $b"
            FAIL=1
        fi
    done
    exit $FAIL
fi

echo "== score"
python3 score.py score.json
echo "== render"
python3 render.py score.json lantern-held.wav --mp3 lantern-held.mp3
echo "== midi"
python3 midi_export.py score.json lantern-held.mid
echo
echo "done. sha256:"
sha256sum lantern-held.wav lantern-held.mp3 lantern-held.mid score.json
