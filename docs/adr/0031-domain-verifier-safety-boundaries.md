# ADR 0031: Domain verifier safety boundaries

Status: Accepted

Coding commands run only through `ToolExecutionService` and the rootless sandbox. Mathematical input is parsed through a strict Python-AST allowlist into a typed expression AST and manually converted to SymPy; `eval`, `exec`, unrestricted `sympify`, and unrestricted parser transformations are forbidden. Logic accepts only a typed Boolean/arithmetic AST and rejects raw SMT-LIB. Physics uses one internal Pint registry and never loads provider unit definitions. Host-enforced time and size bounds apply throughout.
