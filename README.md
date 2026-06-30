# House World Cup 2026 ⚽

A small Streamlit app that shows the 2026 FIFA World Cup knockout bracket and tracks
which of each housemate's allocated teams are still alive in a sweepstake. Anyone with
the link can view it; only someone with the admin password can update results — by hand
**or** by pulling live scores from an API.

![rounds](https://img.shields.io/badge/format-48%20teams%20%C2%B7%20R32%E2%86%92Final-6d28d9)

## Features

- **Knockout bracket** (Round of 32 → Final) styled like an online bracket, with flags,
  scores, winners highlighted, and a `LIVE` badge on in-play games.
- **Six housemate cards** listing each person's teams. Knocked-out teams are crossed out
  with a subheading saying who beat them and the score (e.g. *"Knocked out by 🇫🇷 France ·
  2–1 · Round of 16"*), or *"Eliminated · Group stage"*. A leaderboard chip row shows who
  has the most teams left.
- **Two ways to update:** a password-protected manual editor, and a one-click **Live sync**
  from [football-data.org](https://www.football-data.org/).
- Pre-loaded with all 48 real teams, the 12 groups, and the official Round-of-32 structure.

## Project layout

```
.
├── app.py                       # Streamlit UI
├── core.py                      # logic (winners, eliminations, propagation) — no UI
├── live.py                      # live score fetch + mapping (football-data.org)
├── build_seed.py                # regenerates data.json from scratch
├── data.json                    # live data: groups, players, bracket, results
├── requirements.txt
├── LICENSE
└── .streamlit/
    ├── config.toml              # dark theme
    └── secrets.toml.example     # copy to secrets.toml and fill in
```

`data.json` is the single source of truth and is rewritten whenever you save.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Opens at http://localhost:8501. Default admin password is **`housecup2026`** — change it
in the **Settings** tab, or override it with secrets/an env var (see below).

## Updating results

Log in via the sidebar to switch on edit mode, then use the **Update centre**:

- **⚽ Match results** — pick a round and match, type the two teams, tick *"Game has been
  played"*, enter the score, save. The winner auto-advances to the next round and the
  loser is auto–crossed-out everywhere. Knockout draws prompt for the penalty winner.
- **📡 Live sync** — paste your football-data.org key (or set it in Secrets) and hit
  *Fetch & apply*. See below.
- **🏁 Group stage** — tick the teams knocked out in the group stage (only needed if you
  aren't using Live sync).
- **👥 Players** — rename housemates and adjust allocated teams.
- **⚙️ Settings** — title, subtitle, password.

## Live sync setup

1. Register for a **free** API key at <https://www.football-data.org/client/register>.
2. Add it to `.streamlit/secrets.toml` (copy from `.streamlit/secrets.toml.example`):
   ```toml
   FOOTBALL_DATA_API_KEY = "your-key"
   FOOTBALL_DATA_COMPETITION = "WC"
   ```
   (Or paste the key into the field in the Live sync tab, or set a `FOOTBALL_DATA_API_KEY`
   env var.)
3. Open **Live sync → Fetch & apply**. Finished knockout games update the bracket and
   eliminations; in-play games show a live score; teams that didn't reach the Round of 32
   are crossed out as group-stage exits automatically.

**How matching works / known limits**

- The 2026 tournament uses a new 48-team format, so some API **stage names** and a few
  **team spellings** (e.g. `Korea Republic`, `Côte d'Ivoire`, `Cabo Verde`) may differ.
  The app normalises the common ones; anything it can't match is listed in the sync result
  so you can extend `ALIASES` / `STAGE_MAP` at the top of `live.py` — no other changes
  needed.
- Re-syncing **overwrites** scores for synced matches, so manual edits to those games are
  replaced on the next sync. The housemate cross-outs are always derived from results, so
  they stay correct either way.
- The free tier is rate-limited (~10 requests/min). This app fetches on demand (button),
  not on a timer. To auto-refresh, add `streamlit-autorefresh` and call it at the top of
  `app.py`.
- Prefer a different provider? `live.py` is self-contained — swap `fetch_raw`/`parse_matches`
  for another API (e.g. API-Football, TheSportsDB) and keep `apply_live` as-is.

## Deploy so the housemates can see it

Easiest free option is **Streamlit Community Cloud**:

1. Push this repo to GitHub (see below).
2. On <https://share.streamlit.io>, create an app pointing at `app.py`.
3. In the app's **Settings → Secrets**, add:
   ```toml
   ADMIN_PASSWORD = "something-not-housecup2026"
   FOOTBALL_DATA_API_KEY = "your-key"
   ```

**Persistence caveat:** Streamlit Cloud's filesystem is ephemeral, so writes to
`data.json` can be lost when the app sleeps or redeploys. For a few housemates that's
often fine between updates, but if you want it durable, either commit `data.json` after
edits, or point `core.load_data`/`core.save_data` at a tiny database (a free Supabase /
Postgres table, or a GitHub Gist). That's the only file you'd change.

## Push to GitHub

This folder is already a git repo with an initial commit. Create an empty repo on GitHub,
then:

```bash
git remote add origin https://github.com/<you>/house-world-cup.git
git branch -M main
git push -u origin main
```

(If you're starting fresh instead: `git init && git add -A && git commit -m "init"`.)

## Reset everything

```bash
python build_seed.py     # overwrites data.json with default teams/groups/bracket
```

The starter file deals all 48 teams round-robin to six placeholder housemates (8 each) —
swap these for your real allocations in the **Players** tab.

## License

MIT — see `LICENSE` (add your name to the copyright line).
