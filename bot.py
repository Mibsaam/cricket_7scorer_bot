import os, random, time, threading, urllib.request
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8670400703:AAFx9ZbF8Hzv3SCU9TyN9Mh-LlOuKzV6p-k"
ADMIN_ID = 874225351

# Authorized Scorers List (Admin ID is default included)
AUTHORIZED_SCORERS = {ADMIN_ID}

# 24/7 RENDER KEEP-ALIVE SERVER (Never Sleep)
app = Flask(__name__)
@app.route("/")
def h(): return "Pro Cricket Scorer Active 24/7", 200

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

# MATCH ENGINE STATE
match = {
    "team_a": "Mumbai Strikers",
    "team_b": "Team Unity",
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
    "striker": "Batsman 1",
    "non_striker": "Batsman 2",
    "bowler": "Bowler 1",
    "partnership_runs": 0,
    "partnership_balls": 0,
    "match_status": "Setup / Toss Pending",
    "is_practice_mode": True,
    "history": [],
    "ball_by_ball_log": [],
    "commentary_log": [],
    "awaiting": None,
    "awaiting_profile": False,
    "career_db": {
        "Batsman 1": {"team": "Mumbai Strikers", "matches": 15, "runs": 520, "balls": 340, "fours": 48, "sixes": 22, "wickets": 1, "bowled_balls": 0, "runs_given": 0},
        "Batsman 2": {"team": "Team Unity", "matches": 12, "runs": 390, "balls": 270, "fours": 32, "sixes": 15, "wickets": 0, "bowled_balls": 0, "runs_given": 0},
        "Bowler 1": {"team": "Team Unity", "matches": 18, "runs": 90, "balls": 72, "fours": 6, "sixes": 3, "wickets": 26, "bowled_balls": 120, "runs_given": 110}
    },
    "h2h_db": {}
}

def is_authorized(user_id):
    return user_id in AUTHORIZED_SCORERS

def ensure_player(name, team="General"):
    if name not in match["career_db"]:
        match["career_db"][name] = {"team": team, "matches": 1, "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "wickets": 0, "bowled_balls": 0, "runs_given": 0}

def record_h2h(batter, bowler, runs_scored, is_out=False):
    if batter not in match["h2h_db"]: match["h2h_db"][batter] = {}
    if bowler not in match["h2h_db"][batter]: match["h2h_db"][batter][bowler] = {"runs": 0, "balls": 0, "dismissals": 0}
    match["h2h_db"][batter][bowler]["runs"] += runs_scored
    match["h2h_db"][batter][bowler]["balls"] += 1
    if is_out: match["h2h_db"][batter][bowler]["dismissals"] += 1

def get_h2h_stats(batter, bowler):
    if batter in match["h2h_db"] and bowler in match["h2h_db"][batter]:
        st = match["h2h_db"][batter][bowler]
        return f"⚔️ **H2H (Battle):** `{st['runs']} runs` off `{st['balls']} balls` | Dismissals: `{st['dismissals']}`"
    return "⚔️ **H2H (Battle):** First time facing each other!"

def get_scorer_markup():
    m = InlineKeyboardMarkup(row_width=3)
    m.add(
        InlineKeyboardButton("🔴 0 Dot", callback_data="sc_0"),
        InlineKeyboardButton("🟢 1 Run", callback_data="sc_1"),
        InlineKeyboardButton("🔵 2 Runs", callback_data="sc_2")
    )
    m.add(
        InlineKeyboardButton("🟡 3 Runs", callback_data="sc_3"),
        InlineKeyboardButton("🔥 4 Boundary 4️⃣", callback_data="sc_4"),
        InlineKeyboardButton("🚀 6 Sixer 6️⃣", callback_data="sc_6")
    )
    m.add(
        InlineKeyboardButton("⚡ Wide (+1)", callback_data="sc_wide"),
        InlineKeyboardButton("⚠️ No Ball (+1)", callback_data="sc_nb"),
        InlineKeyboardButton("🏃 Bye (+1)", callback_data="sc_bye")
    )
    m.add(
        InlineKeyboardButton("🦵 Leg Bye (+1)", callback_data="sc_lb"),
        InlineKeyboardButton("🏏 NB + 4 Runs", callback_data="sc_nb_4"),
        InlineKeyboardButton("❌ Wicket Fallen", callback_data="sc_wkt")
    )
    m.add(
        InlineKeyboardButton("🪙 Toss Setup", callback_data="menu_toss"),
        InlineKeyboardButton("⚙️ Match Settings", callback_data="menu_settings")
    )
    m.add(
        InlineKeyboardButton("✏️ Set Striker", callback_data="set_striker"),
        InlineKeyboardButton("✏️ Set Non-Striker", callback_data="set_nonstriker")
    )
    m.add(
        InlineKeyboardButton("⚾ Set Bowler", callback_data="set_bowler"),
        InlineKeyboardButton("📊 Player Record", callback_data="view_profile")
    )
    m.add(
        InlineKeyboardButton("📋 WhatsApp Summary", callback_data="get_summary"),
        InlineKeyboardButton("🏆 Leaderboard", callback_data="match_leaderboard")
    )
    m.add(
        InlineKeyboardButton("🔄 Swap Strike", callback_data="sc_swap"),
        InlineKeyboardButton("⭐ Man of the Match", callback_data="sc_mom")
    )
    m.add(
        InlineKeyboardButton("🧪 Toggle Practice", callback_data="toggle_practice"),
        InlineKeyboardButton("🗑️ Reset Practice", callback_data="reset_practice")
    )
    m.add(
        InlineKeyboardButton("🌧️ Apply DLS", callback_data="sc_dls"),
        InlineKeyboardButton("🛑 Abandon", callback_data="sc_abandon")
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
    h2h_preview = get_h2h_stats(match["striker"], match["bowler"])

    return (
        f"🏆 **ULTIMATE PRO CRICKET SCOREBOARD** 🏏\n"
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
        f" {h2h_preview}\n"
        f"──────────────────────────"
    )

@bot.message_handler(commands=['start', 'scorer'])
def c_start(msg):
    bot.reply_to(
        msg, 
        "⚡ **Pro Cricket Scorer Initialized!**\nControl panel active hai:", 
        reply_markup=get_scorer_markup(), 
        parse_mode="Markdown"
    )
    bot.send_message(msg.chat.id, get_scoreboard_text(), parse_mode="Markdown")

# DYNAMIC SCORER ADDITION COMMAND (/addscorer UserID)
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

@bot.message_handler(commands=['renameplayer'])
def c_renameplayer(msg):
    if not is_authorized(msg.from_user.id): return
    txt = msg.text.replace("/renameplayer", "").strip()
    if "|" not in txt:
        return bot.reply_to(msg, "⚠️ Format: `/renameplayer OldName | NewName`", parse_mode="Markdown")
    old_n, new_n = [x.strip().title() for x in txt.split("|", 1)]
    if old_n in match["career_db"]:
        match["career_db"][new_n] = match["career_db"].pop(old_n)
        if match["striker"] == old_n: match["striker"] = new_n
        if match["non_striker"] == old_n: match["non_striker"] = new_n
        if match["bowler"] == old_n: match["bowler"] = new_n
        bot.reply_to(msg, f"✅ Success! `{old_n}` renamed to `{new_n}`.", parse_mode="Markdown")
    else:
        bot.reply_to(msg, f"❌ Player `{old_n}` nahi mila.", parse_mode="Markdown")

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
            match["commentary_log"].append(comm)
            try: bot.send_message(cid, comm, parse_mode="Markdown")
            except: pass

@bot.callback_query_handler(func=lambda call: True)
def on_scorer_action(call):
    try:
        uid, dt = call.from_user.id, call.data
        if not is_authorized(uid):
            return bot.answer_callback_query(call.id, "⚠️ Aap authorized scorer nahi hain!", show_alert=True)

        if dt == "menu_toss":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("🎲 Bot Toss", callback_data="toss_bot"), InlineKeyboardButton("✍️ Manual Toss", callback_data="toss_manual"))
            return bot.edit_message_text("🪙 **Select Toss Mode:**", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m, parse_mode="Markdown")

        if dt == "toss_bot":
            winner = random.choice([match["team_a"], match["team_b"]])
            decision = random.choice(["bat", "bowl"])
            match["toss_winner"] = winner
            match["toss_decision"] = decision
            if decision == "bat":
                match["batting_team"] = winner
                match["bowling_team"] = match["team_b"] if winner == match["team_a"] else match["team_a"]
            else:
                match["bowling_team"] = winner
                match["batting_team"] = match["team_b"] if winner == match["team_a"] else match["team_a"]
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

        if dt == "set_striker":
            match["awaiting"] = "striker"
            return bot.edit_message_text("✍️ Naye **Striker Batsman** ka naam bhejain:", chat_id=call.message.chat.id, message_id=call.message.message_id)
        if dt == "set_nonstriker":
            match["awaiting"] = "non_striker"
            return bot.edit_message_text("✍️ Naye **Non-Striker Batsman** ka naam bhejain:", chat_id=call.message.chat.id, message_id=call.message.message_id)
        if dt == "set_bowler":
            match["awaiting"] = "bowler"
            return bot.edit_message_text("✍️ Naye **Bowler** ka naam bhejain:", chat_id=call.message.chat.id, message_id=call.message.message_id)
        
        if dt == "view_profile":
            match["awaiting_profile"] = True
            return bot.edit_message_text("✍️ Jis player ka **Record** dekhna hai, uska naam bhejain:", chat_id=call.message.chat.id, message_id=call.message.message_id)

        if dt == "get_summary":
            summary_text = (
                f"📊 *CRICKET MATCH SUMMARY REPORT* 🏏\n"
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
            lb_text = "🏆 **TOURNAMENT LEADERBOARD** 📊\n──────────────────────────\n"
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

        if dt == "sc_dls":
            match["match_status"] = "DLS_APPLIED"
            if match["overs"] > 0:
                current_rr = match["runs"] / (match["balls"] / 6)
                match["target"] = int(match["runs"] + (current_rr * 4))
            bot.answer_callback_query(call.id, "DLS Applied!", show_alert=True)
            return bot.edit_message_text("🌧️ **DLS Method Applied!** Target adjusted.\n\n" + get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "sc_abandon":
            match["match_status"] = "ABANDONED ❌"
            bot.answer_callback_query(call.id, "Match Abandoned!", show_alert=True)
            return bot.edit_message_text("🛑 **Match Abandoned (No Result)!**\n\n" + get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "sc_mom":
            best_player, max_pts = "None", -1
            for p, st in match["career_db"].items():
                pts = (st["runs"] * 1) + (st["wickets"] * 25) + (st["fours"] * 1) + (st["sixes"] * 2)
                if pts > max_pts: max_pts, best_player = pts, p
            mom_text = f"🏆 **MAN OF THE MATCH** 🌟\n\n⭐ **{best_player}** wins Man of the Match!"
            bot.send_message(call.message.chat.id, mom_text, parse_mode="Markdown")
            return bot.answer_callback_query(call.id, "Man of the Match Calculated!")

        if dt == "sc_switch":
            match["batting_team"], match["bowling_team"] = match["bowling_team"], match["batting_team"]
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
            record_h2h(match["striker"], match["bowler"], r_val, is_out=False)
            add_ball(call.message.chat.id, legal=True)
            action_desc = f"Over {match['overs']}: {match['striker']} scored {r_val} off {match['bowler']}"
            if r_val in [1, 3]: match["striker"], match["non_striker"] = match["non_striker"], match["striker"]

        elif dt == "sc_wide":
            match["runs"] += 1
            match["extras"] += 1
            match["career_db"][match["bowler"]]["runs_given"] += 1
            action_desc = f"Over {match['overs']}: Wide ball"

        elif dt == "sc_nb":
            match["runs"] += 1
            match["extras"] += 1
            match["career_db"][match["bowler"]]["runs_given"] += 1
            action_desc = f"Over {match['overs']}: No Ball"

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

        elif dt == "sc_nb_4":
            match["runs"] += 5
            match["extras"] += 1
            match["partnership_runs"] += 4
            p_st = match["career_db"][match["striker"]]
            p_st["runs"] += 4
            p_st["fours"] += 1
            match["career_db"][match["bowler"]]["runs_given"] += 5
            record_h2h(match["striker"], match["bowler"], 4, is_out=False)
            action_desc = f"Over {match['overs']}: No Ball + 4 runs by {match['striker']}"

        elif dt == "sc_wkt":
            if match["wickets"] < 10:
                match["wickets"] += 1
                match["career_db"][match["striker"]]["balls"] += 1
                match["career_db"][match["bowler"]]["wickets"] += 1
                record_h2h(match["striker"], match["bowler"], 0, is_out=True)
                action_desc = f"Over {match['overs']}: WICKET! {match['striker']} out b {match['bowler']}"
                match["partnership_runs"], match["partnership_balls"] = 0, 0
                add_ball(call.message.chat.id, legal=True)
                match["striker"] = f"Batsman WKT-{match['wickets']+1}"
                ensure_player(match["striker"])

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

@bot.message_handler(func=lambda m: match["awaiting"] is not None or match["awaiting_profile"])
def handle_text_inputs(msg):
    if not is_authorized(msg.from_user.id): return
    
    if match["awaiting_profile"]:
        match["awaiting_profile"] = False
        p_name = msg.text.strip().title()
        if p_name in match["career_db"]:
            st = match["career_db"][p_name]
            sr = (st["runs"] / st["balls"] * 100) if st["balls"] > 0 else 0.0
            overs_bowled = f"{st['bowled_balls'] // 6}.{st['bowled_balls'] % 6}"
            econ = (st["runs_given"] / (st['bowled_balls'] / 6)) if st['bowled_balls'] > 0 else 0.0
            profile_msg = (
                f"👤 **PLAYER CAREER RECORD** 📊\n"
                f"──────────────────────────\n"
                f" 🏷️ **Name:** `{p_name}`\n"
                f" 🏏 **Batting:** `{st['runs']} runs` ({st['balls']}b) | SR: `{sr:.2f}`\n"
                f" 🔥 **Boundaries:** `{st['fours']}x4` | `{st['sixes']}x6`\n"
                f" ⚾ **Bowling:** `{st['wickets']} Wickets` | Overs: `{overs_bowled}` | Econ: `{econ:.2f}`\n"
                f"──────────────────────────"
            )
            bot.reply_to(msg, profile_msg, parse_mode="Markdown")
        else:
            bot.reply_to(msg, f"❌ Player `{p_name}` record database mein nahi mila.", parse_mode="Markdown")
        return

    if match["awaiting"] == "set_overs_input":
        match["awaiting"] = None
        try:
            o_val = int(msg.text.strip())
            if o_val <= 0: raise ValueError()
            match["total_match_overs"] = o_val
            bot.reply_to(msg, f"✅ **Match Overs set to `{o_val} Overs`!**\n\n{get_scoreboard_text()}", parse_mode="Markdown")
        except:
            bot.reply_to(msg, "⚠️ Kripya valid number bhejain (Jaise: `20`).", parse_mode="Markdown")
        return

    if match["awaiting"] == "toss_manual_input":
        match["awaiting"] = None
        txt = msg.text.strip()
        if "|" not in txt:
            bot.reply_to(msg, "⚠️ Format: `TeamName | bat` ya `TeamName | bowl`", parse_mode="Markdown")
            return
        t_name, t_dec = [x.strip() for x in txt.split("|", 1)]
        t_dec = t_dec.lower()
        if t_dec not in ["bat", "bowl"]:
            bot.reply_to(msg, "⚠️ Decision sirf `bat` ya `bowl` hona chahiye.", parse_mode="Markdown")
            return
        
        match["toss_winner"] = t_name
        match["toss_decision"] = t_dec
        if t_dec == "bat":
            match["batting_team"] = t_name
            match["bowling_team"] = match["team_b"] if t_name == match["team_a"] else match["team_a"]
        else:
            match["bowling_team"] = t_name
            match["batting_team"] = match["team_b"] if t_name == match["team_a"] else match["team_a"]
        
        bot.reply_to(msg, f"✅ **Toss Updated!** {t_name} elected to {t_dec}.\n\n{get_scoreboard_text()}", parse_mode="Markdown")
        return

    field = match["awaiting"]
    match["awaiting"] = None
    val = msg.text.strip().title()
    ensure_player(val)
    
    if field == "striker": match["striker"] = val
    elif field == "non_striker": match["non_striker"] = val
    elif field == "bowler": match["bowler"] = val

    st = match["career_db"][val]
    sr = (st["runs"] / st["balls"] * 100) if st["balls"] > 0 else 0.0
    h2h_info = ""
    if field in ["striker", "non_striker"]:
        h2h_info = get_h2h_stats(val, match["bowler"])

    flash_msg = (
        f"🚨 **NEW PLAYER ON CREASE!** ⚡\n"
        f"──────────────────────────\n"
        f" 👤 **{val}**\n"
        f" 🏏 Total Runs: `{st['runs']}` (SR: `{sr:.2f}`)\n"
        f" {h2h_info}\n"
        f"──────────────────────────"
    )
    bot.send_message(msg.chat.id, flash_msg, parse_mode="Markdown")
    bot.reply_to(
        msg, 
        f"✅ Updated successfully!\n\n{get_scoreboard_text()}", 
        reply_markup=get_scorer_markup(), 
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    try: bot.remove_webhook()
    except Exception: pass
    print("Pro Cricket Scorer is running 24/7...")
    bot.infinity_polling(skip_pending=True, timeout=20)