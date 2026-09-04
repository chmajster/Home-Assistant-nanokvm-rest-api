# NanoKVM REST Home Assistant app

This Home Assistant app installs the bundled `NanoKVM REST` custom integration into `/config/custom_components/nanokvm_rest` (mounted inside the app as `/homeassistant`).

The app is an installer, not a background NanoKVM service. It uses `startup: once` and stops after copying the integration.

## Installation

1. Add `https://github.com/chmajster/homeassistant-nanokvm-rest-api` as a custom repository in the Home Assistant app/add-on store.
2. Install **NanoKVM REST**.
3. Start the app once.
4. Check the app log for a successful installation message.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration** and select **NanoKVM REST**.

## Updating

After updating the NanoKVM REST app, start it once again so the bundled integration is copied into Home Assistant, then restart Home Assistant.

## Important

The repository must be reachable by the Home Assistant Supervisor. A private GitHub repository cannot be cloned by a normal custom-repository installation unless the Supervisor has a supported authenticated Git source.
