# Donor code policy

Third-party code may be imported only when all of the following are true:

1. The license is known and compatible with Apache-2.0.
2. The reviewed repository, commit, source file, and original URL are recorded.
3. Imported files and subsequent modifications are identified.
4. Tests cover the imported or adapted behavior.
5. A normal library integration is not a simpler option.
6. The architectural benefit and rejected alternatives are documented.

Every donor review must update `docs/architecture/donor-projects.md`. Unknown-origin
snippets, generated code without provenance, and code copied from incompatible sources
must not enter the repository.
