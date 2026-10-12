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

Open http://localhost:8501. The UI looks like Microsoft Teams: chat with **Spot** directly, or mention **@Spot** in the Ops Automation and Payments group chats. Switch demo users from the avatar menu (top right), which also has **Reset demo**.

## Contract

Read [CONTRACTS.md](CONTRACTS.md) before writing any code. It is frozen: nobody changes it.

| File | Owner |
|---|---|
| db.py | Contributor 2 |
| seed.py | Contributor 3 |
| governance.py | Contributor 4 |
| rag.py | Contributor 5 |
| app.py | Contributor 1 |
| demo_script.md, SOW, integration | Contributor 6 |
| config.py | shared, do not edit |
