FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION="0.10.1"
ARG BUILD_ARCH="amd64"

# This add-on is intentionally a one-shot installer. The Home Assistant base image
# uses s6-overlay, whose default verbosity prints the complete service shutdown
# sequence when the installer exits successfully. Keep only real s6 errors so a
# normal one-shot shutdown is not presented as an alarming warning/error log.
ENV S6_VERBOSITY=0

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
