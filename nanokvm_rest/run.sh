#!/usr/bin/with-contenv bashio
set -Eeuo pipefail

SOURCE="/opt/integration/nanokvm_rest"
TARGET_ROOT="/homeassistant/custom_components"
TARGET="${TARGET_ROOT}/nanokvm_rest"
STAGE="${TARGET_ROOT}/.nanokvm_rest.new"
BACKUP="${TARGET_ROOT}/.nanokvm_rest.backup"

install_integration() {
    if [[ ! -d /homeassistant ]]; then
        bashio::log.fatal "Home Assistant configuration directory is not mounted at /homeassistant."
        exit 1
    fi
    if [[ ! -f "${SOURCE}/manifest.json" ]]; then
        bashio::log.fatal "Bundled NanoKVM REST integration is missing."
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
        bashio::log.fatal "Failed to install NanoKVM REST integration."
        exit 1
    fi
    rm -rf "${BACKUP}"
    sync
    bashio::log.info "NanoKVM REST integration synchronized to ${TARGET}."
}

install_integration

if [[ -z "${SUPERVISOR_TOKEN:-}" ]]; then
    bashio::log.fatal "SUPERVISOR_TOKEN is missing. The add-on requires homeassistant_api: true."
    exit 1
fi

bashio::log.info "Starting NanoKVM Manager Web UI on Ingress port 8099."
exec /venv/bin/gunicorn \
    --chdir /opt/webui \
    --bind 0.0.0.0:8099 \
    --workers 1 \
    --threads 6 \
    --timeout 0 \
    --access-logfile - \
    --error-logfile - \
    "app:app"
