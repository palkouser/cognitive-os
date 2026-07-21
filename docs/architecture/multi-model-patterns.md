# Bounded multi-model patterns

Supported patterns are `single_model`, `primary_with_fallback`, `planner_executor`,
`generator_critic`, and `multiple_proposals_with_verifier_selection`. Each role has a separate
routing decision, provider request, Context Bundle, result reference, and Controller step.

The effective call, token, tool, time, and cost budget is the minimum of Controller, routing policy,
strategy, and pattern budgets. A timeout after an uncertain side effect blocks blind fallback. A
planner proposes a plan, a critic provides evidence, and proposal models produce candidates; only
the existing Controller and registered verifiers can authorize execution or final acceptance.
