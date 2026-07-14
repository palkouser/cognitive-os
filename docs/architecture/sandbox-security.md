# Sandbox security

The pinned rootless Docker image runs as UID/GID 10001. Runtime restrictions include a read-only
root, disabled network, dropped capabilities, no-new-privileges, resource limits, tmpfs, and one
task workspace. Host secrets, devices, GPUs, Docker sockets, and privileged namespaces are absent.
