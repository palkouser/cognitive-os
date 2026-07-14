# Donor project registry

## Sprint 6 controller design references

LangGraph, Pydantic AI, and LightFlow were reviewed for stateful workflow, interrupt,
structured-output, human-approval, retry, checkpoint, and resume patterns. Their usage is
pattern-only: none is a runtime dependency and none owns authoritative state. Public
checkpoint restoration and trust-binding concerns reinforce typed checkpoint validation and
explicit continuation scope. Cognitive OS retains its event store, provider execution, Tool
Plane, approval, artifact, telemetry, replay, and recovery boundaries.

| Project | Repository | License | Reviewed commit | Role | Imported files | Adapted concepts | Modifications | Audit status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LightAgent | https://github.com/wanxingai/LightAgent | Apache-2.0 | `8ea4db3c9d8791e0977eea2a4481824441b4ba82` | Runtime foundation | Upstream repository snapshot | Agent loop, tool calling, workflows, hooks, tracing, provider integration | Translated README files removed. Sprint 1 adds narrow lazy imports for MCP and boto3 so optional integrations do not enter the core environment; no runtime behavior changes when their extras are installed. | Contract-tested |

Imported donor source may retain its original-language comments and messages. New and
modified Cognitive OS-owned content remains English-only, and donor exceptions stay within
the registered upstream boundary.
