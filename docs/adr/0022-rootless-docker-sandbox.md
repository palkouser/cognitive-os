# ADR 0022: Rootless Docker sandbox

Status: Accepted

Untrusted development commands run through rootless Docker as UID 10001 with a read-only root,
network disabled, all capabilities dropped, no-new-privileges, bounded PIDs, memory, CPU, output,
and time, a tmpfs, and one writable task workspace. Docker sockets, host configuration, secrets,
devices, GPUs, privileged mode, and host namespaces are forbidden.
