# Spot demo script

Click-by-click. Run against a freshly reset database (sidebar → **Reset demo**) before each rehearsal.

Demo doc: `ops-uae-identity` — "UAE Identity Service Integration Scope" (Ops Automation, v1, author **bob**, approver **alice**). Current content states the cutover date as **November 14, 2026**.

Demo question (ask it verbatim, every time): **"What is the cutover date for the UAE identity service?"**

---

## 1. Propose

1. Sidebar: select user **bob**. Sidebar shows "**Ops Automation** · Contributor".
2. Tab **Ask Spot** (Chat). Type the demo question and click **Ask**.
   - Spot answers from v1: cutover date **November 14, 2026**, cited as *UAE Identity Service Integration Scope · v1 · by bob · approved by alice*.
3. Tab **Approvals** (Pending). Expand **Propose a change**.
4. Doc picker: select **UAE Identity Service Integration Scope (v1)**.
5. In **New content**, edit the cutover sentence from "November 14, 2026" to "**November 28, 2026**" (keep the rest of the paragraph unchanged).
6. **Summary of the change**: type exactly — `Cutover moved two weeks per Infra meeting 10/9`
7. **Approval deadline**: `2026-10-19`
8. Click **Propose**.
   - App shows: **"Proposal sent. Routed to: Payments (depends on Ops Automation)."**
9. Back in **Ask Spot**, ask the demo question again as bob.
   - Spot still answers **November 14, 2026**, v1 — the pending proposal is never used in answers.

## 2. Review

1. Sidebar: switch user to **alice** ("Ops Automation · Approver").
2. Tab **Approvals**. Find the card: **"Approval requested from Payments"**, subtitle "Cutover moved two weeks per Infra meeting 10/9", facts: Document / Proposed by bob / Deadline 2026-10-19 / Routed to Payments (depends on Ops Automation).
3. Click **Approve**.
   - App blocks it: **"Blocked: Only Payments can approve: Payments depends on Ops Automation."** Alice's own team cannot approve a change that another team depends on.
4. Sidebar: switch user to **dave** ("Payments · Approver").
5. Tab **Approvals**. Same card is visible to dave. Point out the side-by-side diff: old (v1, "November 14, 2026") vs. proposed ("November 28, 2026") with the changed line highlighted.
6. Click **Approve**.
   - App shows: **"Approved by dave: UAE Identity Service Integration Scope is now v2."**

## 3. Merge

1. Sidebar: switch user back to **bob** (or stay as dave — same approved content either way).
2. Tab **Ask Spot**. Ask the exact same demo question again.
   - Spot now answers **November 28, 2026**, citing *UAE Identity Service Integration Scope · v2 · by bob · approved by dave*.
3. Say the line: "Same question, same chat — the answer moved because the doc moved. v2, changed by bob, approved by dave."

## 4. Receipt

1. Sidebar: switch user to **carol** ("Payments · Reader").
2. Tab **History**. Document picker: select **UAE Identity Service Integration Scope (Ops Automation)**.
   - "Approved versions" table shows v2: Changed by **bob**, Approved by **dave**, Summary "Cutover moved two weeks per Infra meeting 10/9", Deadline 2026-10-19.
   - Point out: carol is a Reader and never touched Approve/Reject — this is a read-only receipt. History is the receipt: a team is only on the hook for changes it approved.
3. Same picker: select **UAE Payment Gateway Requirements (Ops Automation)** — the *other* UAE doc.
   - "Approved versions" shows only v1 (nothing merged).
   - Below it, "Not approved: not binding" shows the pending proposal: "Move UAE gateway cutover up one week" · proposed by bob · needs Payments · deadline 2026-11-01. Label reads exactly **"Pending · Not approved: not binding."**
4. Say the line: "Two UAE docs, two different states — one merged, one still pending. Spot never lets a pending change answer a question or count as a decision."

## 5. Close: Teams Adaptive Card

1. Switch to the Adaptive Card mockup (screenshot, not the live app): `assets/adaptive_card_mockup.png`.
2. Say: "In Teams, this never lives inside a tab you have to go find — Payments gets this pushed straight into their channel the moment it routes."
3. Card text (verbatim): *"Approval requested from Payments: UAE cutover scope change (Payments depends on Ops Automation). Deadline: 2026-10-19. Approve / Reject"*
4. Close: "Propose, route, block the wrong approver, approve, and the receipt — all four of those just happened inside Teams, not a separate tool."
