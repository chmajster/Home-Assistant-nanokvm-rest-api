# Operations Center

Version 0.10.0 adds a fleet-oriented operations layer to the NanoKVM REST Remote Server panel.

## Fleet monitoring

The integration performs a lightweight API probe for each configured NanoKVM every 60 seconds. The probe records current reachability and API latency. Compact metric samples are persisted at most once every five minutes, retaining enough data for approximately seven days of availability analysis without writing Home Assistant storage on every probe.

The Operations view displays current latency, 24-hour and 7-day availability, average and maximum 24-hour latency, the last successful probe and an advanced Health Score.

## Health Score

The advanced score starts at 100 and applies operational penalties for:

- NanoKVM being unreachable;
- host powered on with missing HDMI signal on PCIe NanoKVM;
- elevated/high/critical API latency;
- degraded 24-hour availability;
- unknown application version;
- an available NanoKVM application update.

The score is classified as Healthy, Warning or Critical.

## Alert Center

Active alerts are generated for:

- NanoKVM offline;
- missing HDMI signal while the host is powered on;
- high API latency;
- low 24-hour availability;
- available NanoKVM application update;
- failed manual or automatic recovery.

Warnings and critical alerts can create Home Assistant persistent notifications. Every new non-muted alert also fires the `nanokvm_rest_operations_alert` event with `entry_id`, device title, alert type, severity and message so users can route alerts through normal Home Assistant automations and mobile notification services.

Alerts can be acknowledged from the sidepanel. Acknowledgement suppresses the corresponding persistent notification until that alert condition resolves and later occurs again.

## Maintenance Mode

Maintenance Mode is configured per NanoKVM. It can be indefinite or expire after a selected duration and can include a short maintenance note.

While active:

- active alerts remain visible but are marked muted;
- new persistent notifications are suppressed;
- the operations event is not fired for new muted alerts;
- Auto Recovery is paused.

## Auto Recovery

Auto Recovery is intentionally conservative. It never power-cycles or resets the attached host automatically.

For administrator-controlled PCIe NanoKVM devices, Auto Recovery can reset the HDMI subsystem after three consecutive one-minute probes report that the host is powered on but HDMI signal is missing. A configurable cooldown and maximum attempts per hour prevent recovery loops.

A NanoKVM that is completely offline cannot be repaired through its own REST API. In that situation the integration reports an offline alert instead of pretending that an in-band recovery action is possible.

## Recovery Center

Manual actions available from Operations include:

- Diagnostics: refresh state and record an operations diagnostic event;
- Safe recovery: reset HID and, for PCIe devices, reset HDMI;
- Reset HID;
- Reset HDMI;
- Reboot NanoKVM, protected by a destructive-action confirmation.

All recovery operations are recorded in the existing Remote Server audit/event history together with the Home Assistant user that requested the operation.

## Power timeline

The selected NanoKVM displays a focused timeline containing host power transitions and manual power/reset operations from the existing persistent Remote Server event log.

## Storage

Operations settings and compact metrics are stored in Home Assistant `.storage` under `nanokvm_rest.operations`. Credentials, NanoKVM session cookies and Remote Console tokens are never stored there.
