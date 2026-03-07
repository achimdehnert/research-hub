#!/bin/bash
# Thin-wrapper — delegates to platform/scripts/ship.sh
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.."; pwd)"
PLATFORM_SHIP="$(cd "$REPO_DIR/../platform/scripts"; pwd)/ship.sh"
if [ ! -f "$PLATFORM_SHIP" ]; then
  echo "ERROR: $PLATFORM_SHIP not found." >&2
  exit 1
fi
exec bash "$PLATFORM_SHIP" --repo "$REPO_DIR" "${@}"
