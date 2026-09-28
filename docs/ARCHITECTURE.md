# Rock V0.1 Architecture

## Runtime pipeline

```
Task
  -> provider selection
  -> parallel generation
  -> normalization
  -> critique
  -> synthesis
  -> verification
  -> persistence
```

## Boundaries

Rock owns the contracts in `src/rock/core`. Provider libraries are adapters.

V0.1 intentionally does not execute arbitrary tools, modify the host filesystem, or delegate to external agent frameworks.

## Provider model

The provider abstraction exposes a stable Rock interface. LiteLLM is the first gateway implementation; the application does not depend on LiteLLM-specific response objects outside the adapter.

## Council model

A Council is a protocol, not a model. Members can be changed through configuration, and failed members do not invalidate the entire run.

Consensus is not considered proof. Verification remains an explicit stage.

## Persistence

SQLite stores tasks, sessions and completed runs. The schema is intentionally small for V0.1 and can evolve without coupling the core contracts to a database ORM.

## Security direction

Future tools must pass through Rock permission policies. Tool execution is intentionally outside V0.1 so the security boundary can be designed before host actions are enabled.
