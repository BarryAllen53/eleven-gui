# Changelog

## 1.0.2 - 2026-04-20

### Added

- Real-time TTS progress announcements every 20 seconds with estimated character and word completion
- Expanded output format selector with WAV family variants, OPUS profiles, PCM family variants, and telephony formats

### Changed

- Studio language code input is now an editable select box with model-aware language options and `Auto`
- Long-form TTS now chunks text in smaller units for more stable generation behavior

### Fixed

- Fixed long-form generation truncation where only the first chunk was audible in some players
- Fixed progress display staying at zero before generation completed
- Improved TTS language application and safer fallback handling when model-language combinations fail
- Improved API error summarization to avoid noisy screen-reader repetition on long failures

## 1.0.1 - 2026-03-31

### Added

- Inno Setup installer build pipeline
- Optional code-signing helper script for release artifacts
- Development certificate workflow for local Authenticode signing without signtool
- Portable mode marker for packaged zip builds

### Changed

- Installed builds now store configuration and generated files in per-user Windows locations instead of the installation directory
- Release documentation now covers installer and signing workflows

### Fixed

- Packaged runtime configuration now behaves correctly for installed deployments
- Nuitka release builds now produce portable artifacts with an explicit mode marker

## 1.0.0 - 2026-03-31

### Added

- Accessible desktop client for ElevenLabs built with Python and PySide6
- Workspace overview for subscription, credit usage, model readiness, and recent activity
- Voice Hub with My Voices, Cloned Voices, and Shared Library sections
- Batch selection, batch delete, and batch import flows for voice management
- Studio workflows for text-to-speech and speech-to-speech
- Instant Voice Clone and Professional Voice Clone flows
- History playback, batch download, and batch delete
- Keyboard shortcut layer and screen-reader-oriented navigation helpers
- Release screenshots and distribution-oriented README

### Changed

- Modernized visual system with calmer spacing, summary-first layouts, and collapsible advanced settings
- Refined screen-reader announcements to avoid noisy repeated messages
- Improved list interactions for both keyboard and pointer users

### Fixed

- Worker lifecycle bug that could prevent Studio generation results from reaching the UI
- Missing voice handling now removes unavailable voices from the visible inventory
- Batch delete now skips unavailable voices instead of aborting the full operation
