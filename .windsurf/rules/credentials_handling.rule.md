---
trigger: always_on
---

# Secure Credentials Handling Policy

- All credentials **must** be stored via `ConfigManager.store_credential()`.
- Credentials are encrypted with a key derived from a master password (PBKDF2 +
  machine-specific salt) using `cryptography.Fernet`.
- No secret material is permitted in plaintext within the repository or logs.
- Environment variables containing secrets must be masked (`****`) in any
  output.
- Any new module interacting with credentials must import `ConfigManager` and
  reutilise its methods; direct file or plaintext DB storage is forbidden.
- Violations should raise `RuntimeError("Insecure credential handling")`.
