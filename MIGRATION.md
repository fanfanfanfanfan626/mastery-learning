# Migration from `mastery-learning`

Version 0.5.0 changes the product and Codex plugin identity to **Mastery Tutor** / `mastery-tutor`.
The two Skill IDs and learner data format do not change.

## What is preserved

- `mastery-coach` and `mastery-tool-creator` Skill identities;
- every learner workspace and its `.mastery/` directory;
- the portable `~/.mastery-learning` registry and legacy Codex registry discovery;
- existing evidence, sessions, review scheduling, generated tools, and curriculum state.

Do not rename or delete `.mastery/` directories. The old registry directory name is retained as a
data-compatibility boundary even though the product display name changed.

## Codex upgrade

The installer intentionally stops if `codex plugin list` still contains `mastery-learning`. This
prevents two copies of the same Skills from loading at once.

1. Record the stable path and version of the existing install.
2. Confirm that learner workspaces are outside the plugin directory.
3. Remove the old plugin through Codex's supported plugin command or UI.
4. Run `install.ps1` on Windows or `install.sh` on macOS/Linux from the 0.5.0 package.
5. Verify that `codex plugin list` contains `mastery-tutor` and no `mastery-learning` entry.
6. Start a new Codex task and resume an existing learning workspace.

Standalone copies under a host's Skills directory are separate conflicts. Show their exact paths
and obtain approval before moving them to a recoverable archive. Never delete learner data as part
of plugin migration.

## Rollback

Remove `mastery-tutor`, restore the previously recorded package, and start a new host session.
Learner state remains usable because version 0.5.0 does not relocate or rewrite it merely due to the
product rename. If a later schema migration is introduced, that release must document its own
forward and backward compatibility.
