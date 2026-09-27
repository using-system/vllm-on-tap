---
name: vot-destroy
description: Destroy the unit vot-<preset> a vllm-on-tap serve created on the current environment (a process, a container or a cloud app), keeping the environment itself. Use when the user wants a served preset stopped and removed; the argument is the preset name.
---

# /vot-destroy <preset>

1. **Environment.** Read `.vot/config.yaml` and
   `.vot/environments/<current>.yaml`. None: tell the user to run
   `/vot-config` and stop. Resolve the stack type per the stack-guide skill
   (an earlier name is read as the current one); a planned type: say it is
   not supported in this version, and stop.
2. **Stack.** Read the stack-guide skill's reference for the environment's
   stack type.
3. **Destroy.** Run the reference's *Destroy* for `vot-<preset>`. A unit that
   does not exist is reported, not an error.
4. **Report.** Say what was removed and what stays, per the reference's
   *Destroy*.
