# Bug list (integration testing — started 0:45 mark)

Procedure: `git fetch origin`, then for each owner's branch, run that file's `if __name__ == "__main__":` block (or, for `app.py`, `streamlit run app.py --server.headless true` and exercise it). Re-pulled `origin/main` repeatedly during this pass since PRs were landing live — see timestamps.

Snapshot at time of writing: `main` is at `d5f5aa4` (merges #7 seed, #8 rag, #9 db). `frankie` branch exists, unmerged, no PR open yet. No `evan` branch exists yet.

## Blocker

- **governance.py is not implemented — no branch pushed yet (Issue #3, owner Evan).** `propose`, `approve`, and `reject` all still `raise NotImplementedError` on `main`. This is the core of the product (docs change only through `approve()`) and the center of the demo arc (Propose → Review → Merge). Nothing downstream can be integration-tested end-to-end until this lands: `app.py`'s real (non-`USE_FAKES`) mode will raise `NotImplementedError` the instant anyone clicks Approve, Reject, or Propose.
  - Status at code freeze: **must be fixed or the demo runs entirely on `app.py`'s `USE_FAKES = True` fake backend**, which still tells the right story (the fakes mirror the CONTRACTS.md shapes) but isn't the real system. Flagging now so it gets priority at the 0:40 check-in.

## Cosmetic / pre-integration (not blockers — expected to resolve once real imports are wired in)

- **`app.py`'s fake `PermissionError` text doesn't match the CONTRACTS.md canonical format.** The fake backend (`_fake_approve`, used while `USE_FAKES = True`) raises e.g. `"{user} is a {role}; only Approvers can approve or reject"`, but CONTRACTS.md and Issue #3 specify the real message format: `"Only Payments can approve: Payments depends on Ops Automation"`. `demo_script.md` uses the CONTRACTS.md text since that's what the real `governance.py` must produce. Re-verify the exact on-screen wording once `app.py` switches off fakes (`USE_FAKES = False`) and `governance.py` is real — the `st.error(f"Blocked: {e}")` wrapper is correct either way.
- **`app.py` is on branch `frankie`, unmerged, no PR open.** Fully built (sidebar, Approvals, History, Ask Spot, Teams skin) and boots clean under `streamlit run app.py` with `USE_FAKES = True` (verified — HTTP 200, no exceptions). Needs a PR before 1:05 integration so Frankie can swap in real imports.
- **`rag.py` `__main__` block fails fast on a clean checkout with no `.env`.** Expected — `LLM_API_KEY` isn't set, so `OpenAI(...)` raises `OpenAIError: Missing credentials`. Not a code bug; make sure `.env` (`LLM_API_KEY`, `LLM_MODEL`) is filled in on the demo machine *before* rehearsal, or Ask Spot will fail live.
- **Missing `watchdog` package** — Streamlit prints a perf warning on every run ("For better performance, install the Watchdog module"). Cosmetic only, `pip install watchdog` silences it.

## Verified working (re-tested against current `main` @ `d5f5aa4`)

- `python db.py` — all assertions pass (`carol` sees both teams' docs, `bob` sees only Ops Automation, `get_dependent_teams("Ops Automation") == ["Payments"]`, double `reset()` is idempotent).
- `python seed.py` — 9 docs seeded (within the 8-10 spec), 1 dependency row, 1 pending proposal on `ops-uae-gateway`, exactly one doc (`ops-uae-identity`) mentions the UAE identity cutover date. Demo doc id confirmed: **`ops-uae-identity`**, current cutover date **November 14, 2026**.
- `app.py` (branch `frankie`, `USE_FAKES = True`) — boots clean, all three tabs render.

## Cut order if behind (per Issue #6)

1. Side-by-side diff view goes first.
2. Adaptive Card mockup goes second.
3. **Never cut**: Pending/Approve, routing, the role check, History, or Chat — these stay no matter what.
