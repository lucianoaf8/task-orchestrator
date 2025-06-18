---
trigger: always_on
---

# Python Quality
- Format all code with Black; enforce via Ruff (--select I,E,F,B).
- Use MyPy in strict-optional mode.
- Public functions & classes must have Google-style docstrings.
- Prefer early returns; avoid nested conditionals.
- No bare `except:`—always catch specific exceptions.