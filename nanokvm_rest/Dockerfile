FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION="0.8.0"
ARG BUILD_ARCH="amd64"

COPY integration /opt/integration
COPY run.sh /run.sh

RUN chmod 0755 /run.sh

LABEL \
    io.hass.name="NanoKVM REST" \
    io.hass.description="Installer for the NanoKVM REST Home Assistant integration" \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}" \
    org.opencontainers.image.title="NanoKVM REST" \
    org.opencontainers.image.description="Installs the NanoKVM REST custom integration into Home Assistant" \
    org.opencontainers.image.version="${BUILD_VERSION}" \
    org.opencontainers.image.source="https://github.com/chmajster/homeassistant-nanokvm-rest-api"

CMD ["/run.sh"]
