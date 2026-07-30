# ADR 0088: The open-development data policy

- Status: Accepted
- Date: 2026-07-29
- Sprint: 21C3
- Stage gate: Gate C3 — Reality-Grade Learning Inputs
- Decision owners: project owner
- Relates to: [ADR 0087](0087-governed-provider-boundary-and-output-retention.md) (governed
  provider boundary and output retention), [ADR 0009](0009-apache-20-license.md) (Apache-2.0
  licence), [ADR 0035](0035-governed-memory-plane-authority.md) (governed Memory Plane
  authority)
- Amends: the provider-side data expectations recorded in ADR 0087. ADR 0087's authority
  table, retention modes, redaction order and secret-scan rules are unchanged.

## Context

Sprint 21C2 called three providers under a data policy that had never been written down as a
project decision. It was inferred from a single conservative default:
`OpenRouterProviderConfig.require_zero_data_retention = True` and
`allow_data_collection = False`, with a per-fixture exception recorded in the sprint report
for the one public advisory task.

That inference has three costs which Sprint 21C3 pays directly.

1. **The exception does not scale to a campaign.** C3 runs ten OpenRouter task attempts, ten
   Codex runs and ten Claude Code runs against generated, project-owned repair tasks. Under
   the C2 shape each of those needs a per-request operator waiver for material the project
   already publishes under Apache-2.0. A waiver that is granted every time is not a control;
   it is a prompt that trains the operator to click through.
2. **Zero-data-retention is a confidentiality answer to a question this project does not
   have.** ZDR protects material whose disclosure to the provider is itself the harm. The C3
   corpus is generated Python repair tasks, public issue descriptions, public benchmark
   cases and the project's own source. Disclosure is not the harm. The `openrouter/free`
   endpoints that C3 depends on for provider diversity are also the endpoints most likely to
   refuse a ZDR requirement, so a default aimed at confidentiality was silently acting as an
   availability constraint.
3. **"Open" was being conflated with "unrestricted".** Without a written classification, the
   only way to relax retention was to relax it everywhere, which would have swept in
   credentials. The two questions are different and need to be separated in writing before
   either can be answered.

## Decision

### Open-development data is a classification, and it is the project default

Cognitive OS is an open, non-enterprise development project. The following material is
**open-development data** and is classified `MemorySensitivity.PUBLIC` unless its own source
says otherwise:

- project-owned source code and documentation;
- generated task packages, fixtures, manifests and test repositories;
- task descriptions and public issue text;
- public benchmark data the project is licensed to use;
- provider prompts derived from any of the above;
- provider answers to those prompts;
- execution evidence: outcomes, verifier results, timings, diffs, statistics.

For open-development data, effective from Sprint 21C3:

| Question | Answer |
|---|---|
| Is zero data retention required? | No |
| May the provider collect the data? | Yes |
| May the project store it? | Yes |
| May the project share or publish it? | Yes |
| Is a per-request operator waiver required? | No |
| Is source licence and usage-rights evidence still required? | **Yes** |
| Is an independent verifier still required for correctness? | **Yes** |

The classification is a **project default expressed in configuration**, not a per-request
exception and not a Sprint 21C3 special case. A source that carries its own restriction
overrides the default; the default never overrides a source.

### What openness does not cover

The following are **never** open-development data, regardless of how the material around them
is classified:

- API keys, tokens, authorization headers, session cookies, bearer values;
- subscription and login identities, provider account material;
- any value the redaction layer of ADR 0087 targets;
- third-party data whose licence or terms restrict redistribution;
- undisclosed personal data.

ADR 0087's ordering is unchanged and remains mandatory: **redact, then scan the unredacted
value, then decide, then retain.** A failed secret scan still blocks `normalized_content`
retention. Openness is a statement about the *subject matter*; it grants no relief from the
credential boundary, and a document that treats it as such is wrong.

### Source rights remain an operator input

Relaxing confidentiality does not answer redistribution. `UsageRightsDecision` stays
`unknown | prohibited | verified` with an evidence hash, and stays an operator input.

The reason is that these are orthogonal: "we do not mind the provider seeing this" and "we
are licensed to redistribute this" are different claims about different risks, and a system
that inferred the second from the first would be marking its own homework — the exact failure
ADR 0087 names. A publicly readable file is not automatically a redistributable one, so **no
licence may be inferred from openness alone.**

### Data policy, cost policy and correctness policy are three policies

Relaxing the data policy relaxes nothing else. These remain independent and remain in force:

| Policy | Control | Unchanged by this ADR |
|---|---|---|
| Cost | `maximum_spend_usd = 0.0`, free-only routing | yes |
| Correctness | an independent verifier; a provider is never its own verifier | yes |
| Authority | providers stay advisory; no provider source kind enters `REAL_GOVERNED_SOURCE_KINDS` | yes |
| Credentials | redaction, secret scanning, zero credentials in Git or artifacts | yes |
| Live execution | enabled configuration **and** an explicit runtime flag | yes |

What this ADR removes is the *third* opt-in — the separate ZDR waiver or interactive
retention prompt — because it asked the operator to re-decide a decision this ADR makes once.
Two independent opt-ins for live execution remain, and collapsing those two into one is still
refused.

### Executable consequences

A policy with no executable consequence is a comment. This decision changes tracked
configuration:

- `OpenRouterProviderConfig.require_zero_data_retention` default becomes `False`;
- `OpenRouterProviderConfig.allow_data_collection` default becomes `True`;
- `config/providers.example.yaml` carries the relaxed project default, not a live-only
  override;
- the per-request ZDR waiver path is removed from the campaign entry point;
- provider campaign execution needs configuration plus one explicit `--live` flag, and no
  interactive dialogue per public-data call.

Those changes are delivered by work items S21C3-040 and S21C3-041 in wave W4 of Sprint 21C3.
Until they land, this ADR is accepted and the code still carries the C2 defaults; the gap is
recorded rather than hidden, and Gate C3 condition 2 does not pass until the configuration
agrees with this document.

## Alternatives considered

- **Keep ZDR mandatory and grant a per-campaign waiver.** Rejected: it is the C2 shape at
  larger scale. Thirty waivers for material published under Apache-2.0 is a control that
  exists to be dismissed, and it would keep `openrouter/free` availability coupled to a
  confidentiality setting that protects nothing here.
- **Classify open-development data as `internal` rather than `public`.** Rejected: `internal`
  would still permit retention under ADR 0087, so the practical effect is the same, but it
  would misdescribe material the project publishes and would leave a future reader unable to
  tell genuinely internal data apart from the corpus.
- **One global "open project" switch that also relaxes rights tracking.** Rejected: it
  merges confidentiality with redistribution. Source rights are the one question a
  self-improving system must not be allowed to answer for itself.
- **Amend ADR 0087 in place.** Rejected by the repository's own ADR convention: accepted ADRs
  are immutable except for status and supersession links, and a changed decision receives a
  new ADR.
- **Defer the decision to Sprint 21D1.** Rejected: C3's provider campaign is the first
  workload the C2 default actually obstructs, so deferring means running C3 under a policy
  the sprint has already outgrown.

## Consequences

Positive:

- one written project default replaces an unwritten inference plus a growing pile of
  per-request exceptions;
- the free OpenRouter endpoints C3 depends on stop being refused by a setting aimed at a risk
  this data does not carry;
- unattended local campaign execution becomes possible after one deliberate configuration
  step, which is what a single-maintainer project needs;
- the credential boundary is now stated separately from the confidentiality default, so
  relaxing one cannot silently relax the other.

Negative, and accepted:

- provider-side copies of open-development data exist and cannot be recalled; this is
  accepted for material the project publishes anyway, and it is the reason the classification
  is written down rather than assumed;
- a future genuinely-confidential workload must set its configuration explicitly instead of
  inheriting a strict default, so the strict path is no longer the lazy path for that case;
- every document that mentions the C2 per-fixture ZDR exception now needs a supersession
  note, and one that is missed will read as current policy.

## Verification

- configuration tests assert the two relaxed OpenRouter defaults and that
  `config/providers.example.yaml` parses to them without a live-only override;
- a test asserts that no campaign path requires an interactive retention prompt, and that
  live execution still requires both the configuration opt-in and the explicit runtime flag;
- the existing adversarial redaction and secret-scan fixtures run unchanged and still block
  `normalized_content` retention on a failed scan — openness must not move them;
- a test asserts that `UsageRightsDecision` is not derivable from sensitivity: a `public`
  item with `unknown` rights is still refused for corpus destinations requiring verified
  rights;
- the repository secret scan and `scripts/verify_artifact_store.sh` continue to run over C3
  campaign evidence.

## References

- Sprint 21C3 technical backlog, §0.3 and §4.13:
  `docs/sprints/sprint-21/sprint-21c3-technical-backlog.md`
- Sprint 21C3 handoff, §3: `docs/sprints/sprint-21/sprint-21c3-handoff.md`
- Project owner's open-development data-policy decision, 2026-07-29
- OpenRouter data-collection and zero-data-retention policy documentation
