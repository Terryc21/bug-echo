#!/bin/bash
#
# setup.sh — materialize a bug-echo fixture as a throwaway git repo.
#
# WHY THIS EXISTS: bug-echo's primary mode (Step 2B) infers the pattern from a
# real diff — `git log -p -1` — and self-validates it against the pre-fix file
# via `git show HEAD~1:<path>`. Neither works on a bare directory. The fixture
# therefore needs actual commit history, which is the one thing a JSON case
# list cannot fake.
#
# WHAT IT DOES:
#   1. Copies the fixture's src/ into a scratch directory
#   2. Commits it with the seed file in its BUGGY state
#   3. Fixes ONLY the seed file
#   4. Commits the fix
#
# HEAD is then a real fix commit whose diff bug-echo can infer from, and HEAD~1
# is a real pre-fix baseline it can self-validate against.
#
# USAGE:
#   bash fixtures/setup.sh                      # default fixture, default dest
#   bash fixtures/setup.sh swift-try-fetch /tmp/be-fix
#
# The destination is created fresh each run. It is NOT inside this repo, so a
# fixture run can never dirty bug-echo's own working tree — which matters
# because bug-echo's Pre-flight step refuses to scan a dirty repo.
#
set -euo pipefail

FIXTURE="${1:-swift-try-fetch}"
DEST="${2:-/tmp/bug-echo-fixture-$FIXTURE}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/$FIXTURE/src"

if [ ! -d "$SRC" ]; then
    echo "❌ No fixture at $SRC" >&2
    echo "   Available:" >&2
    find "$SCRIPT_DIR" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; >&2
    exit 1
fi

# Refuse to clobber anything that isn't ours. A fixture run should never be
# able to delete a real directory because someone passed a wrong second arg.
if [ -e "$DEST" ]; then
    if [ ! -f "$DEST/.bug-echo-fixture" ]; then
        echo "❌ $DEST exists and is not a bug-echo fixture scratch dir." >&2
        echo "   Refusing to delete it. Pass a different destination." >&2
        exit 1
    fi
    rm -rf "$DEST"
fi

mkdir -p "$DEST"
touch "$DEST/.bug-echo-fixture"
cp -R "$SRC" "$DEST/src"

cd "$DEST"
git init -q
git config user.email "fixture@bug-echo.local"
git config user.name "bug-echo fixture"

# --- Commit 1: everything, seed file BUGGY -------------------------------
git add -A
git commit -q -m "Initial import (seed file still buggy)"

# --- Fix ONLY the seed file ----------------------------------------------
# This is the change bug-echo will read as "the fix that just shipped".
cat > src/SettingsStore.swift <<'SWIFT'
import Foundation

/// FIXTURE FILE — THE SEED, post-fix.
///
/// The diff between this and HEAD~1 is what bug-echo infers the pattern from.

final class SettingsStore {
    private let context: DataContext
    private let logger: Logging

    init(context: DataContext, logger: Logging) {
        self.context = context
        self.logger = logger
    }

    func loadPreferences() -> [Item] {
        do {
            return try context.fetch(ItemDescriptor.all)
        } catch {
            logger.error("Preferences fetch failed: \(error)")
            return []
        }
    }
}
SWIFT

git add -A
git commit -q -m "fix(settings): stop swallowing the preferences fetch error

try? discarded the error, so a failed load looked identical to an empty
preferences store. Now caught and logged; the empty return is a deliberate
fallback rather than an accident."

echo "✅ Fixture ready: $DEST"
echo
echo "   HEAD    $(git log -1 --format='%h %s' | head -c 60)"
echo "   HEAD~1  $(git log -1 --skip=1 --format='%h %s')"
echo
echo "   Next: cd \"$DEST\" && run bug-echo in inferred mode."
echo "   Then score with: python3 $SCRIPT_DIR/score.py <report.md> $FIXTURE"
