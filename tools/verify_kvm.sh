#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python}"
PRETTIER="${PRETTIER:-node_modules/prettier/bin/prettier.cjs}"
changed_py=(
  custom_components/nanokvm_rest/providers
  custom_components/nanokvm_rest/{__init__,config_flow,console,diagnostics,kvm_api,operations,panel_ext,panel_v2,panel_v4}.py
  nanokvm_rest/webui/app.py
  tests/{test_manager_inventory,test_jetkvm_protocol,test_kvm_crud,kvm_test_support,browser_jetkvm}.py
)
changed_js=(
  nanokvm_rest/webui/static/{app,device-setup,jetkvm-console-controller,remote-console-controller}.js
  nanokvm_rest/webui/static/style.css
  nanokvm_rest/webui/templates/index.html
  tests/test_jetkvm_console.cjs tests/test_nanokvm_console.cjs
)
printf '[1/6] Python formatter and lint\n'
"$PYTHON" -m ruff format --check "${changed_py[@]}"
"$PYTHON" -m ruff check "${changed_py[@]}"
printf '[2/6] Frontend formatter and syntax\n'
node "$PRETTIER" --check "${changed_js[@]}"
for file in nanokvm_rest/webui/static/*.js; do node --check "$file"; done
printf '[3/6] Backend and package regression tests\n'
"$PYTHON" -m unittest discover -s tests -v
printf '[4/6] Frontend protocol and regression tests\n'
node --test tests/test_*.cjs
printf '[5/6] Compile both integration distributions and app\n'
"$PYTHON" -m compileall -q custom_components/nanokvm_rest nanokvm_rest/integration/nanokvm_rest nanokvm_rest/webui
printf '[6/6] Verification passed (hardware acceptance is separate)\n'
