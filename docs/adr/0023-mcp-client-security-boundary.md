# ADR 0023: MCP client security boundary

Status: Accepted

Sprint 5 uses the stable MCP v1 SDK and explicitly configured local STDIO servers only. Commands
are argument arrays, environments are allowlisted, and automatic installation is forbidden. MCP
descriptions, annotations, schemas, and outputs are untrusted. Discovered tools are namespaced,
default to R2, and use the same validation, policy, approval, persistence, timeout, and artifact
path as built-in tools. Remote transports, OAuth, resources, prompts, and sampling are deferred.
