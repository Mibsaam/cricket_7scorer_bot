import os, json, random, time, threading, urllib.request
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8812331993:AAEQQsuFlUXxOFSH_FgfqFxSNL5y9FVacJE"
ADMIN_ID = 874225351
AUTHORIZED_SCORERS = {ADMIN_ID}
DATA_FILE = "master_cricket_database.json"

# ================= 24/7 FLASK KEEP-ALIVE SERVER =================
app = Flask(__name__)

@app.route("/")
def index():
    return "🏏 Complete Master Cricket Engine 24/7 Online & Active!", 200

@app.route("/health")
def health():
    return "OK", 200

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# ================= DATABASE INITIALIZATION =================
def create_blank_match():
    return {
        "match_id": f"M{random.randint(100, 999)}",
        "series_name": "Pro Championship League 2026",
        "ground": "Shivaji Park Arena",
        "grounds_list": ["Shivaji Park Arena", "Azad Maidan", "Eden Gardens", "Local Street Ground"],
        "stage": "League Match",
        "current_inning": 1,
        "teams": ["Mumbai Strikers", "Royal Fighters"],
        "batting_team": "Mumbai Strikers",
        "bowling_team": "Royal Fighters",
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
        "ball_by_ball_log": [],
        "innings_1_summary": {},
        "match_status": "Active",
        "awaiting_action": None,
        "temp_data": {},
        "history": [],
        "squads": {
            "Mumbai Strikers": ["Rohit", "Virat", "Surya", "Hardik", "Bumrah"],
            "Royal Fighters": ["Warner", "Smith", "Maxwell", "Starc", "Cummins"]
        },
        "career_db": {
            "Rohit": {"uuid": "PLY_101", "username": None, "team": "Mumbai Strikers", "matches": 5, "runs": 140, "balls": 75, "fours": 12, "sixes": 6, "wickets": 0, "bowled_balls": 0, "runs_given": 0, "catches": 3, "drops": 0, "stumpings": 0},
            "Starc": {"uuid": "PLY_102", "username": None, "team": "Royal Fighters", "matches": 5, "runs": 20, "balls": 15, "fours": 2, "sixes": 0, "wickets": 8, "bowled_balls": 60, "runs_given": 45, "catches": 2, "drops": 1, "stumpings": 0}
        },
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

def broadcast_commentary(cid, text):
    try:
        bot.send_message(cid, f"🎙️ **LIVE COMMENTARY:**\n{text}", parse_mode="Markdown")
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
        "current_over_runs": match["current_over_runs"], "recent_len": len(match["recent_balls"])
    })
    if len(match["history"]) > 25: match["history"].pop(0)

# ================= DISPLAY FORMATTER =================
def get_large_scoreboard_text():
    mode = "🦅 [SUPER OVER DECIDER]" if match.get("is_super_over") else ("🧪 [PRACTICE / FAKE MODE]" if match.get("is_practice_mode") else "🏆 [OFFICIAL TOURNAMENT MATCH]")
    fh = " 🔥 [FREE HIT ACTIVE]" if match.get("is_free_hit_active") else ""
    crr = (match['runs'] / (match['balls'] / 6)) if match['balls'] > 0 else 0.0
    
    targ_txt, bar_txt = "", ""
    if match.get("current_inning") == 2:
        needed = max(0, match["target"] - match["runs"])
        b_left = max(0, (match["total_match_overs"] * 6) - match["balls"])
        rrr = (needed / (b_left / 6)) if b_left > 0 else 0.0
        targ_txt = f"\n🎯 **TARGET:** `{match['target']}` | **NEED:** `{needed} runs in {b_left}b` (RRR: `{rrr:.2f}`)"
        
        pct = min(100, int((match["runs"] / match["target"]) * 100)) if match["target"] > 0 else 0
        filled = int(pct / 10)
        bar_txt = f"\n📊 Chase Progress: `[{'█'*filled}{'░'*(10-filled)}] {pct}%`"

    b_st = match["career_db"].get(match["bowler"], {"bowled_balls": 0, "runs_given": 0, "wickets": 0})
    b_ov = f"{b_st['bowled_balls'] // 6}.{b_st['bowled_balls'] % 6}"
    
    rec_balls = " | ".join(match["recent_balls"][-6:]) if match["recent_balls"] else "-"
    
    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 **{match['series_name']}** ({match['stage']})\n"
        f"🏟️ **Ground:** `{match['ground']}` | _{mode}_{fh}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔴 BATTING: **{match['batting_team']}**\n"
        f"🟢 BOWLING: **{match['bowling_team']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏏  **S C O R E B O A R D**  🏏\n"
        f"👉  【 **{match['runs']}  /  {match['wickets']}** 】  👈\n"
        f"⏳  OVERS: 【 **{match['overs']}  /  {match['total_match_overs']}.0** 】\n"
        f"⚡  CRR: `{crr:.2f}` | EXTRAS: `{match['extras_total']}` (Wd:{match['extras_wides']}, NB:{match['extras_noballs']}, B/LB:{match['extras_byes'] + match['extras_legbyes']})\n"
        f"━━━━━━━━━━━━━━━━━━━━"
        f"{targ_txt}{bar_txt}\n"
        f"🤝 **Partnership:** `{match['partnership_runs']} runs ({match['partnership_balls']} balls)`\n"
        f"🎞️ **This Over:** `| {rec_balls} |`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏏 **STRIKER:** 👉 **{match['striker']}** 👈\n"
        f"🏃 **RUNNER:** {match['non_striker']}\n"
        f"⚾ **BOWLER:** {match['bowler']} (`{b_st['wickets']}/{b_st['runs_given']}` in `{b_ov}` ov)\n"
        f"🧤 **WK:** `{match['wicketkeeper']}` | **C:** `{match['captain']}`\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

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
        InlineKeyboardButton("⚡ Wide (+Extras)", callback_data="menu_wide"),
        InlineKeyboardButton("⚠️ No Ball (+Runs)", callback_data="menu_noball"),
        InlineKeyboardButton("🏃 Byes / Leg Byes", callback_data="menu_byes")
    )
    m.add(
        InlineKeyboardButton("❌ WICKET MENU", callback_data="menu_wicket"),
        InlineKeyboardButton("😱 Drop Catch", callback_data="act_drop_catch"),
        InlineKeyboardButton("🔄 Strike Swap", callback_data="act_swap_strike")
    )
    m.add(
        InlineKeyboardButton("👤 Striker", callback_data="pop_set_striker"),
        InlineKeyboardButton("🏃 Non-Striker", callback_data="pop_set_nonstriker"),
        InlineKeyboardButton("⚾ Bowler", callback_data="pop_set_bowler")
    )
    m.add(
        InlineKeyboardButton("🚑 Split Bowler (Injury)", callback_data="pop_injury_split"),
        InlineKeyboardButton("⚡ Quick Opponent Entry", callback_data="menu_quick_innings")
    )
    m.add(
        InlineKeyboardButton("⚙️ Match Overs Settings", callback_data="menu_set_overs"),
        InlineKeyboardButton("🦅 Super Over Mode", callback_data="menu_super_over"),
        InlineKeyboardButton("🪙 Toss / Decision", callback_data="menu_toss")
    )
    m.add(
        InlineKeyboardButton("📊 Score Summary", callback_data="view_summary"),
        InlineKeyboardButton("📜 Match Archives", callback_data="view_archives"),
        InlineKeyboardButton("⭐ MoM Award", callback_data="view_mom")
    )
    m.add(
        InlineKeyboardButton("🏟️ Ground Selector", callback_data="menu_ground"),
        InlineKeyboardButton("👥 Squad & Teams", callback_data="menu_squads"),
        InlineKeyboardButton("🔄 Switch Innings", callback_data="act_switch_innings")
    )
    m.add(
        InlineKeyboardButton("🧪 Toggle Practice Mode", callback_data="act_toggle_mode"),
        InlineKeyboardButton("🗑️ Reset Stats", callback_data="act_reset_stats"),
        InlineKeyboardButton("↩️ Undo Ball", callback_data="act_undo")
    )
    return m

def sync_pinned_card(cid):
    try:
        txt = get_large_scoreboard_text()
        if match.get("pinned_message_id") and match.get("pinned_chat_id") == cid:
            bot.edit_message_text(txt, chat_id=cid, message_id=match["pinned_message_id"], parse_mode="Markdown")
    except:
        pass

# ================= COMMAND HANDLERS =================
@bot.message_handler(commands=['start', 'score', 'cricket'])
def handle_start(msg):
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("🏆 Real Tournament Match", callback_data="init_real_match"),
        InlineKeyboardButton("🧪 Practice / Fake Match", callback_data="init_practice_match")
    )
    bot.reply_to(msg, "🏏 **Cricket Engine Initialized**\nKaunsa match shuru karna hai?", reply_markup=m, parse_mode="Markdown")

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
        res = (
            f"👤 **LIFETIME CAREER PROFILE - {found_p}**\n"
            f"🆔 UUID: `{d['uuid']}` | Team: `{d['team']}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🏏 **Batting:** `{d['runs']} Runs` ({d['balls']}b) | SR: `{sr:.2f}`\n"
            f"🔥 **Boundaries:** `{d['fours']} Fours` | `{d['sixes']} Sixes`\n"
            f"⚾ **Bowling:** `{d['wickets']} Wickets` | Econ: `{econ:.2f}`\n"
            f"🧤 **Fielding:** `{d['catches']} Catches` | `{d['drops']} Drops` (Catch Eff: `{c_eff:.1f}%`)\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        bot.reply_to(msg, res, parse_mode="Markdown")
    else:
        bot.reply_to(msg, "❌ Player nahi mila! Use: `/profile PlayerName`", parse_mode="Markdown")

@bot.message_handler(commands=['addscorer'])
def handle_add_scorer(msg):
    if not is_admin(msg.from_user.id): return
    try:
        t_id = int(msg.text.replace("/addscorer", "").strip())
        AUTHORIZED_SCORERS.add(t_id)
        bot.reply_to(msg, f"✅ User `{t_id}` added to official scorers list!")
    except:
        bot.reply_to(msg, "Format: `/addscorer 12345678`")

def check_match_completion(cid):
    limit_w = match["max_wickets_limit"]
    if match["current_inning"] == 2:
        if match["runs"] >= match["target"]:
            w_left = limit_w - match["wickets"]
            txt = f"🏆 🎊 **CHAMPIONS!** **{match['batting_team']}** WON by **{w_left} wickets**! 🥇"
            broadcast_commentary(cid, txt)
            archive_match()
        elif match["overs"] >= match["total_match_overs"] or match["wickets"] >= limit_w:
            margin = (match["target"] - 1) - match["runs"]
            if margin == 0:
                broadcast_commentary(cid, "🔥 ⚖️ **WHAT A THRILLER! MATCH TIED!** Use Super Over button!")
            elif margin > 0:
                txt = f"🏆 🎊 **VICTORY!** **{match['bowling_team']}** WON by **{margin} runs**! 🥇"
                broadcast_commentary(cid, txt)
            archive_match()

def archive_match():
    if not match["is_practice_mode"]:
        m_entry = {
            "match_id": match["match_id"],
            "ground": match["ground"],
            "teams": f"{match['teams'][0]} vs {match['teams'][1]}",
            "score_1": str(match.get("innings_1_summary", "")),
            "score_2": f"{match['batting_team']} {match['runs']}/{match['wickets']} in {match['overs']} ov",
            "winner": match["batting_team"] if match["runs"] >= match["target"] else match["bowling_team"]
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
        ensure_player(match["bowler"])
        if match["bowler"] in match["career_db"]:
            match["career_db"][match["bowler"]]["bowled_balls"] += 1
        
        if match["is_free_hit_active"]:
            match["is_free_hit_active"] = False

        if rem_b == 0 and match["balls"] > 0:
            match["over_worm"][comp_ov] = match["current_over_runs"]
            match["current_over_runs"] = 0
            
            # Strike rotation
            match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            match["last_bowler"] = match["bowler"]
            match["bowler"] = "Select Bowler"
            
            broadcast_commentary(cid, f"🏁 **OVER {comp_ov} COMPLETED!** Strike rotated. Score: `{match['runs']}/{match['wickets']}`")
            
            # Smart Next Bowler Prompt
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

        # VIEW ONLY BUTTONS
        if dt == "view_summary":
            bot.answer_callback_query(c.id)
            inn1 = match.get("innings_1_summary", "Innings 1 Not Started")
            txt = f"📊 **MATCH SCORECARD SUMMARY**\n━━━━━━━━━━━━━━━━━━━━\n📌 1st Innings: `{inn1}`\n📌 2nd Innings: `{match['batting_team']} {match['runs']}/{match['wickets']} in {match['overs']} ov`\n🎯 Target: `{match['target']}`\n━━━━━━━━━━━━━━━━━━━━"
            return bot.send_message(cid, txt, parse_mode="Markdown")

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
                txt = f"📜 **ARCHIVED MATCH #{entry['match_id']}**\n🏟️ Ground: `{entry['ground']}`\n⚔️ Teams: `{entry['teams']}`\n🥇 Result: `{entry['winner']} WON`\nScore 1: `{entry['score_1']}`\nScore 2: `{entry['score_2']}`"
                return bot.send_message(cid, txt, parse_mode="Markdown")

        if dt == "view_mom":
            bot.answer_callback_query(c.id)
            best_p, max_pts = "None", -999
            for p, st in match["career_db"].items():
                pts = (st["runs"] * 1.2) + (st["fours"] * 1.5) + (st["sixes"] * 2.5) + (st["wickets"] * 35) + (st["catches"] * 10) - (st["drops"] * 5)
                if pts > max_pts:
                    max_pts, best_p = pts, p
            return bot.send_message(cid, f"🏆 **MAN OF THE MATCH:** `{best_p}` (Impact: `{max_pts:.1f}` pts)", parse_mode="Markdown")

        # SCORER PERMISSION CHECK
        if not match["is_practice_mode"] and not is_scorer(uid):
            return bot.answer_callback_query(c.id, "⚠️ Only Official Scorers & Admin can score in Real Mode!", show_alert=True)

        bot.answer_callback_query(c.id)

        # MODE SELECTORS
        if dt in ["init_real_match", "init_practice_match"]:
            match["is_practice_mode"] = (dt == "init_practice_match")
            match["is_super_over"] = False
            match["max_wickets_limit"] = 10
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

        # 1. TOTAL OVERS SETTING MENU
        if dt == "menu_set_overs":
            m = InlineKeyboardMarkup(row_width=3)
            for ov in [5, 7, 8, 10, 12, 15, 20]:
                m.add(InlineKeyboardButton(f"{ov} Overs", callback_data=f"set_ov_{ov}"))
            m.add(InlineKeyboardButton("✍️ Custom Manual Overs", callback_data="type_manual_overs"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("⏳ **Select or Type Total Match Overs:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("set_ov_"):
            ov_val = int(dt.replace("set_ov_", ""))
            match["total_match_overs"] = ov_val
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "type_manual_overs":
            match["awaiting_action"] = "input_manual_overs"
            return bot.edit_message_text("✍️ Match ke **Total Overs** type karke send karein (e.g. 6, 9, 14):", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        # 2. SUPER OVER ENGINE
        if dt == "menu_super_over":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(
                InlineKeyboardButton("🔥 Start Super Over Now", callback_data="exec_start_super_over"),
                InlineKeyboardButton("⬅️ Cancel", callback_data="back_main")
            )
            return bot.edit_message_text("🦅 **SUPER OVER SHOWDOWN:**\nRule: 1 Over, 2 Wickets Max per team!\nStart karein?", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "exec_start_super_over":
            match.update({
                "is_super_over": True,
                "total_match_overs": 1,
                "max_wickets_limit": 2,
                "current_inning": 1,
                "runs": 0, "wickets": 0, "overs": 0.0, "balls": 0,
                "extras_total": 0, "extras_wides": 0, "extras_noballs": 0, "extras_byes": 0, "extras_legbyes": 0,
                "partnership_runs": 0, "partnership_balls": 0, "recent_balls": [],
                "striker": "Select Striker", "non_striker": "Select Non-Striker", "bowler": "Select Bowler"
            })
            save_data()
            broadcast_commentary(cid, f"🦅 🔥 **SUPER OVER COMMENCED!** 1 Over Shootout between {match['batting_team']} & {match['bowling_team']}!")
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # 3. RUN SCORING
        if dt.startswith("act_run_"):
            r = int(dt.replace("act_run_", ""))
            match["temp_data"]["run_val"] = r
            m = InlineKeyboardMarkup(row_width=2)
            for ar in ["Cover", "Point", "Mid-Wicket", "Long-On", "Long-Off", "Square-Leg", "Third-Man", "Fine-Leg"]:
                m.add(InlineKeyboardButton(f"🎯 {ar}", callback_data=f"shot_{ar}"))
            return bot.edit_message_text(f"🎯 **Select Shot Direction for {r} Run(s):**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("shot_"):
            area = dt.replace("shot_", "")
            r = match["temp_data"].get("run_val", 0)
            save_state_for_undo()
            ensure_player(match["striker"], match["batting_team"])
            ensure_player(match["bowler"], match["bowling_team"])
            
            match["runs"] += r
            match["current_over_runs"] += r
            match["partnership_runs"] += r
            
            if match["striker"] in match["career_db"]:
                p_st = match["career_db"][match["striker"]]
                p_st["runs"] += r
                p_st["balls"] += 1
                if r == 4:
                    p_st["fours"] += 1
                    broadcast_commentary(cid, f"🔥 **FOUR!** `{match['striker']}` pierces through `{area}` off `{match['bowler']}`!")
                elif r == 6:
                    p_st["sixes"] += 1
                    broadcast_commentary(cid, f"🚀 **MASSIVE SIX!** `{match['striker']}` sends `{match['bowler']}` sailing over `{area}`!")

            if match["bowler"] in match["career_db"]:
                match["career_db"][match["bowler"]]["runs_given"] += r
            
            register_legal_ball(cid, legal=True, ball_tag=str(r))
            
            if r in [1, 3]:
                match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # 4. WIDE MENU
        if dt == "menu_wide":
            m = InlineKeyboardMarkup(row_width=3)
            for r in range(7):
                m.add(InlineKeyboardButton(f"Wide + {r} Extra", callback_data=f"exec_wide_{r}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("⚡ **Select Wide Ball Deliveries:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("exec_wide_"):
            ex = int(dt.replace("exec_wide_", ""))
            tot = 1 + ex
            save_state_for_undo()
            match["runs"] += tot
            match["current_over_runs"] += tot
            match["extras_total"] += tot
            match["extras_wides"] += tot
            ensure_player(match["bowler"], match["bowling_team"])
            if match["bowler"] in match["career_db"]:
                match["career_db"][match["bowler"]]["runs_given"] += tot
            match["recent_balls"].append(f"Wd+{ex}")
            save_data()
            check_match_completion(cid)
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # 5. NO BALL MENU
        if dt == "menu_noball":
            m = InlineKeyboardMarkup(row_width=3)
            for r in range(7):
                m.add(InlineKeyboardButton(f"NB + {r} Bat Runs", callback_data=f"exec_nb_{r}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("⚠️ **Select No Ball Deliveries (+1 Extra Auto):**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("exec_nb_"):
            bat_r = int(dt.replace("exec_nb_", ""))
            tot = 1 + bat_r
            save_state_for_undo()
            match["runs"] += tot
            match["current_over_runs"] += tot
            match["extras_total"] += 1
            match["extras_noballs"] += 1
            match["partnership_runs"] += bat_r
            
            ensure_player(match["striker"], match["batting_team"])
            if match["striker"] in match["career_db"]:
                p_st = match["career_db"][match["striker"]]
                p_st["runs"] += bat_r
                if bat_r == 4: p_st["fours"] += 1
                if bat_r == 6: p_st["sixes"] += 1
            
            ensure_player(match["bowler"], match["bowling_team"])
            if match["bowler"] in match["career_db"]:
                match["career_db"][match["bowler"]]["runs_given"] += tot
            match["recent_balls"].append(f"NB+{bat_r}")
            
            if match["free_hit_enabled"]:
                match["is_free_hit_active"] = True
                broadcast_commentary(cid, f"⚠️ 🚀 **NO BALL!** Free Hit awarded on next legal ball!")
            
            if bat_r in [1, 3]:
                match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            save_data()
            check_match_completion(cid)
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # 6. BYES / LEG BYES MENU (FULLY CONNECTED)
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
            if is_bye: match["extras_byes"] += b_val
            else: match["extras_legbyes"] += b_val
            
            register_legal_ball(cid, legal=True, ball_tag=f"{'B' if is_bye else 'LB'}+{b_val}")
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # 7. WICKETS & CATCH TRACKER
        if dt == "menu_wicket":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("🔴 Bowled", callback_data="wkt_bowled"), InlineKeyboardButton("🟡 Caught Out", callback_data="wkt_caught"))
            m.add(InlineKeyboardButton("🟢 Run Out", callback_data="wkt_runout"), InlineKeyboardButton("🔵 Stumped", callback_data="wkt_stumped"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("❌ **Select Dismissal Type:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt in ["wkt_bowled", "wkt_stumped", "wkt_runout"]:
            if dt in ["wkt_bowled", "wkt_stumped"] and match["is_free_hit_active"]:
                return bot.send_message(cid, "⚠️ Free Hit Active! Only Run Out allowed!")
            return process_wicket(cid, c.message.message_id, dt.replace("wkt_", "").capitalize(), uid)

        if dt == "wkt_caught":
            if match["is_free_hit_active"]:
                return bot.send_message(cid, "⚠️ Free Hit Active! Catch out not allowed!")
            m = InlineKeyboardMarkup(row_width=2)
            for fld in match["squads"].get(match["bowling_team"], []):
                m.add(InlineKeyboardButton(f"🙌 {fld}", callback_data=f"catch_by_{fld}"))
            m.add(InlineKeyboardButton("➕ Type Fielder Name", callback_data="type_catch_fielder"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_wicket"))
            return bot.edit_message_text(f"🙌 **Who took the catch ({match['bowling_team']})?**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("catch_by_"):
            f_name = dt.replace("catch_by_", "")
            ensure_player(f_name, match["bowling_team"])
            if f_name in match["career_db"]:
                match["career_db"][f_name]["catches"] += 1
            return process_wicket(cid, c.message.message_id, f"Caught by {f_name}", uid)

        if dt == "type_catch_fielder":
            match["awaiting_action"] = "input_catch_fielder"
            return bot.edit_message_text("✍️ Fielder ka **Naam** type karke send karein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        if dt == "act_drop_catch":
            m = InlineKeyboardMarkup(row_width=2)
            for fld in match["squads"].get(match["bowling_team"], []):
                m.add(InlineKeyboardButton(f"❌ {fld}", callback_data=f"drop_by_{fld}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("😱 **Who dropped the catch?**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("drop_by_"):
            f_name = dt.replace("drop_by_", "")
            ensure_player(f_name, match["bowling_team"])
            if f_name in match["career_db"]:
                match["career_db"][f_name]["drops"] += 1
            broadcast_commentary(cid, f"😱 💔 **CATCH DROPPED!** `{f_name}` drops a chance off `{match['bowler']}`!")
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # 8. SQUADS & TEAMS MANAGEMENT (CONNECTED)
        if dt == "menu_squads":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("➕ Add Player to Batting Squad", callback_data="add_ply_bat"))
            m.add(InlineKeyboardButton("➕ Add Player to Bowling Squad", callback_data="add_ply_bowl"))
            m.add(InlineKeyboardButton("📋 View Squad Lists", callback_data="view_full_squads"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("👥 **Squad & Teams Management:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "view_full_squads":
            bat_s = ", ".join(match["squads"].get(match["batting_team"], [])) or "None"
            bowl_s = ", ".join(match["squads"].get(match["bowling_team"], [])) or "None"
            txt = f"👥 **SQUAD LISTINGS:**\n\n🔴 **{match['batting_team']}:**\n`{bat_s}`\n\n🟢 **{match['bowling_team']}:**\n`{bowl_s}`"
            bot.send_message(cid, txt, parse_mode="Markdown")
            return

        if dt == "add_ply_bat":
            match["awaiting_action"] = "input_bat_player"
            return bot.edit_message_text(f"✍️ **{match['batting_team']}** ke naye player ka naam likhein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        if dt == "add_ply_bowl":
            match["awaiting_action"] = "input_bowl_player"
            return bot.edit_message_text(f"✍️ **{match['bowling_team']}** ke naye player ka naam likhein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        # 9. NON-STRIKER SELECTION (CONNECTED)
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
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "type_new_nonstriker":
            match["awaiting_action"] = "input_new_nonstriker"
            return bot.edit_message_text("✍️ Naye Non-Striker ka **Naam** type karke send karein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        # 10. STRIKER & BOWLER SELECTORS
        if dt == "pop_set_striker":
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["batting_team"], []):
                if p != match["non_striker"]:
                    m.add(InlineKeyboardButton(f"🏏 {p}", callback_data=f"sel_str_{p}"))
            m.add(InlineKeyboardButton("➕ Type New Batsman", callback_data="type_new_batsman"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("👤 **Select Striker:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("sel_str_"):
            p_name = dt.replace("sel_str_", "")
            match["striker"] = p_name
            ensure_player(p_name, match["batting_team"])
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "type_new_batsman":
            match["awaiting_action"] = "input_new_striker"
            return bot.edit_message_text("✍️ Naye Batsman ka **Naam** type karke send karein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

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
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "type_new_bowler":
            match["awaiting_action"] = "input_new_bowler"
            return bot.edit_message_text("✍️ Naye Bowler ka **Naam** type karke send karein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        # 11. MID-OVER INJURY SPLIT
        if dt == "pop_injury_split":
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["bowling_team"], []):
                if p != match["bowler"]:
                    m.add(InlineKeyboardButton(f"🚑 {p}", callback_data=f"split_to_{p}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("🚑 **Select Bowler to finish remaining balls of this over:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("split_to_"):
            new_b = dt.replace("split_to_", "")
            prev_b = match["bowler"]
            match["bowler"] = new_b
            ensure_player(new_b, match["bowling_team"])
            broadcast_commentary(cid, f"🚑 **INJURY CHANGE:** `{prev_b}` walks off. `{new_b}` will finish the rest of this over!")
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # 12. QUICK MANUAL OPPONENT INNINGS
        if dt == "menu_quick_innings":
            m = InlineKeyboardMarkup(row_width=3)
            for ov in [5, 7, 8, 10, 12, 15, 20]:
                m.add(InlineKeyboardButton(f"{ov} Overs", callback_data=f"q_ov_{ov}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("⚡ **Quick Opponent Innings:** Overs kitne hue?", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("q_ov_"):
            match["temp_data"]["q_overs"] = int(dt.replace("q_ov_", ""))
            m = InlineKeyboardMarkup(row_width=4)
            for w in range(11):
                m.add(InlineKeyboardButton(f"{w} Wkts", callback_data=f"q_wkt_{w}"))
            return bot.edit_message_text("⚡ **Quick Opponent Innings:** Wickets kitni giri?", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("q_wkt_"):
            match["temp_data"]["q_wkts"] = int(dt.replace("q_wkt_", ""))
            match["awaiting_action"] = "input_quick_runs"
            return bot.edit_message_text("✍️ Opponent ke total **Runs** type karke bhejein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        # 13. GROUND MANAGEMENT
        if dt == "menu_ground":
            m = InlineKeyboardMarkup(row_width=2)
            for g in match["grounds_list"]:
                m.add(InlineKeyboardButton(f"🏟️ {g}", callback_data=f"set_g_{g}"))
            m.add(InlineKeyboardButton("➕ Add New Ground", callback_data="type_new_ground"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_main"))
            return bot.edit_message_text("🏟️ **Select Ground or Add New:**", chat_id=cid, message_id=c.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("set_g_"):
            g_name = dt.replace("set_g_", "")
            match["ground"] = g_name
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "type_new_ground":
            match["awaiting_action"] = "input_new_ground"
            return bot.edit_message_text("✍️ Naye **Ground ka Naam** type karke send karein:", chat_id=cid, message_id=c.message.message_id, parse_mode="Markdown")

        # 14. INNINGS SWITCH & TOSS
        if dt == "act_switch_innings":
            if match["current_inning"] == 1:
                match["innings_1_summary"] = f"{match['batting_team']} {match['runs']}/{match['wickets']} in {match['overs']} ov"
                match["target"] = match["runs"] + 1
                match["current_inning"] = 2
                other = [t for t in match["teams"] if t != match["batting_team"]][0]
                match["bowling_team"], match["batting_team"] = match["batting_team"], other
                match.update({"runs": 0, "wickets": 0, "overs": 0.0, "balls": 0, "extras_total": 0, "extras_wides": 0, "extras_noballs": 0, "extras_byes": 0, "extras_legbyes": 0, "partnership_runs": 0, "partnership_balls": 0, "recent_balls": [], "current_over_runs": 0, "striker": "Select Striker", "non_striker": "Select Non-Striker", "bowler": "Select Bowler"})
                save_data()
                broadcast_commentary(cid, f"🔄 **INNINGS BREAK!** **{match['batting_team']}** need `{match['target']}` runs to win!")
                return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "menu_toss":
            winner = random.choice(match["teams"])
            dec = random.choice(["bat", "bowl"])
            match["toss_winner"], match["toss_decision"] = winner, dec
            other = [t for t in match["teams"] if t != winner][0]
            if dec == "bat": match["batting_team"], match["bowling_team"] = winner, other
            else: match["bowling_team"], match["batting_team"] = winner, other
            save_data()
            broadcast_commentary(cid, f"🪙 **TOSS UPDATE:** `{winner}` won the toss and elected to `{dec}` first!")
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "act_swap_strike":
            match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "act_toggle_mode":
            match["is_practice_mode"] = not match["is_practice_mode"]
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        # 15. UNDO SYSTEM (CONNECTED)
        if dt == "act_undo":
            if not match["history"]:
                return bot.send_message(cid, "⚠️ Undo karne ke liye koi purana state nahi hai!")
            last_st = match["history"].pop()
            match.update(last_st)
            if len(match["recent_balls"]) > last_st.get("recent_len", 0):
                match["recent_balls"] = match["recent_balls"][:last_st["recent_len"]]
            save_data()
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

        if dt == "act_reset_stats":
            if match["is_practice_mode"] or is_admin(uid):
                match.update({"runs": 0, "wickets": 0, "overs": 0.0, "balls": 0, "extras_total": 0, "extras_wides": 0, "extras_noballs": 0, "extras_byes": 0, "extras_legbyes": 0, "partnership_runs": 0, "partnership_balls": 0, "recent_balls": [], "current_over_runs": 0, "history": []})
                save_data()
                return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")
            else:
                return bot.send_message(cid, "⚠️ Only Admin can reset in Real Match mode!")

        if dt == "back_main":
            return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=c.message.message_id, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

    except Exception as e:
        print(f"Error handling callback: {e}")

def process_wicket(cid, mid, reason, uid):
    limit_w = match["max_wickets_limit"]
    if match["wickets"] < limit_w:
        save_state_for_undo()
        match["wickets"] += 1
        ensure_player(match["striker"], match["batting_team"])
        ensure_player(match["bowler"], match["bowling_team"])
        if match["striker"] in match["career_db"]:
            match["career_db"][match["striker"]]["balls"] += 1
        if match["bowler"] in match["career_db"]:
            match["career_db"][match["bowler"]]["wickets"] += 1
        
        broadcast_commentary(cid, f"🚨 💥 **WICKET FALLS!** `{match['striker']}` ({reason}) off `{match['bowler']}`! Score: `{match['runs']}/{match['wickets']}`")
        match["partnership_runs"], match["partnership_balls"] = 0, 0
        register_legal_ball(cid, legal=True, ball_tag="W")
        match["striker"] = "Select Striker"
        save_data()
        
        # Pop-up for Next Batsman
        m = InlineKeyboardMarkup(row_width=2)
        for p in match["squads"].get(match["batting_team"], []):
            if p != match["non_striker"]:
                m.add(InlineKeyboardButton(f"🏏 {p}", callback_data=f"sel_str_{p}"))
        m.add(InlineKeyboardButton("➕ Type New Batsman", callback_data="type_new_batsman"))
        bot.send_message(cid, "👤 **Select Next Striker walking in:**", reply_markup=m, parse_mode="Markdown")
        return bot.edit_message_text(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

# ================= TEXT INPUT HANDLER =================
@bot.message_handler(func=lambda m: match.get("awaiting_action") is not None)
def handle_master_text_inputs(msg):
    uid = msg.from_user.id
    act = match.get("awaiting_action")
    txt = msg.text.strip()
    match["awaiting_action"] = None
    
    if act == "input_manual_overs":
        try:
            ov = int(txt)
            match["total_match_overs"] = ov
            save_data()
            bot.reply_to(msg, f"✅ Match Overs set to **{ov} Overs**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")
        except:
            bot.reply_to(msg, "❌ Invalid number of overs!")

    elif act == "input_quick_runs":
        try:
            r = int(txt)
            ov = match["temp_data"].get("q_overs", 7)
            w = match["temp_data"].get("q_wkts", 5)
            match["innings_1_summary"] = f"{match['bowling_team']} {r}/{w} in {ov} ov"
            match["target"] = r + 1
            match["current_inning"] = 2
            match.update({"runs": 0, "wickets": 0, "overs": 0.0, "balls": 0, "extras_total": 0, "partnership_runs": 0, "partnership_balls": 0, "recent_balls": [], "history": []})
            save_data()
            bot.reply_to(msg, f"✅ **Target Set: {match['target']} Runs**\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")
        except:
            bot.reply_to(msg, "❌ Invalid run amount!")

    elif act == "input_new_ground":
        if txt not in match["grounds_list"]: 
            match["grounds_list"].append(txt)
        match["ground"] = txt
        save_data()
        bot.reply_to(msg, f"✅ Ground set to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

    elif act == "input_new_striker":
        ensure_player(txt, match["batting_team"])
        if txt not in match["squads"][match["batting_team"]]:
            match["squads"][match["batting_team"]].append(txt)
        match["striker"] = txt
        save_data()
        bot.reply_to(msg, f"✅ Striker set to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

    elif act == "input_new_nonstriker":
        ensure_player(txt, match["batting_team"])
        if txt not in match["squads"][match["batting_team"]]:
            match["squads"][match["batting_team"]].append(txt)
        match["non_striker"] = txt
        save_data()
        bot.reply_to(msg, f"✅ Non-Striker set to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

    elif act == "input_new_bowler":
        ensure_player(txt, match["bowling_team"])
        if txt not in match["squads"][match["bowling_team"]]:
            match["squads"][match["bowling_team"]].append(txt)
        match["bowler"] = txt
        save_data()
        bot.reply_to(msg, f"✅ Bowler set to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid), parse_mode="Markdown")

    elif act == "input_bat_player":
        ensure_player(txt, match["batting_team"])
        if txt not in match["squads"][match["batting_team"]]:
            match["squads"][match["batting_team"]].append(txt)
        save_data()
        bot.reply_to(msg, f"✅ Player **{txt}** added to **{match['batting_team']}** squad!")

    elif act == "input_bowl_player":
        ensure_player(txt, match["bowling_team"])
        if txt not in match["squads"][match["bowling_team"]]:
            match["squads"][match["bowling_team"]].append(txt)
        save_data()
        bot.reply_to(msg, f"✅ Player **{txt}** added to **{match['bowling_team']}** squad!")

    elif act == "input_catch_fielder":
        ensure_player(txt, match["bowling_team"])
        if txt in match["career_db"]:
            match["career_db"][txt]["catches"] += 1
        save_data()
        process_wicket(msg.chat.id, None, f"Caught by {txt}", uid)

# ================= 24/7 WORKER RUNNER =================
def run_telegram_worker():
    time.sleep(2)
    try:
        bot.remove_webhook()
    except:
        pass
    print(">>> Telegram Bot Engine Started (Infinity Polling Active)...")
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f">>> Reconnecting Telegram Polling: {e}")
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