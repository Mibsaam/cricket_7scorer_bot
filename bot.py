import os, random, time, threading, urllib.request
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8670400703:AAFx9ZbF8Hzv3SCU9TyN9Mh-LlOuKzV6p-k"
ADMIN_ID = 874225351
AUTHORIZED_SCORERS = {ADMIN_ID}

# 24/7 RENDER KEEP-ALIVE SERVER
app = Flask(__name__)
@app.route("/")
def h(): return "Pro Cricket Series Scorer Active 24/7", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

def auto_ping():
    while True:
        time.sleep(300)
        try:
            render_url = os.environ.get("RENDER_EXTERNAL_URL")
            if render_url: urllib.request.urlopen(render_url)
        except: pass

threading.Thread(target=auto_ping, daemon=True).start()

bot = telebot.TeleBot(BOT_TOKEN)

# ULTIMATE SERIES & TOURNAMENT ENGINE
match = {
    "series_name": "Local Pro League 2026",
    "series_score": {"Team A Wins": 0, "Team B Wins": 0},
    "teams": ["Mumbai Strikers", "Team Unity"],
    "batting_team": "Mumbai Strikers",
    "bowling_team": "Team Unity",
    "total_match_overs": 20,
    "toss_winner": None,
    "toss_decision": None,
    "runs": 0,
    "wickets": 0,
    "overs": 0.0,
    "balls": 0,
    "extras": 0,
    "target": 0,
    "is_second_innings": False,
    "striker": "Select Striker",
    "non_striker": "Select Non-Striker",
    "bowler": "Select Bowler",
    "partnership_runs": 0,
    "partnership_balls": 0,
    "match_status": "Setup / Toss Pending",
    "is_practice_mode": True,
    "history": [],
    "ball_by_ball_log": [],
    "awaiting": None,
    "temp_team": None,
    # Flexible Squads (Supports 8, 11, 14 or 16+ players seamlessly)
    "squads": {
        "Mumbai Strikers": ["Player 1", "Player 2", "Player 3", "Player 4", "Player 5", "Player 6", "Player 7", "Player 8"],
        "Team Unity": ["Bowler 1", "Bowler 2", "Bowler 3", "Bowler 4", "Bowler 5", "Bowler 6", "Bowler 7", "Bowler 8"]
    },
    "career_db": {
        "Player 1": {"team": "Mumbai Strikers", "matches": 5, "runs": 150, "balls": 100, "fours": 12, "sixes": 5, "wickets": 0, "bowled_balls": 0, "runs_given": 0},
        "Player 2": {"team": "Mumbai Strikers", "matches": 4, "runs": 120, "balls": 80, "fours": 10, "sixes": 4, "wickets": 0, "bowled_balls": 0, "runs_given": 0},
        "Bowler 1": {"team": "Team Unity", "matches": 6, "runs": 20, "balls": 15, "fours": 1, "sixes": 0, "wickets": 8, "bowled_balls": 60, "runs_given": 45}
    }
}

def is_authorized(user_id):
    return user_id in AUTHORIZED_SCORERS

def ensure_player(name, team="General"):
    if name not in match["career_db"]:
        match["career_db"][name] = {"team": team, "matches": 1, "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "wickets": 0, "bowled_balls": 0, "runs_given": 0}

def get_scorer_markup():
    m = InlineKeyboardMarkup(row_width=3)
    # 1. Standard Runs Grid
    m.add(
        InlineKeyboardButton("🔴 0 Dot", callback_data="sc_0"),
        InlineKeyboardButton("🟢 1 Run", callback_data="sc_1"),
        InlineKeyboardButton("🔵 2 Runs", callback_data="sc_2")
    )
    m.add(
        InlineKeyboardButton("🟡 3 Runs", callback_data="sc_3"),
        InlineKeyboardButton("🔥 4 Boundary", callback_data="sc_4"),
        InlineKeyboardButton("🚀 6 Sixer", callback_data="sc_6")
    )
    # 2. Fully Dynamic Extras (Wide + Runs, No Ball + Runs, Byes)
    m.add(
        InlineKeyboardButton("⚡ Wide Menu (+Runs)", callback_data="menu_wide"),
        InlineKeyboardButton("⚠️ No Ball Menu (+Runs)", callback_data="menu_nb"),
        InlineKeyboardButton("🏃 Bye / Leg Bye", callback_data="menu_extras")
    )
    m.add(
        InlineKeyboardButton("❌ Wicket / Out", callback_data="sc_wkt"),
        InlineKeyboardButton("🏥 Retire Hurt / Decl.", callback_data="sc_retire")
    )
    # 3. Squad & Player Selection Buttons (Supports 8 to 16+ Players)
    m.add(
        InlineKeyboardButton("✏️ Set Striker", callback_data="btn_set_striker"),
        InlineKeyboardButton("✏️ Set Non-Striker", callback_data="btn_set_nonstriker")
    )
    m.add(
        InlineKeyboardButton("⚾ Change Bowler", callback_data="btn_set_bowler"),
        InlineKeyboardButton("👥 Manage Teams & Squads", callback_data="menu_manage_teams")
    )
    # 4. Match, Series & Tournament Controls
    m.add(
        InlineKeyboardButton("🪙 Toss Menu", callback_data="menu_toss"),
        InlineKeyboardButton("⚙️ Overs Setup", callback_data="menu_settings")
    )
    m.add(
        InlineKeyboardButton("📋 WhatsApp Summary", callback_data="get_summary"),
        InlineKeyboardButton("🏆 Series & Leaderboard", callback_data="match_leaderboard")
    )
    m.add(
        InlineKeyboardButton("🔄 Swap Strike", callback_data="sc_swap"),
        InlineKeyboardButton("⭐ Man of Match / Series", callback_data="sc_mom")
    )
    m.add(
        InlineKeyboardButton("🧪 Practice Mode", callback_data="toggle_practice"),
        InlineKeyboardButton("🗑️ Reset Practice", callback_data="reset_practice")
    )
    m.add(
        InlineKeyboardButton("↩️ Undo", callback_data="sc_undo"),
        InlineKeyboardButton("🔄 Switch Innings", callback_data="sc_switch")
    )
    return m

def get_scoreboard_text():
    overs_display = f"{match['overs']}"
    run_rate = (match['runs'] / (match['balls'] / 6)) if match['balls'] > 0 else 0.0
    target_info = f"\n 🎯 **Target:** `{match['target']}`" if match["is_second_innings"] else ""
    toss_info = f"\n 🪙 **Toss:** `{match['toss_winner']} won & elected to {match['toss_decision']}`" if match["toss_winner"] else ""
    mode_info = "🧪 [PRACTICE MODE]" if match["is_practice_mode"] else "⚡ [REAL TOURNAMENT MODE]"

    return (
        f"🏆 **{match['series_name']}** 🏏\n"
        f"_{mode_info}_\n"
        f"──────────────────────────\n"
        f" Batting: **{match['batting_team']}** vs Bowling: **{match['bowling_team']}**"
        f"{toss_info}{target_info}\n"
        f"──────────────────────────\n"
        f" 🎯 **Score:** `{match['runs']} / {match['wickets']}` in `{overs_display}/{match['total_match_overs']} ov`\n"
        f" ⚡ **Extras:** `{match['extras']}` | **Run Rate:** `{run_rate:.2f}`\n"
        f" 🤝 **Partnership:** `{match['partnership_runs']} runs ({match['partnership_balls']} balls)`\n"
        f"──────────────────────────\n"
        f" 🏏 **Striker:** `{match['striker']}`\n"
        f" 🏃 **Non-Striker:** `{match['non_striker']}`\n"
        f" ⚾ **Bowler:** `{match['bowler']}`\n"
        f"──────────────────────────"
    )

@bot.message_handler(commands=['start', 'scorer'])
def c_start(msg):
    bot.reply_to(
        msg, 
        "⚡ **Pro Cricket Scorer Initialized with Series & Dynamic Extras!**\nControl panel active hai:", 
        reply_markup=get_scorer_markup(), 
        parse_mode="Markdown"
    )
    bot.send_message(msg.chat.id, get_scoreboard_text(), parse_mode="Markdown")

@bot.message_handler(commands=['addscorer'])
def c_addscorer(msg):
    if msg.from_user.id != ADMIN_ID:
        return bot.reply_to(msg, "⚠️ Yeh command sirf Main Admin chala sakta hai!")
    try:
        target_id = int(msg.text.replace("/addscorer", "").strip())
        AUTHORIZED_SCORERS.add(target_id)
        bot.reply_to(msg, f"✅ Success! User ID `{target_id}` ko official Scorer bana diya gaya hai.", parse_mode="Markdown")
    except:
        bot.reply_to(msg, "⚠️ Sahi format use karein:\n`/addscorer 123456789`", parse_mode="Markdown")

def save_state_for_undo():
    match["history"].append({
        "runs": match["runs"],
        "wickets": match["wickets"],
        "overs": match["overs"],
        "balls": match["balls"],
        "extras": match["extras"],
        "striker": match["striker"],
        "non_striker": match["non_striker"],
        "bowler": match["bowler"],
        "partnership_runs": match["partnership_runs"],
        "partnership_balls": match["partnership_balls"],
        "match_status": match["match_status"],
        "log_len": len(match["ball_by_ball_log"])
    })
    if len(match["history"]) > 25: match["history"].pop(0)

def add_ball(cid, legal=True):
    if legal:
        match["balls"] += 1
        match["partnership_balls"] += 1
        completed_overs = match["balls"] // 6
        remaining_balls = match["balls"] % 6
        match["overs"] = float(f"{completed_overs}.{remaining_balls}")
        ensure_player(match["bowler"])
        match["career_db"][match["bowler"]]["bowled_balls"] += 1

        if remaining_balls == 0 and match["balls"] > 0:
            crr = match['runs'] / (match['balls'] / 6)
            comm = f"🎙️ **COMMENTARY:** Over {completed_overs}/{match['total_match_overs']} finished! Score: {match['runs']}/{match['wickets']} (CRR: {crr:.2f})."
            try: bot.send_message(cid, comm, parse_mode="Markdown")
            except: pass

@bot.callback_query_handler(func=lambda call: True)
def on_scorer_action(call):
    try:
        uid, dt = call.from_user.id, call.data
        if not is_authorized(uid):
            return bot.answer_callback_query(call.id, "⚠️ Aap authorized scorer nahi hain!", show_alert=True)

        # 1. TEAM & SQUAD MANAGEMENT
        if dt == "menu_manage_teams":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(
                InlineKeyboardButton("➕ Add New Team", callback_data="sub_add_team"),
                InlineKeyboardButton("➕ Add Player to Squad", callback_data="sub_add_player")
            )
            m.add(InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_home"))
            return bot.edit_message_text("👥 **Team & Squad Management (Supports 8 to 16+ Players):**", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "sub_add_team":
            match["awaiting"] = "input_new_team"
            return bot.edit_message_text("✍️ Nayi **Team ka Naam** type karke bhejain:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")

        if dt == "sub_add_player":
            m = InlineKeyboardMarkup(row_width=2)
            for t in match["teams"]:
                m.add(InlineKeyboardButton(f"📁 {t}", callback_data=f"sel_team_for_player_{t}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="menu_manage_teams"))
            return bot.edit_message_text("📁 Kis team mein player add karna hai, select karein:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("sel_team_for_player_"):
            t_name = dt.replace("sel_team_for_player_", "")
            match["temp_team"] = t_name
            match["awaiting"] = "input_new_player"
            return bot.edit_message_text(f"✍️ Team **{t_name}** ke naye player ka naam type karke bhejain:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")

        # 2. DYNAMIC SQUAD SELECTION BUTTONS (Striker, Non-Striker, Bowler)
        if dt == "btn_set_striker":
            m = InlineKeyboardMarkup(row_width=2)
            bat_team = match["batting_team"]
            squad_list = match["squads"].get(bat_team, [])
            for p in squad_list:
                m.add(InlineKeyboardButton(f"🏏 {p}", callback_data=f"set_str_{p}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_home"))
            return bot.edit_message_text(f"👤 Select **Striker** from **{bat_team}** squad:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("set_str_"):
            p_name = dt.replace("set_str_", "")
            match["striker"] = p_name
            ensure_player(p_name, team=match["batting_team"])
            return bot.edit_message_text(f"✅ Striker updated to **{p_name}**!\n\n" + get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "btn_set_nonstriker":
            m = InlineKeyboardMarkup(row_width=2)
            bat_team = match["batting_team"]
            squad_list = match["squads"].get(bat_team, [])
            for p in squad_list:
                m.add(InlineKeyboardButton(f"🏃 {p}", callback_data=f"set_nonstr_{p}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_home"))
            return bot.edit_message_text(f"👤 Select **Non-Striker** from **{bat_team}** squad:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("set_nonstr_"):
            p_name = dt.replace("set_nonstr_", "")
            match["non_striker"] = p_name
            ensure_player(p_name, team=match["batting_team"])
            return bot.edit_message_text(f"✅ Non-Striker updated to **{p_name}**!\n\n" + get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "btn_set_bowler":
            m = InlineKeyboardMarkup(row_width=2)
            bowl_team = match["bowling_team"]
            squad_list = match["squads"].get(bowl_team, [])
            for p in squad_list:
                m.add(InlineKeyboardButton(f"⚾ {p}", callback_data=f"set_bowl_{p}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_home"))
            return bot.edit_message_text(f"⚾ Select new **Bowler** from **{bowl_team}** squad:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("set_bowl_"):
            p_name = dt.replace("set_bowl_", "")
            match["bowler"] = p_name
            ensure_player(p_name, team=match["bowling_team"])
            return bot.edit_message_text(f"✅ Bowler updated to **{p_name}**!\n\n" + get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        # 3. FULLY DYNAMIC NO BALL & WIDE MENUS (0 to 6 runs off bat)
        if dt == "menu_nb":
            m = InlineKeyboardMarkup(row_width=3)
            for r in range(7):
                m.add(InlineKeyboardButton(f"NB + {r} Bat Runs", callback_data=f"exec_nb_{r}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_home"))
            return bot.edit_message_text("⚠️ **No Ball Dynamic Menu:**\nNo ball par batsman ne bat se kitne runs banaye?", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("exec_nb_"):
            bat_runs = int(dt.replace("exec_nb_", ""))
            total_ball_runs = 1 + bat_runs # 1 for No ball extra + bat runs
            match["runs"] += total_ball_runs
            match["extras"] += 1
            match["partnership_runs"] += bat_runs
            
            ensure_player(match["striker"])
            p_st = match["career_db"][match["striker"]]
            p_st["runs"] += bat_runs
            if bat_runs == 4: p_st["fours"] += 1
            if bat_runs == 6: p_st["sixes"] += 1
            
            ensure_player(match["bowler"])
            match["career_db"][match["bowler"]]["runs_given"] += total_ball_runs
            
            if bat_runs in [1, 3]:
                match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            
            match["ball_by_ball_log"].append(f"Over {match['overs']}: No Ball + {bat_runs} runs by {match['striker']}")
            bot.answer_callback_query(call.id, f"No Ball + {bat_runs} Recorded!")
            return bot.edit_message_text(get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "menu_wide":
            m = InlineKeyboardMarkup(row_width=3)
            for r in range(7):
                m.add(InlineKeyboardButton(f"Wide + {r} Extra/Bat", callback_data=f"exec_wd_{r}"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_home"))
            return bot.edit_message_text("⚡ **Wide Dynamic Menu:**\nWide ball par kitne extra runs jude?", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt.startswith("exec_wd_"):
            extra_w = int(dt.replace("exec_wd_", ""))
            total_wd = 1 + extra_w
            match["runs"] += total_wd
            match["extras"] += total_wd
            ensure_player(match["bowler"])
            match["career_db"][match["bowler"]]["runs_given"] += total_wd
            
            match["ball_by_ball_log"].append(f"Over {match['overs']}: Wide + {extra_w}")
            bot.answer_callback_query(call.id, "Wide Recorded!")
            return bot.edit_message_text(get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "menu_extras":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("🏃 Bye (+1)", callback_data="sc_bye"), InlineKeyboardButton("🦵 Leg Bye (+1)", callback_data="sc_lb"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_home"))
            return bot.edit_message_text("🏃 Select Bye or Leg Bye:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "back_home":
            return bot.edit_message_text(get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        # 4. STANDARD CONTROLS (Toss, Summary, Leaderboard, Series)
        if dt == "menu_toss":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("🎲 Bot Toss", callback_data="toss_bot"), InlineKeyboardButton("✍️ Manual Toss", callback_data="toss_manual"))
            m.add(InlineKeyboardButton("⬅️ Back", callback_data="back_home"))
            return bot.edit_message_text("🪙 **Select Toss Mode:**", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "toss_bot":
            if len(match["teams"]) < 2:
                return bot.answer_callback_query(call.id, "⚠️ Pehle kam se kam 2 teams add karein!", show_alert=True)
            winner = random.choice(match["teams"])
            decision = random.choice(["bat", "bowl"])
            match["toss_winner"] = winner
            match["toss_decision"] = decision
            other_team = [t for t in match["teams"] if t != winner][0]
            if decision == "bat":
                match["batting_team"] = winner
                match["bowling_team"] = other_team
            else:
                match["bowling_team"] = winner
                match["batting_team"] = other_team
            bot.answer_callback_query(call.id, f"Toss Done: {winner} won!")
            return bot.edit_message_text(f"🪙 **Toss Result:** `{winner}` won and elected to `{decision}` first!\n\n" + get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "toss_manual":
            match["awaiting"] = "toss_manual_input"
            return bot.edit_message_text("✍️ **Manual Toss Format:**\n`TeamName | bat` ya `TeamName | bowl`", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")

        if dt == "menu_settings":
            match["awaiting"] = "set_overs_input"
            return bot.edit_message_text("⚙️ **Match Overs Setup:**\nTotal overs type karke bhejain (Jaise: `20`):", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")

        if dt == "toggle_practice":
            match["is_practice_mode"] = not match["is_practice_mode"]
            mode_name = "Practice Mode" if match["is_practice_mode"] else "Real Tournament Mode"
            bot.answer_callback_query(call.id, f"Switched to {mode_name}!")
            return bot.edit_message_text(f"🧪 Bot mode: **{mode_name}**.\n\n" + get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "reset_practice":
            if match["is_practice_mode"]:
                match["runs"], match["wickets"], match["overs"], match["balls"], match["extras"] = 0, 0, 0.0, 0, 0
                match["history"].clear()
                match["ball_by_ball_log"].clear()
                bot.answer_callback_query(call.id, "Practice stats reset!")
                return bot.edit_message_text("🗑️ **Practice stats reset to zero!**\n\n" + get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")
            else:
                return bot.answer_callback_query(call.id, "⚠️ Real Match mode mein reset allowed nahi hai!", show_alert=True)

        if dt == "get_summary":
            summary_text = (
                f"📊 *{match['series_name']} - MATCH SUMMARY* 🏏\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🪙 *Toss:* {match['toss_winner']} elected to {match['toss_decision']}\n"
                f"🏟️ *Batting Team:* {match['batting_team']}\n"
                f"🎯 *Bowling Team:* {match['bowling_team']}\n"
                f"📋 *Final Score:* *{match['runs']} / {match['wickets']}* in *{match['overs']}/{match['total_match_overs']}* Overs\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📜 *BALL-TO-BALL LOG:* \n"
            )
            if match["ball_by_ball_log"]: summary_text += "\n".join(match["ball_by_ball_log"][-20:])
            else: summary_text += "_No logs recorded yet._"
            summary_text += f"\n━━━━━━━━━━━━━━━━━━━━━━\n✨ _Generated via Telegram Pro Cricket Bot_"
            bot.send_message(call.message.chat.id, summary_text, parse_mode="Markdown")
            return bot.answer_callback_query(call.id, "Summary Generated!")

        if dt == "match_leaderboard":
            lb_text = f"🏆 **{match['series_name']} - SERIES STATS** 📊\n──────────────────────────\n"
            sorted_players = sorted(match["career_db"].items(), key=lambda x: x[1]["runs"], reverse=True)
            for idx, (pname, pdata) in enumerate(sorted_players[:5], 1):
                sr = (pdata["runs"] / pdata["balls"] * 100) if pdata["balls"] > 0 else 0.0
                lb_text += f"{idx}. **{pname}** — `{pdata['runs']} runs` | Wkts: `{pdata['wickets']}` | SR: `{sr:.1f}`\n"
            bot.send_message(call.message.chat.id, lb_text, parse_mode="Markdown")
            return bot.answer_callback_query(call.id, "Leaderboard Sent!")

        if dt == "sc_swap":
            match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            bot.answer_callback_query(call.id, "Strike Swapped!")
            return bot.edit_message_text(get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "sc_mom":
            best_player, max_pts = "None", -1
            for p, st in match["career_db"].items():
                pts = (st["runs"] * 1) + (st["wickets"] * 25) + (st["fours"] * 1) + (st["sixes"] * 2)
                if pts > max_pts: max_pts, best_player = pts, p
            mom_text = f"🏆 **SERIES & MATCH AWARDS** 🌟\n\n⭐ **Man of the Match / Series:** `{best_player}` with outstanding overall performance!"
            bot.send_message(call.message.chat.id, mom_text, parse_mode="Markdown")
            return bot.answer_callback_query(call.id, "Awards Calculated!")

        if dt == "sc_switch":
            other_teams = [t for t in match["teams"] if t != match["batting_team"]]
            match["bowling_team"] = match["batting_team"]
            match["batting_team"] = other_teams[0] if other_teams else "Opponent Team"
            match["target"] = match["runs"] + 1
            match["runs"], match["wickets"], match["overs"], match["balls"], match["extras"] = 0, 0, 0.0, 0, 0
            match["partnership_runs"], match["partnership_balls"] = 0, 0
            match["is_second_innings"] = True
            match["history"].clear()
            match["ball_by_ball_log"].clear()
            bot.answer_callback_query(call.id, "Innings Switched!")
            return bot.edit_message_text("🔄 Innings Switched! 2nd Innings Started.\n\n" + get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "sc_undo":
            if not match["history"]: return bot.answer_callback_query(call.id, "Nothing to undo!", show_alert=True)
            last = match["history"].pop()
            match["runs"] = last["runs"]
            match["wickets"] = last["wickets"]
            match["overs"] = last["overs"]
            match["balls"] = last["balls"]
            match["extras"] = last["extras"]
            match["striker"] = last["striker"]
            match["non_striker"] = last["non_striker"]
            match["bowler"] = last["bowler"]
            match["partnership_runs"] = last["partnership_runs"]
            match["partnership_balls"] = last["partnership_balls"]
            if len(match["ball_by_ball_log"]) > last["log_len"]:
                match["ball_by_ball_log"] = match["ball_by_ball_log"][:last["log_len"]]
            bot.answer_callback_query(call.id, "Undo Successful!")
            return bot.edit_message_text(get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "sc_retire":
            match["awaiting"] = "retire_player_name"
            return bot.edit_message_text("✍️ Jo batsman **Retire Hurt** ya **Declare** hua hai, uska exact naam type karke bhejain:", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")

        save_state_for_undo()
        ensure_player(match["striker"])
        ensure_player(match["bowler"])

        action_desc = ""
        if dt in ["sc_0", "sc_1", "sc_2", "sc_3", "sc_4", "sc_6"]:
            r_val = int(dt.split("_")[1])
            match["runs"] += r_val
            match["partnership_runs"] += r_val
            p_st = match["career_db"][match["striker"]]
            p_st["runs"] += r_val
            p_st["balls"] += 1
            if r_val == 4: p_st["fours"] += 1
            if r_val == 6: p_st["sixes"] += 1
            
            match["career_db"][match["bowler"]]["runs_given"] += r_val
            add_ball(call.message.chat.id, legal=True)
            action_desc = f"Over {match['overs']}: {match['striker']} scored {r_val} off {match['bowler']}"
            if r_val in [1, 3]: match["striker"], match["non_striker"] = match["non_striker"], match["striker"]

        elif dt == "sc_bye":
            match["runs"] += 1
            match["extras"] += 1
            add_ball(call.message.chat.id, legal=True)
            action_desc = f"Over {match['overs']}: Bye (+1)"

        elif dt == "sc_lb":
            match["runs"] += 1
            match["extras"] += 1
            add_ball(call.message.chat.id, legal=True)
            action_desc = f"Over {match['overs']}: Leg Bye (+1)"

        elif dt == "sc_wkt":
            if match["wickets"] < 10:
                match["wickets"] += 1
                match["career_db"][match["striker"]]["balls"] += 1
                match["career_db"][match["bowler"]]["wickets"] += 1
                action_desc = f"Over {match['overs']}: WICKET! {match['striker']} out b {match['bowler']}"
                match["partnership_runs"], match["partnership_balls"] = 0, 0
                add_ball(call.message.chat.id, legal=True)
                match["striker"] = "Select Striker"

        if action_desc: match["ball_by_ball_log"].append(action_desc)

        bot.answer_callback_query(call.id, f"Recorded: {dt.replace('sc_', '').upper()}")
        bot.edit_message_text(
            get_scoreboard_text(), 
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            reply_markup=get_scorer_markup(), 
            parse_mode="Markdown"
        )

    except Exception as e:
        try: bot.answer_callback_query(call.id, "⚠️ Action expired, please refresh!", show_alert=True)
        except: pass

@bot.message_handler(func=lambda m: match["awaiting"] is not None)
def handle_text_inputs(msg):
    if not is_authorized(msg.from_user.id): return
    
    state = match["awaiting"]
    match["awaiting"] = None
    txt = msg.text.strip().title()

    if state == "input_new_team":
        if txt not in match["teams"]:
            match["teams"].append(txt)
            match["squads"][txt] = []
            bot.reply_to(msg, f"✅ Team **{txt}** successfully add ho gayi hai!", parse_mode="Markdown")
        else:
            bot.reply_to(msg, f"⚠️ Team pehle se list mein hai.", parse_mode="Markdown")
        return

    if state == "input_new_player":
        t_name = match["temp_team"]
        ensure_player(txt, team=t_name)
        if txt not in match["squads"][t_name]:
            match["squads"][t_name].append(txt)
        bot.reply_to(msg, f"✅ Player **{txt}** ko team **{t_name}** mein add kar diya gaya hai!", parse_mode="Markdown")
        return

    if state == "set_overs_input":
        try:
            o_val = int(txt)
            if o_val <= 0: raise ValueError()
            match["total_match_overs"] = o_val
            bot.reply_to(msg, f"✅ **Match Overs set to `{o_val} Overs`!**\n\n{get_scoreboard_text()}", parse_mode="Markdown")
        except:
            bot.reply_to(msg, "⚠️ Kripya valid number bhejain (Jaise: `20`).", parse_mode="Markdown")
        return

    if state == "toss_manual_input":
        if "|" not in msg.text:
            bot.reply_to(msg, "⚠️ Format: `TeamName | bat` ya `TeamName | bowl`", parse_mode="Markdown")
            return
        t_name, t_dec = [x.strip().title() for x in msg.text.split("|", 1)]
        t_dec = t_dec.lower()
        if t_dec not in ["bat", "bowl"]:
            bot.reply_to(msg, "⚠️ Decision sirf `bat` ya `bowl` hona chahiye.", parse_mode="Markdown")
            return
        
        match["toss_winner"] = t_name
        match["toss_decision"] = t_dec
        other_teams = [t for t in match["teams"] if t != t_name]
        other_team = other_teams[0] if other_teams else "Opponent Team"
        if t_name not in match["teams"]: match["teams"].append(t_name)
        
        if t_dec == "bat":
            match["batting_team"] = t_name
            match["bowling_team"] = other_team
        else:
            match["bowling_team"] = t_name
            match["batting_team"] = other_team
        
        bot.reply_to(msg, f"✅ **Toss Updated!** {t_name} elected to {t_dec}.\n\n{get_scoreboard_text()}", parse_mode="Markdown")
        return

    if state == "retire_player_name":
        if match["striker"] == txt:
            match["striker"] = "Select Striker"
        elif match["non_striker"] == txt:
            match["non_striker"] = "Select Non-Striker"
        bot.reply_to(msg, f"✅ Player **{txt}** ko Retire Hurt / Declare mark kar diya gaya hai. Naya player select karein.", parse_mode="Markdown")
        return

if __name__ == "__main__":
    try: bot.remove_webhook()
    except Exception: pass
    print("Pro Cricket Series Scorer is running 24/7...")
    bot.infinity_polling(skip_pending=True, timeout=20)