#!/usr/bin/env bash
set -euo pipefail
rm -rf "$HOME/.local/share/transcriber"
rm -f "$HOME/.local/share/applications/transcriber.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
echo "Transcriber uninstalled."
echo "Your transcriptions and the model cache (~/.cache/huggingface) were left untouched."
