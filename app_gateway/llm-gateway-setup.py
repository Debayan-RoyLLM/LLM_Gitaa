#!/usr/bin/env python3
"""
llm-gateway-setup.py — thin entry point.

The real code now lives in the `llm_gateway_setup/` package next to this
file, split by concern for easy human debugging:

  config.py   constants, file paths, installers, tools
  detect.py   tool detection + background install jobs
  probe.py    gateway probe + current-state reporting
  writers.py  env / Claude / Qwen / shell-rc file writers
  page.py     the setup-page HTML string
  server.py   HTTP handler + main()

Run:   python3 llm-gateway-setup.py
Then:  a browser opens at http://127.0.0.1:8765

No dependencies. Python 3.9+. Nothing leaves your machine except the
connection test, which goes to your gateway.
"""

from llm_gateway_setup.server import main

if __name__ == "__main__":
    main()
