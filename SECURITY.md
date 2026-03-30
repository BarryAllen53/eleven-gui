# Security Policy

## Reporting a Vulnerability

If you discover a security issue, avoid opening a public issue with exploit details.

Instead, send a private report through GitHub Security Advisories or contact the maintainer through the repository profile. Include:

- A short summary
- Reproduction steps
- Impact assessment
- Suggested mitigation if available

## Secrets

This project does not store ElevenLabs API keys in source control.

- `.env` is ignored
- `api key.txt` is ignored
- release builds expect secrets to be provided by the user at runtime
