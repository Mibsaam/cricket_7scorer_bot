import os, json, random, time, threading, urllib.request
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8812331993:AAFP3u9txnbo5H4n81cCaCF0oDxUrVUiYl8"
ADMIN_ID = 874225351
AUTHORIZED_SCORERS = {ADMIN_ID}
DATA_FILE = "master_cricket_database.json"

# ================= 24/7 FLASK KEEP-ALIVE SERVER =================
app = Flask(__name__)

@app.route("/")
def index():
    return "🏏 Pro Cricket Engine 24/7 Online & Active!", 200

@app.route("/health")
def health():
    return "OK", 200

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# ================= CLEAN DATABASE INITIALIZATION =================
def create_blank_match():
    return {
        "match_id": f"M{random.randint(100, 999)}",
        "series_name": "Cricket Championship 2026",
        "series_total_matches": 1,
        "series_current_match_num": 1,
        "ground": "Local Arena",
        "grounds_list": ["Local Arena", "Shivaji Park Arena", "Azad Maidan", "Eden Gardens"],
        "stage": "League Match",
        "current_inning": 1,
        "teams": [],
        "batting_team": "Team A",
        "bowling_team": "Team B",
        "total_match_overs": 7,
        "max_wickets_limit": 10,
        "is_super_over": False,
        "toss_winner": None,
        "toss_decision": None,
        "runs": 0,
        "wickets": 0,
        "overs": 0.0,
        "balls": 0,
        "extras_total": 0,
        "extras_wides": 0,
        "extras_noballs": 0,
        "extras_byes": 0,
        "extras_legbyes": 0,
        "target": 0,
        "is_practice_mode": False,
        "is_free_hit_active": False,
        "free_hit_enabled": True,
        "last_event_ticker": "Match Started! All systems live.",
        "pinned_message_id": None,
        "pinned_chat_id": None,
        "striker": "Select Striker",
        "non_striker": "Select Non-Striker",
        "bowler": "Select Bowler",
        "last_bowler": None,
        "wicketkeeper": "Not Assigned",
        "captain": "Not Assigned",
        "partnership_runs": 0,
        "partnership_balls": 0,
        "current_over_runs": 0,
        "recent_balls": [],
        "fall_of_wickets": [],
        "over_worm": {},
        "match_status": "Active",
        "awaiting_action": None,
        "temp_data": {},
        "history": [],
        "squads": {},
        "match_innings_data": {
            1: {"team": "", "batting": {}, "bowling": {}, "extras": {"w": 0, "nb": 0, "b": 0, "lb": 0, "total": 0}, "fow": []},
            2: {"team": "", "batting": {}, "bowling": {}, "extras": {"w": 0, "nb": 0, "b": 0, "lb": 0, "total": 0}, "fow": []}
        },
        "career_db": {},
        "match_archives": []
    }

match = create_blank_match()

def save_data():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(match, f, indent=2)
    except:
        pass

def load_data():
    global match
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                match = json.load(f)
        except:
            pass

load_data()

def is_admin(uid):
    return uid == ADMIN_ID

def is_scorer(uid):
    return uid in AUTHORIZED_SCORERS or is_admin(uid)

def ensure_player(p_name, team="General"):
    if not p_name or p_name.startswith("Select"): return
    if p_name not in match["career_db"]:
        match["career_db"][p_name] = {
            "uuid": f"PLY_{random.randint(1000, 9999)}",
            "username": None,
            "team": team,
            "matches": 1,
            "runs": 0,
            "balls": 0,
            "fours": 0,
            "sixes": 0,
            "wickets": 0,
            "bowled_balls": 0,
            "runs_given": 0,
            "catches": 0,
            "drops": 0,
            "stumpings": 0
        }
        save_data()

def ensure_match_player_stat(p_name, team, role="bat"):
    inn = match["current_inning"]
    if inn not in match["match_innings_data"]:
        match["match_innings_data"][inn] = {"team": team, "batting": {}, "bowling": {}, "extras": {"w": 0, "nb": 0, "b": 0, "lb": 0, "total": 0}, "fow": []}
    
    if role == "bat":
        if p_name not in match["match_innings_data"][inn]["batting"]:
            match["match_innings_data"][inn]["batting"][p_name] = {
                "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "status": "Not Out"
            }
    elif role == "bowl":
        if p_name not in match["match_innings_data"][inn]["bowling"]:
            match["match_innings_data"][inn]["bowling"][p_name] = {
                "balls": 0, "runs": 0, "wickets": 0, "maidens": 0
            }

def broadcast_commentary(cid, text):
    try:
        bot.send_message(cid, f"🎙️ **MATCH ANNOUNCEMENT:**\n{text}", parse_mode="Markdown")
    except:
        pass

def save_state_for_undo():
    match["history"].append({
        "runs": match["runs"], "wickets": match["wickets"], "overs": match["overs"],
        "balls": match["balls"], "extras_total": match["extras_total"], "extras_wides": match["extras_wides"],
        "extras_noballs": match["extras_noballs"], "extras_byes": match["extras_byes"],
        "extras_legbyes": match["extras_legbyes"], "striker": match["striker"],
        "non_striker": match["non_striker"], "bowler": match["bowler"],
        "partnership_runs": match["partnership_runs"], "partnership_balls": match["partnership_balls"],
        "current_over_runs": match["current_over_runs"], "recent_balls": list(match["recent_balls"]),
        "last_event_ticker": match["last_event_ticker"],
        "match_innings_snapshot": json.loads(json.dumps(match["match_innings_data"]))
    })
    if len(match["history"]) > 30: match["history"].pop(0)

# ================= CRICBUZZ VISUAL DISPLAY & SCORECARD =================
def get_large_scoreboard_text():
    mode = "🦅 [SUPER OVER DECIDER]" if match.get("is_super_over") else ("🧪 [PRACTICE / FAKE MODE]" if match.get("is_practice_mode") else "🏆 [OFFICIAL TOURNAMENT MATCH]")
    fh = " 🔥 [FREE HIT ACTIVE]" if match.get("is_free_hit_active") else ""
    crr = (match['runs'] / (match['balls'] / 6)) if match['balls'] > 0 else 0.0
    
    targ_txt, bar_txt = "", ""
    if match.get("current_inning") == 2:
        needed = max(0, match["target"] - match["runs"])
        b_left = max(0, (match["total_match_overs"] * 6) - match["balls"])
        rrr = (needed / (b_left / 6)) if b_left > 0 else 0.0
        targ_txt = f"\n║ 🎯 **TARGET:** `{match['target']}` │ **NEED:** `{needed} in {b_left}b` (RRR: `{rrr:.2f}`)"
        
        pct = min(100, int((match["runs"] / match["target"]) * 100)) if match["target"] > 0 else 0
        filled = int(pct / 10)
        bar_txt = f"\n║ 📊 Chase Progress: `[{'█'*filled}{'░'*(10-filled)}] {pct}%`"

    b_st = match["match_innings_data"].get(match["current_inning"], {}).get("bowling", {}).get(match["bowler"], {"balls": 0, "runs": 0, "wickets": 0})
    b_ov = f"{b_st['balls'] // 6}.{b_st['balls'] % 6}"
    
    st_b = match["match_innings_data"].get(match["current_inning"], {}).get("batting", {}).get(match["striker"], {"runs": 0, "balls": 0, "fours": 0, "sixes": 0})
    nst_b = match["match_innings_data"].get(match["current_inning"], {}).get("batting", {}).get(match["non_striker"], {"runs": 0, "balls": 0})
    
    rec_balls = " │ ".join(match["recent_balls"][-6:]) if match["recent_balls"] else "•"
    
    return (
        f"╔══════════════════════════════════════╗\n"
        f"║ 🏆 **{match['series_name']}** ({match['stage']})\n"
        f"║ 🏟️ Ground: `{match['ground']}` │ {mode}{fh}\n"
        f"╠══════════════════════════════════════╣\n"
        f"║ 🔴 BATTING: **{match['batting_team']}**\n"
        f"║ 🟢 BOWLING: **{match['bowling_team']}**\n"
        f"╠══════════════════════════════════════╣\n"
        f"║\n"
        f"║       🏏  【 **{match['runs']}  /  {match['wickets']}** 】  ( **{match['overs']}** / {match['total_match_overs']}.0 )  🏏\n"
        f"║\n"
        f"║ ⏳ CRR: `{crr:.2f}` │ EXTRAS: `{match['extras_total']}` (Wd:{match['extras_wides']}, NB:{match['extras_noballs']})\n"
        f"╠══════════════════════════════════════╣"
        f"{targ_txt}{bar_txt}\n"
        f"║ 🤝 **PARTNERSHIP:** `{match['partnership_runs']} runs ({match['partnership_balls']} balls)`\n"
        f"║ 🎞️ **THIS OVER:** `[ {rec_balls} ]`\n"
        f"╠══════════════════════════════════════╣\n"
        f"║ 🏏 **STRIKER:** 👉 **{match['striker']}** 👈 `{st_b['runs']}* ({st_b['balls']}b)` [4s:{st_b['fours']}, 6s:{st_b['sixes']}]\n"
        f"║ 🏃 **RUNNER:**    **{match['non_striker']}** `{nst_b['runs']} ({nst_b['balls']}b)`\n"
        f"║ ⚾ **BOWLER:**    **{match['bowler']}** (`{b_st['wickets']}/{b_st['runs']}` in `{b_ov}` ov)\n"
        f"║ 🧤 **WK:** `{match['wicketkeeper']}` │ 👑 **CAP:** `{match['captain']}`\n"
        f"╠══════════════════════════════════════╣\n"
        f"║ 🎙️ **LIVE TICKER:** {match['last_event_ticker']}\n"
        f"╚══════════════════════════════════════╝"
    )

def generate_detailed_scorecard_text(match_data=None):
    d = match_data if match_data else match
    inn_data = d.get("match_innings_data", {})
    
    out = (
        f"📊 **LIVE MATCH SCORECARD (CRICBUZZ FORMAT)**\n"
        f"🏆 **{d['series_name']}** │ {d['stage']}\n"
        f"🏟️ Ground: `{d['ground']}` │ Total Overs: `{d['total_match_overs']}.0`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    for inn in [1, 2]:
        if inn not in inn_data or not inn_data[inn].get("team"): continue
        i_info = inn_data[inn]
        out += f"\n🔴 **INNINGS {inn}: {i_info['team']}**\n"
        out += "🏏 **BATTING CARD:**\n"
        for p, st in i_info.get("batting", {}).items():
            sr = (st["runs"] / st["balls"] * 100) if st["balls"] > 0 else 0.0
            out += f"• **{p}**: `{st['runs']}` ({st['balls']}b) [4s:{st['fours']}, 6s:{st['sixes']}] │ SR: `{sr:.1f}` │ _{st['status']}_\n"
            
        out += "\n⚾ **BOWLING CARD:**\n"
        for b, st in i_info.get("bowling", {}).items():
            ov = f"{st['balls'] // 6}.{st['balls'] % 6}"
            econ = (st["runs"] / (st["balls"] / 6)) if st["balls"] > 0 else 0.0
            out += f"• **{b}**: `{ov} ov` │ `{st['runs']} runs` │ `{st['wickets']} wkts` │ Econ: `{econ:.2f}`\n"
            
        ex = i_info.get("extras", {})
        out += f"⚡ **Extras:** `{ex.get('total', 0)}` (Wd:{ex.get('w',0)}, NB:{ex.get('nb',0)}, B:{ex.get('b',0)}, LB:{ex.get('lb',0)})\n"
        out += "────────────────────────────────\n"
        
    return out

# ================= DASHBOARD KEYBOARD =================
def get_scorer_keyboard(uid):
    m = InlineKeyboardMarkup(row_width=3)
    
    m.add(
        InlineKeyboardButton("🔴 0 Dot", callback_data="act_run_0"),
        InlineKeyboardButton("🟢 1 Run", callback_data="act_run_1"),
        InlineKeyboardButton("🔵 2 Runs", callback_data="act_run_2")
    )
    m.add(
        InlineKeyboardButton("🟡 3 Runs", callback_data="act_run_3"),
        InlineKeyboardButton("🔥 4 Boundary", callback_data="act_run_4"),
        InlineKeyboardButton("🚀 6 Sixer", callback_data="act_run_6")
    )
    m.add(
        InlineKeyboardButton("✍️ Custom / Overthrow", callback_data="menu_custom_runs"),
        InlineKeyboardButton("⚡ Wide (+Extras)", callback_data="menu_wide"),
        InlineKeyboardButton("⚠️ No Ball (+Runs)", callback_data="menu_noball")
    )
    m.add(
        InlineKeyboardButton("🏃 Byes / Leg Byes", callback_data="menu_byes"),
        InlineKeyboardButton("❌ WICKET MENU", callback_data="menu_wicket"),
        InlineKeyboardButton("😱 Drop Catch", callback_data="act_drop_catch")
    )
    m.add(
        InlineKeyboardButton("🔄 Strike Swap", callback_data="act_swap_strike"),
        InlineKeyboardButton("👤 Striker", callback_data="pop_set_striker"),
        InlineKeyboardButton("🏃 Non-Striker", callback_data="pop_set_nonstriker")
    )
    m.add(
        InlineKeyboardButton("⚾ Bowler", callback_data="pop_set_bowler"),
        InlineKeyboardButton("🚑 Injury Split", callback_data="pop_injury_split"),
        InlineKeyboardButton("🧤 Set WK / Captain", callback_data="menu_set_wk_cap")
    )
    m.add(
        InlineKeyboardButton("🌧️ DLS / Rain Target", callback_data="menu_dls_reduction"),
        InlineKeyboardButton("⚡ Fast Opponent Entry", callback_data="menu_quick_innings"),
        InlineKeyboardButton("✏️ Edit Match Data", callback_data="menu_edit_match")
    )
    m.add(
        InlineKeyboardButton("📊 Score Summary", callback_data="view_summary"),
        InlineKeyboardButton("📜 Match Archives", callback_data="view_archives"),
        InlineKeyboardButton("⭐ MoM / MoS Award", callback_data="view_mom")
    )
    
    if is_admin(uid):
        m.add(
            InlineKeyboardButton("🛡️ Scorer Management", callback_data="menu_scorers_admin"),
            InlineKeyboardButton("👥 Manage Squads & Teams", callback_data="menu_squads_master")
        )
    else:
        m.add(InlineKeyboardButton("👥 Manage Squads & Teams", callback_data="menu_squads_master"))
        
    m.add(
        InlineKeyboardButton("🔄 Switch Innings", callback_data="act_switch_innings"),
        InlineKeyboardButton("↩️ Undo Ball", callback_data="act_undo"),
        InlineKeyboardButton("🗑️ Reset Match", callback_data="act_reset_stats_confirm")
    )
    return m

def sync_pinned_card(cid):
    try:
        txt = get_large_scoreboard_text()
        if match.get("pinned_message_id") and match.get("pinned_chat_id") == cid:
            bot.edit_message_text(txt, chat_id=cid, message_id=match["pinned_message_id"], parse_mode="Markdown")
    except:
        pass

# ================= SETUP WIZARD & COMMANDS =================
@bot.message_handler(commands=['start', 'score', 'cricket', 'setup'])
def handle_start_wizard(msg):
    m = InlineKeyboardMarkup(row_width=1)
    m.add(
        InlineKeyboardButton("🏆 Real Tournament Match", callback_data="wiz_mode_real"),
        InlineKeyboardButton("🧪 Practice / Fake Match", callback_data="wiz_mode_practice")
    )
    bot.reply_to(msg, "🏏 **PRO CRICKET ENGINE - INTERACTIVE SETUP**\n\n📌 **Step 1:** Select Match Mode:", reply_markup=m, parse_mode="Markdown")

@bot.message_handler(commands=['summary'])
def handle_summary_command(msg):
    txt = generate_detailed_scorecard_text()
    bot.reply_to(msg, txt, parse_mode="Markdown")

@bot.message_handler(commands=['profile'])
def handle_profile(msg):
    txt = msg.text.replace("/profile", "").strip()
    found_p, d = None, None
    for p, data in match["career_db"].items():
        if txt and (txt.lower() == p.lower() or (data.get("username") and txt.lower().replace("@", "") == data["username"].lower().replace("@", ""))):
            found_p, d = p, data
            break
    if found_p:
        sr = (d["runs"] / d["balls"] * 100) if d["balls"] > 0 else 0.0
        econ = (d["runs_given"] / (d["bowled_balls"] / 6)) if d["bowled_balls"] > 0 else 0.0
        tot_c = d["catches"] + d["drops"]
        c_eff = (d["catches"] / tot_c * 100) if tot_c > 0 else 100.0
        u_tag = f"@{d['username']}" if d.get('username') else "Not Linked"
        res = (
            f"👤 **LIFETIME CAREER PROFILE - {found_p}**\n"
            f"🆔 UUID: `{d['uuid']}` │ Handle: `{u_tag}` │ Team: `{d['team']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏏 **Batting:** `{d['runs']} Runs` ({d['balls']}b) │ SR: `{sr:.2f}`\n"
            f"🔥 **Boundaries:** `{d['fours']} Fours` │ `{d['sixes']} Sixes`\n"
            f"⚾ **Bowling:** `{d['wickets']} Wickets` │ Econ: `{econ:.2f}`\n"
            f"🧤 **Fielding:** `{d['catches']} Catches` │ `{d['drops']} Drops` (Catch Eff: `{c_eff:.1f}%`)\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        bot.reply_to(msg, res, parse_mode="Markdown")
    else:
        bot.reply_to(msg, "❌ Player nahi mila! Use: `/profile PlayerName` ya `/profile @username`", parse_mode="Markdown")

def check_match_completion(cid):
    limit_w = match["max_wickets_limit"]
    if match["current_inning"] == 2:
        if match["runs"] >= match["target"]:
            w_left = limit_w - match["wickets"]
            b_left = max(0, (match["total_match_overs"] * 6) - match["balls"])
            txt = f"🏆 🎊 **CHAMPIONS!** **{match['batting_team']}** WON by **{w_left} wickets** (with {b_left} balls remaining)! 🥇"
            broadcast_commentary(cid, txt)
            archive_match()
        elif match["overs"] >= match["total_match_overs"] or match["wickets"] >= limit_w:
            margin = (match["target"] - 1) - match["runs"]
            if margin == 0:
                broadcast_commentary(cid, "🔥 ⚖️ **WHAT A THRILLER! MATCH TIED!**")
            elif margin > 0:
                txt = f"🏆 🎊 **VICTORY!** **{match['bowling_team']}** WON by **{margin} runs**! 🥇"
                broadcast_commentary(cid, txt)
            archive_match()

def archive_match():
    if not match["is_practice_mode"]:
        m_entry = {
            "match_id": match["match_id"],
            "series_name": match["series_name"],
            "ground": match["ground"],
            "stage": match["stage"],
            "total_match_overs": match["total_match_overs"],
            "teams": f"{match['teams'][0] if match.get('teams') else match['batting_team']} vs {match['teams'][1] if len(match.get('teams', [])) > 1 else match['bowling_team']}",
            "winner": match["batting_team"] if match["runs"] >= match["target"] else match["bowling_team"],
            "match_innings_data": json.loads(json.dumps(match["match_innings_data"]))
        }
        match["match_archives"].append(m_entry)
        save_data()

def register_legal_ball(cid, legal=True, ball_tag="0"):
    if legal:
        match["balls"] += 1
        match["partnership_balls"] += 1
        comp_ov = match["balls"] // 6
        rem_b = match["balls"] % 6
        match["overs"] = float(f"{comp_ov}.{rem_b}")
        match["recent_balls"].append(ball_tag)
        
        if match["bowler"] == "Select Bowler":
            match["bowler"] = f"Bowler (Ov {comp_ov + 1})"
            
        ensure_player(match["bowler"], match["bowling_team"])
        ensure_match_player_stat(match["bowler"], match["bowling_team"], role="bowl")
        
        match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["balls"] += 1
        if match["bowler"] in match["career_db"]:
            match["career_db"][match["bowler"]]["bowled_balls"] += 1
        
        if match["is_free_hit_active"]:
            match["is_free_hit_active"] = False

        if rem_b == 0 and match["balls"] > 0:
            match["over_worm"][comp_ov] = match["current_over_runs"]
            match["current_over_runs"] = 0
            match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            match["last_bowler"] = match["bowler"]
            match["bowler"] = "Select Bowler"
            match["last_event_ticker"] = f"🏁 Over {comp_ov} Complete! Strike rotated to {match['striker']}."
            
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["bowling_team"], []):
                if p != match["last_bowler"]:
                    m.add(InlineKeyboardButton(f"⚾ {p}", callback_data=f"sel_bowl_{p}"))
            m.add(InlineKeyboardButton("➕ Type New Bowler", callback_data="type_new_bowler"))
            try:
                bot.send_message(cid, f"🚨 **Select Next Bowler for Over {comp_ov+1}:**", reply_markup=m, parse_mode="Markdown")
            except:
                pass

        save_data()
        sync_pinned_card(cid)
        check_match_completion(cid)

# ================= CALLBACK QUERY ROUTER =================
@bot.callback_query_handler(func=lambda c: True)
def master_action_handler(c):
    try:
        uid, dt = c.from_user.id, c.data
        cid = c.message.chat.id

        # VIEW ONLY ACTIONS
        if dt == "view_summary":
            bot.answer_callback_query(c.id)
            return bot.send_message(cid, generate_detailed_scorecard_text(), parse_mode="Markdown")

        if dt == "view_archives":
            bot.answer_callback_query(c.id)
            if not match["match_archives"]:
                return bot.send_message(cid, "⚠️ Abhi tak koi match archive record mein nahi hai!")
            m = InlineKeyboardMarkup(row_width=1)
            for arc in match["match_archives"][-8:]:
                m.add(InlineKeyboardButton(f"📁 #{arc['match_id']}: {arc['teams']}", callback_data=f"arc_{arc['match_id']}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("📜 **MATCH ARCHIVE VAULT:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("arc_"):
            bot.answer_callback_query(c.id)
            m_id = dt.replace("arc_", "")
            entry = next((a for a in match["match_archives"] if a["match_id"] == m_id), None)
            if entry:
                return bot.send_message(cid, generate_detailed_scorecard_text(entry), parse_mode="Markdown")

        if dt == "view_mom":
            bot.answer_callback_query(c.id)
            win_team = match["batting_team"] if match["runs"] >= match["target"] and match["current_inning"] == 2 else match["bowling_team"]
            best_p, max_pts = "None", -999
            for p, st in match["career_db"].items():
                is_win_player = (st["team"] == win_team)
                win_bonus = 30 if is_win_player else 0
                pts = (st["runs"] * 1.5) + (st["fours"] * 2.0) + (st["sixes"] * 4.0) + (st["wickets"] * 35) + (st["catches"] * 15) - (st["drops"] * 5) + win_bonus
                if pts > max_pts:
                    max_pts, best_p = pts, p
            return bot.send_message(cid, f"⭐ **MAN OF THE MATCH:** `{best_p}` (Impact: `{max_pts:.1f}` pts)\n🏆 Priority awarded to winning team impact!", parse_mode="Markdown")

        # SCORER SECURITY CHECK
        if not match["is_practice_mode"] and not is_scorer(uid):
            return bot.answer_callback_query(c.id, "⚠️ Only Official Scorers & Admin can score in Real Mode!", show_alert=True)

        bot.answer_callback_query(c.id)

        # ================= STEP-BY-STEP SETUP WIZARD =================
        if dt in ["wiz_mode_real", "wiz_mode_practice"]:
            match["is_practice_mode"] = (dt == "wiz_mode_practice")
            match["is_super_over"] = False
            m = InlineKeyboardMarkup(row_width=1)
            m.add(
                InlineKeyboardButton("⚡ Single Standalone Match", callback_data="wiz_series_1"),
                InlineKeyboardButton("🏆 3-Match Bilateral Series", callback_data="wiz_series_3"),
                InlineKeyboardButton("🏆 5-Match Bilateral Series", callback_data="wiz_series_5")
            )
            return bot.edit_message_text("📌 **Step 1.2:** Select **Tournament / Series Format:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("wiz_series_"):
            match["series_total_matches"] = int(dt.replace("wiz_series_", ""))
            m = InlineKeyboardMarkup(row_width=2)
            for t in match.get("teams", []):
                m.add(InlineKeyboardButton(f"📁 {t}", callback_data=f"wiz_t1_{t}"))
            m.add(InlineKeyboardButton("➕ Create Team", callback_data="wiz_create_team"))
            return bot.edit_message_text("📌 **Step 2:** Select **Team 1** (or Create New):", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "wiz_create_team":
            match["awaiting_action"] = "wiz_input_team"
            return bot.edit_message_text("✍️ Nayi **Team ka Naam** type karke send karein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        if dt.startswith("wiz_t1_"):
            t1 = dt.replace("wiz_t1_", "")
            match["temp_data"]["wiz_team1"] = t1
            m = InlineKeyboardMarkup(row_width=2)
            for t in match.get("teams", []):
                if t != t1:
                    m.add(InlineKeyboardButton(f"📁 {t}", callback_data=f"wiz_t2_{t}"))
            m.add(InlineKeyboardButton("➕ Create Team 2", callback_data="wiz_create_team_2"))
            return bot.edit_message_text(f"📌 **Step 2.2:** Team 1: **{t1}**\nAb **Team 2** select karein:", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "wiz_create_team_2":
            match["awaiting_action"] = "wiz_input_team_2"
            return bot.edit_message_text("✍️ Dusri **Team ka Naam** type karke send karein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        if dt.startswith("wiz_t2_"):
            t2 = dt.replace("wiz_t2_", "")
            t1 = match["temp_data"].get("wiz_team1", match["teams"][0] if match["teams"] else "Team 1")
            match["teams"] = [t1, t2]
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("🪙 Auto Random Toss", callback_data="wiz_toss_auto"))
            m.add(InlineKeyboardButton("✍️ Manual Toss Selection", callback_data="wiz_toss_manual"))
            return bot.edit_message_text(f"📌 **Step 3:** Toss Setup for **{t1} vs {t2}**:", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "wiz_toss_auto":
            winner = random.choice(match["teams"])
            dec = random.choice(["bat", "bowl"])
            match["toss_winner"], match["toss_decision"] = winner, dec
            other = [t for t in match["teams"] if t != winner][0]
            if dec == "bat": match["batting_team"], match["bowling_team"] = winner, other
            else: match["bowling_team"], match["batting_team"] = winner, other
            return start_wizard_squad_step(cid, c.message.message_id)

        if dt == "wiz_toss_manual":
            m = InlineKeyboardMarkup(row_width=2)
            for t in match["teams"]:
                m.add(InlineKeyboardButton(f"🔴 {t} (Bat)", callback_data=f"wiz_set_bat_{t}"))
            return bot.edit_message_text("📌 **Step 3.2:** Kaunsi team **Pehle Batting** karegi?", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("wiz_set_bat_"):
            b_team = dt.replace("wiz_set_bat_", "")
            other = [t for t in match["teams"] if t != b_team][0]
            match["batting_team"], match["bowling_team"] = b_team, other
            return start_wizard_squad_step(cid, c.message.message_id)

        if dt.startswith("wiz_str_"):
            p_name = dt.replace("wiz_str_", "")
            match["striker"] = p_name
            ensure_player(p_name, match["batting_team"])
            ensure_match_player_stat(p_name, match["batting_team"], role="bat")
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["batting_team"], []):
                if p != p_name:
                    m.add(InlineKeyboardButton(f"🏃 {p}", callback_data=f"wiz_nstr_{p}"))
            m.add(InlineKeyboardButton("➕ Type Non-Striker", callback_data="wiz_type_nonstriker"))
            return bot.edit_message_text(f"👤 Striker: **{p_name}**\n\n📌 **Step 7.2:** Select **Non-Striker (Runner):**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("wiz_nstr_"):
            p_name = dt.replace("wiz_nstr_", "")
            match["non_striker"] = p_name
            ensure_player(p_name, match["batting_team"])
            ensure_match_player_stat(p_name, match["batting_team"], role="bat")
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["bowling_team"], []):
                m.add(InlineKeyboardButton(f"⚾ {p}", callback_data=f"wiz_bowl_{p}"))
            m.add(InlineKeyboardButton("➕ Type Opening Bowler", callback_data="wiz_type_bowler"))
            return bot.edit_message_text(f"🏃 Runner: **{p_name}**\n\n📌 **Step 7.3:** Select **Opening Bowler ({match['bowling_team']}):**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("wiz_bowl_"):
            p_name = dt.replace("wiz_bowl_", "")
            match["bowler"] = p_name
            ensure_player(p_name, match["bowling_team"])
            ensure_match_player_stat(p_name, match["bowling_team"], role="bowl")
            save_data()
            msg_obj = bot.send_message(cid, get_large_scoreboard_text(), reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")
            try:
                bot.pin_chat_message(cid, msg_obj.message_id)
                match["pinned_message_id"] = msg_obj.message_id
                match["pinned_chat_id"] = cid
                save_data()
            except:
                pass
            return

        # ================= 1-CLICK INSTANT SCORING =================
        if dt.startswith("act_run_"):
            r = int(dt.replace("act_run_", ""))
            save_state_for_undo()
            
            if match["striker"] == "Select Striker": match["striker"] = "Batsman 1"
            if match["non_striker"] == "Select Non-Striker": match["non_striker"] = "Batsman 2"
            if match["bowler"] == "Select Bowler": match["bowler"] = "Bowler 1"
                
            ensure_match_player_stat(match["striker"], match["batting_team"], role="bat")
            ensure_match_player_stat(match["bowler"], match["bowling_team"], role="bowl")
            
            match["runs"] += r
            match["current_over_runs"] += r
            match["partnership_runs"] += r
            
            st_stat = match["match_innings_data"][match["current_inning"]]["batting"][match["striker"]]
            st_stat["runs"] += r
            st_stat["balls"] += 1
            if r == 4: st_stat["fours"] += 1
            if r == 6: st_stat["sixes"] += 1
            
            if match["striker"] in match["career_db"]:
                p_c = match["career_db"][match["striker"]]
                p_c["runs"] += r
                p_c["balls"] += 1
                if r == 4: p_c["fours"] += 1
                if r == 6: p_c["sixes"] += 1
                
            match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["runs"] += r
            if match["bowler"] in match["career_db"]:
                match["career_db"][match["bowler"]]["runs_given"] += r
                
            event_txt = f"⚡ {r} Runs by {match['striker']}"
            if r == 4: event_txt = f"🔥 FOUR! {match['striker']} smashes boundary!"
            elif r == 6: event_txt = f"🚀 MAXIMUM! {match['striker']} launches huge six!"
            match["last_event_ticker"] = event_txt
            
            register_legal_ball(cid, legal=True, ball_tag=str(r))
            if r in [1, 3, 5, 7]: match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
                
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # CUSTOM OVERTHROW RUNS
        if dt == "menu_custom_runs":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("5 Runs (1+4 Overthrow)", callback_data="exec_cust_5"))
            m.add(InlineKeyboardButton("7 Runs (3+4 Overthrow)", callback_data="exec_cust_7"))
            m.add(InlineKeyboardButton("✍️ Type Manual Runs", callback_data="type_custom_runs_val"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("✍️ **Select Custom / Overthrow Runs:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("exec_cust_"):
            r = int(dt.replace("exec_cust_", ""))
            save_state_for_undo()
            ensure_match_player_stat(match["striker"], match["batting_team"], role="bat")
            ensure_match_player_stat(match["bowler"], match["bowling_team"], role="bowl")
            match["runs"] += r
            match["current_over_runs"] += r
            match["partnership_runs"] += r
            match["match_innings_data"][match["current_inning"]]["batting"][match["striker"]]["runs"] += r
            match["match_innings_data"][match["current_inning"]]["batting"][match["striker"]]["balls"] += 1
            match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["runs"] += r
            match["last_event_ticker"] = f"⚡ OVERTHROW! {r} Runs scored by {match['striker']}!"
            register_legal_ball(cid, legal=True, ball_tag=f"OT+{r}")
            if r % 2 != 0: match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "type_custom_runs_val":
            match["awaiting_action"] = "input_custom_runs"
            return bot.edit_message_text("✍️ Kitne runs bane type karke send karein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        # WIDE & NO BALL WITH FREE HIT PROMPT
        if dt == "menu_wide":
            m = InlineKeyboardMarkup(row_width=3)
            for r in range(6): m.add(InlineKeyboardButton(f"Wide + {r}", callback_data=f"exec_wide_{r}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("⚡ **Select Wide Deliveries:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("exec_wide_"):
            ex = int(dt.replace("exec_wide_", ""))
            tot = 1 + ex
            save_state_for_undo()
            match["runs"] += tot
            match["current_over_runs"] += tot
            match["extras_total"] += tot
            match["extras_wides"] += tot
            match["match_innings_data"][match["current_inning"]]["extras"]["w"] += tot
            match["match_innings_data"][match["current_inning"]]["extras"]["total"] += tot
            ensure_match_player_stat(match["bowler"], match["bowling_team"], role="bowl")
            match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["runs"] += tot
            match["recent_balls"].append(f"Wd+{ex}")
            match["last_event_ticker"] = f"⚡ Wide Ball (+{tot} Extras)"
            if ex % 2 != 0: match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            save_data()
            check_match_completion(cid)
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "menu_noball":
            m = InlineKeyboardMarkup(row_width=3)
            for r in range(7): m.add(InlineKeyboardButton(f"NB + {r} Runs", callback_data=f"exec_nb_{r}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("⚠️ **Select No Ball Deliveries (+1 Auto):**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("exec_nb_"):
            bat_r = int(dt.replace("exec_nb_", ""))
            tot = 1 + bat_r
            save_state_for_undo()
            match["runs"] += tot
            match["current_over_runs"] += tot
            match["extras_total"] += 1
            match["extras_noballs"] += 1
            match["partnership_runs"] += bat_r
            match["match_innings_data"][match["current_inning"]]["extras"]["nb"] += 1
            match["match_innings_data"][match["current_inning"]]["extras"]["total"] += 1
            
            ensure_match_player_stat(match["striker"], match["batting_team"], role="bat")
            ensure_match_player_stat(match["bowler"], match["bowling_team"], role="bowl")
            
            st_stat = match["match_innings_data"][match["current_inning"]]["batting"][match["striker"]]
            st_stat["runs"] += bat_r
            if bat_r == 4: st_stat["fours"] += 1
            if bat_r == 6: st_stat["sixes"] += 1
            
            match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["runs"] += tot
            match["recent_balls"].append(f"NB+{bat_r}")
            if bat_r % 2 != 0: match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            save_data()
            
            m = InlineKeyboardMarkup(row_width=1)
            m.add(
                InlineKeyboardButton("🔥 Enable Free Hit Next Ball", callback_data="nb_fh_enable"),
                InlineKeyboardButton("⚡ Standard Delivery (No Free Hit)", callback_data="nb_fh_disable")
            )
            return bot.edit_message_text(f"⚠️ **NO BALL (+{tot} Runs Recorded)!**\nKya agli ball par Free Hit enforce karni hai?", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "nb_fh_enable":
            match["is_free_hit_active"] = True
            match["last_event_ticker"] = "⚠️ NO BALL! Free Hit is ACTIVE on next delivery!"
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "nb_fh_disable":
            match["is_free_hit_active"] = False
            match["last_event_ticker"] = "⚠️ NO BALL! Standard delivery will follow."
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # BYES & LEG BYES
        if dt == "menu_byes":
            m = InlineKeyboardMarkup(row_width=3)
            m.add(InlineKeyboardButton("Bye +1", callback_data="exec_bye_1"), InlineKeyboardButton("Bye +2", callback_data="exec_bye_2"), InlineKeyboardButton("Bye +4", callback_data="exec_bye_4"))
            m.add(InlineKeyboardButton("Leg Bye +1", callback_data="exec_lb_1"), InlineKeyboardButton("Leg Bye +2", callback_data="exec_lb_2"), InlineKeyboardButton("Leg Bye +4", callback_data="exec_lb_4"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("🏃 **Dynamic Byes / Leg Byes Menu:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("exec_bye_") or dt.startswith("exec_lb_"):
            parts = dt.split("_")
            b_val, is_bye = int(parts[2]), (parts[1] == "bye")
            save_state_for_undo()
            match["runs"] += b_val
            match["current_over_runs"] += b_val
            match["extras_total"] += b_val
            if is_bye:
                match["extras_byes"] += b_val
                match["match_innings_data"][match["current_inning"]]["extras"]["b"] += b_val
            else:
                match["extras_legbyes"] += b_val
                match["match_innings_data"][match["current_inning"]]["extras"]["lb"] += b_val
            match["match_innings_data"][match["current_inning"]]["extras"]["total"] += b_val
            match["last_event_ticker"] = f"🏃 {'Byes' if is_bye else 'Leg Byes'} (+{b_val} runs)"
            register_legal_ball(cid, legal=True, ball_tag=f"{'B' if is_bye else 'LB'}+{b_val}")
            if b_val % 2 != 0: match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # WICKET ENGINE & CATCHES
        if dt == "menu_wicket":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("🔴 Bowled", callback_data="wkt_bowled"), InlineKeyboardButton("🟡 Caught Out", callback_data="wkt_caught_menu"))
            m.add(InlineKeyboardButton("🟢 Run Out", callback_data="wkt_runout"), InlineKeyboardButton("🔵 Stumped", callback_data="wkt_stumped"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("❌ **Select Dismissal Type:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt in ["wkt_bowled", "wkt_stumped", "wkt_runout"]:
            if dt in ["wkt_bowled", "wkt_stumped"] and match["is_free_hit_active"]:
                return bot.send_message(cid, "⚠️ Free Hit Active! Only Run Out allowed!")
            return process_wicket(cid, c.message.message_id, dt.replace("wkt_", "").capitalize(), uid)

        if dt == "wkt_caught_menu":
            if match["is_free_hit_active"]:
                return bot.send_message(cid, "⚠️ Free Hit Active! Catch out not allowed!")
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("⚡ Quick Catch (Skip Fielder)", callback_data="wkt_caught_quick"))
            for fld in match["squads"].get(match["bowling_team"], []):
                m.add(InlineKeyboardButton(f"🙌 {fld}", callback_data=f"catch_by_{fld}"))
            m.add(InlineKeyboardButton("➕ Type Fielder Name", callback_data="type_catch_fielder"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_wicket"))
            return bot.edit_message_text(f"🙌 **Who took the catch ({match['bowling_team']})?**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "wkt_caught_quick":
            return process_wicket(cid, c.message.message_id, "Caught", uid)

        if dt.startswith("catch_by_"):
            f_name = dt.replace("catch_by_", "")
            ensure_player(f_name, match["bowling_team"])
            if f_name in match["career_db"]: match["career_db"][f_name]["catches"] += 1
            return process_wicket(cid, c.message.message_id, f"c {f_name} b {match['bowler']}", uid)

        if dt == "act_drop_catch":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("⚡ Quick Log (Skip Fielder)", callback_data="drop_by_general"))
            for fld in match["squads"].get(match["bowling_team"], []):
                m.add(InlineKeyboardButton(f"❌ {fld}", callback_data=f"drop_by_{fld}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("😱 **Who dropped the catch?**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("drop_by_"):
            f_name = dt.replace("drop_by_", "")
            if f_name != "general":
                ensure_player(f_name, match["bowling_team"])
                if f_name in match["career_db"]: match["career_db"][f_name]["drops"] += 1
            match["last_event_ticker"] = f"😱 CATCH DROPPED off {match['bowler']}!"
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # BATSMAN / BOWLER REPLACEMENTS
        if dt == "pop_set_striker":
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["batting_team"], []):
                if p != match["non_striker"]:
                    m.add(InlineKeyboardButton(f"🏏 {p}", callback_data=f"sel_str_{p}"))
            m.add(InlineKeyboardButton("➕ Type New Batsman", callback_data="type_new_striker"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("👤 **Select Striker:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("sel_str_"):
            p_name = dt.replace("sel_str_", "")
            match["striker"] = p_name
            ensure_player(p_name, match["batting_team"])
            ensure_match_player_stat(p_name, match["batting_team"], role="bat")
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "pop_set_nonstriker":
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["batting_team"], []):
                if p != match["striker"]:
                    m.add(InlineKeyboardButton(f"🏃 {p}", callback_data=f"sel_nonstr_{p}"))
            m.add(InlineKeyboardButton("➕ Type New Non-Striker", callback_data="type_new_nonstriker"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("🏃 **Select Non-Striker (Runner):**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("sel_nonstr_"):
            p_name = dt.replace("sel_nonstr_", "")
            match["non_striker"] = p_name
            ensure_player(p_name, match["batting_team"])
            ensure_match_player_stat(p_name, match["batting_team"], role="bat")
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "pop_set_bowler":
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["bowling_team"], []):
                m.add(InlineKeyboardButton(f"⚾ {p}", callback_data=f"sel_bowl_{p}"))
            m.add(InlineKeyboardButton("➕ Type New Bowler", callback_data="type_new_bowler"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("⚾ **Select Bowler:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("sel_bowl_"):
            p_name = dt.replace("sel_bowl_", "")
            match["bowler"] = p_name
            ensure_player(p_name, match["bowling_team"])
            ensure_match_player_stat(p_name, match["bowling_team"], role="bowl")
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # SCORER MANAGEMENT (ADMIN ONLY)
        if dt == "menu_scorers_admin":
            if not is_admin(uid): return bot.answer_callback_query(c.id, "⚠️ Admin only!", show_alert=True)
            m = InlineKeyboardMarkup(row_width=1)
            m.add(
                InlineKeyboardButton("➕ Add New Official Scorer", callback_data="pop_add_scorer"),
                InlineKeyboardButton("📋 View Active Scorers", callback_data="pop_view_scorers"),
                InlineKeyboardButton("⬅️ Back", callback_data="back_main")
            )
            return bot.edit_message_text("🛡️ **Official Scorer Management:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "pop_add_scorer":
            match["awaiting_action"] = "input_add_scorer"
            return bot.edit_message_text("✍️ Naye Scorer ki **Telegram User ID** type karke bhejein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        if dt == "pop_view_scorers":
            s_list = "\n".join([f"• `{s}`" for s in AUTHORIZED_SCORERS])
            return bot.send_message(cid, f"📋 **CURRENT AUTHORIZED SCORERS:**\n{s_list}", parse_mode="Markdown")

        # EDIT MATCH AUDIT PANEL
        if dt == "menu_edit_match":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("🏏 Edit Total Runs", callback_data="edit_tot_runs"))
            m.add(InlineKeyboardButton("❌ Edit Total Wickets", callback_data="edit_tot_wkts"))
            m.add(InlineKeyboardButton("🎯 Edit Target", callback_data="edit_tot_target"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("✏️ **Live Match Data Correction:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "edit_tot_runs":
            match["awaiting_action"] = "input_edit_runs"
            return bot.edit_message_text("✍️ Sahi **Total Runs** type karke send karein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        if dt == "edit_tot_wkts":
            match["awaiting_action"] = "input_edit_wkts"
            return bot.edit_message_text("✍️ Sahi **Total Wickets** type karke send karein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        if dt == "edit_tot_target":
            match["awaiting_action"] = "input_edit_target"
            return bot.edit_message_text("✍️ Naya **Target** type karke send karein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        # DLS REDUCTION
        if dt == "menu_dls_reduction":
            match["awaiting_action"] = "input_dls_revised_overs"
            return bot.edit_message_text("🌧️ **DLS Rain Overs Reduction:**\nBarish ke baad match ke **Revised Total Overs** kitne hue? Type karein (e.g. 5):", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        # SAFE UNDO & RESTORATION
        if dt == "act_undo":
            if not match["history"]:
                return bot.send_message(cid, "⚠️ Undo karne ke liye koi purana state nahi hai!")
            last_st = match["history"].pop()
            match["match_innings_data"] = last_st.pop("match_innings_snapshot", match["match_innings_data"])
            match.update(last_st)
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "act_swap_strike":
            match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            match["last_event_ticker"] = f"🔄 Strike swapped manually to {match['striker']}"
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "act_switch_innings":
            if match["current_inning"] == 1:
                match["target"] = match["runs"] + 1
                match["current_inning"] = 2
                other = [t for t in match["teams"] if t != match["batting_team"]]
                next_bat = other[0] if other else match["bowling_team"]
                match["bowling_team"], match["batting_team"] = match["batting_team"], next_bat
                match.update({"runs": 0, "wickets": 0, "overs": 0.0, "balls": 0, "extras_total": 0, "extras_wides": 0, "extras_noballs": 0, "extras_byes": 0, "extras_legbyes": 0, "partnership_runs": 0, "partnership_balls": 0, "recent_balls": [], "current_over_runs": 0, "striker": "Select Striker", "non_striker": "Select Non-Striker", "bowler": "Select Bowler", "last_event_ticker": f"Innings 2 Started! Target: {match['target']}"})
                save_data()
                broadcast_commentary(cid, f"🔄 **INNINGS BREAK!** **{match['batting_team']}** need `{match['target']}` runs to win!")
                return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "act_reset_stats_confirm":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("⚠️ Yes, Reset", callback_data="act_reset_stats_exec"), InlineKeyboardButton("❌ Cancel", callback_data="back_main"))
            return bot.edit_message_text("⚠️ **Kya aap current match score reset karna chahte hain?**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "act_reset_stats_exec":
            match.update({"runs": 0, "wickets": 0, "overs": 0.0, "balls": 0, "extras_total": 0, "extras_wides": 0, "extras_noballs": 0, "extras_byes": 0, "extras_legbyes": 0, "partnership_runs": 0, "partnership_balls": 0, "recent_balls": [], "current_over_runs": 0, "history": [], "last_event_ticker": "Match stats reset clean."})
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "back_main":
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

    except Exception as e:
        print(f"Callback error: {e}")

# ================= WIZARD HELPER FUNCTIONS =================
def start_wizard_squad_step(cid, mid):
    t1, t2 = match["teams"][0], match["teams"][1]
    if t1 not in match["squads"]: match["squads"][t1] = []
    if t2 not in match["squads"]: match["squads"][t2] = []
    
    m = InlineKeyboardMarkup(row_width=2)
    m.add(InlineKeyboardButton(f"➕ Add Player ({t1})", callback_data=f"wiz_add_p_{t1}"))
    m.add(InlineKeyboardButton(f"➕ Add Player ({t2})", callback_data=f"wiz_add_p_{t2}"))
    m.add(InlineKeyboardButton("➡️ Continue to Ground & Overs", callback_data="wiz_ground_step"))
    return bot.edit_message_text(f"📌 **Step 4:** Manage Squads for **{t1}** & **{t2}**:\n(Players add karein ya direct aage badhein)", chat_id=cid, message_id=mid, reply_markup=m, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("wiz_add_p_"))
def wizard_add_player_prompt(c):
    team_n = c.data.replace("wiz_add_p_", "")
    match["temp_data"]["target_team"] = team_n
    match["awaiting_action"] = "input_squad_player"
    bot.edit_message_text(f"✍️ **{team_n}** ke player ka naam type karke send karein:", chat_id=c.message.chat.id, message_id=c.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "wiz_ground_step")
def wizard_ground_step_callback(c):
    m = InlineKeyboardMarkup(row_width=2)
    for g in match["grounds_list"]:
        m.add(InlineKeyboardButton(f"🏟️ {g}", callback_data=f"wiz_set_g_{g}"))
    m.add(InlineKeyboardButton("✍️ Type Custom Ground", callback_data="wiz_type_ground"))
    bot.edit_message_text("📌 **Step 5:** Select **Match Ground:**", chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("wiz_set_g_"))
def wizard_set_ground_callback(c):
    g_name = c.data.replace("wiz_set_g_", "")
    match["ground"] = g_name
    m = InlineKeyboardMarkup(row_width=3)
    m.add(InlineKeyboardButton("✍️ Type Custom / Manual Overs", callback_data="wiz_type_overs"))
    for ov in [5, 7, 8, 10, 12, 15, 20]:
        m.add(InlineKeyboardButton(f"{ov} Overs", callback_data=f"wiz_set_ov_{ov}"))
    bot.edit_message_text(f"🏟️ Ground: **{g_name}**\n\n📌 **Step 6:** Select **Total Match Overs:**", chat_id=c.message.chat.id, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data.startswith("wiz_set_ov_"))
def wizard_set_overs_callback(c):
    ov = int(c.data.replace("wiz_set_ov_", ""))
    match["total_match_overs"] = ov
    save_data()
    start_wizard_openers_step(c.message.chat.id, c.message.message_id)

def start_wizard_openers_step(cid, mid):
    m = InlineKeyboardMarkup(row_width=2)
    for p in match["squads"].get(match["batting_team"], []):
        m.add(InlineKeyboardButton(f"🏏 {p}", callback_data=f"wiz_str_{p}"))
    m.add(InlineKeyboardButton("➕ Type Striker", callback_data="wiz_type_striker"))
    if mid:
        bot.edit_message_text(f"📌 **Step 7.1:** Select **Opening Striker ({match['batting_team']}):**", chat_id=cid, message_id=mid, reply_markup=m, parse_mode="Markdown")
    else:
        bot.send_message(cid, f"📌 **Step 7.1:** Select **Opening Striker ({match['batting_team']}):**", reply_markup=m, parse_mode="Markdown")

def process_wicket(cid, mid, reason, uid):
    limit_w = match["max_wickets_limit"]
    if match["wickets"] < limit_w:
        save_state_for_undo()
        match["wickets"] += 1
        
        ensure_match_player_stat(match["striker"], match["batting_team"], role="bat")
        ensure_match_player_stat(match["bowler"], match["bowling_team"], role="bowl")
        
        match["match_innings_data"][match["current_inning"]]["batting"][match["striker"]]["balls"] += 1
        match["match_innings_data"][match["current_inning"]]["batting"][match["striker"]]["status"] = reason
        
        if "Run Out" not in reason:
            match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["wickets"] += 1
            if match["bowler"] in match["career_db"]:
                match["career_db"][match["bowler"]]["wickets"] += 1
                
        match["last_event_ticker"] = f"🚨 WICKET! {match['striker']} ({reason})!"
        match["partnership_runs"], match["partnership_balls"] = 0, 0
        register_legal_ball(cid, legal=True, ball_tag="W")
        
        out_batter = match["striker"]
        match["striker"] = "Select Striker"
        save_data()
        
        m = InlineKeyboardMarkup(row_width=2)
        for p in match["squads"].get(match["batting_team"], []):
            if p != match["non_striker"] and p != out_batter:
                m.add(InlineKeyboardButton(f"🏏 {p}", callback_data=f"sel_str_{p}"))
        m.add(InlineKeyboardButton("➕ Type Next Batsman", callback_data="type_new_striker"))
        bot.send_message(cid, f"👤 **{out_batter} OUT!** Next Batsman select karein:", reply_markup=m, parse_mode="Markdown")
        if mid:
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

# ================= TEXT INPUT HANDLER =================
@bot.message_handler(func=lambda m: match.get("awaiting_action") is not None)
def handle_text_inputs(msg):
    uid = msg.from_user.id
    act = match.get("awaiting_action")
    txt = msg.text.strip()
    match["awaiting_action"] = None
    
    if act == "wiz_input_team":
        if txt not in match["teams"]: match["teams"].append(txt)
        match["squads"][txt] = []
        match["temp_data"]["wiz_team1"] = txt
        save_data()
        m = InlineKeyboardMarkup(row_width=2)
        for t in match["teams"]:
            if t != txt: m.add(InlineKeyboardButton(f"📁 {t}", callback_data=f"wiz_t2_{t}"))
        m.add(InlineKeyboardButton("➕ Create Team 2", callback_data="wiz_create_team_2"))
        bot.reply_to(msg, f"✅ Team 1 set to **{txt}**!\n\n📌 Select **Team 2**:", reply_markup=m, parse_mode="Markdown")

    elif act == "wiz_input_team_2":
        if txt not in match["teams"]: match["teams"].append(txt)
        match["squads"][txt] = []
        t1 = match["temp_data"].get("wiz_team1", match["teams"][0])
        match["teams"] = [t1, txt]
        save_data()
        m = InlineKeyboardMarkup(row_width=2)
        m.add(InlineKeyboardButton("🪙 Auto Random Toss", callback_data="wiz_toss_auto"))
        m.add(InlineKeyboardButton("✍️ Manual Toss Selection", callback_data="wiz_toss_manual"))
        bot.reply_to(msg, f"✅ Team 2 set to **{txt}**!\n\n📌 **Step 3:** Toss Setup for **{t1} vs {txt}**:", reply_markup=m, parse_mode="Markdown")

    elif act == "input_squad_player":
        t_target = match["temp_data"].get("target_team", match["batting_team"])
        if t_target not in match["squads"]: match["squads"][t_target] = []
        if txt not in match["squads"][t_target]: match["squads"][t_target].append(txt)
        ensure_player(txt, t_target)
        save_data()
        m = InlineKeyboardMarkup(row_width=2)
        m.add(InlineKeyboardButton(f"➕ Add Another to {t_target}", callback_data=f"wiz_add_p_{t_target}"))
        m.add(InlineKeyboardButton("➡️ Continue to Ground & Overs", callback_data="wiz_ground_step"))
        bot.reply_to(msg, f"✅ Added **{txt}** to **{t_target}**!", reply_markup=m, parse_mode="Markdown")

    elif act == "input_add_scorer":
        try:
            s_uid = int(txt)
            AUTHORIZED_SCORERS.add(s_uid)
            bot.reply_to(msg, f"✅ User ID `{s_uid}` is now an Authorized Scorer!")
        except:
            bot.reply_to(msg, "❌ Please enter a valid Numeric Telegram User ID!")

    elif act == "input_edit_runs":
        try:
            match["runs"] = int(txt)
            save_data()
            bot.reply_to(msg, f"✅ Total Runs updated to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")
        except:
            bot.reply_to(msg, "❌ Invalid number!")

    elif act == "input_edit_wkts":
        try:
            match["wickets"] = int(txt)
            save_data()
            bot.reply_to(msg, f"✅ Total Wickets updated to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")
        except:
            bot.reply_to(msg, "❌ Invalid number!")

    elif act == "input_edit_target":
        try:
            match["target"] = int(txt)
            save_data()
            bot.reply_to(msg, f"✅ Target updated to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")
        except:
            bot.reply_to(msg, "❌ Invalid number!")

    elif act == "input_custom_runs":
        try:
            r = int(txt)
            save_state_for_undo()
            match["runs"] += r
            match["current_over_runs"] += r
            match["partnership_runs"] += r
            ensure_match_player_stat(match["striker"], match["batting_team"], role="bat")
            ensure_match_player_stat(match["bowler"], match["bowling_team"], role="bowl")
            match["match_innings_data"][match["current_inning"]]["batting"][match["striker"]]["runs"] += r
            match["match_innings_data"][match["current_inning"]]["batting"][match["striker"]]["balls"] += 1
            match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["runs"] += r
            match["last_event_ticker"] = f"⚡ {r} Runs scored by {match['striker']}"
            register_legal_ball(msg.chat.id, legal=True, ball_tag=f"OT+{r}")
            if r % 2 != 0: match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            save_data()
            bot.reply_to(msg, f"✅ Added **{r} Runs**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")
        except:
            bot.reply_to(msg, "❌ Invalid number of runs!")

    elif act == "input_dls_revised_overs":
        try:
            rev_ov = int(txt)
            orig_ov = match["total_match_overs"]
            if match["current_inning"] == 2 and orig_ov > 0:
                match["target"] = int((match["target"] * (rev_ov / orig_ov)) + 1)
            match["total_match_overs"] = rev_ov
            match["last_event_ticker"] = f"🌧️ DLS APPLIED! Overs: {rev_ov}.0 │ Target: {match['target']}"
            save_data()
            bot.reply_to(msg, f"✅ **DLS Applied!** New Total Overs: `{rev_ov}.0` │ Revised Target: `{match['target']}` Runs\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")
        except:
            bot.reply_to(msg, "❌ Invalid overs number!")

    elif act in ["wiz_type_striker", "type_new_striker"]:
        ensure_player(txt, match["batting_team"])
        if txt not in match["squads"].get(match["batting_team"], []): match["squads"][match["batting_team"]].append(txt)
        match["striker"] = txt
        ensure_match_player_stat(txt, match["batting_team"], role="bat")
        save_data()
        bot.reply_to(msg, f"✅ Striker set to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

    elif act in ["wiz_type_nonstriker", "type_new_nonstriker"]:
        ensure_player(txt, match["batting_team"])
        if txt not in match["squads"].get(match["batting_team"], []): match["squads"][match["batting_team"]].append(txt)
        match["non_striker"] = txt
        ensure_match_player_stat(txt, match["batting_team"], role="bat")
        save_data()
        bot.reply_to(msg, f"✅ Non-Striker set to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

    elif act in ["wiz_type_bowler", "type_new_bowler"]:
        ensure_player(txt, match["bowling_team"])
        if txt not in match["squads"].get(match["bowling_team"], []): match["squads"][match["bowling_team"]].append(txt)
        match["bowler"] = txt
        ensure_match_player_stat(txt, match["bowling_team"], role="bowl")
        save_data()
        bot.reply_to(msg, f"✅ Bowler set to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

    elif act == "wiz_type_ground":
        if txt not in match["grounds_list"]: match["grounds_list"].append(txt)
        match["ground"] = txt
        save_data()
        m = InlineKeyboardMarkup(row_width=3)
        m.add(InlineKeyboardButton("✍️ Type Custom / Manual Overs", callback_data="wiz_type_overs"))
        for ov in [5, 7, 8, 10, 12, 15, 20]:
            m.add(InlineKeyboardButton(f"{ov} Overs", callback_data=f"wiz_set_ov_{ov}"))
        bot.reply_to(msg, f"🏟️ Ground set to **{txt}**!\n\n📌 **Step 6:** Select **Total Match Overs:**", reply_markup=m, parse_mode="Markdown")

    elif act in ["wiz_type_overs", "input_manual_overs"]:
        try:
            ov = int(txt)
            match["total_match_overs"] = ov
            save_data()
            start_wizard_openers_step(msg.chat.id, None)
        except:
            bot.reply_to(msg, "❌ Invalid number of overs!")

    elif act == "type_catch_fielder":
        ensure_player(txt, match["bowling_team"])
        if txt in match["career_db"]: match["career_db"][txt]["catches"] += 1
        save_data()
        process_wicket(msg.chat.id, None, f"c {txt} b {match['bowler']}", uid)

# ================= 24/7 WORKER RUNNER =================
def run_telegram_worker():
    time.sleep(2)
    try:
        bot.remove_webhook()
    except:
        pass
    print(">>> Telegram Bot Engine Started (Non-blocking infinity loop)...")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f">>> Reconnecting Polling: {e}")
            time.sleep(5)

def run_pinger_worker():
    while True:
        time.sleep(240)
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL")
            if url:
                urllib.request.urlopen(f"{url}/health", timeout=10)
        except:
            pass

if __name__ == "__main__":
    threading.Thread(target=run_telegram_worker, daemon=True).start()
    threading.Thread(target=run_pinger_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    print(f">>> Render Web Service Listening on Port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)