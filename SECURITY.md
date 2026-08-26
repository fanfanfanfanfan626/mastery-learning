# Security policy

## Supported versions

Security fixes are provided for the latest released version. Development snapshots may change
without migration guarantees.

## Security boundaries

Mastery Tutor can write learner-owned files, run its bundled Python utilities, generate local HTML,
and—in supported hosts—observe learner code. These capabilities are intentionally constrained:

- classrooms and tools are local artifacts with no analytics or remote runtime dependency;
- local web content binds to `127.0.0.1` on a dynamically selected port;
- generated tools use content hashes, verification reports, and stale/rejected states;
- paths, symlinks, junctions, external commands, local references, and cleanup instructions are
  validated before a tool can be treated as verified;
- learner code is not executed by a static validator;
- deletion is limited to an explicitly selected workspace or install target and never includes
  learner records during ordinary uninstall or upgrade.

A Skill file is executable instruction material. Review a Release and its checksum before installing
it, especially when an AI agent has command execution access. Compatibility with a host does not
grant that host permission to weaken these boundaries.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for the repository. Include the affected
version, host and version, operating system, minimal reproduction, impact, and whether learner data
or code execution is involved. Do not post working exploits or private learner records in a public
issue.

General bugs belong in the public issue tracker; support questions belong in [SUPPORT.md](SUPPORT.md).
