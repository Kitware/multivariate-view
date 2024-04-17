from pathlib import Path

serve_path = str(Path(__file__).with_name("serve").resolve())
serve = {"__trame_radvolviz": serve_path}
scripts = ["__trame_radvolviz/trame_radvolviz.umd.js"]
vue_use = ["trame_radvolviz"]
