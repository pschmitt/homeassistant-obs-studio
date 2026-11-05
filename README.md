<p align="center">
  <img src="logo.png" width="128" alt="OBS Studio logo">
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/marketplace_repository/?owner=pschmitt&amp;repository=homeassistant-obs-studio&amp;category=integration"><img src="https://my.home-assistant.io/badges/marketplace_repository.svg" alt="Open this integration in Home Assistant Marketplace"></a>
</p>

<h1 align="center">OBS Studio for Home Assistant</h1>

<p align="center">Monitor and control OBS Studio through its WebSocket v5 server.</p>

## Features

- **OBS status:** Track the current scene, streaming, recording, system metrics and output state. See [Entities and controls](docs/controls.md).
- **Playback controls:** Switch scenes and manage streams, recordings, the virtual camera and replay buffer through Home Assistant services.
- **Connection options:** Connect directly to OBS or forward its localhost WebSocket through SSH. See [Connection setup](docs/connection.md).
- **Template overlays:** Render Home Assistant and OBS data into HTML for OBS Browser Sources. See [Template overlays](docs/overlays.md).

## Install

Use the Marketplace badge above on Home Assistant 2026.11 or later to add this
repository as a custom integration. On older versions, add it as a HACS
custom repository of type **Integration**. Install and restart Home Assistant.
The badge does not imply a public catalog listing. For manual installation,
copy `custom_components/obs_studio/` into Home Assistant's
`custom_components/` directory and restart.

## Quick start

1. Enable **WebSocket Server** in OBS Studio 28 or later under **Tools → WebSocket Server Settings**.
2. Add **OBS Studio** under **Settings → Devices & services → Add integration**.
3. Enter the OBS address, WebSocket port and password, then select a scene in Home Assistant.

See [Connection setup](docs/connection.md) for localhost-only OBS servers.

## Documentation

| Topic | Description |
|-------|-------------|
| [Connection setup](docs/connection.md) | Direct WebSocket and SSH tunnel configuration |
| [Entities and controls](docs/controls.md) | Status entities and service names |
| [Template overlays](docs/overlays.md) | Template sources, output and Browser Source setup |

## License

[GPL-3.0](LICENSE). The OBS Studio logo belongs to OBS Project contributors and
is distributed under their [GPL-2.0 license](https://github.com/obsproject/obs-studio/blob/master/COPYING).
