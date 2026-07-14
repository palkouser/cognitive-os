# Verifier execution

```text
Controller -> Verifier Selection -> Verification Service -> Verifier
           -> Evidence Artifacts -> Verification Bundle
           -> Acceptance Policy -> Acceptance Decision
```

The service validates identity, capability, configuration, subject size, and timeout; persists start; executes once; bounds evidence; and persists one terminal result. Subject failures and verifier infrastructure failures remain distinct.
