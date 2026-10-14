# Spot

Version control for project requirements.

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

In the project-root `.env`, set `LLM_API_KEY` to your provider's API key.
`LLM_BASE_URL` can stay blank for OpenAI; other compatible providers need their
endpoint here. `LLM_MODEL` must name a model available from that provider.

To use an existing SQLite database, place it at `spot.db` in the project root,
or set `DB_PATH` in `.env` to its path. Startup preserves existing data and
seeds an empty database. **Reset demo** replaces the database with sample data.
It asks for confirmation before replacing documents, proposals, history, and chats.
Both `.env` and `spot.db` are gitignored.

## Run

```bash
python app.py
```

The workspace includes local profile portraits, searchable conversations and approved
files (Ctrl/Cmd + K), member profiles, conversation drafts, and responsive navigation.
Chats show messages and quoted replies in time order; channels retain post threads.
The **Shared** tab in chats (**Files** in channels) shows approved documents available to the signed-in user's team;
open a document to read its current version or jump to its history. The profile
menu in the top bar switches demo users and shows their team and approval role.
Portrait sources are recorded in [static/avatars/README.md](static/avatars/README.md).
Use the sun/moon button in the top bar to switch light and dark mode. Your choice
is remembered in this browser; until you choose, the app follows your system theme.
After backend changes, restart the Flask server before refreshing the browser.

## Contributors

This project was built by:
- Esther Li
- Frankie Febbo
- Evan Su
- Derrick Sual
- Aarnav Hariramani
- Emilio Cardillo-Schrader
