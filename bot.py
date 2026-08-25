import os
import json
import telebot
from telebot import types
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import copy
import random
from datetime import datetime

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8812331993:AAGiKVEV-xlPFs_-qS-7oeiA15t6y4SFPBk")
bot = telebot.TeleBot(BOT_TOKEN)

DATA_FILE = "career_data.json"

matches = {}
user_states = {}

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

# ================== HELPERS ==================
def get_match(chat_id):
    return matches.get(chat_id)

def create_empty_match():
    return {
        "team1": "", "team2": "", "overs": 0,
        "toss_winner": None, "batting_first": None,
        "squad1": [], "squad2": [],
        "innings": 1, "score": [0, 0], "balls": 0,
        "target": None,
        "striker": None, "non_striker": None, "bowler": None,
        "batting_team": 1, "bowling_team": 2,
        "players": {}, "bowlers": {},
        "history": [], "free_hit": False,
        "over_number": 0, "match_over": False,
        "scorers": []
    }

def balls_to_overs(balls):
    return f"{balls // 6}.{balls % 6}"

def crr(runs, balls):
    return round((runs / balls) * 6, 2) if balls > 0 else 0.0

def rrr(target, runs, balls, total_balls):
    rem_runs = target - runs
    rem_balls = total_balls - balls
    return round((rem_runs / rem_balls) * 6, 2) if rem_balls > 0 else 0.0

def update_batsman(match, player, runs=0, balls=0, fours=0, sixes=0, is_out=False):
    if player not in match["players"]:
        match["players"][player] = {"runs": 0, "balls": 0, "fours": 0, "sixes": 0, "out": False}
    p = match["players"][player]
    p["runs"] += runs
    p["balls"] += balls
    p["fours"] += fours
    p["sixes"] += sixes
    if is_out:
        p["out"] = True

def update_bowler(match, bowler, runs=0, wickets=0, balls=0):
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

def available_batsmen(match):
    squad = match["squad1"] if match["batting_team"] == 1 else match["squad2"]
    return [p for p in squad if p not in match["players"] or not match["players"][p]["out"]]

def bowling_squad(match):
    return match["squad2"] if match["batting_team"] == 1 else match["squad1"]

# ================== KEYBOARDS ==================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🏏 New Match", "📋 Scorecard")
    kb.add("📊 Career / Leaderboard", "➕ Add Player")
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
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    kb.add("0", "1", "2", "3")
    kb.add("4", "6", "1D (Bat)", "2D (Bat)")
    kb.add("1D (Extra)", "Wide", "No Ball", "Bye (+1)")
    kb.add("Wicket", "🔄 Swap Strike", "Undo")
    kb.add("New Bowler", "📋 Card", "🏠 Main Menu")
    if free_hit:
        kb.add("⚠️ FREE HIT ACTIVE")
    return kb

def wide_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add("Wd +0", "Wd +1", "Wd +2", "Wd +4")
    kb.add("🔙 Back")
    return kb

def noball_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.add("NB +0", "NB +1", "NB +2")
    kb.add("NB +3", "NB +4", "NB +6")
    kb.add("🔙 Back")
    return kb

def wicket_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("Striker Out", "Non-Striker Out")
    kb.add("🔙 Back")
    return kb

def player_kb(players, back=True):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for p in players:
        kb.add(p)
    if back:
        kb.add("🔙 Back")
    return kb

# ================== START ==================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    bot.send_message(message.chat.id,
        "🏏 *Gully Cricket Scorer Bot*\n\n"
        "Sab kuch buttons se chalega!\n"
        "*New Match* dabao match shuru karne ke liye.",
        parse_mode="Markdown", reply_markup=main_menu())

# ================== NEW MATCH ==================
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
    bot.send_message(chat_id, "Kitne overs ka match? (number):")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "overs")
def set_overs(message):
    chat_id = message.chat.id
    try:
        overs = int(message.text.strip())
        if not 1 <= overs <= 50:
            bot.send_message(chat_id, "1 se 50 ke beech daalo.")
            return
        matches[chat_id]["overs"] = overs
        user_states[chat_id] = "toss"
        bot.send_message(chat_id, "Toss karo!", reply_markup=toss_kb())
    except:
        bot.send_message(chat_id, "Sahi number daalo.")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "toss" and m.text in ["🪙 Heads", "🪙 Tails"])
def do_toss(message):
    chat_id = message.chat.id
    result = random.choice(["🪙 Heads", "🪙 Tails"])
    winner = matches[chat_id]["team1"] if message.text == result else matches[chat_id]["team2"]
    matches[chat_id]["toss_winner"] = winner
    user_states[chat_id] = "bat_bowl"
    bot.send_message(chat_id, f"Result: *{result}*\n*{winner}* jeet gaya!\nBat ya Bowl?",
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
    bot.send_message(chat_id, f"*{match['team1']}* players (comma separated):\nExample: Rohit, Virat, Dhoni",
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
    bot.send_message(chat_id, f"*{matches[chat_id]['team2']}* players (comma separated):", parse_mode="Markdown")

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "squad2")
def set_squad2(message):
    chat_id = message.chat.id
    players = [p.strip() for p in message.text.split(",") if p.strip()]
    if len(players) < 2:
        bot.send_message(chat_id, "Kam se kam 2 players daalo.")
        return
    matches[chat_id]["squad2"] = players
    user_states[chat_id] = "select_striker"
    batting = matches[chat_id]["squad1"] if matches[chat_id]["batting_team"] == 1 else matches[chat_id]["squad2"]
    bot.send_message(chat_id, "*Striker* select karo:", parse_mode="Markdown",
                     reply_markup=player_kb(batting, back=False))

# ================== SELECT STRIKER / NON-STRIKER / BOWLER ==================
@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "select_striker")
def select_striker(message):
    chat_id = message.chat.id
    match = matches[chat_id]
    match["striker"] = message.text.strip()
    user_states[chat_id] = "select_non_striker"
    batting = available_batsmen(match)
    batting = [p for p in batting if p != match["striker"]]
    bot.send_message(chat_id, "*Non-Striker* select karo:", parse_mode="Markdown",
                     reply_markup=player_kb(batting, back=False))

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "select_non_striker")
def select_non_striker(message):
    chat_id = message.chat.id
    match = matches[chat_id]
    match["non_striker"] = message.text.strip()
    user_states[chat_id] = "select_bowler"
    bot.send_message(chat_id, "*Bowler* select karo:", parse_mode="Markdown",
                     reply_markup=player_kb(bowling_squad(match), back=False))

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "select_bowler")
def select_bowler(message):
    chat_id = message.chat.id
    match = matches[chat_id]
    match["bowler"] = message.text.strip()
    user_states[chat_id] = "scoring"
    send_score_update(chat_id, "Match Shuru! 🏏")
    bot.send_message(chat_id, "Scoring shuru karo:", reply_markup=scoring_kb())

# ================== SCORE UPDATE ==================
def send_score_update(chat_id, comment=""):
    match = get_match(chat_id)
    if not match:
        return
    team = match["team1"] if match["batting_team"] == 1 else match["team2"]
    overs = balls_to_overs(match["balls"])
    text = f"*{team}*   {match['score'][0]}/{match['score'][1]}   ({overs})\n"
    text += f"CRR: {crr(match['score'][0], match['balls'])}"
    if match["innings"] == 2 and match["target"]:
        text += f" | Target: {match['target']} | RRR: {rrr(match['target'], match['score'][0], match['balls'], match['overs']*6)}"
    text += f"\n\n🏏 *Striker:* {match['striker']}"
    text += f"\n🏏 *Non-Striker:* {match['non_striker']}"
    text += f"\n🎳 *Bowler:* {match['bowler']}"
    if match["free_hit"]:
        text += "\n\n⚠️ *FREE HIT*"
    if comment:
        text += f"\n\n💬 {comment}"
    bot.send_message(chat_id, text, parse_mode="Markdown")

# ================== PROCESS BALL ==================
def process_ball(chat_id, runs, is_extra=False, is_wicket=False, wicket_player=None, extra_type=None, bat_runs=0):
    match = get_match(chat_id)
    if not match or match["match_over"]:
        return

    # History for Undo
    match["history"].append(copy.deepcopy({
        "score": match["score"][:], "balls": match["balls"],
        "striker": match["striker"], "non_striker": match["non_striker"],
        "bowler": match["bowler"], "free_hit": match["free_hit"],
        "players": copy.deepcopy(match["players"]),
        "bowlers": copy.deepcopy(match["bowlers"])
    }))
    if len(match["history"]) > 25:
        match["history"].pop(0)

    total_runs = runs
    legal = True

    if extra_type == "wide":
        total_runs = 1 + bat_runs
        legal = False
        update_bowler(match, match["bowler"], runs=total_runs)
    elif extra_type == "noball":
        total_runs = 1 + bat_runs
        legal = False
        match["free_hit"] = True
        update_bowler(match, match["bowler"], runs=total_runs)
        if bat_runs > 0:
            update_batsman(match, match["striker"], runs=bat_runs,
                           fours=1 if bat_runs == 4 else 0, sixes=1 if bat_runs == 6 else 0)
    elif extra_type == "bye":
        total_runs = 1
        update_bowler(match, match["bowler"], balls=1)
    elif extra_type == "1d_extra":
        total_runs = 1
        legal = False
        update_bowler(match, match["bowler"], runs=1)
    else:
        # Normal / 1D Bat / 2D Bat
        update_batsman(match, match["striker"], runs=runs, balls=1,
                       fours=1 if runs == 4 else 0, sixes=1 if runs == 6 else 0)
        update_bowler(match, match["bowler"], runs=runs, balls=1)

    match["score"][0] += total_runs

    if legal:
        match["balls"] += 1

    # Strike rotation (odd runs)
    if runs % 2 == 1 and not is_wicket and extra_type not in ["wide", "noball", "1d_extra"]:
        match["striker"], match["non_striker"] = match["non_striker"], match["striker"]

    if is_wicket and not match["free_hit"]:
        match["score"][1] += 1
        update_batsman(match, wicket_player, is_out=True)
        update_bowler(match, match["bowler"], wickets=1)

        avail = available_batsmen(match)
        if not avail:
            end_innings(chat_id)
            return
        else:
            user_states[chat_id] = "new_batsman"
            bot.send_message(chat_id, f"Wicket! Naya batsman select karo:",
                             reply_markup=player_kb(avail))
            return

    if match["free_hit"] and legal:
        match["free_hit"] = False

    # Over complete
    if match["balls"] % 6 == 0 and legal:
        match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
        bot.send_message(chat_id, "Over complete! Naya bowler select karo:",
                         reply_markup=player_kb(bowling_squad(match)))
        user_states[chat_id] = "new_bowler_force"
        return

    # Innings / Match end check
    total_balls = match["overs"] * 6
    if match["balls"] >= total_balls or match["score"][1] >= len(available_batsmen(match)) + match["score"][1]:
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
        match["free_hit"] = False
        match["batting_team"], match["bowling_team"] = match["bowling_team"], match["batting_team"]
        match["players"] = {}  # reset for 2nd innings display (career already saved later)
        user_states[chat_id] = "select_striker"
        batting = match["squad1"] if match["batting_team"] == 1 else match["squad2"]
        bot.send_message(chat_id, f"1st Innings over!\n*Target: {match['target']}*\n\n2nd Innings - Striker select karo:",
                         parse_mode="Markdown", reply_markup=player_kb(batting, back=False))
    else:
        end_match(chat_id)

def end_match(chat_id, msg=None):
    match = get_match(chat_id)
    match["match_over"] = True
    save_to_career(match)
    if not msg:
        if match["score"][0] >= match["target"]:
            winner = match["team1"] if match["batting_team"] == 1 else match["team2"]
            msg = f"*{winner}* jeet gaya! 🏆"
        else:
            winner = match["team2"] if match["batting_team"] == 1 else match["team1"]
            msg = f"*{winner}* jeet gaya! 🏆"
    bot.send_message(chat_id, msg, parse_mode="Markdown", reply_markup=main_menu())
    user_states[chat_id] = None

# ================== SCORING HANDLERS ==================
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
            match.update(last)
            bot.send_message(chat_id, "Undo successful ✅")
            send_score_update(chat_id)
        else:
            bot.send_message(chat_id, "Kuch undo karne layak nahi.")
        return
    if text == "🔄 Swap Strike":
        match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
        bot.send_message(chat_id, "Strike swap ho gaya ✅")
        send_score_update(chat_id)
        return
    if text == "New Bowler":
        user_states[chat_id] = "new_bowler_force"
        bot.send_message(chat_id, "Naya bowler select karo:", reply_markup=player_kb(bowling_squad(match)))
        return
    if text == "Wicket":
        user_states[chat_id] = "wicket_select"
        bot.send_message(chat_id, "Kaun out hua?", reply_markup=wicket_kb())
        return
    if text == "Wide":
        user_states[chat_id] = "wide_select"
        bot.send_message(chat_id, "Wide + kitne?", reply_markup=wide_kb())
        return
    if text == "No Ball":
        user_states[chat_id] = "noball_select"
        bot.send_message(chat_id, "No Ball + bat runs?", reply_markup=noball_kb())
        return
    if text == "Bye (+1)":
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
        runs_map = {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "6": 6, "1D (Bat)": 1, "2D (Bat)": 2}
        runs = runs_map[text]
        comment = {0: "Dot ball", 4: "FOUR! 🔥", 6: "SIX! 🚀"}.get(runs, text)
        process_ball(chat_id, runs)
        send_score_update(chat_id, comment)
        if user_states.get(chat_id) == "scoring":  # agar wicket/new batsman nahi aaya
            bot.send_message(chat_id, "Continue:", reply_markup=scoring_kb(match["free_hit"]))

@bot.message_handler(func=lambda m: user_states.get(m.chat.id) == "wide_select")
def handle_wide(message):
    chat_id = message.chat.id
    if message.text == "🔙 Back":
        user_states[chat_id] = "scoring"
        bot.send_message(chat_id, "Back", reply_markup=scoring_kb())
        return
    mp = {"Wd +0": 0, "Wd +1": 1, "Wd +2": 2, "Wd +4": 4}
    if message.text in mp:
        process_ball(chat_id, 0, is_extra=True, extra_type="wide", bat_
