# Persistence and Observability

V0.8 extends the local SQLite store with executions, artifacts, verifications, structured events, and provider usage.

## Audit trail

A task can now be represented as a sequence of structured events and durable execution records. Events are append-only records keyed by task ID; state objects use upsert semantics where appropriate.

## Provider usage

Provider usage stores provider/model, token counts, estimated cost, task ID, and timestamp so later reporting can calculate model and task consumption.

## Scope

SQLite remains the default local store. V0.8 does not introduce a remote database, dashboard, or distributed telemetry service.
