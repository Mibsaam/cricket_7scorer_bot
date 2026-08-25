import os
import json
import telebot
from telebot import types
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
from datetime import datetime

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8812331993:AAGiKVEV-xlPFs_-qS-7oeiA15t6y4SFPBk")  # Render pe env var se aayega
bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "career_data.json"

# ================== DATA STORAGE ==================
matches = {}          # chat_id → match data
user_states = {}      # chat_id → current state

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
        "players": {},            # player_name → stats
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
    kb.add("➕ Add Scorer", "➕ Add Player", "❌ Abandon Match")
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
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    kb.add("0", "1", "2", "3")
    kb.add("4", "6", "1D (Bat)", "2D (Bat)")
    kb.add("1D (Extra)", "Wide", "No Ball", "Bye")
    kb.add("Wicket", "Undo", "New Bowler")
    if free_hit:
        kb.add("⚠️ FREE HIT ACTIVE")
    kb.add("📋 Card", "🏠 Main Menu")
    return kb

def wide_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add("Wide +0", "Wide +1", "Wide +2")
    kb.add("Wide +4", "🔙 Back")
    return kb

def noball_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add("NB +0", "NB +1", "NB +2")
    kb.add("NB +3", "NB +4", "NB +6")
    kb.add("🔙 Back")
    return kb

def wicket_type_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("Striker Out", "Non-Striker Out")
    kb.add("🔙 Back")
    return kb

def yes_no_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("✅ Yes", "❌ No")
    return kb

# ================== START ==================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, 
        "🏏 *Gully Cricket Scorer Bot*\n\n"
        "Sab kuch buttons se chalega!\n"
        "Match shuru karne ke liye *New Match* dabao.",
        parse_mode="Markdown",
        reply_markup=main_menu())

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
    
    # Set opening batsmen
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
    
    text = f"*{team}*  {match['score'][0]}/{match['score'][1]}  ({overs})\n"
    text += f"CRR: {crr}"
    
    if match["innings"] == 2 and match["target"]:
        rrr = calculate_rrr(match["target"], match["score"][0], match["balls"], match["overs"]*6)
        text += f" | Target: {match['target']} | RRR: {rrr}"
    
    text += f"\n\n*Striker:* {match['striker']}"
    text += f"\n*Non-Striker:* {match['non_striker']}"
    text += f"\n*Bowler:* {match['bowler']}"
    
    if match["free_hit"]:
        text += "\n\n⚠️ *FREE HIT*"
    
    if comment:
        text += f"\n\n💬 {comment}"
    
    bot.send_message(chat_id, text, parse_mode="Markdown")

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
    legal_ball = not is_extra or extra_type in ["bye"]  # bye is legal ball usually, but adjust as needed
    
    if extra_type == "wide":
        total_runs = 1 + bat_runs   # wide + runs
        legal_ball = False
        update_bowler_stats(match, match["bowler"], runs=total_runs, balls=0)
    elif extra_type == "noball":
        total_runs = 1 + bat_runs
        legal_ball = False
        match["free_hit"] = True
        update_bowler_stats(match, match["bowler"], runs=total_runs, balls=0)
        if bat_runs > 0:
            update_player_stats(match, match["striker"], runs=bat_runs, balls=0, 
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
        # Normal delivery or 1D/2D bat
        legal_ball = True
        update_player_stats(match, match["striker"], runs=runs, balls=1,
                           fours=1 if runs==4 else 0, sixes=1 if runs==6 else 0)
        update_bowler_stats(match, match["bowler"], runs=runs, balls=1)
    
    match["score"][0] += total_runs
    
    if legal_ball:
        match["balls"] += 1
        match["current_over_balls"].append(str(runs) if not is_wicket else "W")
    
    # Strike rotation
    if runs % 2 == 1 and not is_wicket and extra_type not in ["wide", "noball"]:
        match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
    
    # Wicket
    if is_wicket and not match["free_hit"]:
        match["score"][1] += 1
        update_player_stats(match, wicket_player, is_out=True)
        update_bowler_stats(match, match["bowler"], wickets=1)
        
        # New batsman
        batting_squad = match["squad1"] if match["batting_team"] == 1 else match["squad2"]
        available = [p for p in batting_squad if p not in match["players"] or not match["players"][p]["out"]]
        if len(available) > 0:
            new_batsman = available[0]
            if wicket_player == match["striker"]:
                match["striker"] = new_batsman
            else:
                match["non_striker"] = new_batsman
        else:
            # All out
            end_innings(chat_id)
            return
    
    # Free hit used
    if match["free_hit"] and legal_ball:
        match["free_hit"] = False
    
    # Over complete?
    if match["balls"] % 6 == 0 and legal_ball:
        match["over_number"] += 1
        match["striker"], match["non_striker"] = match["non_striker"], match["striker"]  # change ends
        match["current_over_balls"] = []
        bot.send_message(chat_id, f"Over complete! New bowler select karo.", reply_markup=scoring_kb(match["free_hit"]))
    
    # Check innings end
    total_balls = match["overs"] * 6
    if match["balls"] >= total_balls or match["score"][1] >= (len(match["squad1"] if match["batting_team"]==1 else match["squad2"]) - 1):
        end_innings(chat_id)
        return
    
    if match["innings"] == 2 and match["target"] and match["score"][0] >= match["target"]:
        end_match(chat_id, "Target chase ho gaya! 🏆")
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
        
        # Swap teams
        match["batting_team"], match["bowling_team"] = match["bowling_team"], match["batting_team"]
        
        if match["batting_team"] == 1:
            match["striker"] = match["squad1"][0]
            match["non_striker"] = match["squad1"][1]
            match["bowler"] = match["squad2"][0]
        else:
            match["striker"] = match["squad2"][0]
            match["non_striker"] = match["squad2"][1]
            match["bowler"] = match["squad1"][0]
        
        bot.send_message(chat_id, f"1st Innings over!\nTarget: *{match['target']}*\n\n2nd Innings shuru!", 
                         parse_mode="Markdown", reply_markup=scoring_kb())
        send_score_update(chat_id)
    else:
        end_match(chat_id)

def end_match(chat_id, custom_msg=None):
    match = get_match(chat_id)
    match["match_over"] = True
    save_to_career(match)
    
    t1 = match["team1"]
    t2 = match["team2"]
    # Simple winner logic
    if match["innings"] == 1:
        msg = "Match abandoned after 1st innings."
    else:
        if match["score"][0] >= match["target"]:
            winner = t1 if match["batting_team"] == 1 else t2
            msg = f"*{winner}* jeet gaya! 🏆"
        else:
            winner = t2 if match["batting_team"] == 1 else t1
            msg = f"*{winner}* jeet gaya! 🏆"
    
    if custom_msg:
        msg = custom_msg
    
    bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=main_menu())
    user_states[chat_id] = None

# ================== BUTTON HANDLERS ==================
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "scoring")
def handle_scoring(message):
    chat_id = message.chat.id
    text = message.text
    match = get_match(chat_id)
    
    if not match:
        bot.send_message(chat_id, "Pehle New Match start karo.", reply_markup=main_menu())
        return
    
    if text == "🏠 Main Menu":
        bot.send_message(chat_id, "Main Menu", reply_markup=main_menu())
        return
    
    if text == "📋 Card":
        show_scorecard(chat_id)
        return
    
    if text == "Undo":
        if match["history"]:
            last = match["history"].pop()
            match["score"] = last["score"]
            match["balls"] = last["balls"]
            match["striker"] = last["striker"]
            match["non_striker"] = last["non_striker"]
            match["bowler"] = last["bowler"]
            match["free_hit"] = last["free_hit"]
            match["players"] = last["players"]
            match["bowlers"] = last["bowlers"]
            match["over_number"] = last["over_number"]
            bot.send_message(chat_id, "Undo successful ✅")
            send_score_update(chat_id)
        else:
            bot.send_message(chat_id, "Kuch undo karne ke liye nahi hai.")
        return
    
    if text == "New Bowler":
        user_states[chat_id] = "new_bowler"
        bowling_squad = match["squad2"] if match["batting_team"] == 1 else match["squad1"]
        bot.send_message(chat_id, "Naya bowler ka naam likho:\n" + ", ".join(bowling_squad))
        return
    
    if text == "Wicket":
        bot.send_message(chat_id, "Kaun out hua?", reply_markup=wicket_type_kb())
        user_states[chat_id] = "wicket_select"
        return
    
    if text == "Wide":
        bot.send_message(chat_id, "Wide + kitne runs?", reply_markup=wide_kb())
        user_states[chat_id] = "wide_select"
        return
    
    if text == "No Ball":
        bot.send_message(chat_id, "No Ball + kitne bat runs?", reply_markup=noball_kb())
        user_states[chat_id] = "noball_select"
        return
    
    if text == "Bye":
        process_ball(chat_id, 1, is_extra=True, extra_type="bye")
        send_score_update(chat_id, "Bye +1")
        bot.send_message(chat_id, "Continue:", reply_markup=scoring_kb(match["free_hit"]))
        return
    
    if text == "1D (Extra)":
        process_ball(chat_id, 1, is_extra=True, extra_type="1d_extra")
        send_score_update(chat_id, "1D (Extra)")
        bot.send_message(chat_id, "Continue:", reply_markup=scoring_kb(match["free_hit"]))
        return
    
    if text in ["0", "1", "2", "3", "4", "6", "1D (Bat)", "2D (Bat)"]:
        runs_map = {"0":0, "1":1, "2":2, "3":3, "4":4, "6":6, "1D (Bat)":1, "2D (Bat)":2}
        runs = runs_map[text]
        comment = text if text not in ["1D (Bat)", "2D (Bat)"] else text
        if runs == 4:
            comment = "FOUR! 🔥"
        elif runs == 6:
            comment = "SIX! 🚀"
        elif runs == 0:
            comment = "Dot ball"
        
        process_ball(chat_id, runs)
        send_score_update(chat_id, comment)
        bot.send_message(chat_id, "Continue:", reply_markup=scoring_kb(match["free_hit"]))
        return

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "wide_select")
def handle_wide(message):
    chat_id = message.chat.id
    text = message.text
    if text == "🔙 Back":
        user_states[chat_id] = "scoring"
        bot.send_message(chat_id, "Back", reply_markup=scoring_kb())
        return
    
    runs_map = {"Wide +0":0, "Wide +1":1, "Wide +2":2, "Wide +4":4}
    if text in runs_map:
        bat_runs = runs_map[text]
        process_ball(chat_id, 0, is_extra=True, extra_type="wide", bat_runs=bat_runs)
        send_score_update(chat_id, f"Wide +{bat_runs}")
        user_states[chat_id] = "scoring"
        bot.send_message(chat_id, "Continue:", reply_markup=scoring_kb(get_match(chat_id)["free_hit"]))

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "noball_select")
def handle_noball(message):
    chat_id = message.chat.id
    text = message.text
    if text == "🔙 Back":
        user_states[chat_id] = "scoring"
        bot.send_message(chat_id, "Back", reply_markup=scoring_kb())
        return
    
    runs_map = {"NB +0":0, "NB +1":1, "NB +2":2, "NB +3":3, "NB +4":4, "NB +6":6}
    if text in runs_map:
        bat_runs = runs_map[text]
        process_ball(chat_id, 0, is_extra=True, extra_type="noball", bat_runs=bat_runs)
        send_score_update(chat_id, f"No Ball +{bat_runs} (Free Hit)")
        user_states[chat_id] = "scoring"
        bot.send_message(chat_id, "Continue:", reply_markup=scoring_kb(True))

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "wicket_select")
def handle_wicket(message):
    chat_id = message.chat.id
    match = get_match(chat_id)
    text = message.text
    
    if text == "🔙 Back":
        user_states[chat_id] = "scoring"
        bot.send_message(chat_id, "Back", reply_markup=scoring_kb(match["free_hit"]))
        return
    
    if text == "Striker Out":
        process_ball(chat_id, 0, is_wicket=True, wicket_player=match["striker"])
        send_score_update(chat_id, f"WICKET! {match['striker']} out")
    elif text == "Non-Striker Out":
        process_ball(chat_id, 0, is_wicket=True, wicket_player=match["non_striker"])
        send_score_update(chat_id, f"WICKET! {match['non_striker']} out")
    
    user_states[chat_id] = "scoring"
    bot.send_message(chat_id, "Continue:", reply_markup=scoring_kb(match["free_hit"]))

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "new_bowler")
def set_new_bowler(message):
    chat_id = message.chat.id
    match = get_match(chat_id)
    match["bowler"] = message.text.strip()
    user_states[chat_id] = "scoring"
    bot.send_message(chat_id, f"New bowler: {match['bowler']}", reply_markup=scoring_kb(match["free_hit"]))
    send_score_update(chat_id)

# ================== SCORECARD ==================
def show_scorecard(chat_id):
    match = get_match(chat_id)
    if not match:
        bot.send_message(chat_id, "Koi active match nahi hai.")
        return
    
    text = "📋 *SCORECARD*\n\n"
    
    # Batting
    text += "*Batting:*\n"
    for p, s in match["players"].items():
        status = "out" if s["out"] else "not out"
        sr = round((s["runs"]/s["balls"]*100), 1) if s["balls"] > 0 else 0
        text += f"{p}: {s['runs']} ({s['balls']}) 4s:{s['fours']} 6s:{s['sixes']} SR:{sr} [{status}]\n"
    
    text += "\n*Bowling:*\n"
    for b, s in match["bowlers"].items():
        overs = balls_to_overs(s["balls"])
        eco = round((s["runs"]/s["balls"]*6), 2) if s["balls"] > 0 else 0
        text += f"{b}: {overs} - {s['runs']} - {s['wickets']}  Eco:{eco}\n"
    
    bot.send_message(chat_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📋 Scorecard")
def scorecard_btn(message):
    show_scorecard(message.chat.id)

# ================== CAREER ==================
@bot.message_handler(func=lambda m: m.text == "📊 Career / Leaderboard")
def show_career(message):
    if not career:
        bot.send_message(message.chat.id, "Abhi koi career data nahi hai.")
        return
    
    text = "📊 *Career Leaderboard (Top Runs)*\n\n"
    sorted_players = sorted(career.items(), key=lambda x: x[1]["runs"], reverse=True)[:15]
    for i, (p, s) in enumerate(sorted_players, 1):
        avg = round(s["runs"]/s["outs"], 1) if s["outs"] > 0 else s["runs"]
        text += f"{i}. {p}: {s['runs']} runs ({s['matches']} mat) Avg:{avg}\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ================== ADD SCORER / PLAYER ==================
@bot.message_handler(func=lambda m: m.text == "➕ Add Scorer")
def add_scorer(message):
    chat_id = message.chat.id
    user_states[chat_id] = "add_scorer"
    bot.send_message(chat_id, "Scorer ka Telegram username ya naam likho:")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "add_scorer")
def save_scorer(message):
    chat_id = message.chat.id
    match = get_match(chat_id)
    if match:
        match["scorers"].append(message.text.strip())
    user_states[chat_id] = "scoring" if match else None
    bot.send_message(chat_id, "Scorer add ho gaya ✅", reply_markup=scoring_kb() if match else main_menu())

@bot.message_handler(func=lambda m: m.text == "➕ Add Player")
def add_player(message):
    chat_id = message.chat.id
    user_states[chat_id] = "add_player_team"
    bot.send_message(chat_id, "Kis team mein add karna hai? Team name likho:")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "add_player_team")
def add_player_team(message):
    chat_id = message.chat.id
    user_states[chat_id] = "add_player_name"
    matches[chat_id]["_temp_team"] = message.text.strip()
    bot.send_message(chat_id, "Player ka naam likho:")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "add_player_name")
def add_player_name(message):
    chat_id = message.chat.id
    match = get_match(chat_id)
    team = match.get("_temp_team", "")
    name = message.text.strip()
    
    if match:
        if team.lower() == match["team1"].lower():
            match["squad1"].append(name)
        elif team.lower() == match["team2"].lower():
            match["squad2"].append(name)
        else:
            bot.send_message(chat_id, "Team name match nahi hua.")
            user_states[chat_id] = "scoring"
            return
    
    user_states[chat_id] = "scoring"
    bot.send_message(chat_id, f"{name} add ho gaya ✅", reply_markup=scoring_kb())

# ================== ABANDON ==================
@bot.message_handler(func=lambda m: m.text == "❌ Abandon Match")
def abandon(message):
    chat_id = message.chat.id
    if chat_id in matches:
        del matches[chat_id]
    user_states[chat_id] = None
    bot.send_message(chat_id, "Match abandon kar diya gaya.", reply_markup=main_menu())

# ================== KEEP ALIVE SERVER (for Render) ==================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Gully Cricket Bot is running!")
    
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# ================== START BOT ==================
if __name__ == "__main__":
    # Start health check server in background
    threading.Thread(target=run_server, daemon=True).start()
    
    print("Bot starting...")
    bot.infinity_polling()
