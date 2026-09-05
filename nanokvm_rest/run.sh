#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE="/opt/integration/nanokvm_rest"
TARGET_ROOT="/homeassistant/custom_components"
TARGET="${TARGET_ROOT}/nanokvm_rest"
STAGE="${TARGET_ROOT}/.nanokvm_rest.new"
BACKUP="${TARGET_ROOT}/.nanokvm_rest.backup"

if [[ ! -d /homeassistant ]]; then
    echo "ERROR: Home Assistant configuration directory is not mounted at /homeassistant." >&2
    exit 1
fi

if [[ ! -f "${SOURCE}/manifest.json" ]]; then
    echo "ERROR: Bundled NanoKVM REST integration is missing." >&2
    exit 1
fi

mkdir -p "${TARGET_ROOT}"
rm -rf "${STAGE}" "${BACKUP}"
mkdir -p "${STAGE}"
cp -a "${SOURCE}/." "${STAGE}/"

if [[ -e "${TARGET}" || -L "${TARGET}" ]]; then
    mv "${TARGET}" "${BACKUP}"
fi

if ! mv "${STAGE}" "${TARGET}"; then
    rm -rf "${STAGE}"
    if [[ -e "${BACKUP}" || -L "${BACKUP}" ]]; then
        mv "${BACKUP}" "${TARGET}"
    fi
    echo "ERROR: Failed to install NanoKVM REST integration." >&2
    exit 1
fi

rm -rf "${BACKUP}"
sync

printf '\n'
echo "SUCCESS: NanoKVM REST integration installed in ${TARGET}."
echo "Next step: restart Home Assistant, then add NanoKVM REST from Settings -> Devices & services -> Add integration."
echo "This add-on is a one-shot installer and will now stop normally. A stopped add-on after this SUCCESS message is expected."
