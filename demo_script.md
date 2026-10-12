# Spot demo script

Click-by-click. Start the app with `python app.py` (every start is a clean demo), open http://localhost:8501, and click **Reset demo** (top bar) between rehearsals. All people and conversations are fictional.

Demo doc: `ops-uae-identity`, "UAE Identity Service Integration Scope" (Ops Automation, v1). v1 says the cutover is **November 14, 2026**. The seeded proposal moves it to **November 28, 2026**.

Demo question (ask it verbatim, every time): **"What is the cutover date for the UAE identity service?"**

---

## 1. Propose: the decision nobody wrote down

1. Top bar: **Signed in as → Marcus Chen (Ops Automation · Contributor)**.
2. Left list, **Chats → Cutover sync (call recap)**.
3. Say: "Yesterday Payments, Network and the program office decided on a call to move the UAE identity cutover two weeks. Nobody from Ops Automation was on it."
4. Point at Daniel's message: *"Decision from the call: the UAE identity service cutover is moving two weeks, from November 14 to November 28."*
5. Point at the system line: *"Sofia Alvarez added Marcus Chen and Priya Raman to the chat."* (after Sofia's angry ping in Program Office).
6. In Daniel's thread: Marcus replied **"@Spot add"**, and Spot answered in-thread: *"Proposal created: UAE identity service cutover moved two weeks. Routed to Payments (depends on Ops Automation)."* with the approval card.
7. On the card, point at **Changes**: November ~~14~~ **28**, the deadline, and **Routed to: Payments (depends on Ops Automation)**.
8. Optional: **Spot (rail) → Chat**, type `ask What is the cutover date for the UAE identity service?` Spot still answers **November 14**, v1, because the change isn't approved.

## 2. Review: only the dependent team can approve

1. **Signed in as → Priya Raman (Ops Automation · Approver)**.
2. On the same card, click **Approve**.
   - Blocked under the card: **"Only Payments can approve: Payments depends on Ops Automation"**.
3. Say: "Ops can't sign off its own change when Payments depends on it."
4. **Signed in as → Daniel Okafor (Payments · Approver)**. The **Activity** bell shows a badge; click it, then the request to jump to the thread.
5. Click **Approve** on the card. The card flips to **"✓ Approved by Daniel Okafor"** and Spot replies: *"Daniel Okafor approved. UAE Identity Service Integration Scope is now v2 and recorded in History."*

## 3. Merge: the answer moves with the approved doc

1. **Spot (rail) → Chat**, ask the demo question again.
2. Spot answers **November 28, 2026**, citing *UAE Identity Service Integration Scope · v2 · by Marcus Chen · approved by Daniel Okafor*.

## 4. Receipt: History, and what isn't binding

1. **Signed in as → Elena Rossi (Payments · Reader)**.
2. **Spot (rail) → History**. It opens on *UAE Identity Service Integration Scope*: **v2 · Current**, changed by Marcus Chen, approved by Daniel Okafor, deadline Oct 16, 2026; below it the v1 original.
3. Pick **UAE Payment Gateway Requirements** and click **Continue**. Under **"Not approved: not binding"**: *Pending: Move UAE gateway cutover up one week*, captured with "@Spot add" in the *UAE gateway readiness* chat but never approved.
4. Say: "History is the receipt. Payments is on the hook for the identity date because Daniel approved it. Nobody is on the hook for the gateway change, because nobody approved it."

## 5. Close: production path

"Everything you saw is a real Adaptive Card. In production Spot is a Teams bot: the same cards and Approve buttons work inside Microsoft Teams, roles come from Entra ID, and the dependency graph comes from Terraform and the service catalog." Optionally show the Adaptive Card mockup from Contributor 6's SOW.

---

**Reset between rehearsals:** top bar → **Reset demo**.
