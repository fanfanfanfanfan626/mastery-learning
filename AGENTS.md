# Mastery Learning repository instructions

## Installation classification

This repository is a **Codex plugin marketplace**, not a standalone Skill repository. It bundles
both `mastery-coach` and `mastery-tool-creator` under one plugin identity.

When a user asks to install this repository:

1. Do not invoke `skill-installer` and do not search for a root `SKILL.md`.
2. Keep the clone or extracted Release in a stable path that will not be deleted after the task.
3. Read `INSTALL.md`, verify the marketplace and plugin manifests, then run the root installer for
   the current platform.
4. Treat successful `codex plugin add mastery-learning@mastery-learning` completion as the install
   boundary, then ask the user to open a new Codex task so the bundled Skills reload.

If the Codex CLI cannot be launched on the current surface, report that exact blocker. Do not work
around it by copying one nested Skill, because that produces a partial and unsupported install.

## Repository changes

Preserve the distinction between the complete plugin and its two bundled Skills. Installation
documentation, release archives, and tests must continue to install the plugin as one unit.
