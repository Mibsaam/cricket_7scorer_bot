import os
import json
import telebot
from telebot import types
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8812331993:AAGiKVEV-xlPFs_-qS-7oeiA15t6y4SFPBk")
bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "career_data.json"

# ================== RENDER 24/7 KEEP-ALIVE SERVER ==================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ================== DATA STORAGE ==================
matches = {}          # chat_id -> match data
user_states = {}      # chat_id -> current state

def load_career():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_career(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

career = load_career()

# ================== HELPER FUNCTIONS ==================
def get_match(chat_id):
    return matches.get(chat_id)

def create_empty_match():
    return {
        "team1": "",
        "team2": "",
        "overs": 0,
        "toss_winner": None,
        "batting_first": None,
        "squad1": [],
        "squad2": [],
        "innings": 1,
        "score": [0, 0],          # [runs, wickets]
        "balls": 0,
        "target": None,
        "striker": None,
        "non_striker": None,
        "bowler": None,
        "batting_team": 1,
        "bowling_team": 2,
        "players": {},            # player_name -> stats
        "bowlers": {},
        "history": [],            # for undo
        "free_hit": False,
        "current_over_balls": [],
        "over_number": 0,
        "match_over": False,
        "scorers": []
    }

def balls_to_overs(balls):
    return f"{balls // 6}.{balls % 6}"

def calculate_crr(runs, balls):
    if balls == 0:
        return 0.0
    return round((runs / balls) * 6, 2)

def calculate_rrr(target, runs, balls, total_balls):
    remaining_runs = target - runs
    remaining_balls = total_balls - balls
    if remaining_balls <= 0:
        return 0.0
    return round((remaining_runs / remaining_balls) * 6, 2)

def update_player_stats(match, player, runs=0, balls=0, fours=0, sixes=0, is_out=False):
    if not player or player == "NONE":
        return
    if player not in match["players"]:
        match["players"][player] = {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": False}
    p = match["players"][player]
    p["runs"] += runs
    p["balls"] += balls
    p["fours"] += fours
    p["sixes"] += sixes
    if is_out:
        p["out"] = True

def update_bowler_stats(match, bowler, runs=0, wickets=0, balls=0):
    if not bowler or bowler == "NONE":
        return
    if bowler not in match["bowlers"]:
        match["bowlers"][bowler] = {"runs": 0, "wickets": 0, "balls": 0}
    b = match["bowlers"][bowler]
    b["runs"] += runs
    b["wickets"] += wickets
    b["balls"] += balls

def save_to_career(match):
    global career
    for player, stats in match["players"].items():
        if player not in career:
            career[player] = {"matches": 0, "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "outs": 0, "wickets": 0, "bowl_runs": 0, "bowl_balls": 0}
        c = career[player]
        c["matches"] += 1
        c["runs"] += stats["runs"]
        c["balls"] += stats["balls"]
        c["fours"] += stats["fours"]
        c["sixes"] += stats["sixes"]
        if stats["out"]:
            c["outs"] += 1
    for bowler, stats in match["bowlers"].items():
        if bowler not in career:
            career[bowler] = {"matches": 0, "runs": 0, "balls": 0, "fours": 0, "sixes": 0, "outs": 0, "wickets": 0, "bowl_runs": 0, "bowl_balls": 0}
        c = career[bowler]
        c["wickets"] += stats["wickets"]
        c["bowl_runs"] += stats["runs"]
        c["bowl_balls"] += stats["balls"]
    save_career(career)

# ================== KEYBOARDS ==================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🏏 New Match", "📋 Scorecard", "📊 Career / Leaderboard")
    kb.add("❌ Abandon Match")
    return kb

def toss_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🪙 Heads", "🪙 Tails")
    return kb

def bat_bowl_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🏏 Bat", "🎳 Bowl")
    return kb

def scoring_kb(free_hit=False):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add("0", "1", "2")
    kb.add("3", "4 🔥", "6 💥")
    kb.add("⚡ 1D (Bat)", "⚡ 2D (Bat)", "⚡ 1D (Extra)")
    kb.add("Wide Menu", "NoBall Menu", "Bye (+1)")
    kb.add("☝️ WICKET", "🔄 Swap Strike", "↩️ Undo")
    kb.add("🎯 Bowler", "📋 Card", "🏠 Main Menu")
    if free_hit:
        kb.add("⚠️ FREE HIT ACTIVE")
    return kb

def wide_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add("Wd +0", "Wd +1", "Wd +2")
    kb.add("Wd +4", "🔙 Back")
    return kb

def noball_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add("NB +0", "NB +1", "NB +2")
    kb.add("NB +3", "NB +4 🔥", "NB +6 💥")
    kb.add("🔙 Back")
    return kb

def wicket_type_kb():
    match = get_match(bot.current_chat_id) if hasattr(bot, 'current_chat_id') else None
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if match:
        kb.add(f"Striker ({match['striker']})", f"Non-Striker ({match['non_striker']})")
    else:
        kb.add("Striker Out", "Non-Striker Out")
    kb.add("🔙 Back")
    return kb

# ================== START ==================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, 
        "🏏 *Gully Cricket Scorer Bot (Pro Edition)*\n\n"
        "Sab kuch buttons se chalega!\n"
        "Match shuru karne ke liye *New Match* dabao.",
        parse_mode="Markdown",
        reply_markup=main_menu())

# ================== LEADERBOARD & SCORECARD ==================
@bot.message_handler(func=lambda m: m.text == "📊 Career / Leaderboard")
def show_leaderboard(message):
    chat_id = message.chat.id
    if not career:
        bot.send_message(chat_id, "Abhi koi career record saved nahi hai.")
        return
    sorted_players = sorted(career.items(), key=lambda x: x[1]['runs'], reverse=True)[:10]
    text = "🏆 *LEADERBOARD (Top Runs)*:\n\n"
    for idx, (p, stats) in enumerate(sorted_players, 1):
        sr = round((stats['runs'] / stats['balls']) * 100, 1) if stats['balls'] > 0 else 0.0
        text += f"{idx}. *{p}* — {stats['runs']} runs ({stats['balls']}b) | SR: {sr} | 4s:{stats['fours']} 6s:{stats['sixes']}\n"
    bot.send_message(chat_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📋 Scorecard")
def scorecard_command(message):
    show_scorecard(message.chat.id)

def show_scorecard(chat_id):
    match = get_match(chat_id)
    if not match or not match.get("team1"):
        bot.send_message(chat_id, "Koi active match nahi hai!")
        return
    
    bat_team = match["team1"] if match["batting_team"] == 1 else match["team2"]
    text = f"📋 *SCORECARD: {bat_team}*\n"
    text += f"Score: {match['score'][0]}/{match['score'][1]} ({balls_to_overs(match['balls'])} ov)\n"
    text += "====================\n*BATSMEN*:\n"
    
    for p, stats in match["players"].items():
        sr = round((stats['runs'] / stats['balls']) * 100, 1) if stats['balls'] > 0 else 0.0
        status = "out" if stats['out'] else "not out"
        text += f"• {p} ({status}): {stats['runs']} ({stats['balls']}b) [4s:{stats['fours']} 6s:{stats['sixes']}] SR:{sr}\n"
    
    text += "\n*BOWLERS*:\n"
    for b, stats in match["bowlers"].items():
        econ = round(stats['runs'] / (stats['balls'] / 6), 2) if stats['balls'] > 0 else 0.0
        text += f"• {b}: {balls_to_overs(stats['balls'])} ov | {stats['runs']}r | {stats['wickets']}w | Econ:{econ}\n"
    
    bot.send_message(chat_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "❌ Abandon Match")
def abandon_match(message):
    chat_id = message.chat.id
    if chat_id in matches:
        matches[chat_id]["match_over"] = True
        del matches[chat_id]
    user_states[chat_id] = None
    bot.send_message(chat_id, "🛑 Match abandon kar diya gaya.", reply_markup=main_menu())

# ================== NEW MATCH FLOW ==================
@bot.message_handler(func=lambda m: m.text == "🏏 New Match")
def new_match(message):
    chat_id = message.chat.id
    matches[chat_id] = create_empty_match()
    user_states[chat_id] = "team1"
    bot.send_message(chat_id, "Team 1 ka naam likho:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "team1")
def set_team1(message):
    chat_id = message.chat.id
    matches[chat_id]["team1"] = message.text.strip()
    user_states[chat_id] = "team2"
    bot.send_message(chat_id, "Team 2 ka naam likho:")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "team2")
def set_team2(message):
    chat_id = message.chat.id
    matches[chat_id]["team2"] = message.text.strip()
    user_states[chat_id] = "overs"
    bot.send_message(chat_id, "Kitne overs ka match hai? (number likho):")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "overs")
def set_overs(message):
    chat_id = message.chat.id
    try:
        overs = int(message.text.strip())
        if overs < 1 or overs > 50:
            bot.send_message(chat_id, "1 se 50 ke beech number daalo.")
            return
        matches[chat_id]["overs"] = overs
        user_states[chat_id] = "toss"
        bot.send_message(chat_id, f"Toss karo! {matches[chat_id]['team1']} vs {matches[chat_id]['team2']}", reply_markup=toss_kb())
    except:
        bot.send_message(chat_id, "Sahi number daalo.")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "toss" and m.text in ["🪙 Heads", "🪙 Tails"])
def do_toss(message):
    chat_id = message.chat.id
    import random
    result = random.choice(["🪙 Heads", "🪙 Tails"])
    winner = matches[chat_id]["team1"] if message.text == result else matches[chat_id]["team2"]
    matches[chat_id]["toss_winner"] = winner
    user_states[chat_id] = "bat_bowl"
    bot.send_message(chat_id, f"Toss result: *{result}*\n*{winner}* jeet gaya!\n\nBat ya Bowl choose karo:", 
                     parse_mode="Markdown", reply_markup=bat_bowl_kb())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "bat_bowl" and m.text in ["🏏 Bat", "🎳 Bowl"])
def set_bat_bowl(message):
    chat_id = message.chat.id
    match = matches[chat_id]
    if message.text == "🏏 Bat":
        match["batting_first"] = match["toss_winner"]
    else:
        match["batting_first"] = match["team2"] if match["toss_winner"] == match["team1"] else match["team1"]
    
    if match["batting_first"] == match["team1"]:
        match["batting_team"] = 1
        match["bowling_team"] = 2
    else:
        match["batting_team"] = 2
        match["bowling_team"] = 1
    
    user_states[chat_id] = "squad1"
    bot.send_message(chat_id, f"*{match['team1']}* ke players (comma separated likho):\nExample: Rohit, Virat, Dhoni, Hardik", 
                     parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "squad1")
def set_squad1(message):
    chat_id = message.chat.id
    players = [p.strip() for p in message.text.split(",") if p.strip()]
    if len(players) < 2:
        bot.send_message(chat_id, "Kam se kam 2 players daalo.")
        return
    matches[chat_id]["squad1"] = players
    user_states[chat_id] = "squad2"
    bot.send_message(chat_id, f"*{matches[chat_id]['team2']}* ke players (comma separated):", parse_mode="Markdown")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "squad2")
def set_squad2(message):
    chat_id = message.chat.id
    players = [p.strip() for p in message.text.split(",") if p.strip()]
    if len(players) < 2:
        bot.send_message(chat_id, "Kam se kam 2 players daalo.")
        return
    match = matches[chat_id]
    match["squad2"] = players
    
    # Set opening batsmen & bowler
    if match["batting_team"] == 1:
        match["striker"] = match["squad1"][0]
        match["non_striker"] = match["squad1"][1]
        match["bowler"] = match["squad2"][0]
    else:
        match["striker"] = match["squad2"][0]
        match["non_striker"] = match["squad2"][1]
        match["bowler"] = match["squad1"][0]
    
    user_states[chat_id] = "scoring"
    send_score_update(chat_id, "Match shuru! 🏏")
    bot.send_message(chat_id, "Scoring start karo:", reply_markup=scoring_kb())

# ================== SCORING ENGINE ==================
def send_score_update(chat_id, comment=""):
    match = get_match(chat_id)
    if not match:
        return
    
    team = match["team1"] if match["batting_team"] == 1 else match["team2"]
    overs = balls_to_overs(match["balls"])
    crr = calculate_crr(match["score"][0], match["balls"])
    
    # Get striker/non-striker stats
    s_stats = match["players"].get(match["striker"], {"runs": 0, "balls": 0, "fours": 0, "sixes": 0})
    ns_stats = match["players"].get(match["non_striker"], {"runs": 0, "balls": 0})
    b_stats = match["bowlers"].get(match["bowler"], {"runs": 0, "wickets": 0, "balls": 0})
    
    text = f"🏏 *{team}*  {match['score'][0]}/{match['score'][1]}  ({overs}/{match['overs']} ov) | CRR: {crr}\n"
    
    if match["innings"] == 2 and match["target"]:
        rrr = calculate_rrr(match["target"], match["score"][0], match["balls"], match["overs"]*6)
        text += f"🎯 Target: {match['target']} | RRR: {rrr}\n"
    
    text += "------------------------------------\n"
    text += f"🏏 *{match['striker']}*: {s_stats['runs']} ({s_stats['balls']}b) [4s:{s_stats['fours']} 6s:{s_stats['sixes']}]\n"
    text += f"🏏 {match['non_striker']}: {ns_stats['runs']} ({ns_stats['balls']}b)\n"
    text += f"🎯 *Bowler ({match['bowler']})*: {b_stats['wickets']}/{b_stats['runs']} ({balls_to_overs(b_stats['balls'])} ov)\n"
    
    if match["free_hit"]:
        text += "\n⚠️ *FREE HIT ACTIVE!*"
    
    if comment:
        text += f"\n\n💬 _{comment}_"
    
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=scoring_kb(match["free_hit"]))

def process_ball(chat_id, runs, is_extra=False, is_wicket=False, wicket_player=None, extra_type=None, bat_runs=0):
    match = get_match(chat_id)
    if not match or match["match_over"]:
        return
    
    # Save history for undo
    import copy
    match["history"].append(copy.deepcopy({
        "score": match["score"][:],
        "balls": match["balls"],
        "striker": match["striker"],
        "non_striker": match["non_striker"],
        "bowler": match["bowler"],
        "free_hit": match["free_hit"],
        "players": copy.deepcopy(match["players"]),
        "bowlers": copy.deepcopy(match["bowlers"]),
        "over_number": match["over_number"]
    }))
    if len(match["history"]) > 20:
        match["history"].pop(0)
    
    total_runs = runs
    legal_ball = True
    
    if extra_type == "wide":
        total_runs = 1 + bat_runs
        legal_ball = False
        update_bowler_stats(match, match["bowler"], runs=total_runs, balls=0)
    elif extra_type == "noball":
        total_runs = 1 + bat_runs
        legal_ball = False
        match["free_hit"] = True
        update_bowler_stats(match, match["bowler"], runs=total_runs, balls=0)
        if bat_runs > 0:
            update_player_stats(match, match["striker"], runs=bat_runs, balls=1, 
                               fours=1 if bat_runs==4 else 0, sixes=1 if bat_runs==6 else 0)
    elif extra_type == "bye":
        total_runs = runs
        legal_ball = True
        update_bowler_stats(match, match["bowler"], runs=0, balls=1)
    elif extra_type == "1d_extra":
        total_runs = 1
        legal_ball = False
        update_bowler_stats(match, match["bowler"], runs=1, balls=0)
    else:
        legal_ball = True
        update_player_stats(match, match["striker"], runs=runs, balls=1,
                           fours=1 if runs==4 else 0, sixes=1 if runs==6 else 0)
        update_bowler_stats(match, match["bowler"], runs=runs, balls=1)
    
    match["score"][0] += total_runs
    
    if legal_ball:
        match["balls"] += 1
    
    # Strike rotation on odd runs
    if runs % 2 == 1 and not is_wicket and extra_type not in ["wide", "noball"]:
        match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
    
    # Wicket handling
    if is_wicket and not match["free_hit"]:
        match["score"][1] += 1
        update_player_stats(match, wicket_player, is_out=True)
        update_bowler_stats(match, match["bowler"], wickets=1)
        
        batting_squad = match["squad1"] if match["batting_team"] == 1 else match["squad2"]
        available = [p for p in batting_squad if p not in match["players"] or not match["players"][p]["out"]]
        if len(available) > 0:
            new_batsman = available[0]
            if wicket_player == match["striker"]:
                match["striker"] = new_batsman
            else:
                match["non_striker"] = new_batsman
        else:
            end_innings(chat_id)
            return
    
    if match["free_hit"] and legal_ball:
        match["free_hit"] = False
    
    # Over complete check
    if match["balls"] > 0 and match["balls"] % 6 == 0 and legal_ball:
        match["over_number"] += 1
        match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
        bot.send_message(chat_id, f"🏁 Over Complete! Naya bowler select karo.")
    
    # Innings / Match check
    total_balls = match["overs"] * 6
    if match["balls"] >= total_balls or match["score"][1] >= (len(match["squad1"] if match["batting_team"]==1 else match["squad2"]) - 1):
        end_innings(chat_id)
        return
    
    if match["innings"] == 2 and match["target"] and match["score"][0] >= match["target"]:
        end_match(chat_id, "🏆 Target successfully chase ho gaya!")
        return

def end_innings(chat_id):
    match = get_match(chat_id)
    if match["innings"] == 1:
        match["target"] = match["score"][0] + 1
        match["innings"] = 2
        match["score"] = [0, 0]
        match["balls"] = 0
        match["over_number"] = 0
        match["free_hit"] = False
        
        match["batting_team"], match["bowling_team"] = match["bowling_team"], match["batting_team"]
        
        if match["batting_team"] == 1:
            match["striker"] = match["squad1"][0]
            match["non_striker"] = match["squad1"][1]
            match["bowler"] = match["squad2"][0]
        else:
            match["striker"] = match["squad2"][0]
            match["non_striker"] = match["squad2"][1]
            match["bowler"] = match["squad1"][0]
        
        bot.send_message(chat_id, f"🏁 1st Innings Over!\nTarget for 2nd Innings: *{match['target']}*\n\n2nd Innings Shuru!", parse_mode="Markdown")
        send_score_update(chat_id)
    else:
        end_match(chat_id)

def end_match(chat_id, custom_msg=None):
    match = get_match(chat_id)
    if not match:
        return
    match["match_over"] = True
    save_to_career(match)
    
    t1 = match["team1"]
    t2 = match["team2"]
    if match["innings"] == 1:
        msg = "Match abandoned."
    else:
        if match["score"][0] >= match["target"]:
            winner = t1 if match["batting_team"] == 1 else t2
            msg = f"🏆 *{winner}* jeet gaya match!"
        elif match["sco
