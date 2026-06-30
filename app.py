"""
House World Cup 2026 — sweepstake tracker.
Run with:  streamlit run app.py
"""
import os
import html
from datetime import datetime, timezone

import streamlit as st

import core
import live

DATA_PATH = os.environ.get("WC_DATA", "data.json")

st.set_page_config(page_title="House World Cup 2026", page_icon="⚽", layout="wide")

# --------------------------------------------------------------------------- #
# Styling
# --------------------------------------------------------------------------- #
CSS = """
<style>
:root{
  --wc-bg:#0e1117; --wc-card:#ffffff; --wc-ink:#16181d; --wc-mut:#7a8390;
  --wc-line:#c9d2dc; --wc-accent:#6d28d9; --wc-win:#0f9d58; --wc-win-bg:#eafaf0;
  --wc-out:#9aa3ad; --wc-chip:#eef1f5;
}
.block-container{padding-top:1.4rem;max-width:1500px;}
.wc-h1{font-size:2.0rem;font-weight:800;letter-spacing:-.5px;margin:0;color:#fff;}
.wc-sub{color:#aab2bd;margin:.15rem 0 1.1rem;font-size:.95rem;}
.wc-champ{display:inline-block;background:linear-gradient(90deg,#f9c846,#f59e0b);
  color:#3a2a00;font-weight:800;padding:.35rem .8rem;border-radius:999px;margin-bottom:1rem;}

.section-title{font-size:1.15rem;font-weight:800;color:#fff;margin:1.6rem 0 .7rem;
  display:flex;align-items:center;gap:.5rem;}

/* ----- bracket ----- */
.bracket-scroll{overflow-x:auto;padding:6px 2px 16px;}
.bracket{display:flex;gap:0;min-width:1050px;min-height:880px;}
.round{display:flex;flex-direction:column;min-width:206px;flex:1;padding:0 9px;}
.round-title{font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;
  color:#aab2bd;text-align:center;margin-bottom:.5rem;}
.round-body{display:flex;flex-direction:column;justify-content:space-around;flex:1;}
.pair{display:flex;flex-direction:column;justify-content:space-around;flex:1;position:relative;}
.matchup{background:var(--wc-card);border:1px solid #e4e9f0;border-radius:10px;
  overflow:hidden;position:relative;box-shadow:0 1px 2px rgba(0,0,0,.18);margin:5px 0;}
.team{display:flex;align-items:center;justify-content:space-between;gap:6px;
  padding:7px 10px;font-size:.86rem;color:var(--wc-ink);}
.team+.team{border-top:1px solid #eef1f5;}
.team .tname{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.team .tscore{font-variant-numeric:tabular-nums;color:var(--wc-mut);
  background:var(--wc-chip);border-radius:6px;padding:0 7px;min-width:22px;text-align:center;}
.team.win{font-weight:800;background:var(--wc-win-bg);box-shadow:inset 3px 0 0 var(--wc-win);}
.team.win .tscore{color:#0b6b3d;background:#d6f3e2;}
.team.tbd .tname{color:#aab2bd;font-style:italic;}
/* connector stubs + vertical pair lines */
.round:not(:last-child) .matchup::after{content:"";position:absolute;left:100%;top:50%;
  width:9px;height:2px;background:var(--wc-line);}
.round:not(:first-child) .matchup::before{content:"";position:absolute;right:100%;top:50%;
  width:9px;height:2px;background:var(--wc-line);}
.round:not(:last-child) .pair::after{content:"";position:absolute;left:100%;top:25%;bottom:25%;
  width:2px;background:var(--wc-line);transform:translateX(9px);}

/* ----- group stage ----- */
.grid-groups{display:grid;grid-template-columns:repeat(auto-fill,minmax(178px,1fr));gap:10px;}
.gcard{background:var(--wc-card);border:1px solid #e4e9f0;border-radius:10px;padding:9px 11px;}
.gcard h4{margin:0 0 6px;font-size:.8rem;color:var(--wc-accent);font-weight:800;}
.grow{display:flex;justify-content:space-between;font-size:.82rem;color:var(--wc-ink);padding:2px 0;}
.grow.out{color:var(--wc-out);text-decoration:line-through;}
.tag{font-size:.62rem;font-weight:800;padding:1px 6px;border-radius:999px;}
.tag.adv{background:#e7f8ee;color:#0b6b3d;}

/* ----- players ----- */
.lead{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:.9rem;}
.lchip{background:#1b2230;border:1px solid #2a3342;border-radius:999px;padding:.3rem .7rem;
  color:#dfe6ef;font-size:.82rem;font-weight:700;}
.lchip b{color:#fff;}
.grid-players{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px;}
.pcard{background:var(--wc-card);border:1px solid #e4e9f0;border-radius:12px;padding:13px 15px;
  box-shadow:0 1px 3px rgba(0,0,0,.16);}
.pcard .phead{display:flex;justify-content:space-between;align-items:baseline;
  margin-bottom:.55rem;border-bottom:1px solid #eef1f5;padding-bottom:.45rem;}
.pcard .pname{font-weight:800;font-size:1.02rem;color:var(--wc-ink);}
.pcard .pscore{font-size:.78rem;font-weight:700;color:var(--wc-accent);
  background:#f1ecfb;border-radius:999px;padding:.12rem .6rem;}
.pteam{padding:.32rem 0;border-bottom:1px dashed #f0f2f5;}
.pteam:last-child{border-bottom:none;}
.pteam .pt-name{font-size:.92rem;color:var(--wc-ink);font-weight:600;}
.pteam.out .pt-name{color:var(--wc-out);text-decoration:line-through;font-weight:500;}
.pteam .pt-sub{font-size:.72rem;color:var(--wc-mut);margin-top:1px;}
.pteam.out .pt-sub{color:#b03636;}
.live-badge{position:absolute;top:-7px;right:-6px;background:#e11d48;color:#fff;
  font-size:.56rem;font-weight:800;letter-spacing:.04em;padding:1px 5px;border-radius:999px;
  box-shadow:0 1px 2px rgba(0,0,0,.3);z-index:2;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(s):
    return html.escape(str(s))


# --------------------------------------------------------------------------- #
# HTML builders
# --------------------------------------------------------------------------- #
def match_card_html(m):
    w = core.winner_of(m)
    t1, t2 = m.get("team1") or "", m.get("team2") or ""
    s1 = "" if m.get("score1") is None else m["score1"]
    s2 = "" if m.get("score2") is None else m["score2"]

    def row(team, score):
        tbd = "" if team else " tbd"
        win = " win" if w and team == w else ""
        label = f"{core.flag(team)} {esc(team)}".strip() if team else "TBD"
        return (f'<div class="team{win}{tbd}">'
                f'<span class="tname">{label}</span>'
                f'<span class="tscore">{esc(score)}</span></div>')

    badge = '<span class="live-badge">LIVE</span>' if core.is_live(m) else ""
    return f'<div class="matchup">{badge}{row(t1, s1)}{row(t2, s2)}</div>'


def bracket_html(data):
    cols = []
    last = core.ROUND_ORDER[-1]
    for rk in core.ROUND_ORDER:
        matches = data["matches"].get(rk, [])
        cards = [match_card_html(m) for m in matches]
        if rk != last and len(cards) >= 2:
            body = ""
            for i in range(0, len(cards), 2):
                body += '<div class="pair">' + "".join(cards[i:i + 2]) + "</div>"
        else:
            body = "".join(f'<div class="pair">{c}</div>' for c in cards)
        cols.append(
            f'<div class="round"><div class="round-title">{esc(core.round_name(data, rk))}</div>'
            f'<div class="round-body">{body}</div></div>'
        )
    return '<div class="bracket-scroll"><div class="bracket">' + "".join(cols) + "</div></div>"


def group_stage_html(data, statuses):
    cards = []
    for g, teams in data["groups"].items():
        rows = ""
        for t in teams:
            out = statuses.get(t, {}).get("status") == "out"
            cls = " out" if out else ""
            tag = "" if out else '<span class="tag adv">in</span>'
            rows += (f'<div class="grow{cls}"><span>{core.flag(t)} {esc(t)}</span>{tag}</div>')
        cards.append(f'<div class="gcard"><h4>Group {esc(g)}</h4>{rows}</div>')
    return '<div class="grid-groups">' + "".join(cards) + "</div>"


def players_html(data, statuses):
    summaries = []
    for name in data["players"]:
        s = core.player_summary(data, statuses, name)
        summaries.append((name, s))

    lead = "".join(
        f'<span class="lchip">{esc(n)} <b>{s["alive"]}</b>/{s["total"]}</span>'
        for n, s in sorted(summaries, key=lambda x: (-x[1]["alive"], x[0]))
    )

    cards = ""
    for name, s in summaries:
        rows = ""
        for t in s["teams"]:
            info = statuses.get(t, {"status": "active"})
            if info["status"] == "out":
                if info.get("stage") == "Group stage":
                    sub = "Eliminated · Group stage"
                else:
                    by = f'{core.flag(info["by"])} {esc(info["by"])}'.strip()
                    bits = [f"Knocked out by {by}"]
                    if info.get("score"):
                        bits.append(esc(info["score"]))
                    if info.get("round"):
                        bits.append(esc(info["round"]))
                    sub = " · ".join(bits)
                rows += (f'<div class="pteam out"><div class="pt-name">{core.flag(t)} {esc(t)}</div>'
                         f'<div class="pt-sub">{sub}</div></div>')
            else:
                rows += (f'<div class="pteam"><div class="pt-name">{core.flag(t)} {esc(t)}</div></div>')
        cards += (
            f'<div class="pcard"><div class="phead"><span class="pname">{esc(name)}</span>'
            f'<span class="pscore">{s["alive"]}/{s["total"]} alive</span></div>{rows}</div>'
        )
    return f'<div class="lead">{lead}</div><div class="grid-players">{cards}</div>'


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def get_secret(name, default=""):
    """Read from st.secrets, then environment, then the given default."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name, default)


def check_password(data, attempt):
    real = get_secret("ADMIN_PASSWORD") or data.get("config", {}).get("admin_password", "")
    return attempt == real and real != ""


def auth_sidebar(data):
    with st.sidebar:
        st.markdown("### ⚽ Admin")
        if st.session_state.get("is_admin"):
            st.success("Logged in — edit mode on")
            if st.button("Log out", use_container_width=True):
                st.session_state.is_admin = False
                st.rerun()
        else:
            pw = st.text_input("Password", type="password",
                               placeholder="enter to update results")
            if st.button("Log in", use_container_width=True):
                if check_password(data, pw):
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Wrong password")
        st.caption("Anyone can view. Only admins can edit.")


# --------------------------------------------------------------------------- #
# Admin panels
# --------------------------------------------------------------------------- #
def admin_panel(data):
    st.markdown('<div class="section-title">🔧 Update centre</div>', unsafe_allow_html=True)
    tab_res, tab_live, tab_grp, tab_ply, tab_set = st.tabs(
        ["⚽ Match results", "📡 Live sync", "🏁 Group stage", "👥 Players", "⚙️ Settings"])

    teams_opts = [""] + core.all_teams(data)

    # ----- match results -----
    with tab_res:
        rk = st.selectbox("Round", core.ROUND_ORDER,
                          format_func=lambda r: core.round_name(data, r))
        matches = data["matches"][rk]
        labels = {m["id"]: f'{m["id"]}  ·  {(m["team1"] or "TBD")} v {(m["team2"] or "TBD")}'
                  for m in matches}
        mid = st.selectbox("Match", [m["id"] for m in matches],
                           format_func=lambda i: labels[i])
        m = core._find(data, rk, mid)

        c1, c2 = st.columns(2)
        t1 = c1.text_input("Home team", value=m.get("team1") or "", key=f"t1{mid}")
        t2 = c2.text_input("Away team", value=m.get("team2") or "", key=f"t2{mid}")

        played = st.checkbox("Game has been played",
                             value=core.match_decided(m), key=f"pl{mid}")
        s1 = s2 = None
        winner = None
        if played:
            sc1, sc2 = st.columns(2)
            s1 = sc1.number_input(f"{t1 or 'Home'} goals", min_value=0, step=1,
                                  value=int(m.get("score1") or 0), key=f"s1{mid}")
            s2 = sc2.number_input(f"{t2 or 'Away'} goals", min_value=0, step=1,
                                  value=int(m.get("score2") or 0), key=f"s2{mid}")
            if s1 == s2:
                choice = st.radio("Drawn after extra time — who won on penalties?",
                                  [t1 or "Home", t2 or "Away"], horizontal=True, key=f"pk{mid}")
                winner = t1 if choice == (t1 or "Home") else t2

        if st.button("💾 Save result", type="primary"):
            if played and not (t1 and t2):
                st.error("Enter both team names before saving a result.")
            else:
                core.set_match(data, rk, mid, t1, t2,
                               s1 if played else None, s2 if played else None,
                               winner, final=played)
                core.save_data(DATA_PATH, data)
                st.success("Saved.")
                st.rerun()
        st.caption("Saving a result auto-fills the winner into the next round. "
                   "Tip: fill in team names for a match even before it's played, "
                   "so the bracket shows the upcoming fixture.")

    # ----- live sync -----
    with tab_live:
        st.write("Pull fixtures and scores from **football-data.org** and apply them "
                 "automatically. Finished games update the bracket and cross out "
                 "knocked-out teams; in-play games show a LIVE score.")
        key = get_secret("FOOTBALL_DATA_API_KEY")
        comp = get_secret("FOOTBALL_DATA_COMPETITION", "WC")
        key_in = st.text_input(
            "API key", value=key, type="password",
            help="Free key from football-data.org/client/register. "
                 "Better: store it in Secrets as FOOTBALL_DATA_API_KEY.")
        comp_in = st.text_input("Competition code", value=comp,
                                help="World Cup is 'WC' on the free tier.")
        col_a, col_b = st.columns([1, 2])
        if col_a.button("📡 Fetch & apply", type="primary"):
            try:
                payload = live.fetch_raw(key_in, comp_in or "WC")
                report = live.apply_live(data, live.parse_matches(payload))
                data["last_sync"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                core.save_data(DATA_PATH, data)
                st.success(
                    f"Updated {report['knockout_set']} knockout fixtures "
                    f"({report['finished']} final, {report['in_play']} live). "
                    f"{report['advanced']} teams through, "
                    f"{report['group_out']} out in the group stage.")
                if report["unmatched_teams"]:
                    st.warning("These API team names didn't match — add them to "
                               "`ALIASES` in live.py:\n\n- "
                               + "\n- ".join(report["unmatched_teams"]))
                if report["unknown_stages"]:
                    st.warning("Unrecognised stage names (extend `STAGE_MAP` in live.py): "
                               + ", ".join(report["unknown_stages"]))
                st.rerun()
            except live.LiveError as e:
                st.error(str(e))
            except Exception as e:  # noqa: BLE001 - surface anything unexpected
                st.error(f"Unexpected error: {e}")
        if data.get("last_sync"):
            col_b.caption(f"Last synced: {data['last_sync']} UTC")
        st.caption("Re-syncing overwrites scores for synced matches, so manual edits to "
                   "those games will be replaced. Anything the API can't match is listed "
                   "above so you can extend the team/stage maps in live.py.")

    # ----- group stage -----
    with tab_grp:
        st.write("Tick the teams that were **knocked out in the group stage**. "
                 "Everyone else is treated as still alive until they lose a knockout game.")
        current = set(data.get("group_stage_out", []))
        new_out = []
        cols = st.columns(3)
        for i, (g, teams) in enumerate(data["groups"].items()):
            with cols[i % 3]:
                picked = st.multiselect(f"Group {g}", teams,
                                        default=[t for t in teams if t in current],
                                        key=f"go{g}")
                new_out.extend(picked)
        if st.button("💾 Save group-stage exits", type="primary"):
            data["group_stage_out"] = new_out
            core.save_data(DATA_PATH, data)
            st.success("Saved.")
            st.rerun()

    # ----- players -----
    with tab_ply:
        st.write("Rename housemates and adjust their allocated teams.")
        edited = {}
        names = list(data["players"].keys())
        cols = st.columns(2)
        ok = True
        for i, name in enumerate(names):
            with cols[i % 2]:
                new_name = st.text_input("Name", value=name, key=f"pn{i}")
                picks = st.multiselect("Teams", core.all_teams(data),
                                       default=data["players"][name], key=f"pt{i}")
                if new_name in edited:
                    ok = False
                edited[new_name] = picks
        if st.button("💾 Save players", type="primary"):
            if not ok:
                st.error("Two housemates can't share the same name.")
            else:
                data["players"] = edited
                core.save_data(DATA_PATH, data)
                st.success("Saved.")
                st.rerun()

    # ----- settings -----
    with tab_set:
        cfg = data.get("config", {})
        title = st.text_input("Page title", value=cfg.get("title", ""))
        subtitle = st.text_input("Subtitle", value=cfg.get("subtitle", ""))
        pw = st.text_input("Admin password", value=cfg.get("admin_password", ""))
        if st.button("💾 Save settings", type="primary"):
            cfg.update({"title": title, "subtitle": subtitle, "admin_password": pw})
            data["config"] = cfg
            core.save_data(DATA_PATH, data)
            st.success("Saved.")
            st.rerun()
        st.caption("An ADMIN_PASSWORD environment variable, if set, overrides this value.")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    data = core.load_data(DATA_PATH)
    statuses = core.compute_team_statuses(data)
    cfg = data.get("config", {})

    auth_sidebar(data)

    st.markdown(f'<div class="wc-h1">⚽ {esc(cfg.get("title", "World Cup"))}</div>',
                unsafe_allow_html=True)
    if cfg.get("subtitle"):
        st.markdown(f'<div class="wc-sub">{esc(cfg["subtitle"])}</div>', unsafe_allow_html=True)

    champ = core.champion(data)
    if champ:
        st.markdown(f'<div class="wc-champ">🏆 Champions: {core.flag(champ)} {esc(champ)}</div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="section-title">🏆 Knockout bracket</div>', unsafe_allow_html=True)
    st.markdown(bracket_html(data), unsafe_allow_html=True)

    st.markdown('<div class="section-title">👥 The housemates</div>', unsafe_allow_html=True)
    st.markdown(players_html(data, statuses), unsafe_allow_html=True)

    with st.expander("🏁 Group stage — who's still in"):
        st.markdown(group_stage_html(data, statuses), unsafe_allow_html=True)

    if st.session_state.is_admin:
        st.divider()
        admin_panel(data)


if __name__ == "__main__":
    main()
