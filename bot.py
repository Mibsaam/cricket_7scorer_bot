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
       
