#!/bin/bash
# Re-establish hardlinks from the repo's skills/ to the canonical authoring copies.
# Hardlinks share an inode, so the repo always reflects the in-use skill text.
# An atomic-save editor can break the link (writes a new inode); re-run this to resync.
# Skeptics who clone the repo do NOT need this — they already have real file copies.
set -e
CANON="${CANON:-$HOME/Documents/june.kim/skills}"
REPO="$(cd "$(dirname "$0")/.." && pwd)/skills"
for s in recon craft audit; do
  if [ -f "$CANON/$s/skill.md" ]; then
    ln -f "$CANON/$s/skill.md" "$REPO/$s/skill.md"
    echo "linked $s (inode $(ls -i "$REPO/$s/skill.md" | cut -d' ' -f1))"
  else
    echo "skip $s: canonical $CANON/$s/skill.md not found (clone-only checkout — keeping repo copy)"
  fi
done
