# ADR 0033: External evaluation adapters

Status: Accepted

Inspect AI is an optional exporter and SWE-bench is a metadata adapter. Neither owns acceptance, events, artifacts, providers, tools, or benchmark state. Imports never download datasets, clone repositories, apply gold patches, or execute tasks. Dataset source, revision, and license are mandatory; protected evaluation data is excluded from provider-visible context.
