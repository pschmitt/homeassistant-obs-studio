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

For example, call a scene by name:

```yaml
action: obs_studio.set_scene
data:
  scene_name: Main Scene
```
