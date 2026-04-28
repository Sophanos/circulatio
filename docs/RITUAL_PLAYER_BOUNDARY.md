# Ritual Player Boundary

The artifact player is a playback surface. It can render audio, captions, imagery, cinema, breath, meditation, sections, timeline progress, and explicit body-response capture at closing or completion.

A played artifact may later launch a separate live guidance session owned by Hermes or another host runtime. That future surface can manage camera permissions, sensor confidence, reference movement, and live coaching, but it must use its own session identity and event stream.

Ritual completion data remains limited to playback completion, completed sections, explicit user-authored body state, and client metadata already present in the completion contract. Camera frames, pose landmarks, sensor confidence, live coaching state, and inferred movement signals must not enter the ritual completion payload.

This pass does not ship live camera, sensor, or guidance UI. It only hardens artifact playback, shell timeline ownership, lens availability, and closing/completion body capture.
