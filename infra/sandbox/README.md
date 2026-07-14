# Sprint 5 sandbox image

The sandbox uses Python 3.12 slim Bookworm pinned to OCI index digest
`sha256:d50fb7611f86d04a3b0471b46d7557818d88983fc3136726336b2a4c657aa30b`,
resolved on 2026-07-14. It runs as UID/GID 10001 and contains pinned pytest, Ruff, and
MyPy versions. Runtime invocations add a read-only root, disabled network, dropped
capabilities, no-new-privileges, bounded resources, and one task workspace mount.
