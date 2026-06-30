"""House World Cup 2026 sweepstake tracker. Run: streamlit run app.py"""
import base64
import html
import os
from datetime import datetime, timezone
from io import BytesIO
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from PIL import Image, ImageOps
from streamlit_autorefresh import st_autorefresh

import core
import live

DATA_PATH = os.environ.get("WC_DATA", "data.json")
SYDNEY = ZoneInfo("Australia/Sydney")

st.set_page_config(page_title="House World Cup 2026", page_icon="⚽", layout="wide")

CSS = """
<style>
:root{--bg:#080b10;--panel:#111720;--panel2:#151d28;--ink:#f4f7fb;--mut:#8e99a8;
--line:#2a3544;--accent:#32d296;--win:#34d399;--winbg:#102b24;--danger:#ff4d5e;}
.stApp{background:radial-gradient(circle at 20% 0%,#111827 0,#080b10 38%);color:var(--ink)}
.block-container{padding-top:1.2rem;max-width:1550px}.wc-h1{font-size:2rem;font-weight:850;color:#fff}
.wc-sub,.match-time{color:var(--mut)}.section-title{font-size:1.15rem;font-weight:800;color:#fff;margin:1.5rem 0 .7rem}
.bracket-scroll{overflow-x:auto;padding:4px 2px 18px}.bracket{display:flex;min-width:1120px;min-height:900px}
.round{display:flex;flex-direction:column;min-width:215px;flex:1;padding:0 9px}.round-title{text-align:center;text-transform:uppercase;
letter-spacing:.08em;color:#9aa5b4;font-size:.72rem;font-weight:800;margin-bottom:.45rem}.round-body{display:flex;flex-direction:column;justify-content:space-around;flex:1}
.pair{display:flex;flex-direction:column;justify-content:space-around;flex:1;position:relative}.matchup{background:linear-gradient(180deg,#151b24,#10151d);
border:1px solid #293342;border-radius:12px;overflow:hidden;position:relative;box-shadow:0 7px 20px rgba(0,0,0,.25);margin:5px 0}
.team{display:flex;align-items:center;justify-content:space-between;gap:7px;min-height:43px;padding:7px 10px;font-size:.86rem;color:#e9edf4}.team+.team{border-top:1px solid #26303d}
.team .tname{min-width:0;flex:1;overflow:hidden;display:block}.team-left{min-width:0;display:flex;align-items:center;gap:6px;overflow:hidden}.team-country{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:0 1 auto}.owner-inline{min-width:0;display:inline-flex;align-items:center;gap:4px;color:#7f8a99;font-size:.60rem;font-weight:500;line-height:1;white-space:nowrap;flex:0 1 auto}.owner-name{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.owner-avatar{width:19px;height:19px;border-radius:50%;object-fit:cover;border:1px solid #3b4757;background:#222b37;flex:0 0 auto}.owner-avatar-fallback{display:inline-flex;align-items:center;justify-content:center;color:#b6c0cd;font-size:.54rem;font-weight:850}.team .tscore{font-variant-numeric:tabular-nums;color:#c3cad5;background:#222b37;border-radius:7px;padding:1px 7px;min-width:24px;text-align:center;font-size:.9rem}.score-stack{display:flex;align-items:center;gap:5px;flex:0 0 auto}.pen-score{display:flex;flex-direction:column;align-items:center;justify-content:center;min-width:25px;color:#b8c2cf;font-size:.66rem;line-height:.78rem}.pen-score b{font-size:.72rem;color:#dce3ec}.pen-score small{font-size:.48rem;text-transform:uppercase;letter-spacing:.04em}.flag-icon{width:18px;height:13px;object-fit:cover;border-radius:2px;box-shadow:0 0 0 1px rgba(255,255,255,.13);flex:0 0 auto}
.team.win{font-weight:800;background:var(--winbg);box-shadow:inset 3px 0 0 var(--win)}.team.win .tscore{color:#bff8dd;background:#174638}.team.tbd .tname{color:#7c8795;font-style:italic}
.match-meta{font-size:.64rem;color:#7f8a99;text-align:center;padding:3px 7px 5px;border-top:1px solid #222b36}.shootout-note{color:#aeb8c5;margin-left:6px}
.round:not(:last-child) .matchup::after{content:"";position:absolute;left:100%;top:50%;width:9px;height:2px;background:var(--line)}
.round:not(:first-child) .matchup::before{content:"";position:absolute;right:100%;top:50%;width:9px;height:2px;background:var(--line)}
.round:not(:last-child) .pair::after{content:"";position:absolute;left:100%;top:25%;bottom:25%;width:2px;background:var(--line);transform:translateX(9px)}
.live-badge{position:absolute;top:3px;right:4px;background:#e11d48;color:#fff;font-size:.54rem;font-weight:900;padding:1px 5px;border-radius:999px;z-index:2}
.grid-players{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:13px}.pcard{background:linear-gradient(180deg,#151b24,#10151d);border:1px solid #293342;border-radius:14px;padding:14px 15px;box-shadow:0 7px 20px rgba(0,0,0,.22)}
.pcard.loser{border:2px solid var(--danger);background:linear-gradient(180deg,#2b1117,#170c10)}.loser-banner{font-size:1.1rem;font-weight:950;color:#ff5b69;text-transform:uppercase;text-align:center;margin:3px 0 10px;letter-spacing:.04em}
.phead{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #293342;padding-bottom:.55rem;margin-bottom:.55rem}.person{display:flex;align-items:center;gap:9px}.avatar{width:38px;height:38px;border-radius:50%;object-fit:cover;border:2px solid #344154;background:#222b37}.avatar-fallback{display:flex;align-items:center;justify-content:center;font-weight:900;color:#cbd5e1}
.pname{font-weight:850;color:#fff}.pscore{font-size:.75rem;font-weight:800;color:#b8f7dc;background:#14392f;border-radius:999px;padding:.15rem .55rem}.pteam{padding:.32rem 0;border-bottom:1px dashed #293342}.pteam:last-child{border:0}.pt-name,.grow .tname{display:flex;align-items:center;gap:6px}.pt-name{color:#edf1f7;font-weight:650}.pteam.out .pt-name{color:#7f8996;text-decoration:line-through}.pt-sub{font-size:.7rem;color:#ff7b87;margin-top:1px}
.lead{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:.9rem}.lchip{background:#151d28;border:1px solid #2c3746;border-radius:999px;padding:.3rem .7rem;color:#d9e0e9;font-size:.82rem;font-weight:700}
.grid-groups{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px}.gcard{background:#111720;border:1px solid #293342;border-radius:11px;padding:10px}.gcard h4{color:#70e4b5;margin:0 0 6px}.grow{display:flex;justify-content:space-between;color:#e7ebf2;font-size:.82rem;padding:2px}.grow.out{color:#77818f;text-decoration:line-through}
.wc-champ{display:inline-flex;align-items:center;gap:6px;background:linear-gradient(90deg,#facc15,#f59e0b);color:#291d00;font-weight:900;padding:.35rem .8rem;border-radius:999px;margin-bottom:1rem}
div[data-testid="stTextInput"] input,div[data-testid="stNumberInput"] input,div[data-baseweb="select"]>div,textarea{background:#111720!important;color:#f4f7fb!important;border-color:#303b4a!important}
</style>"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(x): return html.escape(str(x))

def secret(name, default=""):
    try:
        if name in st.secrets: return st.secrets[name]
    except Exception: pass
    return os.environ.get(name, default)

def persistence_settings():
    return secret("GITHUB_REPO"), secret("GITHUB_TOKEN"), secret("GITHUB_BRANCH", "main"), secret("GITHUB_DATA_PATH", "data.json")

def load_data():
    repo, token, branch, path = persistence_settings()
    st.session_state["github_data_read_only"] = False
    st.session_state["github_data_error"] = ""
    if repo and token:
        try:
            data = core.github_load_data(repo, token, path, branch)
        except Exception as e:
            # Local fallback keeps the page viewable, but writes are blocked so
            # an old bundled data.json can never overwrite the user's GitHub data.
            st.session_state["github_data_read_only"] = True
            st.session_state["github_data_error"] = str(e)
            st.error(
                "GitHub data could not be loaded, so the app is temporarily "
                "read-only and is showing its bundled backup. " + str(e)
            )
            data = core.load_data(DATA_PATH)
    else:
        data = core.load_data(DATA_PATH)
    # Automatically migrate the old chronological/index bracket into FIFA's
    # official match-number topology. This fixes wrong visual feeder pairings.
    core.ensure_official_bracket(data)
    data.setdefault("player_photos", {})
    _compact_existing_photos(data)
    return data

def save_data(data, message="Update World Cup tracker"):
    if st.session_state.get("github_data_read_only"):
        raise RuntimeError(
            "Save blocked because GitHub data did not load. This protects your "
            "saved players and photos from being overwritten by the local backup."
        )
    core.save_data(DATA_PATH, data)
    repo, token, branch, path = persistence_settings()
    if repo and token:
        core.github_save_data(repo, token, data, path, branch, message)

def sydney_time(utc_text):
    if not utc_text: return ""
    try:
        dt = datetime.fromisoformat(utc_text.replace("Z", "+00:00")).astimezone(SYDNEY)
        return dt.strftime("%a %-d %b · %-I:%M %p Sydney")
    except Exception:
        return ""

@st.cache_data(show_spinner=False, ttl=7 * 24 * 60 * 60)
def _flag_data_uri(code):
    """Fetch a tiny flag on the server, then embed it directly in the page.

    This avoids the browser/CSP issue that caused country-code letters to appear
    instead of flags. A failed request returns no flag rather than a broken icon.
    """
    if not code:
        return ""
    try:
        response = requests.get(
            f"https://flagcdn.com/w40/{code}.png",
            headers={"User-Agent": "world-cup-comp-tracker"},
            timeout=8,
        )
        response.raise_for_status()
        if not response.content:
            return ""
        return "data:image/png;base64," + base64.b64encode(response.content).decode("ascii")
    except requests.RequestException:
        return ""


def flag_html(team):
    """Render a self-contained flag image, or nothing if it cannot be loaded."""
    src = _flag_data_uri(core.flag_code(team))
    if not src:
        return ""
    return (f'<img class="flag-icon" src="{src}" '
            f'alt="" aria-hidden="true">')


def team_name_html(team):
    if not team:
        return "TBD"
    flag = flag_html(team)
    return f'{flag}<span>{esc(team)}</span>'


def _photo_data_uri(raw_bytes):
    """Resize/crop an uploaded photo so data.json stays small and durable."""
    try:
        image = Image.open(BytesIO(raw_bytes))
        image = ImageOps.exif_transpose(image).convert("RGB")
        width, height = image.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        image = image.crop((left, top, left + side, top + side))
        image = image.resize((160, 160), Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format="JPEG", quality=82, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")
    except Exception as exc:
        raise ValueError("That photo could not be processed. Try a JPG, PNG or WebP image.") from exc


def _compact_existing_photos(data):
    """Shrink older, very large embedded photos in memory when possible."""
    photos = data.get("player_photos", {})
    for name, src in list(photos.items()):
        if not isinstance(src, str) or not src.startswith("data:image/") or len(src) < 120_000:
            continue
        try:
            encoded = src.split(",", 1)[1]
            photos[name] = _photo_data_uri(base64.b64decode(encoded))
        except Exception:
            # Keep the original rather than ever deleting a user's photo.
            pass


def team_owner(data, team):
    """Return the housemate allocated to a team, if any."""
    if not team:
        return None
    for name, teams in data.get("players", {}).items():
        if team in teams:
            return name
    return None


def bracket_team_html(data, team):
    """Team label plus the owning housemate's small avatar and name."""
    if not team:
        return "TBD"

    owner = team_owner(data, team)
    owner_html = ""
    if owner:
        src = data.get("player_photos", {}).get(owner)
        if src:
            photo = f'<img class="owner-avatar" src="{src}" alt="{esc(owner)}">'
        else:
            initial = esc(owner[:1].upper()) if owner else "?"
            photo = f'<span class="owner-avatar owner-avatar-fallback">{initial}</span>'
        owner_html = (f'<span class="owner-inline" title="Owned by {esc(owner)}">{photo}'
                      f'<span class="owner-name">{esc(owner)}</span></span>')

    return (f'<span class="team-left">{flag_html(team)}'
            f'<span class="team-country">{esc(team)}</span>{owner_html}</span>')


def match_card_html(m, data):
    winner = core.winner_of(m)
    team1, team2 = m.get("team1") or "", m.get("team2") or ""
    score1 = "" if m.get("score1") is None else m["score1"]
    score2 = "" if m.get("score2") is None else m["score2"]
    pen1, pen2 = m.get("pen1"), m.get("pen2")

    def row(team, score, penalties):
        # Normally the large score is the score after play (90/120 minutes) and
        # the small score is the shootout. If a provider supplies only shootout
        # numbers, use them as the large score and label the match below.
        fallback_to_penalties = score == "" and penalties is not None
        big_score = penalties if fallback_to_penalties else score
        pen_html = ""
        if penalties is not None and not fallback_to_penalties:
            pen_html = (f'<span class="pen-score"><b>{esc(penalties)}</b>'
                        f'<small>pens</small></span>')
        label = bracket_team_html(data, team)
        classes = f'{" win" if winner == team and team else ""}{" tbd" if not team else ""}'
        score_html = ""
        if big_score != "" or pen_html:
            score_html = (f'<span class="score-stack"><span class="tscore">'
                          f'{esc(big_score)}</span>{pen_html}</span>')
        return (f'<div class="team{classes}"><span class="tname">{label}</span>'
                f'{score_html}</div>')

    badge = '<span class="live-badge">LIVE</span>' if core.is_live(m) else ""
    match_time = sydney_time(m.get("utc_date"))
    shootout = pen1 is not None and pen2 is not None
    meta_bits = []
    if match_time:
        meta_bits.append(esc(match_time))
    if shootout:
        meta_bits.append('<span class="shootout-note">Decided on penalties</span>')
    meta = f'<div class="match-meta">{" · ".join(meta_bits)}</div>' if meta_bits else ""
    return f'<div class="matchup">{badge}{row(team1, score1, pen1)}{row(team2, score2, pen2)}{meta}</div>'

def bracket_html(data):
    cols=[]
    for rk in core.ROUND_ORDER:
        cards=[match_card_html(m, data) for m in data["matches"].get(rk,[])]
        body="".join('<div class="pair">'+"".join(cards[i:i+2])+"</div>" for i in range(0,len(cards),2)) if rk!="F" else "".join(f'<div class="pair">{c}</div>' for c in cards)
        cols.append(f'<div class="round"><div class="round-title">{esc(core.round_name(data,rk))}</div><div class="round-body">{body}</div></div>')
    return '<div class="bracket-scroll"><div class="bracket">'+"".join(cols)+"</div></div>"

def avatar_html(name,data):
    src=data.get("player_photos",{}).get(name)
    if src: return f'<img class="avatar" src="{src}" alt="{esc(name)}">'
    return f'<div class="avatar avatar-fallback">{esc(name[:1].upper())}</div>'

def players_html(data,statuses):
    summaries=[(n,core.player_summary(data,statuses,n)) for n in data["players"]]
    lead="".join(f'<span class="lchip">{esc(n)} <b>{s["alive"]}</b>/{s["total"]}</span>' for n,s in sorted(summaries,key=lambda x:(-x[1]["alive"],x[0])))
    cards=[]
    for name,s in summaries:
        rows=[]
        for t in s["teams"]:
            info=statuses.get(t,{"status":"active"})
            if info["status"]=="out":
                sub="Eliminated · Group stage" if info.get("stage")=="Group stage" else " · ".join(x for x in [f'Knocked out by {flag_html(info.get("by"))}<span>{esc(info.get("by"))}</span>',esc(info.get("score") or ""),esc(info.get("round") or "")] if x)
                rows.append(f'<div class="pteam out"><div class="pt-name">{team_name_html(t)}</div><div class="pt-sub">{sub}</div></div>')
            else: rows.append(f'<div class="pteam"><div class="pt-name">{team_name_html(t)}</div></div>')
        lost_all=s["total"]>0 and s["alive"]==0
        banner=f'<div class="loser-banner">{esc(name)} is a loser</div>' if lost_all else ""
        cards.append(f'<div class="pcard{" loser" if lost_all else ""}">{banner}<div class="phead"><div class="person">{avatar_html(name,data)}<span class="pname">{esc(name)}</span></div><span class="pscore">{s["alive"]}/{s["total"]} alive</span></div>{"".join(rows)}</div>')
    return f'<div class="lead">{lead}</div><div class="grid-players">{"".join(cards)}</div>'

def group_stage_html(data,statuses):
    cards=[]
    for g,teams in data["groups"].items():
        rows="".join(f'<div class="grow{" out" if statuses.get(t,{}).get("status")=="out" else ""}"><span class="tname">{team_name_html(t)}</span></div>' for t in teams)
        cards.append(f'<div class="gcard"><h4>Group {esc(g)}</h4>{rows}</div>')
    return '<div class="grid-groups">'+"".join(cards)+"</div>"

def do_live_sync(data,quiet=False):
    key=secret("FOOTBALL_DATA_API_KEY"); comp=secret("FOOTBALL_DATA_COMPETITION","WC")
    if not key: return None
    payload=live.fetch_raw(key,comp); report=live.apply_live(data,live.parse_matches(payload))
    data["last_sync"]=datetime.now(timezone.utc).isoformat(timespec="seconds")
    save_data(data,"Automatic World Cup score sync")
    if not quiet:
        st.success(f"Updated {report['knockout_set']} fixtures; {report['finished']} final and {report['in_play']} live.")
        if report.get("unmatched_fixtures"):
            st.warning("Could not place these fixtures in the official bracket: " + "; ".join(report["unmatched_fixtures"]))
    return report

def maybe_auto_sync(data):
    cfg=data.setdefault("config",{})
    if not cfg.get("auto_update",False): return
    if st.session_state.get("github_data_read_only"):
        st.sidebar.caption("Auto-update paused until GitHub data can be loaded safely.")
        return
    interval=max(60,int(cfg.get("auto_update_seconds",90)))
    st_autorefresh(interval=interval*1000,key="wc_auto_refresh")
    last=data.get("last_sync")
    due=True
    if last:
        try: due=(datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds()>=interval
        except Exception: pass
    if due:
        try: do_live_sync(data,quiet=True); st.rerun()
        except Exception as e: st.sidebar.caption(f"Auto-update retry pending: {e}")

def auth_sidebar(data):
    with st.sidebar:
        st.markdown("### ⚽ Admin")
        if st.session_state.get("is_admin"):
            st.success("Edit mode on")
            if st.button("Log out",use_container_width=True): st.session_state.is_admin=False; st.rerun()
        else:
            pw=st.text_input("Password",type="password")
            if st.button("Log in",use_container_width=True):
                real=secret("ADMIN_PASSWORD") or data.get("config",{}).get("admin_password","")
                if pw==real and real: st.session_state.is_admin=True; st.rerun()
                else: st.error("Wrong password")
        if data.get("last_sync"): st.caption(f"Last score sync: {data['last_sync']} UTC")

def admin_panel(data):
    st.markdown('<div class="section-title">🔧 Update centre</div>',unsafe_allow_html=True)
    tab_res,tab_live,tab_grp,tab_ply,tab_set=st.tabs(["⚽ Match results","📡 Live sync","🏁 Group stage","👥 Players","⚙️ Settings"])
    with tab_res:
        rk=st.selectbox("Round",core.ROUND_ORDER,format_func=lambda r:core.round_name(data,r)); matches=data["matches"][rk]
        mid=st.selectbox("Match",[m["id"] for m in matches],format_func=lambda i:next(f'{m["id"]} · {m.get("team1") or "TBD"} v {m.get("team2") or "TBD"}' for m in matches if m["id"]==i)); m=core._find(data,rk,mid)
        c1,c2=st.columns(2); t1=c1.text_input("Home team",m.get("team1") or "",key=f"t1{mid}"); t2=c2.text_input("Away team",m.get("team2") or "",key=f"t2{mid}")
        played=st.checkbox("Game has been played",value=core.match_decided(m),key=f"pl{mid}"); s1=s2=pen1=pen2=None; winner=None
        if played:
            a,b=st.columns(2); s1=a.number_input("Home goals",0,20,int(m.get("score1") or 0),key=f"s1{mid}"); s2=b.number_input("Away goals",0,20,int(m.get("score2") or 0),key=f"s2{mid}")
            if s1==s2:
                p1,p2=st.columns(2); pen1=p1.number_input("Home penalties",0,20,int(m.get("pen1") or 0),key=f"p1{mid}"); pen2=p2.number_input("Away penalties",0,20,int(m.get("pen2") or 0),key=f"p2{mid}")
                winner=t1 if pen1>pen2 else t2 if pen2>pen1 else None
        if st.button("💾 Save result",type="primary"):
            if played and (not t1 or not t2 or (s1==s2 and winner is None)): st.error("Enter both teams and a valid penalty result.")
            else:
                try:
                    core.set_match(data,rk,mid,t1,t2,s1 if played else None,s2 if played else None,winner,played,pen1,pen2); save_data(data,"Manual match result update"); st.rerun()
                except Exception as exc: st.error(str(exc))
    with tab_live:
        st.write("The API is polled automatically when enabled, including during live matches. A manual sync is available here.")
        if st.button("📡 Fetch & apply now",type="primary"):
            try: do_live_sync(data); st.rerun()
            except Exception as e: st.error(str(e))
    with tab_grp:
        current=set(data.get("group_stage_out",[])); new=[]
        for g,teams in data["groups"].items(): new.extend(st.multiselect(f"Group {g}",teams,default=[t for t in teams if t in current],key=f"g{g}"))
        if st.button("Save group exits"):
            try: data["group_stage_out"]=new; save_data(data,"Update group-stage exits"); st.rerun()
            except Exception as exc: st.error(str(exc))
    with tab_ply:
        edited={}; photos=dict(data.get("player_photos",{}))
        for i,(name,teams) in enumerate(data["players"].items()):
            st.markdown(f"**Player {i+1}**"); c1,c2=st.columns([2,1]); new_name=c1.text_input("Name",name,key=f"pn{i}"); picks=c1.multiselect("Teams",core.all_teams(data),default=teams,key=f"pt{i}"); upload=c2.file_uploader("Photo",type=["png","jpg","jpeg","webp"],key=f"ph{i}")
            edited[new_name]=picks
            if upload:
                try:
                    photos[new_name] = _photo_data_uri(upload.getvalue())
                except ValueError as exc:
                    c2.error(str(exc))
            elif name in photos and new_name!=name: photos[new_name]=photos.pop(name)
            if c2.checkbox("Remove photo",key=f"rm{i}"): photos.pop(new_name,None)
        if st.button("💾 Save players",type="primary"):
            if len(edited)!=len(data["players"]): st.error("Player names must be unique.")
            else:
                try: data["players"]=edited; data["player_photos"]=photos; save_data(data,"Update players and photos"); st.rerun()
                except Exception as exc: st.error(str(exc))
    with tab_set:
        cfg=data.setdefault("config",{}); title=st.text_input("Page title",cfg.get("title","")); subtitle=st.text_input("Subtitle",cfg.get("subtitle","")); pw=st.text_input("Admin password",cfg.get("admin_password",""),type="password")
        auto=st.toggle("Automatically update live results",value=cfg.get("auto_update",False),help="Polls football-data.org and refreshes the bracket. Requires FOOTBALL_DATA_API_KEY in Secrets.")
        secs=st.number_input("Auto-update interval (seconds)",min_value=60,max_value=900,value=max(60,int(cfg.get("auto_update_seconds",90))),step=30)
        if st.button("💾 Save settings",type="primary"):
            try: cfg.update({"title":title,"subtitle":subtitle,"admin_password":pw,"auto_update":auto,"auto_update_seconds":int(secs)}); save_data(data,"Update tracker settings"); st.rerun()
            except Exception as exc: st.error(str(exc))
        repo,token,branch,path=persistence_settings()
        if repo and token and not st.session_state.get("github_data_read_only"): st.success(f"Durable GitHub persistence is active: {repo}/{path} ({branch}).")
        elif repo and token: st.error("GitHub persistence is in safe read-only mode: " + st.session_state.get("github_data_error", "unknown error"))
        else: st.warning("For durable Streamlit Cloud storage, add GITHUB_REPO, GITHUB_TOKEN, GITHUB_BRANCH and GITHUB_DATA_PATH to Secrets. Local files may be lost after sleep or redeploy.")

def main():
    st.session_state.setdefault("is_admin",False)
    data=load_data(); data.setdefault("player_photos",{})
    maybe_auto_sync(data)
    statuses=core.compute_team_statuses(data); cfg=data.get("config",{})
    auth_sidebar(data)
    st.markdown(f'<div class="wc-h1">⚽ {esc(cfg.get("title","World Cup"))}</div>',unsafe_allow_html=True)
    if cfg.get("subtitle"): st.markdown(f'<div class="wc-sub">{esc(cfg["subtitle"])}</div>',unsafe_allow_html=True)
    champ=core.champion(data)
    if champ: st.markdown(f'<div class="wc-champ">🏆 Champions: {flag_html(champ)} {esc(champ)}</div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">🏆 Knockout bracket</div>',unsafe_allow_html=True); st.markdown(bracket_html(data),unsafe_allow_html=True)
    st.caption("All match times are shown in Sydney time. Times update automatically from the fixture API.")
    st.markdown('<div class="section-title">👥 The housemates</div>',unsafe_allow_html=True); st.markdown(players_html(data,statuses),unsafe_allow_html=True)
    with st.expander("🏁 Group stage — who's still in"): st.markdown(group_stage_html(data,statuses),unsafe_allow_html=True)
    if st.session_state.is_admin: st.divider(); admin_panel(data)

if __name__=="__main__": main()
