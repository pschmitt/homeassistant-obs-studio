# Entities and controls

The integration exposes the current scene, CPU and memory usage, available
recording disk space, active FPS, skipped frames, stream and record durations,
OBS version and platform as sensors. Binary sensors report streaming,
recording, paused recording, virtual camera, studio mode and replay buffer.
A scene select and virtual-camera and studio-mode switches provide controls.

Service actions use the `obs_studio` domain, not `obs`:

| Action | Purpose |
|--------|---------|
| `obs_studio.set_scene` | Switch to a named scene |
| `obs_studio.start_stream`, `stop_stream`, `toggle_stream` | Control the stream |
| `obs_studio.start_record`, `stop_record`, `toggle_record` | Control recording |
| `obs_studio.pause_record`, `resume_record` | Pause or resume recording |
| `obs_studio.start_virtual_cam`, `stop_virtual_cam` | Control the virtual camera |
| `obs_studio.start_replay_buffer`, `stop_replay_buffer`, `save_replay_buffer` | Control the replay buffer |
| `obs_studio.trigger_hotkey` | Trigger a named OBS hotkey |
| `obs_studio.render_templates` | Render configured overlays on demand |
| `obs_studio.set_input_mute` | Mute or unmute an input, read back from OBS |
| `obs_studio.step_input_volume` | Raise or lower an input volume by a step within bounds |

For example, call a scene by name:

```yaml
action: obs_studio.set_scene
data:
  scene_name: Main Scene
```

## Input audio

`set_input_mute` and `step_input_volume` act either on one input (`input_name`)
or on the allowed input(s) of the scene that is currently on air
(`scene_inputs`). Both return a before/after summary when called with
`response_variable`.

`scene_inputs` maps a program scene name to the input names that may be changed
while that scene is on air. The actions fail without touching OBS when the
current scene has no entry or none of its listed inputs is visible, so a stale
automation cannot change a source that is not playing. Enabled items in nested
scenes and groups count as visible. `input_kinds` optionally restricts the OBS
input kinds (version suffixes such as `_v2` are ignored).

`step_input_volume` reads the current volume from OBS, moves it by `step_db`
and keeps it within `min_db` and `max_db`. With `unmute_on_up: true`, raising
the volume also unmutes the input, even at the maximum; lowering it never
changes mute. Bounds must lie within -100 to 26 dB, and `step_db`, `min_db` and
`max_db` must be finite.

```yaml
action: obs_studio.step_input_volume
data:
  direction: up
  step_db: 3
  min_db: -40
  max_db: 0
  unmute_on_up: true
  input_kinds: [ffmpeg_source, browser_source]
  scene_inputs:
    Main Scene: [Media]
    Other Scene: [Browser, Media]
response_variable: result
```
