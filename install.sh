#!/usr/bin/env bash
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/kde-transcriber"
VENV="$DEST/venv"
APPS="$HOME/.local/share/applications"

command -v ffmpeg >/dev/null || { echo "ffmpeg is required: install it with your package manager"; exit 1; }

mkdir -p "$DEST" "$APPS"
rm -rf "$DEST/kde_transcriber" "$DEST/resources"
cp -r "$SRC/kde_transcriber" "$DEST/kde_transcriber"
cp -r "$SRC/resources" "$DEST/resources"

echo ">> Creating environment (Python 3.12)…"
if command -v uv >/dev/null; then
    uv venv --python 3.12 "$VENV"
    uv pip install --python "$VENV/bin/python" -r "$SRC/requirements.txt"
else
    PY=""
    for c in python3.12 python3.11 python3.10; do
        command -v "$c" >/dev/null && { PY="$c"; break; }
    done
    [ -n "$PY" ] || { echo "Need Python 3.10-3.12 (install 'uv' or a python3.12 package)"; exit 1; }
    "$PY" -m venv "$VENV"
    "$VENV/bin/pip" install --upgrade pip
    "$VENV/bin/pip" install -r "$SRC/requirements.txt"
fi

cat > "$DEST/run.sh" <<'RUNSH'
#!/usr/bin/env bash
DEST="$HOME/.local/share/kde-transcriber"
PY="$DEST/venv/bin/python"
# CUDA libs come from the pip wheels (namespace packages); locate their dirs.
LIBS="$("$PY" - <<'PYLIBS'
import os
import nvidia
dirs = []
for base in list(nvidia.__path__):
    for sub in ("cublas/lib", "cudnn/lib", "cuda_nvrtc/lib"):
        d = os.path.join(base, sub)
        if os.path.isdir(d):
            dirs.append(d)
print(":".join(dirs))
PYLIBS
)"
export LD_LIBRARY_PATH="${LIBS:+$LIBS:}${LD_LIBRARY_PATH:-}"
export PYTHONPATH="$DEST"
exec "$PY" -m kde_transcriber "$@"
RUNSH
chmod +x "$DEST/run.sh"

sed -e "s#__RUN__#$DEST/run.sh#g" -e "s#__ICON__#$DEST/resources/kde-transcriber.svg#g" \
    "$SRC/kde-transcriber.desktop" | grep -v '^#!' > "$APPS/kde-transcriber.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" >/dev/null 2>&1 || true
command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true

echo ">> Done. Look for 'KDE Transcriber' in your application menu."
echo "   (The first run downloads the chosen Whisper model from Hugging Face.)"
