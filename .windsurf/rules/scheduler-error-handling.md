---
trigger: always_on
---

<error_handling>
- In `run_scheduler()`, wrap the loop body in a `try`/`except Exception as e:`.
- On exception: log full stack trace, sleep 60 s, then continue.
- Ensure *any* uncaught error never exits the scheduler process.
</error_handling>