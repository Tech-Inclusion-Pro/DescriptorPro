"""PyInstaller entry point for the DescriptorPro service (plan Phase 7).

The Electron shell spawns this binary from resources/service/ in the
packaged app; in development it keeps using `.venv/bin/python -m
service.main` instead.
"""

from service.main import main

if __name__ == "__main__":
    main()
