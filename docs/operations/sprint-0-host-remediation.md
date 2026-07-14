# Sprint 0 host remediation

These host-level commands must be run manually by the machine owner. Project automation
must not invoke `sudo`, modify `/etc/fstab`, install drivers, or reboot the workstation.

## Host tools status on 2026-07-14

```text
Installed: git-lfs fd-find tree shellcheck smartmontools nvme-cli tmux gh
Authentication pending: gh
```

Install and verify:

```bash
gh auth login -h github.com
gh auth status
./scripts/check_host_prerequisites.sh
```

The Ubuntu packages, Git LFS initialization, fd symlink, and GitHub CLI installation are
complete. The saved GitHub token was invalid during the final automated check, so only
interactive re-authentication remains.

`nvme list` successfully detects both NVMe drives. Complete the SMART health capture with:

```bash
sudo smartctl -H /dev/nvme0
sudo smartctl -H /dev/nvme1
sudo smartctl -H /dev/sda
```

## NVIDIA driver

Observed state:

- GeForce RTX 5070 Ti detected at PCI `2b:00.0`.
- Recommended `nvidia-driver-595-open` 595.71.05 is installed and its modules are loaded.
- Secure Boot is disabled and nouveau is not loaded.
- An unsandboxed host check reports `nvidia-smi` exit code 0, driver 595.71.05, and the
  RTX 5070 Ti with 16,303 MiB VRAM.

The earlier exit code 9 was caused by the Codex sandbox hiding `/dev/nvidia*`; it was not a
host driver fault. Kernel module, NVML library, userspace tools, and installed packages all
use version 595.71.05.

No NVIDIA remediation command is required. Do not run a driver purge, reinstall,
initramfs update, or reboot solely because of the sandbox result. The authoritative
evidence is `docs/baseline/generated/nvidia-host-verification.txt`.

The recovery path below is retained only for a future real host failure:

```bash
sudo apt update
sudo apt install -y ubuntu-drivers-common linux-headers-"$(uname -r)"
sudo apt upgrade
sudo reboot
```

After reboot, run `nvidia-smi`. Only if it still fails, use the Ubuntu-managed driver path:

```bash
ubuntu-drivers list
sudo ubuntu-drivers install
sudo reboot
```

Do not install an NVIDIA `.run` package and do not blacklist nouveau: nouveau was not
loaded in the captured failure state. After any future recovery, run
`./scripts/collect_nvidia_diagnostics.sh after` from a normal host terminal.

## Archive mount

`/home/palkouser/backup` is already backed by `/dev/sda2` (exFAT, UUID `F65E-FC00`) and
has an `/etc/fstab` entry. The archive hierarchy and source snapshot have been created.
Reboot persistence still requires a manual reboot verification.
