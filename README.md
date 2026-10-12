# Spot

Version control for project requirements, for a Mastercard program with many interdependent teams.

- A change to a requirements doc is a **proposal** (like a pull request).
- It is routed to the teams that depend on the doc's team (like CODEOWNERS).
- Only an **Approver** on that team can approve or reject it.
- Approval creates a new doc version and a **history** row (like a commit). History is the receipt: a team is only on the hook for changes it approved.
- **@Spot ask** answers questions from the current *approved* docs only. Pending proposals are never used in answers.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in LLM_API_KEY and LLM_MODEL
```

## Run

```bash
python app.py
```

Open http://localhost:8501. The UI is a Microsoft Teams lookalike for a fictional Mastercard workspace (all people and conversations are fictional; see `workspace.py`). Mention **@Spot** in any channel or chat, or open **Spot** in the left rail for Pending, History and Chat. Switch demo users with **Signed in as** in the top bar; **Reset demo** restores the seed data.

Demo users: Marcus Chen (Ops Automation, Contributor), Priya Raman (Ops Automation, Approver), Daniel Okafor (Payments, Approver), Elena Rossi (Payments, Reader). Walkthrough: [demo_script.md](demo_script.md).

## Contract

Read [CONTRACTS.md](CONTRACTS.md) before writing any code. It is frozen: nobody changes it.

| File | Owner |
|---|---|
| db.py | Contributor 2 |
| seed.py | Contributor 3 |
| governance.py | Contributor 4 |
| rag.py | Contributor 5 |
| app.py, static/, workspace.py | Contributor 1 |
| demo_script.md, SOW, integration | Contributor 6 |
| config.py | shared, do not edit |
