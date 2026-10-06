# Describe Studio development targets. The PyQt app is unaffected: make pyqt.

setup:
	python3 -m venv .venv --system-site-packages
	.venv/bin/pip install -r requirements-service.txt
	cd ui && npm install
	cd shell && npm install

dev:
	zsh scripts/dev.sh

dev-web:
	zsh scripts/dev.sh --web

test:
	.venv/bin/python -m pytest tests/
	cd ui && npm test

build-ui:
	.venv/bin/python ui/scripts/export-translations.py
	cd ui && npm run build

pyqt:
	python3 main.py

.PHONY: setup dev dev-web test build-ui pyqt
