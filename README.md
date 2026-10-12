# Spot

Version control for project requirements, for a Mastercard program with many interdependent teams.

- A change to a requirements doc is a **proposal** (like a pull request).
- It is routed to the teams that depend on the doc's team (like CODEOWNERS).
- Only an **Approver** on that team can approve or reject it.
- Approval creates a new doc version and a **history** row (like a commit). History is the receipt: a team is only on the hook for changes it approved.
- **Chat** answers questions from the current *approved* docs only. Pending proposals are never used in answers.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in LLM_API_KEY and LLM_MODEL
```

## Run

```bash
streamlit run app.py
```

## Contract

Read [CONTRACTS.md](CONTRACTS.md) before writing any code. It is frozen: nobody changes it.

| File | Owner |
|---|---|
| db.py | Person 1 |
| seed.py | Person 2 |
| governance.py | Person 3 |
| rag.py | Person 4 |
| app.py | Person 5 |
| demo_script.md, SOW, integration | Person 6 |
| config.py | shared, do not edit |
