#!/usr/bin/env bash
set -euo pipefail
rm -rf "$HOME/.local/share/kde-transcriber"
rm -f "$HOME/.local/share/applications/kde-transcriber.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
echo "KDE Transcriber uninstalled."
echo "Your transcriptions and the model cache (~/.cache/huggingface) were left untouched."
