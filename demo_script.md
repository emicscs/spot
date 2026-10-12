# Spot demo script

Click-by-click against the real app (`app.py` with `USE_FAKES = False`, the real `db`/`governance`/`rag`). Run `http://localhost:8501`, use the account menu (top right) to switch users, and **Reset demo** from that same menu before each rehearsal.

Demo doc: `ops-uae-identity` — "UAE Identity Service Integration Scope" (Ops Automation, v1, author **bob**, approver **alice**). Current content states the cutover date as **November 14, 2026**.

Demo question (type it verbatim, every time): **"What is the cutover date for the UAE identity service?"**

The UI is a Teams chat: a **Spot** DM (talk to it directly, no @mention needed) plus **Ops Automation** and **Payments** group chats (mention **@Spot** there). Cards (propose form, approval request, history, answer) render inline as real Adaptive Cards.

---

## 1. Propose

1. Account menu (top right): switch to **bob**. Toast: "Signed in as bob · Ops Automation Contributor".
2. Open the **Spot** chat (left rail, top item — it's the default). Type the demo question and send.
   - Spot replies with an Answer card: cutover date **November 14, 2026**, sources chip *UAE Identity Service Integration Scope · v1 · by bob · approved by alice*.
3. In the same **Spot** chat, type `propose identity` and send.
   - Spot opens a **Propose a change** card for "UAE Identity Service Integration Scope", showing "Current: v1, approved by alice."
4. In the **New content** field, edit the cutover sentence from "...scheduled for November 14, 2026." to "...scheduled for **November 28, 2026**." (leave the rest of the paragraph unchanged).
5. **What changed and why**: type exactly — `Cutover moved two weeks per Infra meeting 10/9`
6. **Approval needed by**: leave the default (`2026-10-19` — today + 7 days).
7. Click **Submit for approval**.
   - Spot replies in the DM: **"Routed to Payments (depends on Ops Automation). I've asked them in the Payments chat."**
   - The same approval-request card is posted into the **Payments** group chat.
8. Still as bob, ask the demo question again in the **Spot** DM.
   - Spot still answers **November 14, 2026**, v1 — the pending proposal is never used in answers.

## 2. Review

1. Account menu: switch to **alice** (Ops Automation · Approver).
2. Open the **Payments** chat. Find the card: **"Approval requested from Payments"**, summary "Cutover moved two weeks per Infra meeting 10/9", facts: Document / Proposed by bob / Deadline 2026-10-19 / Routed to Payments (depends on Ops Automation).
3. Click **Approve**.
   - Blocked, shown inline under the card: **"Only Payments can approve: Payments depends on Ops Automation (alice is on Ops Automation)."** Alice's own team cannot approve a change that another team depends on.
4. Account menu: switch to **dave** (Payments · Approver).
5. Open the **Payments** chat — same card. Point out the side-by-side diff columns: CURRENT · APPROVED ("...November 14, 2026...") vs. PROPOSED ("...November 28, 2026...") with the changed line highlighted.
6. Click **Approve**.
   - Spot posts: **"dave approved. UAE Identity Service Integration Scope is now v2 and recorded in History."**
   - The card itself updates in place: title turns green — "Approved by dave" — with the line "✅ Binding now. UAE Identity Service Integration Scope is v2, changed by bob, approved by dave."

## 3. Merge

1. Account menu: switch back to **bob** (or stay as dave — same approved content either way).
2. In the **Spot** DM, ask the exact same demo question again.
   - Spot now answers **November 28, 2026**, sources chip *UAE Identity Service Integration Scope · v2 · by bob · approved by dave*.
3. Say the line: "Same question, same chat — the answer moved because the doc moved. v2, changed by bob, approved by dave."

## 4. Receipt

1. Account menu: switch to **carol** (Payments · Reader).
2. In the **Spot** DM, type `history identity` and send.
   - History card: "UAE Identity Service Integration Scope", "Ops Automation · current v2, approved by dave." One row: **v2 · CURRENT**, summary "Cutover moved two weeks per Infra meeting 10/9", "changed by bob · approved by dave · 2026-10-12 · deadline 2026-10-19." (v1 does not get its own row — History only records approved *changes*, and v1 was the seeded starting state, never itself an approved proposal.)
   - Point out: carol is a Reader and never touched Approve/Reject — this is a read-only receipt. History is the receipt: a team is only on the hook for changes it approved.
3. Type `history gateway` and send — the *other* UAE doc.
   - No approved-version rows at all (same reason — v1 is seed data, nothing has been approved on this doc yet). Straight to **"NOT APPROVED: NOT BINDING"** — "**Pending:** Move UAE gateway cutover up one week" / "proposed by bob · needs Payments · deadline 2026-11-01T17:00:00Z · Not approved: not binding."
4. Say the line: "Two UAE docs, two different states — one merged, one still pending. Spot never lets a pending change answer a question or count as a decision."

## 5. Close: Teams Adaptive Card

1. Switch to the mockup image: `assets/adaptive_card_mockup.png`.
2. Say: "Every card you just saw was a real Adaptive Card, rendered inside this app. In production, Payments doesn't open Spot to find it — this is pushed straight into their Teams channel the moment it routes, same card, same buttons."
3. Card text (verbatim): *"Approval requested from Payments: UAE cutover scope change (Payments depends on Ops Automation). Deadline: 2026-10-19. Approve / Reject"*
4. Close: "Propose, route, block the wrong approver, approve, and the receipt — all four of those just happened inside Teams, not a separate tool."
