# Host contract

The canonical Skills describe teaching behavior. A host adapter supplies the capabilities needed to
perform that behavior without changing its evidence or safety rules.

## Capability levels

### Full

A full adapter provides:

- filesystem read/write access to a learner-selected persistent workspace;
- Python 3.10+ or a documented, host-provided runtime resolver;
- safe local command observation separated from static validation;
- loopback HTTP on `127.0.0.1` with dynamic-port discovery;
- the ability to open or return a local classroom URL;
- loading of both Skills and recovery in a new agent session;
- reliable process cleanup and install/uninstall lifecycle hooks.

Subagent creation is an optional quality accelerator, not a Full-adapter requirement. When a host
provides it, the tutor may delegate bounded planning, subject review, rendering, or assurance for a
substantial lesson. It must retain one learner-facing lead, one state writer, a shared turn contract,
and a single-agent fallback; ordinary feedback must not spawn an organization merely because the
capability exists.

### Guided

A guided adapter can persist state and render HTML artifacts but may require the learner to open a
URL or run an explicitly shown command. It must label that limitation and must not claim automatic
inspection or cleanup.

### Protocol only

A protocol-only host can load instruction files but cannot run the state or tool utilities. It may
teach conversationally, but it must not fabricate `.mastery/` state, verification reports, delayed
evidence, or successful tool inspection.

## Non-negotiable invariants

Capability loss may change the medium, never the truth standard. Every adapter must preserve:

- self-reports are placement hints, not mastery evidence;
- assisted completion cannot satisfy independent evidence requirements;
- tool verification distinguishes structure, external observation, staleness, and rejection;
- runtime/cache files and path escapes cannot hide from a verified snapshot;
- generated HTML escapes learner-controlled text and has a usable non-script fallback;
- local servers use unique dynamic ports and are stopped after inspection;
- learner data is visible, exportable, and deleted only on an explicit scoped request.

Host-specific installation documents live in `docs/install/`. Compatibility labels are governed by
[COMPATIBILITY.md](../COMPATIBILITY.md), not by the presence of an adapter directory alone.
