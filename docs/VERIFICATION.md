# Verification and Correction

V0.7 introduces a reusable bounded verification loop.

The loop performs at most three verification attempts, even when a larger value is requested. A failed verification may invoke a correction callback before the next attempt. If all attempts fail, the last verified state and findings are returned for escalation.

Tool execution uses the verification primitive to validate successful handler completion. More sophisticated semantic verification can be attached by higher-level workflows.

The existing Council verification remains responsible for model-level synthesis verification; this component provides the reusable execution/workflow primitive rather than replacing that logic.
