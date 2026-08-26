import os, random, time, threading, urllib.request
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8812331993:AAHKPvObvrR6NhBXZIhE9dN-lRPTbye9bdQ"
ADMIN_ID = 874225351

# 24/7 RENDER KEEP-ALIVE SERVER (Never Sleep)
app = Flask(__name__)
@app.route("/")
def h(): return "Ultimate Pro Cricket Scorer Active 24/7", 200

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

# ADVANCED MATCH & PROFESSIONAL STATS ENGINE
match = {
    "batting_team": "Mumbai Strikers",
    "bowling_team": "Team Unity",
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
    "match_status": "LIVE",
    "history": [],
    "ball_by_ball_log": [], # Detailed log for WhatsApp Summary
    "awaiting": None,
    "awaiting_profile": False,
    # Professional Career Database for Testing & Practice Mode
    "career_db": {
        "Batsman 1": {"matches": 15, "runs": 520, "balls": 340, "fours": 48, "sixes": 22, "wickets": 1},
        "Batsman 2": {"matches": 12, "runs": 390, "balls": 270, "fours": 32, "sixes": 15, "wickets": 0},
        "Bowler 1": {"matches": 18, "runs": 90, "balls": 72, "fours": 6, "sixes": 3, "wickets": 26}
    }
}

def ensure_player(name):
    if name not in match["career_db"]:
        match["career_db"][name] = {"matches": 1, "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "wickets": 0}

def get_scorer_markup():
    m = InlineKeyboardMarkup(row_width=3)
    # 1. Standard Runs
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
    # 2. Extras & Bat Combinations
    m.add(
        InlineKeyboardButton("⚡ Wide (+1)", callback_data="sc_wide"),
        InlineKeyboardButton("⚠️ No Ball (+1)", callback_data="sc_nb"),
        InlineKeyboardButton("🏏 NB + 4 Runs", callback_data="sc_nb_4")
    )
    m.add(
        InlineKeyboardButton("🚀 NB + 6 Runs", callback_data="sc_nb_6"),
        InlineKeyboardButton("❌ Wicket Fallen", callback_data="sc_wkt")
    )
    # 3. Player Management & Profiles
    m.add(
        InlineKeyboardButton("✏️ Set Striker", callback_data="set_striker"),
        InlineKeyboardButton("✏️ Set Non-Striker", callback_data="set_nonstriker")
    )
    m.add(
        InlineKeyboardButton("⚾ Set Bowler", callback_data="set_bowler"),
        InlineKeyboardButton("📊 Player Profile Lookup", callback_data="view_profile")
    )
    # 4. Special Reports & Tournament Extras
    m.add(
        InlineKeyboardButton("📋 WhatsApp Summary", callback_data="get_summary"),
        InlineKeyboardButton("🏆 Leaderboard / Stats", callback_data="match_leaderboard")
    )
    m.add(
        InlineKeyboardButton("🔄 Swap Strike", callback_data="sc_swap"),
        InlineKeyboardButton("⭐ Man of the Match", callback_data="sc_mom")
    )
    # 5. Match Controls & Rules
    m.add(
        InlineKeyboardButton("🌧️ Apply DLS", callback_data="sc_dls"),
        InlineKeyboardButton("🛑 Abandon Match", callback_data="sc_abandon")
    )
    m.add(
        InlineKeyboardButton("↩️ Undo Last Ball", callback_data="sc_undo"),
        InlineKeyboardButton("🔄 Switch Innings", callback_data="sc_switch")
    )
    return m

def get_scoreboard_text():
    overs_display = f"{match['overs']}"
    run_rate = (match['runs'] / (match['balls'] / 6)) if match['balls'] > 0 else 0.0
    target_info = f"\n 🎯 **Target:** `{match['target']}`" if match["is_second_innings"] else ""
    status_info = f"\n 📌 **Status:** `{match['match_status']}`" if match["match_status"] != "LIVE" else ""
    
    return (
        f"🏆 **ULTIMATE PRO CRICKET SCOREBOARD** 🏏\n"
        f"──────────────────────────\n"
        f" Batting: **{match['batting_team']}** vs Bowling: **{match['bowling_team']}**"
        f"{target_info}{status_info}\n"
        f"──────────────────────────\n"
        f" 🎯 **Score:** `{match['runs']} / {match['wickets']}`\n"
        f" 🌀 **Overs:** `{overs_display}` | **Extras:** `{match['extras']}`\n"
        f" 📈 **Run Rate:** `{run_rate:.2f}`\n"
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
        "⚡ **Pro Cricket Scorer Initialized for Live & Practice Testing!**\nControl panel active hai:", 
        reply_markup=get_scorer_markup(), 
        parse_mode="Markdown"
    )
    bot.send_message(msg.chat.id, get_scoreboard_text(), parse_mode="Markdown")

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

def add_ball(legal=True):
    if legal:
        match["balls"] += 1
        match["partnership_balls"] += 1
        completed_overs = match["balls"] // 6
        remaining_balls = match["balls"] % 6
        match["overs"] = float(f"{completed_overs}.{remaining_balls}")

@bot.callback_query_handler(func=lambda call: True)
def on_scorer_action(call):
    try:
        uid, dt = call.from_user.id, call.data
        if uid != ADMIN_ID:
            return bot.answer_callback_query(call.id, "⚠️ Only Admin/Scorer can control this!", show_alert=True)

        if dt == "set_striker":
            match["awaiting"] = "striker"
            return bot.edit_message_text("✍️ Naye **Striker Batsman** ka naam type karke bhejain:", chat_id=call.message.chat.id, message_id=call.message.message_id)
        if dt == "set_nonstriker":
            match["awaiting"] = "non_striker"
            return bot.edit_message_text("✍️ Naye **Non-Striker Batsman** ka naam type karke bhejain:", chat_id=call.message.chat.id, message_id=call.message.message_id)
        if dt == "set_bowler":
            match["awaiting"] = "bowler"
            return bot.edit_message_text("✍️ Naye **Bowler** ka naam type karke bhejain:", chat_id=call.message.chat.id, message_id=call.message.message_id)
        
        if dt == "view_profile":
            match["awaiting_profile"] = True
            return bot.edit_message_text("✍️ Jis player ka **Career Profile** dekhna hai, uska naam type karke bhejain:", chat_id=call.message.chat.id, message_id=call.message.message_id)

        # WHATSAPP SUMMARY GENERATOR
        if dt == "get_summary":
            summary_text = (
                f"📊 *CRICKET MATCH SUMMARY REPORT* 🏏\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏟️ *Batting Team:* {match['batting_team']}\n"
                f"🎯 *Bowling Team:* {match['bowling_team']}\n"
                f"📋 *Final Score:* *{match['runs']} / {match['wickets']}* in *{match['overs']}* Overs\n"
                f"⚡ *Extras:* {match['extras']} | *Run Rate:* {(match['runs'] / (match['balls'] / 6) if match['balls'] > 0 else 0.0):.2f}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📜 *BALL-TO-BALL OVERALL LOG:* \n"
            )
            if match["ball_by_ball_log"]:
                summary_text += "\n".join(match["ball_by_ball_log"][-20:])
            else:
                summary_text += "_No ball logs recorded yet._"
            
            summary_text += f"\n━━━━━━━━━━━━━━━━━━━━━━\n✨ _Generated via Telegram Pro Cricket Bot_"
            bot.send_message(call.message.chat.id, summary_text, parse_mode="Markdown")
            return bot.answer_callback_query(call.id, "WhatsApp Summary Generated!")

        # TOURNAMENT LEADERBOARD / STATS
        if dt == "match_leaderboard":
            lb_text = "🏆 **MATCH LEADERBOARD & STATS** 📊\n──────────────────────────\n"
            sorted_players = sorted(match["career_db"].items(), key=lambda x: x[1]["runs"], reverse=True)
            for idx, (pname, pdata) in enumerate(sorted_players[:5], 1):
                sr = (pdata["runs"] / pdata["balls"] * 100) if pdata["balls"] > 0 else 0.0
                lb_text += f"{idx}. **{pname}** — `{pdata['runs']} runs` ({pdata['balls']}b) | SR: `{sr:.1f}`\n"
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
                if pts > max_pts:
                    max_pts = pts
                    best_player = p
            mom_text = f"🏆 **MAN OF THE MATCH** 🌟\n\n⭐ **{best_player}** wins Man of the Match based on overall career impact & performance!"
            bot.send_message(call.message.chat.id, mom_text, parse_mode="Markdown")
            return bot.answer_callback_query(call.id, "Man of the Match Calculated!")

        if dt == "sc_switch":
            match["batting_team"], match["bowling_team"] = match["bowling_team"], match["batting_team"]
            match["target"] = match["runs"] + 1
            match["runs"], match["wickets"], match["overs"], match["balls"], match["extras"] = 0, 0, 0.0, 0, 0
            match["partnership_runs"], match["partnership_balls"] = 0, 0
            match["is_second_innings"] = True
            match["match_status"] = "LIVE"
            match["history"].clear()
            match["ball_by_ball_log"].clear()
            bot.answer_callback_query(call.id, "Innings Switched!")
            return bot.edit_message_text("🔄 Innings Switched! 2nd Innings Started.\n\n" + get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        if dt == "sc_undo":
            if not match["history"]:
                return bot.answer_callback_query(call.id, "Nothing to undo!", show_alert=True)
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
            match["match_status"] = last["match_status"]
            if len(match["ball_by_ball_log"]) > last["log_len"]:
                match["ball_by_ball_log"] = match["ball_by_ball_log"][:last["log_len"]]
            bot.answer_callback_query(call.id, "Undo Successful!")
            return bot.edit_message_text(get_scoreboard_text(), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_scorer_markup(), parse_mode="Markdown")

        save_state_for_undo()
        ensure_player(match["striker"])

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
            
            add_ball(legal=True)
            action_desc = f"Over {match['overs']}: {match['striker']} scored {r_val} run(s)"
            if r_val in [1, 3]:
                match["striker"], match["non_striker"] = match["non_striker"], match["striker"]

        elif dt == "sc_wide":
            match["runs"] += 1
            match["extras"] += 1
            action_desc = f"Over {match['overs']}: Wide ball (+1 extra)"

        elif dt == "sc_nb":
            match["runs"] += 1
            match["extras"] += 1
            action_desc = f"Over {match['overs']}: No Ball (+1 extra)"

        elif dt == "sc_nb_4":
            match["runs"] += 5
            match["extras"] += 1
            match["partnership_runs"] += 4
            p_st = match["career_db"][match["striker"]]
            p_st["runs"] += 4
            p_st["fours"] += 1
            action_desc = f"Over {match['overs']}: No Ball + 4 runs by {match['striker']}"

        elif dt == "sc_nb_6":
            match["runs"] += 7
            match["extras"] += 1
            match["partnership_runs"] += 6
            p_st = match["career_db"][match["striker"]]
            p_st["runs"] += 6
            p_st["sixes"] += 1
            action_desc = f"Over {match['overs']}: No Ball + 6 runs by {match['striker']}"

        elif dt == "sc_wkt":
            if match["wickets"] < 10:
                match["wickets"] += 1
                match["career_db"][match["striker"]]["balls"] += 1
                if match["bowler"] in match["career_db"]:
                    match["career_db"][match["bowler"]]["wickets"] += 1
                action_desc = f"Over {match['overs']}: WICKET! {match['striker']} out b {match['bowler']}"
                match["partnership_runs"], match["partnership_balls"] = 0, 0
                add_ball(legal=True)
                match["striker"] = f"Batsman WKT-{match['wickets']+1}"
                ensure_player(match["striker"])

        if action_desc:
            match["ball_by_ball_log"].append(action_desc)

        bot.answer_callback_query(call.id, f"Recorded: {dt.replace('sc_', '').upper()}")
        bot.edit_message_text(
            get_scoreboard_text(), 
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            reply_markup=get_scorer_markup(), 
            parse_mode="Markdown"
        )

    except Exception as e:
        try:
            bot.answer_callback_query(call.id, "⚠️ Action expired, please refresh!", show_alert=True)
        except:
            pass

@bot.message_handler(func=lambda m: match["awaiting"] is not None or match["awaiting_profile"])
def handle_text_inputs(msg):
    if msg.from_user.id != ADMIN_ID: return
    
    if match["awaiting_profile"]:
        match["awaiting_profile"] = False
        p_name = msg.text.strip().title()
        if p_name in match["career_db"]:
            st = match["career_db"][p_name]
            sr = (st["runs"] / st["balls"] * 100) if st["balls"] > 0 else 0.0
            profile_msg = (
                f"👤 **PLAYER CAREER PROFILE** 📊\n"
                f"──────────────────────────\n"
                f" 🏷️ **Name:** `{p_name}`\n"
                f" 🏏 **Matches:** `{st['matches']}` | **Runs:** `{st['runs']}`\n"
                f" 🌀 **Balls Faced:** `{st['balls']}` | **Strike Rate:** `{sr:.2f}`\n"
                f" 🔥 **Fours:** `{st['fours']}` | **Sixes:** `{st['sixes']}`\n"
                f" ⚾ **Wickets Taken:** `{st['wickets']}`\n"
                f"──────────────────────────"
            )
            bot.reply_to(msg, profile_msg, parse_mode="Markdown")
        else:
            bot.reply_to(msg, f"❌ Player `{p_name}` ka career record database mein nahi mila!", parse_mode="Markdown")
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
    flash_msg = (
        f"🚨 **NEW PLAYER ON CREASE!** ⚡\n"
        f"──────────────────────────\n"
        f" 👤 **{val}**\n"
        f" 📊 Career Matches: `{st['matches']}`\n"
        f" 🏏 Total Runs: `{st['runs']}` (SR: `{sr:.2f}`)\n"
        f" 🔥 Boundaries: `{st['fours']}x4` | `{st['sixes']}x6`\n"
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
    print("Ultimate Pro Cricket Scorer with WhatsApp Summary & Leaderboard is running 24/7...")
    bot.infinity_polling(skip_pending=True, timeout=20)
