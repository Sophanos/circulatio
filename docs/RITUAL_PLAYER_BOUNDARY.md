# Ritual Player Boundary

The artifact player is a playback surface. It can render audio, captions, imagery, cinema, breath, meditation, sections, timeline progress, and explicit completion capture at closing or playback completion. Completion can include no notes, body-response detail, literal reflection text, and practice feedback, but it remains a completion write only.

A played artifact may later launch a separate live guidance session owned by Hermes or another host runtime. That future surface can manage camera permissions, sensor confidence, reference movement, and live coaching, but it must use its own session identity and event stream.

Ritual completion data remains limited to playback completion, completed sections, explicit user-authored body state, and client metadata already present in the completion contract. Camera frames, pose landmarks, sensor confidence, live coaching state, and inferred movement signals must not enter the ritual completion payload.

This pass ships the first no-camera live guidance shell under `/live/{guidanceSessionId}` with focus modes, pause/stop/complete states, and explicit camera preflight. It still does not ship pose estimation, sensor telemetry, reference movement comparison, or camera-derived persistence.
