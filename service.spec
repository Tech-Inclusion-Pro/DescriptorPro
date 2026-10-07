# PyInstaller spec for the DescriptorPro service (onedir).
# Build:  .venv/bin/pyinstaller service.spec --noconfirm
# Output: dist/describe-studio-service/  → copied into the Electron app's
# resources/service/ by the packaging step. The shell auto-prefers it.
#
# Kept separate from LaMiaScribe.spec — the PyQt app's build is untouched.

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [
    ("prompts", "prompts"),
    ("standards", "standards"),
    ("player/vendor", "player/vendor"),
    ("ui/dist", "ui/dist"),
]
binaries = []
hiddenimports = (
    collect_submodules("service")
    + collect_submodules("core")
    + collect_submodules("exporters")
    + collect_submodules("utils")
    + [
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "keyring.backends.macOS",
    ]
)

# Packages that carry data files or native libraries the engine loads
# lazily. collect_all is heavy-handed but correct; the onedir is a local
# service, not a download.
for package in (
    "faster_whisper",
    "ctranslate2",
    "mlx",
    "parakeet_mlx",
    "sherpa_onnx",
    "onnxruntime",
    "rapidocr_onnxruntime",
    "kokoro_onnx",
    "espeakng_loader",
    "pypdfium2",
    "pypdfium2_raw",
    "scenedetect",
    "cv2",
    "docx",
    "tokenizers",
    "huggingface_hub",
    "ollama",
    "misaki",
):
    try:
        d, b, h = collect_all(package)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass  # optional package not installed on this platform

a = Analysis(
    ["service_entry.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["PyQt6", "tkinter", "matplotlib", "PyInstaller"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="describe-studio-service",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="describe-studio-service",
)
