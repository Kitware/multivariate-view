from pathlib import Path

serve_path = str(Path(__file__).with_name("serve").resolve())
serve = {"__multivariate_view": serve_path}
scripts = ["__multivariate_view/multivariate_view.umd.js"]
vue_use = ["multivariate_view"]
