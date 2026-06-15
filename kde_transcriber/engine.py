import gc
import logging

log = logging.getLogger("kde_transcriber")

_model = None
_key = None


def pick_device():
    import ctranslate2
    try:
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except Exception:
        pass
    return "cpu"


def unload():
    global _model, _key
    _model = None
    _key = None
    gc.collect()


def load_model(name, on_status=None):
    global _model, _key
    device = pick_device()
    if _model is not None and _key == (name, device):
        return _model, device, None

    unload()  # free the previous model's VRAM before loading another one
    from faster_whisper import WhisperModel

    note = None
    if device == "cuda":
        if on_status:
            on_status(f"Loading {name} on the GPU…")
        try:
            _model = WhisperModel(name, device="cuda", compute_type="int8_float16")
        except Exception as exc:
            unload()
            device = "cpu"
            if "out of memory" in str(exc).lower():
                note = ("Not enough GPU memory — using CPU. Close other apps using "
                        "the GPU and try again.")
                log.error("GPU OOM with %s; falling back to CPU.", name)
            else:
                note = f"Could not use the GPU ({exc}) — using CPU."
                log.error("GPU failure with %s: %s", name, exc)

    if _model is None:
        if on_status:
            on_status(f"Loading {name} on the CPU…")
        _model = WhisperModel(name, device="cpu", compute_type="int8")

    _key = (name, device)
    return _model, device, note


def transcribe(model, audio_path, language):
    return model.transcribe(str(audio_path), language=language, vad_filter=True)
