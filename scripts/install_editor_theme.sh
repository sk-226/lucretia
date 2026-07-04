#!/usr/bin/env bash
set -euo pipefail

# Install Lucretia into both VS Code and Cursor through the same VSIX.
#
# The tempting development setup is to symlink dist/vscode into Cursor and use
# `code --install-extension` for VS Code. That creates two different lifecycle
# models for one extension ID: Cursor keeps a live directory and VS Code keeps a
# versioned copy. In practice Cursor also records removed versions in
# ~/.cursor/extensions/.obsolete, so a later package version can be hidden even
# while the symlink still points at valid files. A single VSIX install path keeps
# both editors on the same versioned artifact and avoids that cache mismatch.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTENSION_DIR="$ROOT/dist/vscode"
VSIX_DIR="$ROOT/dist/vsix"
VSIX_PATH="$VSIX_DIR/lucretia-theme.vsix"
CURSOR_DEV_LINK="$HOME/.cursor/extensions/lucretia-theme"

python3 "$ROOT/scripts/build_dist.py"

# Keep the package archive outside dist/vscode. Cursor scans extension
# directories as extension source trees; putting the archive inside the source
# directory is not needed by either editor and makes the development directory
# look different from the installed copy.
mkdir -p "$VSIX_DIR"

# npx is used instead of vendoring a Node project because this repository is a
# color-palette source tree, not a JavaScript package. The trade-off is that a
# first run may need network access; the benefit is no node_modules or lockfile
# churn for a one-command packaging tool.
(cd "$EXTENSION_DIR" && npx -y @vscode/vsce package --allow-missing-repository -o "$VSIX_PATH")

# Remove the old Cursor development symlink before installing the VSIX. Leaving
# it in place can give Cursor two local copies with the same publisher.name ID,
# and which copy wins then depends on cached extension metadata rather than the
# current files in this repository.
if [ -L "$CURSOR_DEV_LINK" ]; then
  unlink "$CURSOR_DEV_LINK"
fi

code --install-extension "$VSIX_PATH" --force
cursor --install-extension "$VSIX_PATH" --force
