# Verification-Driven Python Repair

Apply the smallest Python repair supported by failing verifier evidence. Use registered workspace,
tool, and verifier capabilities only. Do not weaken tests or broaden permissions.

1. Reproduce the focused failure.
2. Patch the smallest relevant surface.
3. Run focused verification, then the required broader checks.
