# Logic verifiers

The typed AST supports Boolean, integer, and real values with a closed operator set. Mapping to Z3 is manual. SAT, UNSAT, and UNKNOWN remain distinct; UNKNOWN never passes. Solver time, AST size, depth, variable count, constraint count, and counterexample output are bounded. Raw SMT-LIB and provider solver options are forbidden.
