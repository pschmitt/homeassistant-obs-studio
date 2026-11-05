# Connection setup

OBS Studio 28 or later includes a WebSocket v5 server. Enable it under
**Tools → WebSocket Server Settings**, configure authentication, and add
**OBS Studio** under Home Assistant's **Settings → Devices & services → Add
integration**. The OBS WebSocket port defaults to 4455. Home Assistant
installs its `obsws-python` dependency automatically.

For a server reachable from Home Assistant over the network, use its host,
port and WebSocket password in the integration's config flow. The integration
also supports an SSH tunnel if OBS listens only on localhost. Enable the
SSH tunnel option, provide the remote SSH host, user and a pre-authorized
key path (the default is `/config/.ssh/id_ed25519`), and keep the OBS remote
host set to localhost. The key's public half must be in the remote account's
`~/.ssh/authorized_keys`; configure host-key verification in the integration
options where available. Do not expose OBS WebSocket without authentication.
