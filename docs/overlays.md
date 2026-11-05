# Template overlays

On each OBS poll, the integration renders Jinja2 HTML templates and writes the
results under `/config/www/obs-studio/`, where Home Assistant serves them as
`/local/obs-studio/`. Add the resulting URL as an OBS **Browser Source** and
turn on **Page is transparent**. The browser must be able to reach your Home
Assistant instance.

For automatic discovery, place `<name>.html.j2` in
`/config/obs_studio/templates/` (the **source**, not the output directory).
For example, `status.html.j2` there produces
`/config/www/obs-studio/status.html`. Alternatively, add an inline template
or a template with an explicit source file path through **Settings → Devices
& services → OBS Studio → Configure → Template overlays**. These options can
also specify a different output directory. An options-flow template overrides
an auto-discovered template with the same name and output directory.

Home Assistant's normal template functions are available alongside these OBS
variables: `obs_scene`, `obs_streaming`, `obs_recording`, `obs_fps`,
`obs_cpu` and `obs_mem`. A small overlay might contain:

```html
<!doctype html>
<html>
  <head><meta charset="utf-8"><style>body { background: transparent; color: white; }</style></head>
  <body><p>Scene: {{ obs_scene }}</p><p>Streaming: {{ obs_streaming }}</p></body>
</html>
```

Save it as `/config/obs_studio/templates/status.html.j2`. In OBS, use the
Browser Source URL `http://homeassistant.local:8123/local/obs-studio/status.html`
if that name resolves from the OBS machine. Refresh the Browser Source to
pick up newly rendered output.
