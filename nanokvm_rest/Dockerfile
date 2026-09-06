ARG BUILD_FROM=ghcr.io/home-assistant/base-python:3.14-alpine3.23
FROM ${BUILD_FROM}

ARG BUILD_VERSION="0.11.1"
ARG BUILD_ARCH="amd64"

COPY requirements.txt /tmp/requirements.txt
RUN python3.14 -m venv /venv \
    && /venv/bin/python -m pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

COPY integration /opt/integration
COPY webui /opt/webui
COPY run.sh /run.sh
RUN chmod 0755 /run.sh

ENV PATH="/venv/bin:${PATH}" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1" \
    BUILD_VERSION="${BUILD_VERSION}"

LABEL \
    io.hass.name="NanoKVM Manager" \
    io.hass.description="NanoKVM fleet management with Home Assistant Ingress" \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}" \
    org.opencontainers.image.title="NanoKVM Manager" \
    org.opencontainers.image.description="NanoKVM remote management UI for Home Assistant" \
    org.opencontainers.image.version="${BUILD_VERSION}" \
    org.opencontainers.image.source="https://github.com/chmajster/homeassistant-nanokvm-rest-api"

CMD ["/run.sh"]
