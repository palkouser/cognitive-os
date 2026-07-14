# Development machine baseline

- Initial capture: 2026-07-13
- Remediation capture: 2026-07-14 (Europe/Budapest)
- Sprint items: S0-00 and S0-01

## Hardware and operating system

| Component | Observed value |
| --- | --- |
| CPU | AMD Ryzen 7 5700X, 8 cores / 16 threads |
| RAM | 45 GiB usable |
| GPU | NVIDIA GeForce RTX 5070 Ti, PCI ID `10de:2c05` |
| Swap | `/swap.img`, 8 GiB |
| OS | Ubuntu 26.04 LTS (`resolute`), x86-64 |
| Kernel | `7.0.0-27-generic` |
| System Python | 3.14.4; must not receive project packages |
| Project Python | 3.12.13, managed by uv in `.venv` |
| uv | 0.11.28 |

## Storage

| Device | Model | Size | Filesystem | Mount point | Free space / status |
| --- | --- | --- | --- | --- | --- |
| `/dev/nvme0n1p1` | WDC WDS100T2B0C-00PXH0 | 931.5 GiB | ext4 | `/home/palkouser/projekt` | about 869 GiB free |
| `/dev/nvme1n1p4` | KINGSTON SNV3S1000G | 732.4 GiB partition | ext4 | `/` | about 647 GiB free at initial capture |
| `/dev/sda2` | WDC WD40EZAZ-00SF3B0 | 3.6 TiB | exFAT | `/home/palkouser/backup` | about 2.6 TiB free |

Linux block-device names changed between boots; UUID and mount point are the stable
identifiers. The project filesystem UUID is
`8dc2a866-c844-4f76-bdfd-a615b421c7f0`. The archive filesystem UUID is `F65E-FC00`.

The project directory is owned by `palkouser:palkouser` and is writable. The required
150–200 GB NVMe reserve is available. The execution sandbox exposes a duplicate
read-only/read-write project mount view, but direct repository writes and tests succeed.

## Archive baseline

- Persistent mount: `/home/palkouser/backup`
- Backing device: `/dev/sda2`, separate physical 4 TB HDD
- Filesystem: exFAT
- `/etc/fstab`: `UUID=F65E-FC00 /home/palkouser/backup exfat defaults,uid=1000,gid=1000,umask=007,nofail 0 0`
- Archive root: `/home/palkouser/backup/cognitive-os-archive`
- Archive hierarchy: database backups, trace archives, artifacts, releases, model archives,
  source snapshots, and recovery
- Read/write test: passed on 2026-07-14
- Source snapshot: `source-snapshots/sprint0-remediation-test.tar.gz`, validated with
  `tar -tzf`; SHA-256 sidecar created
- Reboot persistence: fstab entry exists, but post-remediation reboot verification remains
  a manual closure check

Because exFAT applies mount-wide permission masks, the requested mode 0750 is represented
by the mount's effective 0770 permissions (`umask=007`).

## Host tool baseline

Verified available:

- Git 2.53.0
- jq 1.8.1
- ripgrep 15.1.0
- uv 0.11.28
- build-essential, ca-certificates, curl, wget, make, and pkg-config

Installed and verified on 2026-07-14:

- Git LFS 3.7.1 (initialized)
- fd-find 10.3.0 with `~/.local/bin/fd` symlink
- tree 2.3.1
- ShellCheck 0.11.0
- smartmontools 7.5
- nvme-cli 2.16
- tmux 3.6a
- GitHub CLI 2.96.0

The exact manual installation and verification commands are in
`docs/operations/sprint-0-host-remediation.md`. Codex did not run `sudo` or install host
packages, in accordance with `AGENTS.md`. GitHub CLI is installed, but its saved token was
invalid at the final automated check; interactive re-authentication is required before push.

## NVIDIA baseline

- GPU is detected and uses the `nvidia` kernel driver.
- Ubuntu's recommended `nvidia-driver-595-open` version 595.71.05 is installed.
- `nvidia`, `nvidia_modeset`, `nvidia_drm`, and `nvidia_uvm` modules are loaded.
- nouveau is not loaded.
- Secure Boot is disabled.
- Host `nvidia-smi` succeeds with exit code 0 and reports 16,303 MiB VRAM.
- CUDA Toolkit 12.4 is present on the host, although it is not required by Sprint 0 and is
  not used by the Sprint 0 test suite.

The original failures in `nvidia-diagnostics-before.txt` and
`nvidia-before-remediation.txt` were captured inside the Codex workspace sandbox, where
`/dev/nvidia*` is intentionally hidden. The authoritative unsandboxed host result is stored
in `docs/baseline/generated/nvidia-host-verification.txt`. No driver reinstall, package
upgrade, initramfs update, or reboot was necessary.

## GitHub repository

- Expected repository: `https://github.com/palkouser/cognitive-os.git`
- Local `origin`: configured to the expected URL
- Remote reachability: verified; repository currently contains no refs (empty)
- `upstream`: `https://github.com/wanxingai/LightAgent.git`
- First push remains an explicitly manual operation in the closure plan

## Remaining machine-level closure checks

1. Complete `gh auth login -h github.com` interactively and verify `gh auth status`.
2. Confirm both fstab mounts after a real reboot; the archive mount and read/write path are
   already operational in the current boot.
3. `nvme list` succeeds and detects both NVMe devices. `smartctl --scan` detects the disks
   outside the sandbox, but reading SMART health requires administrator permission; run the
   health queries manually with `sudo smartctl`.
