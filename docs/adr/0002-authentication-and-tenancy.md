# ADR 0002: Authentication and tenant context

## Decision

Use short-lived signed JWT access tokens with Argon2id password hashes. The
server loads the active user for each protected request and derives tenant,
role, and division scope from that trusted identity.

## Consequences

Routes never trust client-supplied tenant IDs. Refresh-token support is
deferred until session UX and revocation requirements are confirmed.
