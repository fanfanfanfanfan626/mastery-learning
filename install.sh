#!/bin/sh
set -eu

CHECK_ONLY=0
CODEX_COMMAND=codex

while [ "$#" -gt 0 ]; do
    case "$1" in
        --check-only)
            CHECK_ONLY=1
            shift
            ;;
        --codex)
            if [ "$#" -lt 2 ]; then
                echo "--codex requires a command path" >&2
                exit 2
            fi
            CODEX_COMMAND=$2
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPOSITORY_ROOT=$SCRIPT_DIR
MARKETPLACE_PATH=$REPOSITORY_ROOT/.agents/plugins/marketplace.json
PLUGIN_MANIFEST_PATH=$REPOSITORY_ROOT/plugins/mastery-learning/.codex-plugin/plugin.json

if [ ! -f "$MARKETPLACE_PATH" ]; then
    echo "Not a Mastery Learning marketplace root: missing .agents/plugins/marketplace.json" >&2
    exit 1
fi
if [ ! -f "$PLUGIN_MANIFEST_PATH" ]; then
    echo "Incomplete plugin package: missing plugins/mastery-learning/.codex-plugin/plugin.json" >&2
    exit 1
fi
if ! grep -Eq '"name"[[:space:]]*:[[:space:]]*"mastery-learning"' "$MARKETPLACE_PATH"; then
    echo "Marketplace identity mismatch: expected mastery-learning" >&2
    exit 1
fi
if ! grep -Eq '"path"[[:space:]]*:[[:space:]]*"\./plugins/mastery-learning"' "$MARKETPLACE_PATH"; then
    echo "Marketplace source mismatch: expected local path ./plugins/mastery-learning" >&2
    exit 1
fi
if ! grep -Eq '"name"[[:space:]]*:[[:space:]]*"mastery-learning"' "$PLUGIN_MANIFEST_PATH"; then
    echo "Plugin identity mismatch: expected mastery-learning" >&2
    exit 1
fi
if ! grep -Eq '"skills"[[:space:]]*:[[:space:]]*"\./skills/"' "$PLUGIN_MANIFEST_PATH"; then
    echo "Plugin identity mismatch: expected bundled ./skills/" >&2
    exit 1
fi

echo "Preflight passed: Codex plugin marketplace 'mastery-learning' with bundled Skills."
echo "Repository root: $REPOSITORY_ROOT"

if [ "$CHECK_ONLY" -eq 1 ]; then
    echo "Check-only mode: Codex configuration was not changed."
    exit 0
fi

case "$REPOSITORY_ROOT/" in
    "${TMPDIR:-/tmp}/"*|/tmp/*|/var/tmp/*)
        echo "Refusing a temporary install source. Move the complete repository to a stable directory and run again." >&2
        exit 1
        ;;
esac

if ! "$CODEX_COMMAND" plugin marketplace add "$REPOSITORY_ROOT"; then
    echo "Codex marketplace registration failed. Do not use skill-installer as a fallback." >&2
    exit 1
fi
if ! "$CODEX_COMMAND" plugin add "mastery-learning@mastery-learning"; then
    echo "Codex plugin installation failed. Do not copy a nested Skill as a fallback." >&2
    exit 1
fi

echo "Installed mastery-learning as a Codex plugin. Open a new Codex task to load both bundled Skills."
