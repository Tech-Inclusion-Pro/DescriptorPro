"""Qt-free engine for Describe Studio and the PyQt app.

Modules here must never import PyQt6 (enforced by tests/test_no_qt_in_engine.py).
Long-running functions take a ProgressReporter and a CancelToken so both the
PyQt worker threads and the FastAPI job runner can drive them.
"""
