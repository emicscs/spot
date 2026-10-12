# Spot — Statement of Work (Production Path)

Sections owned by Aarnav per `CONTRACTS.md`. These describe how the hackathon prototype (SQLite, hardcoded users, Streamlit buttons, a hand-seeded `team_dependencies` row) becomes the production system inside the Mastercard program. Sections 1–6, 8–11 and 14 are tracked separately and are out of scope here.

## 7. Technical Architecture — Data Platform

The prototype's `db.py` is a single SQLite file (`docs`, `proposals`, `history`, `team_dependencies`) accessed through two helpers, `execute` and `query`. The schema is already the right shape; it is the storage engine that does not survive contact with a multi-team, always-on program.

- **Target**: Azure SQL Database as the default (relational schema, strong consistency for the approve-in-one-transaction guarantee in `governance.approve`), with Azure Cosmos DB as the alternative if teams/doc counts grow large enough to need multi-region active-active writes and the transactional guarantee can move to Cosmos's multi-document transaction batch within a single partition.
- **Migration**: the four tables map 1:1 onto Azure SQL tables; no schema redesign is needed, only a driver swap (`pyodbc`/`azure-sql` client instead of `sqlite3`) behind the existing `get_conn`/`execute`/`query` contract.
- **Transactions**: `governance.approve()`'s single-transaction update (docs + history + proposal status) becomes a SQL `BEGIN TRAN` / `COMMIT`, preserving the current all-or-nothing guarantee.
- **Durability & recovery**: point-in-time restore and geo-redundant backup replace the gitignored, un-backed-up `spot.db` file; `history` becomes the audited system of record instead of a table that disappears if the file is deleted.
- **Access**: database access via Azure Private Link from the app's hosting environment only; no public endpoint.

## 12. Security — Identity & Access Management

The prototype's `USERS` dict in `db.py` hardcodes four accounts and their team/role. That is correct for a timeboxed demo and wrong for anything with real approvers.

- **Target**: Microsoft Entra ID as the identity provider, with Teams SSO (on-behalf-of flow) so a user is never prompted to log in a second time inside the Teams client.
- **Roles**: the current `role` column (`Reader` / `Contributor` / `Approver`) maps to Entra ID app roles declared in the app registration manifest, assigned per team via Entra ID security groups — one group per team (e.g. `spot-ops-automation-approvers`), mirroring the `team` + `role` pair the prototype hardcodes today.
- **Team membership**: `get_user(name).team` is replaced by the caller's Entra ID group membership, resolved from the validated AAD token on each request; no code path trusts a client-supplied team or role.
- **Authorization boundary**: the permission checks in `governance.propose`/`approve`/`reject` are unchanged in *shape* (role check + team-matches-required_team check) — only the source of `role` and `team` changes, from a dict literal to a token claim.
- **Audit**: every `approve`/`reject` call is attributed to an Entra ID object ID in `history.approved_by`/`changed_by`, not a free-text username, closing the gap where a display name could collide or be spoofed.

## 13. Integration — Approval Notifications via Teams Adaptive Cards

The prototype surfaces pending proposals as in-app cards inside a Streamlit tab styled to look like Teams; a user only sees one if they happen to open Spot.

- **Target**: real Microsoft Teams Adaptive Cards (schema 1.5), pushed proactively into the required-team Approver's Teams chat or channel via the Bot Framework and Microsoft Graph the moment `governance.propose()` computes `required_team` — the same routing logic, just delivered instead of waited-for.
- **Card contract**: the same facts shown in the current Streamlit card (Document, Proposed by, Deadline, Routed-to reason) become the Adaptive Card's `FactSet`; Approve/Reject become `Action.Execute` buttons that call the same `governance.approve`/`reject` functions behind an API, not a new code path.
- **In-place refresh**: on Approve/Reject, the card refreshes via a Universal Action response instead of a page rerun — the approver sees "Approved by dave — now v2" replace the buttons in the same card, matching the `st.session_state.flash` behavior in the prototype's `app.py`.
- **Permission errors stay visible**: a blocked action (wrong team, wrong role) returns a card-level error message using the exact `PermissionError` text `governance.py` already raises (e.g. "Only Payments can approve: Payments depends on Ops Automation") — no new copy to write, just a new delivery surface.

## 15. Deployment — Dependency Graph and Regional Topology

The prototype's routing logic depends entirely on one hand-seeded row in `team_dependencies`: `("Payments", "Ops Automation")`. That is accurate for a two-team demo and does not scale to a program with many interdependent teams.

- **Target**: the dependency graph is generated, not hand-maintained — sourced from Terraform state (team/service ownership tags already present on provisioned infrastructure) and cross-checked against the internal service catalog, so `team_dependencies` becomes a materialized, regularly-refreshed view rather than a table someone edits by hand.
- **Sync**: a CI pipeline step parses `terraform show -json` output plus the service catalog's ownership metadata on every merge to the infra repo, diffs it against the current `team_dependencies` table, and writes the delta — the same `required_team = first dependent team` rule in `governance.propose` runs unchanged against graph data instead of seed data.
- **Regional deployment**: production hosting is in-region in Azure UAE (UAE North / UAE Central), co-located with the Ops Automation and Payments teams this scope change concerns, for both latency and Mastercard's regional data-residency requirements — approved content and history, which are the audited record of what each team signed off on, do not leave the region.
- **Scale note**: today's `required_team = first dependent team, else the doc's own team` rule is deliberately simple for a two-team demo; with a real dependency graph, teams with more than one dependent will need an explicit routing decision (e.g. route to all dependents, or to a designated primary) — flagged here as a known gap, not solved in this SOW.
