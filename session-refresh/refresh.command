#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if ! .venv/bin/python -c 'from playwright.sync_api import sync_playwright' >/dev/null 2>&1; then
  .venv/bin/python -m pip install 'playwright>=1.51,<2'
fi
.venv/bin/python -m playwright install chromium
exec .venv/bin/python refresh_login.py "$@"
