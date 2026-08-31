import os
import json
import random
import time
import copy
import math
import threading
import urllib.request
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8812331993:AAFm0uvGcDiEYwbKDdqCXGTXg6-8J_10ya0"
ADMIN_ID = 874225351
AUTHORIZED_SCORERS = {ADMIN_ID}
DATA_FILE = "master_cricket_database.json"

STATE_LOCK = threading.Lock()

# Standard T20 Resource Percentages for Standard DLS Engine
DLS_RESOURCE_TABLE = {
    0: 0.0, 1: 3.5, 2: 7.0, 3: 10.5, 4: 14.0, 5: 17.5,
    6: 21.0, 7: 24.5, 8: 28.0, 9: 31.5, 10: 35.0, 12: 41.5,
    15: 50.5, 18: 59.0, 20: 65.0
}

# ================= 24/7 FLASK KEEP-ALIVE SERVER =================
app = Flask(__name__)

@app.route("/")
def index():
    return "ðŸ Pro Cricket Tournament Engine 24/7 Online & Active!", 200

@app.route("/health")
def health():
    return "OK", 200

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)

# ================= DATABASE INITIALIZATION =================
def create_blank_match():
    return {
        "match_id": f"M{random.randint(100, 999)}",
        "tournament_mode": False,
        "tournament_teams": [],
        "tournament_fixtures": [],
        "series_name": "Cricket Championship 2026",
        "series_list": ["Cricket Championship 2026", "T20 Premier League", "Gully Cricket Cup", "Bilateral Trophy", "Super Cup"],
        "series_total_matches": 1,
        "series_current_match_num": 1,
        "series_tally": {},
        "ground": "Local Arena",
        "grounds_list": ["Local Arena", "Shivaji Park Arena", "Azad Maidan", "Eden Gardens", "Gully Ground 1"],
        "stage": "League Match",
        "current_inning": 1,
        "teams": ["Team A", "Team B"],
        "batting_team": "Team A",
        "bowling_team": "Team B",
        "total_match_overs": 7,
        "original_match_overs": 7,
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
        "dls_applied": False,
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
        "user_actions": {},
        "temp_data": {},
        "history": [],
        "squads": {"Team A": [], "Team B": []},
        "team_records": {},
        "h2h_records": {},
        "matchup_db": {},
        "match_innings_data": {
            1: {"team": "Team A", "batting": {}, "bowling": {}, "extras": {"w": 0, "nb": 0, "b": 0, "lb": 0, "total": 0}, "fow": [], "partnerships": [], "final_score": 0, "final_wickets": 0, "final_overs": 0.0},
            2: {"team": "Team B", "batting": {}, "bowling": {}, "extras": {"w": 0, "nb": 0, "b": 0, "lb": 0, "total": 0}, "fow": [], "partnerships": [], "final_score": 0, "final_wickets": 0, "final_overs": 0.0}
        },
        "career_db": {},
        "match_archives": [],
        "timer_enabled": False,
        "timer_allocated_mins": 30,
        "timer_start_epoch": None,
        "timer_paused": False,
        "timer_pause_epoch": None,
        "timer_total_paused_sec": 0,
        "timer_alerts_sent": {"midway": False, "warn5": False, "expired": False},
        "fielding_penalty_active": False
    }

match = create_blank_match()

def save_data():
    with STATE_LOCK:
        try:
            tmp_file = f"{DATA_FILE}.tmp"
            with open(tmp_file, "w") as f:
                json.dump(match, f, indent=2)
            os.replace(tmp_file, DATA_FILE)
        except Exception as e:
            print(f"Save error: {e}")

def load_data():
    global match
    with STATE_LOCK:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    match.update(data)
            except Exception as e:
                print(f"Load error: {e}")

load_data()

def is_admin(uid):
    return uid == ADMIN_ID

def is_scorer(uid):
    return uid in AUTHORIZED_SCORERS or is_admin(uid)

def to_subscript_balls(balls):
    subs = str.maketrans("0123456789", "â‚€â‚â‚‚â‚ƒâ‚„â‚…â‚†â‚‡â‚ˆâ‚‰")
    return str(balls).translate(subs)

def to_serif_bold_num(num_str):
    serif_bold = str.maketrans("0123456789", "ðŸŽðŸðŸðŸ‘ðŸ’ðŸ“ðŸ”ðŸ•ðŸ–ðŸ—")
    return str(num_str).translate(serif_bold)

def clean_txt(text):
    if text is None:
        return ""
    return str(text).replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")

def calculate_allocated_time_mins(overs):
    ov_time_map = {
        1: 5, 2: 8, 3: 12, 4: 16, 5: 20, 6: 25, 7: 30,
        8: 34, 10: 42, 12: 50, 15: 65, 20: 85
    }
    if overs in ov_time_map:
        return ov_time_map[overs]
    return max(5, int(overs * 4.25))

def get_dls_resource(ov_rem):
    if ov_rem in DLS_RESOURCE_TABLE:
        return DLS_RESOURCE_TABLE[ov_rem]
    if ov_rem <= 20:
        return ov_rem * 3.25
    return min(100.0, ov_rem * 2.0)

def get_h2h_key(t1, t2):
    teams_sorted = sorted([clean_txt(t1), clean_txt(t2)])
    return f"{teams_sorted[0]}_vs_{teams_sorted[1]}"

def get_h2h_summary(t1, t2):
    k = get_h2h_key(t1, t2)
    h_rec = match.setdefault("h2h_records", {}).setdefault(k, {
        "matches": 0,
        clean_txt(t1): 0,
        clean_txt(t2): 0,
        "tied": 0,
        "no_result": 0
    })
    return h_rec

def record_h2h_result(winner, loser, tied=False, no_result=False):
    if not match.get("teams") or len(match["teams"]) < 2: return
    t1, t2 = match["teams"][0], match["teams"][1]
    h_rec = get_h2h_summary(t1, t2)
    h_rec["matches"] += 1
    if no_result:
        h_rec["no_result"] += 1
    elif tied:
        h_rec["tied"] += 1
    else:
        w_clean = clean_txt(winner)
        h_rec[w_clean] = h_rec.get(w_clean, 0) + 1
    save_data()

def record_player_matchup(batter, bowler, runs_scored, is_out=False):
    bat = clean_txt(batter)
    bwl = clean_txt(bowler)
    if bat.startswith("Select") or bwl.startswith("Select") or not bat or not bwl: return
    
    m_key = f"{bat}__vs__{bwl}"
    m_data = match.setdefault("matchup_db", {}).setdefault(m_key, {
        "batter": bat, "bowler": bwl, "balls": 0, "runs": 0, "outs": 0, "fours": 0, "sixes": 0
    })
    m_data["balls"] += 1
    m_data["runs"] += runs_scored
    if runs_scored == 4: m_data["fours"] += 1
    if runs_scored == 6: m_data["sixes"] += 1
    if is_out: m_data["outs"] += 1

def generate_h2h_card_text(t1, t2):
    h = get_h2h_summary(t1, t2)
    w1 = h.get(clean_txt(t1), 0)
    w2 = h.get(clean_txt(t2), 0)
    tot = h.get("matches", 0)
    
    if tot == 0:
        leader_txt = "ðŸ¤ Pehla match hai! Abhi tak koi match database me save nahi hai."
    elif w1 > w2:
        leader_txt = f"ðŸ”¥ **{clean_txt(t1)}** head-to-head me aage chal rahi hai ({w1} - {w2})!"
    elif w2 > w1:
        leader_txt = f"ðŸ”¥ **{clean_txt(t2)}** head-to-head me aage chal rahi hai ({w2} - {w1})!"
    else:
        leader_txt = f"âš–ï¸ Dono barabar chal rahi hain ({w1} - {w2})!"

    return (
        f"â•­â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•®\n"
        f"â”‚ âš”ï¸ **HEAD-TO-HEAD BATTLE HISTORY**\n"
        f"â”‚ ðŸ”´ {clean_txt(t1)[:12]} vs ðŸŸ¢ {clean_txt(t2)[:12]}\n"
        f"â•°â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•¯\n\n"
        f"ðŸ“Š **Total Matches:** `{tot}`\n"
        f"ðŸ† **{clean_txt(t1)} Wins:** `{w1}`\n"
        f"ðŸ† **{clean_txt(t2)} Wins:** `{w2}`\n"
        f"âš–ï¸ **Tied / No Result:** `{h.get('tied', 0)} / {h.get('no_result', 0)}`\n\n"
        f"ðŸ“Œ **Status:** {leader_txt}"
    )

def generate_player_vs_bowler_text(batter, bowler):
    bat = clean_txt(batter)
    bwl = clean_txt(bowler)
    k = f"{bat}__vs__{bwl}"
    st = match.get("matchup_db", {}).get(k)
    if not st or st["balls"] == 0:
        return f"ðŸ“Š **Matchup Record:**\nAbhi tak **{bat}** aur **{bwl}** ke beech koi ball record nahi hui hai."
    
    sr = (st["runs"] / st["balls"] * 100) if st["balls"] > 0 else 0.0
    return (
        f"â•­â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•®\n"
        f"â”‚ ðŸŽ¯ **MATCHUP: {bat} vs {bwl}**\n"
        f"â•°â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•¯\n"
        f"ðŸ **Runs Scored:** `{st['runs']}` runs ({st['balls']}b)\n"
        f"ðŸ’¥ **Boundaries:** `{st['fours']} Fours` â”‚ `{st['sixes']} Sixes`\n"
        f"âš¡ **Strike Rate:** `{sr:.1f}`\n"
        f"âŒ **Dismissed by Bowler:** `{st['outs']} Times`"
    )

def get_timer_status_info():
    if not match.get("timer_enabled") or not match.get("timer_start_epoch"):
        return None
    
    total_sec = match.get("timer_allocated_mins", 30) * 60
    now = time.time()
    
    if match.get("timer_paused"):
        elapsed_sec = (match.get("timer_pause_epoch", now) - match["timer_start_epoch"]) - match.get("timer_total_paused_sec", 0)
    else:
        elapsed_sec = (now - match["timer_start_epoch"]) - match.get("timer_total_paused_sec", 0)
        
    rem_sec = max(0, total_sec - elapsed_sec)
    rem_min = int(rem_sec // 60)
    
    is_expired = (elapsed_sec >= total_sec)
    return {
        "rem_mins": rem_min,
        "rem_sec": int(rem_sec % 60),
        "total_mins": match.get("timer_allocated_mins", 30),
        "paused": match.get("timer_paused", False),
        "expired": is_expired
    }

def ensure_team_record(team_name):
    team_name = clean_txt(team_name)
    if "team_records" not in match: match["team_records"] = {}
    if team_name not in match["team_records"]:
        match["team_records"][team_name] = {"played": 0, "won": 0, "lost": 0, "tied": 0, "no_result": 0}

def ensure_player(p_name, team="General"):
    p_name = clean_txt(p_name).strip()
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

def ensure_match_player_stat(p_name, team, role="bat"):
    p_name = clean_txt(p_name).strip()
    if not p_name or p_name.startswith("Select"): return
    inn = match["current_inning"]
    if inn not in match["match_innings_data"]:
        match["match_innings_data"][inn] = {"team": team, "batting": {}, "bowling": {}, "extras": {"w": 0, "nb": 0, "b": 0, "lb": 0, "total": 0}, "fow": [], "partnerships": [], "final_score": 0, "final_wickets": 0, "final_overs": 0.0}
    
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
        bot.send_message(cid, f"ðŸŽ™ï¸ **MATCH ANNOUNCEMENT:**\n{text}", parse_mode="Markdown")
    except Exception:
        try:
            bot.send_message(cid, f"ðŸŽ™ï¸ MATCH ANNOUNCEMENT:\n{clean_txt(text)}")
        except Exception:
            pass

def save_state_for_undo():
    match["history"].append({
        "match_state": copy.deepcopy({
            "runs": match["runs"], "wickets": match["wickets"], "overs": match["overs"],
            "balls": match["balls"], "extras_total": match["extras_total"], "extras_wides": match["extras_wides"],
            "extras_noballs": match["extras_noballs"], "extras_byes": match["extras_byes"],
            "extras_legbyes": match["extras_legbyes"], "striker": match["striker"],
            "non_striker": match["non_striker"], "bowler": match["bowler"],
            "last_bowler": match["last_bowler"], "is_free_hit_active": match["is_free_hit_active"],
            "partnership_runs": match["partnership_runs"], "partnership_balls": match["partnership_balls"],
            "current_over_runs": match["current_over_runs"], "recent_balls": list(match["recent_balls"]),
            "last_event_ticker": match["last_event_ticker"], "match_status": match["match_status"],
            "match_innings_data": match["match_innings_data"], "target": match["target"],
            "current_inning": match["current_inning"],
            "fall_of_wickets": list(match.get("fall_of_wickets", [])),
            "fielding_penalty_active": match.get("fielding_penalty_active", False),
            "total_match_overs": match["total_match_overs"],
            "dls_applied": match.get("dls_applied", False)
        }),
        "career_db": copy.deepcopy(match["career_db"])
    })
    if len(match["history"]) > 30:
        match["history"].pop(0)

def safe_send_message(chat_id, text, reply_markup=None):
    try:
        return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        return bot.send_message(chat_id, clean_txt(text), reply_markup=reply_markup)

def safe_edit_message(text, chat_id, message_id, reply_markup=None):
    try:
        bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=reply_markup, parse_mode="Markdown")
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e):
            try:
                bot.edit_message_text(clean_txt(text), chat_id=chat_id, message_id=message_id, reply_markup=reply_markup)
            except Exception:
                pass

# ================= COMPACT MOBILE SCOREBOARD =================
def get_large_scoreboard_text():
    crr = (match['runs'] / (match['balls'] / 6)) if match['balls'] > 0 else 0.0
    
    b_st = match["match_innings_data"].get(match["current_inning"], {}).get("bowling", {}).get(match["bowler"], {"balls": 0, "runs": 0, "wickets": 0})
    b_ov = f"{b_st['balls'] // 6}.{b_st['balls'] % 6}"
    
    st_b = match["match_innings_data"].get(match["current_inning"], {}).get("batting", {}).get(match["striker"], {"runs": 0, "balls": 0, "fours": 0, "sixes": 0})
    nst_b = match["match_innings_data"].get(match["current_inning"], {}).get("batting", {}).get(match["non_striker"], {"runs": 0, "balls": 0, "fours": 0, "sixes": 0})
    
    st_sr = (st_b['runs'] / st_b['balls'] * 100) if st_b.get('balls', 0) > 0 else 0.0
    nst_sr = (nst_b['runs'] / nst_b['balls'] * 100) if nst_b.get('balls', 0) > 0 else 0.0
    
    st_b_sub = to_subscript_balls(st_b['balls'])
    nst_b_sub = to_subscript_balls(nst_b['balls'])
    
    rec_balls = " â”‚ ".join(match["recent_balls"][-6:]) if match["recent_balls"] else "â€¢"
    
    s_runs = to_serif_bold_num(match['runs'])
    s_wkts = to_serif_bold_num(match['wickets'])
    s_overs = to_serif_bold_num(f"{match['overs']:.1f}")
    s_crr = to_serif_bold_num(f"{crr:.2f}")
    
    team_name = clean_txt(match['batting_team'])[:14].upper()
    dls_tag = " (DLS)" if match.get("dls_applied") else ""
    
    if match.get("current_inning") == 2 and match["target"] > 0:
        needed = max(0, match["target"] - match["runs"])
        b_left = max(0, (match["total_match_overs"] * 6) - match["balls"])
        bottom_box = (
            f"â•­â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•®\n"
            f"â”‚ ðŸŽ¯ ð“ð€ð‘ð†ð„ð“: {to_serif_bold_num(match['target'])}{dls_tag} â”‚ ððžðžð {to_serif_bold_num(needed)} ({to_serif_bold_num(b_left)}ð›)\n"
            f"â”‚ ðŸŽžï¸ [ {rec_balls} ]\n"
            f"â•°â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•¯"
        )
    else:
        bottom_box = (
            f"â•­â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•®\n"
            f"â”‚ ðŸ¤ ð'ð’ð‡ðˆð: {to_serif_bold_num(match['partnership_runs'])} ({to_serif_bold_num(match['partnership_balls'])}ð›) â”‚ âš¡ ð„ð±: {to_serif_bold_num(match['extras_total'])}\n"
            f"â”‚ ðŸŽžï¸ [ {rec_balls} ]\n"
            f"â•°â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•¯"
        )
        
    fh_tag = " ðŸ”¥ [FREE HIT ACTIVE]" if match.get("is_free_hit_active") else ""
    pen_tag = " âš ï¸ [FIELDING PENALTY ACTIVE]" if match.get("fielding_penalty_active") else ""
    
    t_info = get_timer_status_info()
    timer_str = ""
    if t_info:
        if t_info["paused"]:
            timer_str = f"â¸ï¸ Time: `{t_info['rem_mins']}m Left (Paused)` â”‚ "
        elif t_info["expired"]:
            timer_str = f"ðŸš¨ Time: `EXPIRED (+Penalty)` â”‚ "
        else:
            timer_str = f"â³ Time: `{t_info['rem_mins']}m Left` â”‚ "
            
    clean_ticker = clean_txt(match['last_event_ticker'])
    status_label = f"Status: `{match['match_status']}`" if match["match_status"] != "Active" else f"{timer_str}ðŸŽ™ï¸ Event: {clean_ticker}"
    
    return (
        f"â•­â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•®\n"
        f"â”‚ ðŸ”´ **{team_name}** (Inn {match['current_inning']}) : ã€ {s_runs} / {s_wkts} ã€‘\n"
        f"â”‚ â³ {s_overs} / {match['total_match_overs']}.0 ðŽð¯   â”‚ ð‚ð‘ð‘: {s_crr}\n"
        f"â•°â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•¯\n\n"
        f"ðŸ â˜… **{clean_txt(match['striker'])}** *\n"
        f"   â–¶ {to_serif_bold_num(st_b['runs'])} â‚{st_b_sub}â‚Ž â”‚ ðŸ’ð¬: {to_serif_bold_num(st_b['fours'])}  ðŸ”ð¬: {to_serif_bold_num(st_b['sixes'])} [{to_serif_bold_num(f'{st_sr:.1f}')}]\n\n"
        f"ðŸƒ   **{clean_txt(match['non_striker'])}**\n"
        f"   â–¶ {to_serif_bold_num(nst_b['runs'])} â‚{nst_b_sub}â‚Ž â”‚ ðŸ’ð¬: {to_serif_bold_num(nst_b['fours'])}  ðŸ”ð¬: {to_serif_bold_num(nst_b['sixes'])} [{to_serif_bold_num(f'{nst_sr:.1f}')}]\n\n"
        f"âš¾   **{clean_txt(match['bowler'])}**\n"
        f"   â–¶ {to_serif_bold_num(b_st['wickets'])} / {to_serif_bold_num(b_st['runs'])} ({to_serif_bold_num(b_ov)} ov)\n\n"
        f"{bottom_box}\n"
        f"ðŸŸï¸ Ground: `{clean_txt(match['ground'])}`\n"
        f"ðŸ† **{clean_txt(match['series_name'])}** (M {match['series_current_match_num']}/{match['series_total_matches']}){fh_tag}{pen_tag}\n"
        f"{status_label}"
    )

# ================= DETAILED SCORECARD =================
def generate_detailed_scorecard_text(match_data=None):
    d = match_data if match_data else match
    inn_data = d.get("match_innings_data", {})
    t1 = d["teams"][0] if len(d.get("teams", [])) > 0 else d["batting_team"]
    t2 = d["teams"][1] if len(d.get("teams", [])) > 1 else d["bowling_team"]
    
    out = (
        f"â•­â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•®\n"
        f"â”‚ ðŸ“Š ðŽð…ð…ðˆð‚ðˆð€ð‹ ð’ð‚ðŽð‘ð„ð‚ð€ð‘ðƒ       â”‚\n"
        f"â”‚ ðŸ”´ {clean_txt(t1)[:12]} vs ðŸŸ¢ {clean_txt(t2)[:12]}\n"
        f"â”‚ Status: {d.get('match_status', 'Active')}\n"
        f"â•°â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•¯\n"
    )
    
    for inn in [1, 2]:
        i_info = inn_data.get(inn, {})
        team_n = i_info.get("team") if i_info.get("team") else (d["batting_team"] if inn == d["current_inning"] else d["bowling_team"])
        
        out += f"\nðŸ”´ ð—œð—¡ð—¡ð—œð—¡ð—šð—¦ {inn} : **{clean_txt(team_n)}**"
        if i_info.get("final_score") is not None and inn < d["current_inning"]:
            out += f" ({i_info.get('final_score')}/{i_info.get('final_wickets')} in {i_info.get('final_overs')} ov)\n"
        else:
            out += "\n"
            
        out += "ðŸ ðð€ð“ð“ðˆðð†\n"
        batting_dict = i_info.get("batting", {})
        
        has_bat = False
        for p, st in batting_dict.items():
            if p.startswith("Select") or p.startswith("Batsman"): continue
            has_bat = True
            sr = (st["runs"] / st["balls"] * 100) if st.get("balls", 0) > 0 else 0.0
            p_sub = to_subscript_balls(st['balls'])
            status_txt = f"*{clean_txt(st['status'])}*" if st['status'] == "Not Out" else f"_{clean_txt(st['status'])}_"
            out += f"â€¢ **{clean_txt(p)}** â–¶ {to_serif_bold_num(st['runs'])} â‚{p_sub}â‚Ž â”‚ ðŸ’ð¬:{to_serif_bold_num(st['fours'])} ðŸ”ð¬:{to_serif_bold_num(st['sixes'])} [{to_serif_bold_num(f'{sr:.1f}')}] {status_txt}\n"
            
        if not has_bat:
            out += "â€¢ _Yet to bat_\n"
            
        out += "\nâš¾ ððŽð–ð‹ðˆðð†\n"
        bowling_dict = i_info.get("bowling", {})
        has_bowl = False
        for b, st in bowling_dict.items():
            if b.startswith("Select") or b.startswith("Bowler"): continue
            has_bowl = True
            b_cnt = st.get("balls", 0)
            ov = f"{b_cnt // 6}.{b_cnt % 6}"
            econ = (st["runs"] / (b_cnt / 6)) if b_cnt > 0 else 0.0
            out += f"â€¢ **{clean_txt(b)}** â–¶ {to_serif_bold_num(ov)} ov (M:{st.get('maidens',0)}) â”‚ {to_serif_bold_num(st['wickets'])}/{to_serif_bold_num(st['runs'])} â”‚ ER: {to_serif_bold_num(f'{econ:.1f}')}\n"
            
        if not has_bowl:
            out += "â€¢ _Yet to bowl_\n"
            
        ex = i_info.get("extras", {"w": 0, "nb": 0, "b": 0, "lb": 0, "total": 0})
        out += f"\nâš¡ Extras: {to_serif_bold_num(ex.get('total', 0))} (Wd:{ex.get('w',0)}, NB:{ex.get('nb',0)}, B:{ex.get('b',0)}, LB:{ex.get('lb',0)})\n"
        
        ps_list = i_info.get("partnerships", [])
        if ps_list:
            out += "ðŸ¤ Partnerships:\n"
            for ps in ps_list:
                out += f"  â†³ {clean_txt(ps)}\n"
        elif inn == d["current_inning"] and not d["striker"].startswith("Select"):
            out += f"ðŸ¤ Current Partnership: {to_serif_bold_num(d['partnership_runs'])} runs ({to_serif_bold_num(d['partnership_balls'])}b) â€” {clean_txt(d['striker'])} & {clean_txt(d['non_striker'])}\n"
            
        fow_list = i_info.get("fow", [])
        if fow_list:
            out += "ðŸ“‰ Fall of Wickets:\n  â†³ " + ", ".join([clean_txt(f) for f in fow_list]) + "\n"
            
        out += "â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€\n"
        
    out += (
        f"ðŸŸï¸ Ground: `{clean_txt(d['ground'])}` â”‚ â³ {d['total_match_overs']}.0 Ov ({d.get('max_wickets_limit', 10)} Wkts)\n"
        f"ðŸ† **{clean_txt(d['series_name'])}** (Match {d.get('series_current_match_num', 1)}/{d.get('series_total_matches', 1)})"
    )
    return out

# ================= DASHBOARD KEYBOARD =================
def get_scorer_keyboard(uid):
    m = InlineKeyboardMarkup(row_width=3)
    
    if match.get("match_status") == "Innings Break":
        m.add(InlineKeyboardButton("ðŸ Start 2nd Innings & Select Openers", callback_data="act_switch_innings"))
        m.add(InlineKeyboardButton("ðŸ“Š Score Summary", callback_data="view_summary"))
        m.add(
            InlineKeyboardButton("ðŸ”„ Soft Reset", callback_data="act_reset_stats_confirm"),
            InlineKeyboardButton("ðŸš€ Hard Reset (New Setup)", callback_data="act_hard_reset_confirm")
        )
        return m

    if match.get("match_status") in ["Finished", "Abandoned", "Cancelled"]:
        m.add(
            InlineKeyboardButton("ðŸ“Š Full Scorecard", callback_data="view_summary"),
            InlineKeyboardButton("âš”ï¸ Head-to-Head History", callback_data="view_h2h_live")
        )
        m.add(
            InlineKeyboardButton("ðŸ”„ Soft Reset (Same Match)", callback_data="act_reset_stats_confirm"),
            InlineKeyboardButton("ðŸš€ Hard Reset (New Setup)", callback_data="act_hard_reset_confirm")
        )
        return m

    m.add(
        InlineKeyboardButton("ðŸ”´ 0 Dot", callback_data="act_run_0"),
        InlineKeyboardButton("ðŸŸ¢ 1 Run", callback_data="act_run_1"),
        InlineKeyboardButton("ðŸ”µ 2 Runs", callback_data="act_run_2")
    )
    m.add(
        InlineKeyboardButton("ðŸŸ¡ 3 Runs", callback_data="act_run_3"),
        InlineKeyboardButton("ðŸ”¥ 4 Boundary", callback_data="act_run_4"),
        InlineKeyboardButton("ðŸš€ 6 Sixer", callback_data="act_run_6")
    )
    m.add(
        InlineKeyboardButton("âœï¸ Custom Runs", callback_data="menu_custom_runs"),
        InlineKeyboardButton("âš¡ Wide (+Extras)", callback_data="menu_wide"),
        InlineKeyboardButton("âš ï¸ No Ball (+Runs)", callback_data="menu_noball")
    )
    m.add(
        InlineKeyboardButton("ðŸƒ Byes / Leg Byes", callback_data="menu_byes"),
        InlineKeyboardButton("âŒ WICKET MENU", callback_data="menu_wicket"),
        InlineKeyboardButton("ðŸ˜± Drop Catch", callback_data="act_drop_catch")
    )
    m.add(
        InlineKeyboardButton("ðŸ”„ Strike Swap", callback_data="act_swap_strike"),
        InlineKeyboardButton("ðŸ‘¤ Striker", callback_data="pop_set_striker"),
        InlineKeyboardButton("ðŸƒ Non-Striker", callback_data="pop_set_nonstriker")
    )
    m.add(
        InlineKeyboardButton("âš¾ Bowler", callback_data="pop_set_bowler"),
        InlineKeyboardButton("ðŸŽ¯ Batter vs Bowler", callback_data="view_matchup_current"),
        InlineKeyboardButton("âš”ï¸ H2H Ledger", callback_data="view_h2h_live")
    )
    m.add(
        InlineKeyboardButton("â±ï¸ Over-Rate Timer", callback_data="menu_timer_control"),
        InlineKeyboardButton("ðŸŒ§ï¸ DLS Target Engine", callback_data="menu_dls_reduction"),
        InlineKeyboardButton("ðŸ›‘ Abandon / Cancel Match", callback_data="menu_abandon_match")
    )
    m.add(
        InlineKeyboardButton("ðŸš‘ Injury Split", callback_data="pop_injury_split"),
        InlineKeyboardButton("ðŸ§¤ Set WK / Captain", callback_data="menu_set_wk_cap"),
        InlineKeyboardButton("âš¡ Fast 1st Inn Entry", callback_data="menu_quick_innings")
    )
    m.add(
        InlineKeyboardButton("ðŸ“Š Score Summary", callback_data="view_summary"),
        InlineKeyboardButton("ðŸ“œ Match Archives", callback_data="view_archives"),
        InlineKeyboardButton("â­ MoM / MoS Award", callback_data="view_mom")
    )
    m.add(
        InlineKeyboardButton("âž• Extend Series", callback_data="menu_extend_series"),
        InlineKeyboardButton("ðŸ‘¥ Squads & Teams", callback_data="menu_squads_master"),
        InlineKeyboardButton("âœï¸ Edit Match Data", callback_data="menu_edit_match")
    )
    if is_admin(uid):
        m.add(InlineKeyboardButton("ðŸ›¡ï¸ Scorer Permissions", callback_data="menu_scorers_admin"))
        
    m.add(
        InlineKeyboardButton("ðŸ”„ Switch Innings", callback_data="act_switch_innings"),
        InlineKeyboardButton("â†©ï¸ Undo Ball", callback_data="act_undo")
    )
    m.add(
        InlineKeyboardButton("ðŸ”„ Soft Reset", callback_data="act_reset_stats_confirm"),
        InlineKeyboardButton("ðŸš€ Hard Reset (New Setup)", callback_data="act_hard_reset_confirm")
    )
    return m

def sync_pinned_card(cid):
    try:
        txt = get_large_scoreboard_text()
        if match.get("pinned_message_id") and match.get("pinned_chat_id") == cid:
            safe_edit_message(txt, chat_id=cid, message_id=match["pinned_message_id"], reply_markup=get_scorer_keyboard(ADMIN_ID))
    except Exception:
        pass

# ================= BULLETPROOF HELPER TO FILTER AVAILABLE BATSMEN =================
def get_available_batsmen(team_name):
    inn = match["current_inning"]
    b_dict = match["match_innings_data"].get(inn, {}).get("batting", {})
    
    current_active = {clean_txt(match["striker"]).lower(), clean_txt(match["non_striker"]).lower()}
    
    avail = []
    for p in match["squads"].get(team_name, []):
        p_clean = clean_txt(p)
        if not p_clean or p_clean.lower() in current_active:
            continue
            
        matched_entry = next((st for b_name, st in b_dict.items() if clean_txt(b_name).lower() == p_clean.lower()), None)
        if matched_entry:
            if matched_entry.get("status") == "Retired Hurt":
                avail.append(p_clean)
        else:
            avail.append(p_clean)
            
    return avail

# ================= STRICT VALIDATION BEFORE SCORING =================
def validate_on_field_players(cid):
    if match["match_status"] == "Innings Break":
        safe_send_message(cid, "ðŸ **Innings 1 Over ho chuki hai!** Niche diye gaye button se 2nd Innings shuru karein:", reply_markup=get_scorer_keyboard(ADMIN_ID))
        return False

    if match["match_status"] != "Active":
        safe_send_message(cid, f"âš ï¸ Match is currently **{match['match_status']}**!")
        return False
        
    total_allowed_balls = match["total_match_overs"] * 6
    if match["balls"] >= total_allowed_balls:
        check_match_completion(cid)
        return False

    if match["striker"].startswith("Select") or not match["striker"]:
        m = InlineKeyboardMarkup(row_width=2)
        for p in get_available_batsmen(match["batting_team"]):
            m.add(InlineKeyboardButton(f"ðŸ {p}", callback_data=f"replace_str_{p}"))
        m.add(InlineKeyboardButton("âž• Type Striker", callback_data="type_replace_str"))
        safe_send_message(cid, f"ðŸš¨ **Pehle Striker ({match['batting_team']}) assign karein:**", reply_markup=m)
        return False
        
    if match["non_striker"].startswith("Select") or not match["non_striker"]:
        m = InlineKeyboardMarkup(row_width=2)
        for p in get_available_batsmen(match["batting_team"]):
            m.add(InlineKeyboardButton(f"ðŸƒ {p}", callback_data=f"replace_nstr_{p}"))
        m.add(InlineKeyboardButton("âž• Type Non-Striker", callback_data="type_replace_nstr"))
        safe_send_message(cid, f"ðŸš¨ **Pehle Non-Striker ({match['batting_team']}) assign karein:**", reply_markup=m)
        return False
        
    if match["bowler"].startswith("Select") or not match["bowler"]:
        m = InlineKeyboardMarkup(row_width=2)
        for p in match["squads"].get(match["bowling_team"], []):
            if p != match["last_bowler"]:
                m.add(InlineKeyboardButton(f"âš¾ {p}", callback_data=f"sel_bowl_{p}"))
        m.add(InlineKeyboardButton("âž• Type Bowler", callback_data="wiz_type_bowler"))
        safe_send_message(cid, f"ðŸš¨ **Pehle Bowler ({match['bowling_team']}) assign karein:**", reply_markup=m)
        return False
        
    return True

# ================= SETUP WIZARD & COMMANDS =================
def reset_for_new_match_setup():
    """Start a completely fresh match while preserving permanent databases/squads."""
    global match
    with STATE_LOCK:
        old = match
        blank = create_blank_match()

        # Preserve only permanent/reference data. Everything match-specific
        # (score, innings, teams, toss, timer, history, temp wizard state,
        # pinned message IDs, etc.) must come from a brand-new match object.
        for key in (
            "series_list", "grounds_list", "squads", "team_records",
            "h2h_records", "matchup_db", "career_db", "match_archives",
        ):
            blank[key] = copy.deepcopy(old.get(key, blank.get(key)))

        match.clear()
        match.update(blank)
    save_data()


@bot.message_handler(commands=['start', 'score', 'cricket', 'setup'])
def handle_start_wizard(msg):
    with STATE_LOCK:
        match["user_actions"][msg.from_user.id] = None
    m = InlineKeyboardMarkup(row_width=1)
    m.add(
        InlineKeyboardButton("ðŸ† Real Tournament / Bilateral Series", callback_data="wiz_mode_real"),
        InlineKeyboardButton("ðŸŸï¸ Multi-Team Tournament / League Mode", callback_data="wiz_mode_tournament"),
        InlineKeyboardButton("ðŸ§ª Practice / Fake Match", callback_data="wiz_mode_practice")
    )
    safe_send_message(msg.chat.id, "ðŸ **PRO CRICKET ENGINE - INTERACTIVE SETUP**\n\nðŸ“Œ **Step 1:** Select Match / Tournament Mode:", reply_markup=m)

@bot.message_handler(commands=['summary'])
def handle_summary_command(msg):
    txt = generate_detailed_scorecard_text()
    safe_send_message(msg.chat.id, txt)

@bot.message_handler(commands=['h2h'])
def handle_h2h_command(msg):
    t1 = match["teams"][0] if len(match.get("teams", [])) > 0 else match["batting_team"]
    t2 = match["teams"][1] if len(match.get("teams", [])) > 1 else match["bowling_team"]
    safe_send_message(msg.chat.id, generate_h2h_card_text(t1, t2))

@bot.message_handler(commands=['teams'])
def handle_teams_ledger(msg):
    out = "ðŸ“Š **PERMANENT TEAM HEAD-TO-HEAD & STANDINGS:**\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
    if not match.get("team_records"):
        out += "Abhi tak koi team records save nahi hain!"
    else:
        for t, rec in match["team_records"].items():
            win_pct = (rec["won"] / rec["played"] * 100) if rec["played"] > 0 else 0.0
            out += f"â€¢ **{clean_txt(t)}** â–¶ Played: `{rec['played']}` â”‚ Won: `{rec['won']}` â”‚ Lost: `{rec['lost']}` â”‚ NR: `{rec.get('no_result', 0)}` â”‚ Win%: `{win_pct:.1f}%`\n"
    safe_send_message(msg.chat.id, out)

@bot.message_handler(commands=['profile'])
def handle_profile(msg):
    txt = msg.text.replace("/profile", "").strip().lower()
    found_p, d = None, None
    for p, data in match["career_db"].items():
        u = str(data.get("username", "")).lower().replace("@", "")
        if txt and (txt == p.lower() or txt == u):
            found_p, d = p, data
            break
    if found_p:
        sr = (d["runs"] / d["balls"] * 100) if d["balls"] > 0 else 0.0
        econ = (d["runs_given"] / (d["bowled_balls"] / 6)) if d["bowled_balls"] > 0 else 0.0
        tot_c = d["catches"] + d["drops"]
        c_eff = (d["catches"] / tot_c * 100) if tot_c > 0 else 100.0
        u_tag = f"@{d['username']}" if d.get('username') else "Not Linked"
        res = (
            f"ðŸ‘¤ **LIFETIME CAREER PROFILE - {clean_txt(found_p)}**\n"
            f"ðŸ†” UUID: `{d['uuid']}` â”‚ Handle: `{u_tag}` â”‚ Team: `{d['team']}`\n"
            f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
            f"ðŸ **Batting:** `{d['runs']} Runs` ({d['balls']}b) â”‚ SR: `{sr:.2f}`\n"
            f"ðŸ”¥ **Boundaries:** `{d['fours']} Fours` â”‚ `{d['sixes']} Sixes`\n"
            f"âš¾ **Bowling:** `{d['wickets']} Wickets` (Stumpings: `{d.get('stumpings', 0)}`) â”‚ Econ: `{econ:.2f}`\n"
            f"ðŸ§¤ **Fielding:** `{d['catches']} Catches` â”‚ `{d['drops']} Drops` (Catch Eff: `{c_eff:.1f}%`)\n"
            f"â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
        )
        safe_send_message(msg.chat.id, res)
    else:
        safe_send_message(msg.chat.id, "âŒ Player nahi mila! Use: `/profile PlayerName` ya `/profile @username`")

def check_match_completion(cid):
    limit_w = match["max_wickets_limit"]
    total_balls_limit = match["total_match_overs"] * 6
    
    if match["current_inning"] == 1:
        if match["balls"] >= total_balls_limit or match["wickets"] >= limit_w:
            match["match_innings_data"][1]["final_score"] = match["runs"]
            match["match_innings_data"][1]["final_wickets"] = match["wickets"]
            match["match_innings_data"][1]["final_overs"] = match["overs"]
            
            # Simple & Exact Cricket Target: Runs + 1
            match["target"] = max(1, match["runs"] + 1)
            match["match_status"] = "Innings Break"
            
            txt = (
                f"ðŸ **INNINGS 1 COMPLETE!**\n"
                f"**{clean_txt(match['batting_team'])}** scored `{match['runs']}/{match['wickets']}` in `{match['overs']}` ov.\n"
                f"ðŸŽ¯ **Target for {clean_txt(match['bowling_team'])}:** `{match['target']}` runs in `{match['total_match_overs']}.0` overs."
            )
            broadcast_commentary(cid, txt)
            save_data()
            sync_pinned_card(cid)
            m = InlineKeyboardMarkup(row_width=1)
            m.add(InlineKeyboardButton("ðŸ Start 2nd Innings & Select Openers", callback_data="act_switch_innings"))
            safe_send_message(cid, "ðŸ‘‰ Click below to deploy 2nd Innings:", reply_markup=m)
            return

    elif match["current_inning"] == 2 and match["target"] > 0:
        if match["runs"] >= match["target"]:
            match["match_status"] = "Finished"
            match["match_innings_data"][2]["final_score"] = match["runs"]
            match["match_innings_data"][2]["final_wickets"] = match["wickets"]
            match["match_innings_data"][2]["final_overs"] = match["overs"]
            
            w_left = limit_w - match["wickets"]
            b_left = max(0, total_balls_limit - match["balls"])
            winner = match['batting_team']
            loser = match['bowling_team']
            
            ensure_team_record(winner)
            ensure_team_record(loser)
            match["team_records"][winner]["played"] += 1
            match["team_records"][winner]["won"] += 1
            match["team_records"][loser]["played"] += 1
            match["team_records"][loser]["lost"] += 1
            
            match["series_tally"][winner] = match["series_tally"].get(winner, 0) + 1
            record_h2h_result(winner, loser, tied=False, no_result=False)
            
            dls_note = " (DLS Method)" if match.get("dls_applied") else ""
            txt = f"ðŸ† ðŸŽŠ **CHAMPIONS!** **{clean_txt(winner)}** WON Match {match['series_current_match_num']} by **{w_left} wickets** (with {b_left} balls remaining){dls_note}! ðŸ¥‡"
            broadcast_commentary(cid, txt)
            archive_match("Finished", winner)
            sync_pinned_card(cid)
            
        elif match["balls"] >= total_balls_limit or match["wickets"] >= limit_w:
            match["match_status"] = "Finished"
            match["match_innings_data"][2]["final_score"] = match["runs"]
            match["match_innings_data"][2]["final_wickets"] = match["wickets"]
            match["match_innings_data"][2]["final_overs"] = match["overs"]
            
            margin = (match["target"] - 1) - match["runs"]
            if margin == 0:
                t1, t2 = match['batting_team'], match['bowling_team']
                ensure_team_record(t1)
                ensure_team_record(t2)
                match["team_records"][t1]["played"] += 1
                match["team_records"][t1]["tied"] += 1
                match["team_records"][t2]["played"] += 1
                match["team_records"][t2]["tied"] += 1
                record_h2h_result(t1, t2, tied=True, no_result=False)
                broadcast_commentary(cid, "ðŸ”¥ âš–ï¸ **WHAT A THRILLER! MATCH TIED!**")
                archive_match("Finished", "Tied")
            elif margin > 0:
                winner = match['bowling_team']
                loser = match['batting_team']
                ensure_team_record(winner)
                ensure_team_record(loser)
                match["team_records"][winner]["played"] += 1
                match["team_records"][winner]["won"] += 1
                match["team_records"][loser]["played"] += 1
                match["team_records"][loser]["lost"] += 1
                match["series_tally"][winner] = match["series_tally"].get(winner, 0) + 1
                record_h2h_result(winner, loser, tied=False, no_result=False)
                dls_note = " (DLS Method)" if match.get("dls_applied") else ""
                txt = f"ðŸ† ðŸŽŠ **VICTORY!** **{clean_txt(winner)}** WON Match {match['series_current_match_num']} by **{margin} runs**{dls_note}! ðŸ¥‡"
                broadcast_commentary(cid, txt)
                archive_match("Finished", winner)
            sync_pinned_card(cid)

def archive_match(status_reason="Finished", winner_team="None"):
    if not match["is_practice_mode"]:
        m_entry = {
            "match_id": match["match_id"],
            "series_name": match["series_name"],
            "series_current_match_num": match["series_current_match_num"],
            "series_total_matches": match["series_total_matches"],
            "ground": match["ground"],
            "stage": match["stage"],
            "total_match_overs": match["total_match_overs"],
            "max_wickets_limit": match["max_wickets_limit"],
            "teams": f"{match['teams'][0] if match.get('teams') else match['batting_team']} vs {match['teams'][1] if len(match.get('teams', [])) > 1 else match['bowling_team']}",
            "match_status": status_reason,
            "winner": winner_team,
            "match_innings_data": copy.deepcopy(match["match_innings_data"])
        }
        match["match_archives"].append(m_entry)
        save_data()

def register_legal_ball(cid, legal=True, ball_tag="0", runs_on_ball=0):
    if legal:
        match["balls"] += 1
        match["partnership_balls"] += 1
        comp_ov = match["balls"] // 6
        rem_b = match["balls"] % 6
        match["overs"] = float(f"{comp_ov}.{rem_b}")
        match["recent_balls"].append(ball_tag)
        
        ensure_player(match["bowler"], match["bowling_team"])
        ensure_match_player_stat(match["bowler"], match["bowling_team"], role="bowl")
        
        match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["balls"] += 1
        if match["bowler"] in match["career_db"]:
            match["career_db"][match["bowler"]]["bowled_balls"] += 1
        
        if match["is_free_hit_active"]:
            match["is_free_hit_active"] = False

        save_data()
        sync_pinned_card(cid)

        total_b_limit = match["total_match_overs"] * 6
        if match["balls"] >= total_b_limit or match["wickets"] >= match["max_wickets_limit"] or (match["current_inning"] == 2 and match["target"] > 0 and match["runs"] >= match["target"]):
            check_match_completion(cid)
            return

        if rem_b == 0 and match["balls"] > 0:
            if match["current_over_runs"] == 0:
                match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["maidens"] += 1
                
            match["over_worm"][comp_ov] = match["current_over_runs"]
            match["current_over_runs"] = 0
            
            if runs_on_ball % 2 == 0:
                match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
                
            match["last_bowler"] = match["bowler"]
            match["bowler"] = "Select Bowler"
            match["last_event_ticker"] = f"ðŸ Over {comp_ov} Complete! Strike rotated to {clean_txt(match['striker'])}."
            
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["bowling_team"], []):
                if p != match["last_bowler"]:
                    m.add(InlineKeyboardButton(f"âš¾ {p}", callback_data=f"sel_bowl_{p}"))
            m.add(InlineKeyboardButton("âž• Type New Bowler", callback_data="wiz_type_bowler"))
            try:
                safe_send_message(cid, f"ðŸš¨ **Select Next Bowler for Over {comp_ov+1}:**", reply_markup=m)
            except Exception:
                pass

        elif runs_on_ball % 2 != 0:
            match["striker"], match["non_striker"] = match["non_striker"], match["striker"]

        save_data()

def start_wizard_squad_step(cid, mid):
    t1 = match["teams"][0] if len(match.get("teams", [])) > 0 else "Team 1"
    t2 = match["teams"][1] if len(match.get("teams", [])) > 1 else "Team 2"
    if t1 not in match["squads"]: match["squads"][t1] = []
    if t2 not in match["squads"]: match["squads"][t2] = []
    
    m = InlineKeyboardMarkup(row_width=2)
    m.add(InlineKeyboardButton(f"âž• Bulk Add ({t1})", callback_data=f"wiz_add_p_{t1}"))
    m.add(InlineKeyboardButton(f"âž• Bulk Add ({t2})", callback_data=f"wiz_add_p_{t2}"))
    m.add(InlineKeyboardButton("âž¡ï¸ Continue to Ground & Overs", callback_data="wiz_ground_step"))
    txt = f"ðŸ“Œ **Step 4: Manage Squads for {t1} & {t2}:**\n(Aap ek sath comma ',' se separate karke saare players bhej sakte hain)"
    if mid:
        safe_edit_message(txt, chat_id=cid, message_id=mid, reply_markup=m)
    else:
        safe_send_message(cid, txt, reply_markup=m)

# AUTOMATIC STEP 7 POPUP CHAINS
def start_wizard_openers_step(cid, mid):
    match["striker"] = "Select Striker"
    match["non_striker"] = "Select Non-Striker"
    match["bowler"] = "Select Bowler"
    save_data()
    
    avail = get_available_batsmen(match["batting_team"])
    m = InlineKeyboardMarkup(row_width=2)
    for p in avail:
        m.add(InlineKeyboardButton(f"ðŸ {p}", callback_data=f"wiz_str_{p}"))
    m.add(InlineKeyboardButton("âž• Type Striker", callback_data="wiz_type_striker"))
    txt = f"ðŸ“Œ **Step 7.1:** Select/Type **Opening Striker ({match['batting_team']}):**"
    if mid:
        safe_edit_message(txt, chat_id=cid, message_id=mid, reply_markup=m)
    else:
        safe_send_message(cid, txt, reply_markup=m)

def prompt_non_striker_step(cid, mid=None):
    avail = get_available_batsmen(match["batting_team"])
    m = InlineKeyboardMarkup(row_width=2)
    for p in avail:
        m.add(InlineKeyboardButton(f"ðŸƒ {p}", callback_data=f"wiz_nstr_{p}"))
    m.add(InlineKeyboardButton("âž• Type Non-Striker", callback_data="wiz_type_nonstriker"))
    txt = f"ðŸ‘¤ Striker: **{match['striker']}**\n\nðŸ“Œ **Step 7.2:** Ab **Non-Striker (Runner)** select/type karein:"
    if mid:
        safe_edit_message(txt, chat_id=cid, message_id=mid, reply_markup=m)
    else:
        safe_send_message(cid, txt, reply_markup=m)

def prompt_opening_bowler_step(cid, mid=None):
    m = InlineKeyboardMarkup(row_width=2)
    for p in match["squads"].get(match["bowling_team"], []):
        m.add(InlineKeyboardButton(f"âš¾ {p}", callback_data=f"wiz_bowl_{p}"))
    m.add(InlineKeyboardButton("âž• Type Opening Bowler", callback_data="wiz_type_bowler"))
    txt = f"ðŸ Striker: **{match['striker']}**\nðŸƒ Runner: **{match['non_striker']}**\n\nðŸ“Œ **Step 7.3:** Ab **Opening Bowler ({match['bowling_team']})** select/type karein:"
    if mid:
        safe_edit_message(txt, chat_id=cid, message_id=mid, reply_markup=m)
    else:
        safe_send_message(cid, txt, reply_markup=m)

# ================= UNIFIED MASTER CALLBACK ROUTER =================
@bot.callback_query_handler(func=lambda c: True)
def master_action_handler(c):
    try:
        bot.answer_callback_query(c.id)
    except Exception:
        pass
        
    try:
        uid, dt = c.from_user.id, c.data
        cid = c.message.chat.id
        mid = c.message.message_id

        if dt == "view_summary":
            return safe_send_message(cid, generate_detailed_scorecard_text())

        if dt == "view_h2h_live":
            t1 = match["teams"][0] if len(match.get("teams", [])) > 0 else match["batting_team"]
            t2 = match["teams"][1] if len(match.get("teams", [])) > 1 else match["bowling_team"]
            return safe_send_message(cid, generate_h2h_card_text(t1, t2))

        if dt == "view_matchup_current":
            return safe_send_message(cid, generate_player_vs_bowler_text(match["striker"], match["bowler"]))

        if dt == "view_archives":
            if not match["match_archives"]:
                return safe_send_message(cid, "âš ï¸ Abhi tak koi match archive record mein nahi hai!")
            m = InlineKeyboardMarkup(row_width=1)
            for arc in match["match_archives"][-8:]:
                m.add(InlineKeyboardButton(f"ðŸ“ #{arc['match_id']}: {arc['teams']} ({arc.get('winner', 'No Result')})", callback_data=f"arc_{arc['match_id']}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("ðŸ“œ **MATCH ARCHIVE VAULT:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("arc_"):
            m_id = dt.replace("arc_", "")
            entry = next((a for a in match["match_archives"] if a["match_id"] == m_id), None)
            if entry:
                return safe_send_message(cid, generate_detailed_scorecard_text(entry))

        if dt == "view_mom":
            win_team = match["batting_team"] if match["runs"] >= match["target"] and match["current_inning"] == 2 else match["bowling_team"]
            best_p, max_pts = "None", -999
            for inn_idx in [1, 2]:
                i_data = match["match_innings_data"].get(inn_idx, {})
                t_name = i_data.get("team", "")
                is_winner = (t_name == win_team)
                w_bonus = 25 if is_winner else 0
                for p, bst in i_data.get("batting", {}).items():
                    if p.startswith("Select") or p.startswith("Batsman"): continue
                    pts = (bst["runs"] * 1.5) + (bst["fours"] * 2.5) + (bst["sixes"] * 4.0) + w_bonus
                    if pts > max_pts:
                        max_pts, best_p = pts, p
                for p, b_st in i_data.get("bowling", {}).items():
                    if p.startswith("Select") or p.startswith("Bowler"): continue
                    pts = (b_st["wickets"] * 30) + (b_st.get("maidens", 0) * 15) - (b_st["runs"] * 0.5) + w_bonus
                    if pts > max_pts:
                        max_pts, best_p = pts, p
                        
            mos_p, mos_pts = "None", -999
            for p, st in match["career_db"].items():
                pts = (st["runs"] * 1.5) + (st["fours"] * 2.0) + (st["sixes"] * 4.0) + (st["wickets"] * 30) + (st["catches"] * 15)
                if pts > mos_pts:
                    mos_pts, mos_p = pts, p

            res_txt = (
                f"â­ **MATCH IMPACT LEADER (MoM):** `{clean_txt(best_p)}` (Score: `{max_pts:.1f}` pts)\n"
                f"ðŸ† Calculated on current match performances!\n\n"
                f"ðŸŽ–ï¸ **TOURNAMENT / SERIES MVP (MoS):**\n"
                f"ðŸ‘‰ `{clean_txt(mos_p)}` with `{mos_pts:.1f}` career performance index!"
            )
            return safe_send_message(cid, res_txt)

        if not match["is_practice_mode"] and not is_scorer(uid):
            return safe_send_message(cid, "âš ï¸ Only Official Scorers & Admin can score in Real Mode!")

        # ================= SETUP WIZARD ROUTING =================
        if dt in ["wiz_mode_real", "wiz_mode_practice"]:
            # The Step-1 mode selection is the explicit start of a NEW match.
            # Reset all old match state here so a previous score/innings/toss
            # can never leak into the new setup wizard. Permanent databases
            # and squads are preserved by reset_for_new_match_setup().
            reset_for_new_match_setup()
            match["is_practice_mode"] = (dt == "wiz_mode_practice")
            match["tournament_mode"] = False
            m = InlineKeyboardMarkup(row_width=2)
            for s in match["series_list"]:
                m.add(InlineKeyboardButton(f"ðŸ† {s}", callback_data=f"wiz_set_series_{s}"))
            m.add(InlineKeyboardButton("âœï¸ Type Custom Series Name", callback_data="wiz_type_series_name"))
            return safe_edit_message("ðŸ“Œ **Step 1.1:** Select or Type **Series Name:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("wiz_set_series_"):
            s_name = clean_txt(dt.replace("wiz_set_series_", ""))
            match["series_name"] = s_name
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("âš¡ 1 Match Standalone", callback_data="wiz_series_1"), InlineKeyboardButton("ðŸ† 2-Match Series", callback_data="wiz_series_2"))
            m.add(InlineKeyboardButton("ðŸ† 3-Match Series", callback_data="wiz_series_3"), InlineKeyboardButton("ðŸ† 5-Match Series", callback_data="wiz_series_5"))
            m.add(InlineKeyboardButton("âœï¸ Custom Series Length", callback_data="wiz_series_custom"))
            return safe_edit_message(f"ðŸ† Series: **{s_name}**\n\nðŸ“Œ **Step 1.2:** Select **Series Format:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "wiz_type_series_name":
            match["user_actions"][uid] = "wiz_type_series_name"
            return safe_edit_message("âœï¸ Nayi **Series ka Naam** type karke send karein:", chat_id=cid, message_id=mid)

        if dt == "wiz_mode_tournament":
            # Same clean-start guarantee for tournament mode.
            reset_for_new_match_setup()
            match["tournament_mode"] = True
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("3 Teams", callback_data="tour_teams_3"), InlineKeyboardButton("4 Teams (IPL Style)", callback_data="tour_teams_4"))
            m.add(InlineKeyboardButton("6 Teams", callback_data="tour_teams_6"), InlineKeyboardButton("8 Teams", callback_data="tour_teams_8"))
            m.add(InlineKeyboardButton("âœï¸ Custom Teams Count", callback_data="tour_teams_custom"))
            return safe_edit_message("ðŸŸï¸ **Multi-Team Tournament Mode:**\nTournament mein kitni teams hongi?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("tour_teams_"):
            val = dt.replace("tour_teams_", "")
            if val == "custom":
                match["user_actions"][uid] = "input_tour_custom_teams_count"
                return safe_edit_message("âœï¸ Tournament mein kitni teams hongi number type karein:", chat_id=cid, message_id=mid)
            else:
                match["temp_data"]["tour_teams_needed"] = int(val)
                match["tournament_teams"] = []
                match["user_actions"][uid] = "input_tour_team_name"
                return safe_edit_message(f"âœï¸ Team 1 ka naam type karke send karein (1/{val}):", chat_id=cid, message_id=mid)

        if dt == "wiz_series_custom":
            match["user_actions"][uid] = "input_series_custom_matches"
            return safe_edit_message("âœï¸ Series mein total **kitne matches** honge type karein (e.g. 2, 4, 6):", chat_id=cid, message_id=mid)

        if dt.startswith("wiz_series_"):
            match["series_total_matches"] = int(dt.replace("wiz_series_", ""))
            m = InlineKeyboardMarkup(row_width=2)
            for t in match.get("teams", []):
                m.add(InlineKeyboardButton(f"ðŸ“ {t}", callback_data=f"wiz_t1_{t}"))
            m.add(InlineKeyboardButton("âž• Create Team", callback_data="wiz_create_team"))
            return safe_edit_message("ðŸ“Œ **Step 2:** Select **Team 1** (or Create New):", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "wiz_create_team":
            match["user_actions"][uid] = "wiz_input_team"
            return safe_edit_message("âœï¸ Nayi **Team ka Naam** type karke send karein:", chat_id=cid, message_id=mid)

        if dt.startswith("wiz_t1_"):
            t1 = clean_txt(dt.replace("wiz_t1_", ""))
            match["temp_data"]["wiz_team1"] = t1
            m = InlineKeyboardMarkup(row_width=2)
            for t in match.get("teams", []):
                if t != t1:
                    m.add(InlineKeyboardButton(f"ðŸ“ {t}", callback_data=f"wiz_t2_{t}"))
            m.add(InlineKeyboardButton("âž• Create Team 2", callback_data="wiz_create_team_2"))
            return safe_edit_message(f"ðŸ“Œ **Step 2.2:** Team 1: **{t1}**\nAb **Team 2** select karein:", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "wiz_create_team_2":
            match["user_actions"][uid] = "wiz_input_team_2"
            return safe_edit_message("âœï¸ Dusri **Team ka Naam** type karke send karein:", chat_id=cid, message_id=mid)

        if dt.startswith("wiz_t2_"):
            t2 = clean_txt(dt.replace("wiz_t2_", ""))
            t1 = match["temp_data"].get("wiz_team1", match["teams"][0] if match["teams"] else "Team 1")
            match["teams"] = [t1, t2]
            ensure_team_record(t1)
            ensure_team_record(t2)
            
            # Show live H2H preview before toss
            h2h_txt = generate_h2h_card_text(t1, t2)
            broadcast_commentary(cid, f"âš”ï¸ **UPCOMING CLASH PREVIEW:**\n{h2h_txt}")
            
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("ðŸª™ Auto Random Toss", callback_data="wiz_toss_auto"))
            m.add(InlineKeyboardButton("âœï¸ Manual Toss Selection", callback_data="wiz_toss_manual"))
            return safe_edit_message(f"ðŸ“Œ **Step 3:** Toss Setup for **{t1} vs {t2}**:", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "wiz_toss_auto":
            winner = random.choice(match["teams"])
            dec = random.choice(["bat", "bowl"])
            match["toss_winner"], match["toss_decision"] = winner, dec
            other = [t for t in match["teams"] if t != winner][0]
            if dec == "bat": match["batting_team"], match["bowling_team"] = winner, other
            else: match["bowling_team"], match["batting_team"] = winner, other
            return start_wizard_squad_step(cid, mid)

        if dt == "wiz_toss_manual":
            m = InlineKeyboardMarkup(row_width=2)
            for t in match["teams"]:
                m.add(InlineKeyboardButton(f"ðŸ”´ {t} (Bat)", callback_data=f"wiz_set_bat_{t}"))
            return safe_edit_message("ðŸ“Œ **Step 3.2:** Kaunsi team **Pehle Batting** karegi?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("wiz_set_bat_"):
            b_team = clean_txt(dt.replace("wiz_set_bat_", ""))
            other = [t for t in match["teams"] if t != b_team][0]
            match["batting_team"], match["bowling_team"] = b_team, other
            return start_wizard_squad_step(cid, mid)

        if dt.startswith("wiz_add_p_"):
            team_n = clean_txt(dt.replace("wiz_add_p_", ""))
            match["temp_data"]["target_team"] = team_n
            match["user_actions"][uid] = "input_squad_player"
            return safe_edit_message(f"âœï¸ **{team_n}** ke players ke naam type karein (Comma ',' ya Enter se alag karke ek sath bhejein):", chat_id=cid, message_id=mid)

        if dt == "wiz_ground_step":
            m = InlineKeyboardMarkup(row_width=2)
            for g in match["grounds_list"]:
                m.add(InlineKeyboardButton(f"ðŸŸï¸ {g}", callback_data=f"wiz_set_g_{g}"))
            m.add(InlineKeyboardButton("âœï¸ Type Custom Ground", callback_data="wiz_type_ground"))
            return safe_edit_message("ðŸ“Œ **Step 5:** Select **Match Ground:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("wiz_set_g_"):
            g_name = clean_txt(dt.replace("wiz_set_g_", ""))
            match["ground"] = g_name
            m = InlineKeyboardMarkup(row_width=3)
            m.add(InlineKeyboardButton("âœï¸ Custom Overs", callback_data="wiz_type_overs"))
            for ov in [2, 3, 5, 6, 7, 8, 10, 12, 15, 20]:
                m.add(InlineKeyboardButton(f"{ov} Overs", callback_data=f"wiz_set_ov_{ov}"))
            return safe_edit_message(f"ðŸŸï¸ Ground: **{g_name}**\n\nðŸ“Œ **Step 6.1:** Select **Total Match Overs:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("wiz_set_ov_"):
            ov = int(dt.replace("wiz_set_ov_", ""))
            match["total_match_overs"] = ov
            match["original_match_overs"] = ov
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("10 Wkts (Standard)", callback_data="wiz_set_wlimit_10"))
            m.add(InlineKeyboardButton("11 Wkts (Gully)", callback_data="wiz_set_wlimit_11"))
            m.add(InlineKeyboardButton("14 Wkts (Gully Mega)", callback_data="wiz_set_wlimit_14"))
            m.add(InlineKeyboardButton("âœï¸ Custom Limit", callback_data="wiz_type_wlimit"))
            return safe_edit_message(f"â³ Match Overs: **{ov}.0**\n\nðŸ“Œ **Step 6.2:** Select **Max Wickets Limit:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("wiz_set_wlimit_"):
            w_lim = int(dt.replace("wiz_set_wlimit_", ""))
            match["max_wickets_limit"] = w_lim
            m = InlineKeyboardMarkup(row_width=2)
            m.add(
                InlineKeyboardButton("â±ï¸ Enable Over-Rate Timer", callback_data="wiz_timer_enable"),
                InlineKeyboardButton("âš¡ No Timer (Casual)", callback_data="wiz_timer_disable")
            )
            return safe_edit_message(f"ðŸ“Œ **Step 6.3:** Match Timer / Over-Rate configure karein:", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "wiz_timer_enable":
            match["timer_enabled"] = True
            match["timer_allocated_mins"] = calculate_allocated_time_mins(match["total_match_overs"])
            save_data()
            return start_wizard_openers_step(cid, mid)

        if dt == "wiz_timer_disable":
            match["timer_enabled"] = False
            save_data()
            return start_wizard_openers_step(cid, mid)

        if dt == "wiz_type_wlimit":
            match["user_actions"][uid] = "input_max_wickets_limit"
            return safe_edit_message("âœï¸ Match mein **Kitni Wickets** par all-out hoga type karein (e.g. 10, 11, 14, 16):", chat_id=cid, message_id=mid)

        if dt == "wiz_type_ground":
            match["user_actions"][uid] = "wiz_type_ground"
            return safe_edit_message("âœï¸ Naya Ground Name type karke send karein:", chat_id=cid, message_id=mid)

        if dt == "wiz_type_overs":
            match["user_actions"][uid] = "wiz_type_overs"
            return safe_edit_message("âœï¸ Match kitne overs ka hai number type karein:", chat_id=cid, message_id=mid)

        # STEP 7 TYPE BUTTON HANDLERS (EXPLICIT CALLBACK ROUTING)
        if dt == "wiz_type_striker":
            match["user_actions"][uid] = "wiz_type_striker"
            return safe_edit_message(f"âœï¸ **Striker ({match['batting_team']})** ka naam type karke send karein:", chat_id=cid, message_id=mid)

        if dt == "wiz_type_nonstriker":
            match["user_actions"][uid] = "wiz_type_nonstriker"
            return safe_edit_message(f"âœï¸ **Non-Striker (Runner)** ka naam type karke send karein:", chat_id=cid, message_id=mid)

        if dt == "wiz_type_bowler":
            match["user_actions"][uid] = "wiz_type_bowler"
            return safe_edit_message(f"âœï¸ **Opening Bowler ({match['bowling_team']})** ka naam type karke send karein:", chat_id=cid, message_id=mid)

        if dt.startswith("wiz_str_"):
            p_name = clean_txt(dt.replace("wiz_str_", ""))
            match["striker"] = p_name
            ensure_player(p_name, match["batting_team"])
            ensure_match_player_stat(p_name, match["batting_team"], role="bat")
            save_data()
            return prompt_non_striker_step(cid, mid)

        if dt.startswith("wiz_nstr_"):
            p_name = clean_txt(dt.replace("wiz_nstr_", ""))
            match["non_striker"] = p_name
            ensure_player(p_name, match["batting_team"])
            ensure_match_player_stat(p_name, match["batting_team"], role="bat")
            save_data()
            return prompt_opening_bowler_step(cid, mid)

        if dt.startswith("wiz_bowl_"):
            p_name = clean_txt(dt.replace("wiz_bowl_", ""))
            match["bowler"] = p_name
            match["user_actions"][uid] = None
            ensure_player(p_name, match["bowling_team"])
            ensure_match_player_stat(p_name, match["bowling_team"], role="bowl")
            
            # Reset ball state only if match hasn't started yet
            if match["balls"] == 0:
                match["runs"] = 0
                match["wickets"] = 0
                match["overs"] = 0.0
                match["extras_total"] = 0
                match["extras_wides"] = 0
                match["extras_noballs"] = 0
                match["extras_byes"] = 0
                match["extras_legbyes"] = 0
                match["partnership_runs"] = 0
                match["partnership_balls"] = 0
                match["recent_balls"] = []
                match["current_over_runs"] = 0
                match["fall_of_wickets"] = []
                match["history"] = []
            
            match["match_status"] = "Active"
            match["last_event_ticker"] = f"Innings {match['current_inning']} Live! Striker: {match['striker']}"
            if match.get("timer_enabled") and match.get("timer_start_epoch") is None:
                match["timer_start_epoch"] = time.time()
                match["timer_paused"] = False
                match["timer_total_paused_sec"] = 0
                match["timer_alerts_sent"] = {"midway": False, "warn5": False, "expired": False}
            match["fielding_penalty_active"] = False
            
            save_data()
            try: bot.delete_message(cid, mid)
            except Exception: pass
            msg_obj = safe_send_message(cid, get_large_scoreboard_text(), reply_markup=get_scorer_keyboard(uid))
            try:
                bot.pin_chat_message(cid, msg_obj.message_id)
                match["pinned_message_id"] = msg_obj.message_id
                match["pinned_chat_id"] = cid
                save_data()
            except Exception:
                pass
            return

        # ================= 1-CLICK INSTANT SCORING =================
        if dt.startswith("act_run_"):
            if not validate_on_field_players(cid):
                return
                
            r = int(dt.replace("act_run_", ""))
            save_state_for_undo()
            
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
                
            record_player_matchup(match["striker"], match["bowler"], r, is_out=False)
            
            event_txt = f"âš¡ {r} Runs by {clean_txt(match['striker'])}"
            if r == 4: event_txt = f"ðŸ”¥ FOUR! {clean_txt(match['striker'])} smashes boundary!"
            elif r == 6: event_txt = f"ðŸš€ MAXIMUM! {clean_txt(match['striker'])} launches huge six!"
            match["last_event_ticker"] = event_txt
            
            register_legal_ball(cid, legal=True, ball_tag=str(r), runs_on_ball=r)
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        # CUSTOM OVERTHROW RUNS
        if dt == "menu_custom_runs":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("5 Runs (1+4 Overthrow)", callback_data="exec_cust_5"))
            m.add(InlineKeyboardButton("7 Runs (3+4 Overthrow)", callback_data="exec_cust_7"))
            m.add(InlineKeyboardButton("âœï¸ Type Manual Runs", callback_data="type_custom_runs_val"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("âœï¸ **Select Custom / Overthrow Runs:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("exec_cust_"):
            if not validate_on_field_players(cid):
                return
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
            record_player_matchup(match["striker"], match["bowler"], r, is_out=False)
            match["last_event_ticker"] = f"âš¡ OVERTHROW! {r} Runs scored by {clean_txt(match['striker'])}!"
            register_legal_ball(cid, legal=True, ball_tag=f"OT+{r}", runs_on_ball=r)
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "type_custom_runs_val":
            match["user_actions"][uid] = "input_custom_runs"
            return safe_edit_message("âœï¸ Kitne runs bane type karke send karein:", chat_id=cid, message_id=mid)

        # WIDE & NO BALL
        if dt == "menu_wide":
            m = InlineKeyboardMarkup(row_width=3)
            for r in range(6): m.add(InlineKeyboardButton(f"Wide + {r}", callback_data=f"exec_wide_{r}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("âš¡ **Select Wide Deliveries:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("exec_wide_"):
            if not validate_on_field_players(cid):
                return
            ex = int(dt.replace("exec_wide_", ""))
            tot = 1 + ex
            save_state_for_undo()
            match["runs"] += tot
            match["current_over_runs"] += tot
            match["partnership_runs"] += tot
            match["extras_total"] += tot
            match["extras_wides"] += tot
            match["match_innings_data"][match["current_inning"]]["extras"]["w"] += tot
            match["match_innings_data"][match["current_inning"]]["extras"]["total"] += tot
            ensure_match_player_stat(match["bowler"], match["bowling_team"], role="bowl")
            match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["runs"] += tot
            match["recent_balls"].append(f"Wd+{ex}")
            match["last_event_ticker"] = f"âš¡ Wide Ball (+{tot} Extras)"
            if ex % 2 != 0: match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            save_data()
            if match["current_inning"] == 2 and match["target"] > 0 and match["runs"] >= match["target"]:
                check_match_completion(cid)
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "menu_noball":
            m = InlineKeyboardMarkup(row_width=3)
            for r in range(7): m.add(InlineKeyboardButton(f"NB + {r} Runs", callback_data=f"exec_nb_{r}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("âš ï¸ **Select No Ball Deliveries (+1 Auto):**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("exec_nb_"):
            if not validate_on_field_players(cid):
                return
            bat_r = int(dt.replace("exec_nb_", ""))
            tot = 1 + bat_r
            save_state_for_undo()
            match["runs"] += tot
            match["current_over_runs"] += tot
            match["extras_total"] += 1
            match["extras_noballs"] += 1
            match["partnership_runs"] += tot
            match["match_innings_data"][match["current_inning"]]["extras"]["nb"] += 1
            match["match_innings_data"][match["current_inning"]]["extras"]["total"] += 1
            
            ensure_match_player_stat(match["striker"], match["batting_team"], role="bat")
            ensure_match_player_stat(match["bowler"], match["bowling_team"], role="bowl")
            
            st_stat = match["match_innings_data"][match["current_inning"]]["batting"][match["striker"]]
            st_stat["runs"] += bat_r
            if bat_r == 4: st_stat["fours"] += 1
            if bat_r == 6: st_stat["sixes"] += 1
            
            match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["runs"] += tot
            record_player_matchup(match["striker"], match["bowler"], bat_r, is_out=False)
            match["recent_balls"].append(f"NB+{bat_r}")
            if bat_r % 2 != 0: match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            save_data()
            
            m = InlineKeyboardMarkup(row_width=1)
            m.add(
                InlineKeyboardButton("ðŸ”¥ Enable Free Hit Next Ball", callback_data="nb_fh_enable"),
                InlineKeyboardButton("âš¡ Standard Delivery (No Free Hit)", callback_data="nb_fh_disable")
            )
            return safe_edit_message(f"âš ï¸ **NO BALL (+{tot} Runs Recorded)!**\nFree Hit activate karni hai?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "nb_fh_enable":
            match["is_free_hit_active"] = True
            match["last_event_ticker"] = "âš ï¸ NO BALL! Free Hit is ACTIVE on next delivery!"
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "nb_fh_disable":
            match["is_free_hit_active"] = False
            match["last_event_ticker"] = "âš ï¸ NO BALL! Standard delivery will follow."
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        # BYES & LEG BYES
        if dt == "menu_byes":
            m = InlineKeyboardMarkup(row_width=3)
            m.add(InlineKeyboardButton("Bye +1", callback_data="exec_bye_1"), InlineKeyboardButton("Bye +2", callback_data="exec_bye_2"), InlineKeyboardButton("Bye +4", callback_data="exec_bye_4"))
            m.add(InlineKeyboardButton("Leg Bye +1", callback_data="exec_lb_1"), InlineKeyboardButton("Leg Bye +2", callback_data="exec_lb_2"), InlineKeyboardButton("Leg Bye +4", callback_data="exec_lb_4"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("ðŸƒ **Dynamic Byes / Leg Byes Menu:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("exec_bye_") or dt.startswith("exec_lb_"):
            if not validate_on_field_players(cid):
                return
            parts = dt.split("_")
            b_val, is_bye = int(parts[2]), (parts[1] == "bye")
            save_state_for_undo()
            match["runs"] += b_val
            match["current_over_runs"] += b_val
            match["partnership_runs"] += b_val
            match["extras_total"] += b_val
            if is_bye:
                match["extras_byes"] += b_val
                match["match_innings_data"][match["current_inning"]]["extras"]["b"] += b_val
            else:
                match["extras_legbyes"] += b_val
                match["match_innings_data"][match["current_inning"]]["extras"]["lb"] += b_val
            match["match_innings_data"][match["current_inning"]]["extras"]["total"] += b_val
            
            ensure_match_player_stat(match["striker"], match["batting_team"], role="bat")
            match["match_innings_data"][match["current_inning"]]["batting"][match["striker"]]["balls"] += 1
            if match["striker"] in match["career_db"]: match["career_db"][match["striker"]]["balls"] += 1
            
            match["last_event_ticker"] = f"ðŸƒ {'Byes' if is_bye else 'Leg Byes'} (+{b_val} runs)"
            register_legal_ball(cid, legal=True, ball_tag=f"{'B' if is_bye else 'LB'}+{b_val}", runs_on_ball=b_val)
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        # WICKET ENGINE
        if dt == "menu_wicket":
            if not validate_on_field_players(cid):
                return
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("ðŸ”´ Bowled", callback_data="wkt_bowled"), InlineKeyboardButton("ðŸŸ¡ Caught Out", callback_data="wkt_caught_menu"))
            m.add(InlineKeyboardButton("ðŸŸ¢ Run Out (Striker)", callback_data="wkt_runout_str"), InlineKeyboardButton("ðŸŸ¢ Run Out (Runner)", callback_data="wkt_runout_nstr"))
            m.add(InlineKeyboardButton("ðŸ”µ Stumped", callback_data="wkt_stumped"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("âŒ **Select Dismissal Type:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt in ["wkt_bowled", "wkt_stumped"]:
            if match["is_free_hit_active"]:
                return safe_send_message(cid, "âš ï¸ Free Hit Active! Only Run Out allowed!")
            return process_wicket(cid, mid, dt.replace("wkt_", "").capitalize(), uid, target_batter="striker")

        if dt == "wkt_runout_str":
            return process_wicket(cid, mid, "Run Out", uid, target_batter="striker")

        if dt == "wkt_runout_nstr":
            return process_wicket(cid, mid, "Run Out", uid, target_batter="non_striker")

        if dt == "wkt_caught_menu":
            if match["is_free_hit_active"]:
                return safe_send_message(cid, "âš ï¸ Free Hit Active! Catch out not allowed!")
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("âš¡ Quick Catch (Skip Fielder)", callback_data="wkt_caught_quick"))
            for fld in match["squads"].get(match["bowling_team"], []):
                m.add(InlineKeyboardButton(f"ðŸ™Œ {fld}", callback_data=f"catch_by_{fld}"))
            m.add(InlineKeyboardButton("âž• Type Fielder Name", callback_data="type_catch_fielder"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_wicket"))
            return safe_edit_message(f"ðŸ™Œ **Who took the catch ({match['bowling_team']})?**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "wkt_caught_quick":
            return process_wicket(cid, mid, "Caught", uid, target_batter="striker")

        if dt.startswith("catch_by_"):
            f_name = clean_txt(dt.replace("catch_by_", ""))
            ensure_player(f_name, match["bowling_team"])
            if f_name in match["career_db"]: match["career_db"][f_name]["catches"] += 1
            return process_wicket(cid, mid, f"c {f_name} b {match['bowler']}", uid, target_batter="striker")

        if dt == "type_catch_fielder":
            match["user_actions"][uid] = "type_catch_fielder"
            return safe_edit_message(f"âœï¸ Catch lene wale **Fielder** ka naam type karke send karein:", chat_id=cid, message_id=mid)

        if dt == "act_drop_catch":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("âš¡ Quick Log (Skip Fielder)", callback_data="drop_by_general"))
            for fld in match["squads"].get(match["bowling_team"], []):
                m.add(InlineKeyboardButton(f"âŒ {fld}", callback_data=f"drop_by_{fld}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("ðŸ˜± **Who dropped the catch?**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("drop_by_"):
            f_name = clean_txt(dt.replace("drop_by_", ""))
            if f_name != "general":
                ensure_player(f_name, match["bowling_team"])
                if f_name in match["career_db"]: match["career_db"][f_name]["drops"] += 1
            match["last_event_ticker"] = f"ðŸ˜± CATCH DROPPED off {clean_txt(match['bowler'])}!"
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        # INJURY SPLIT
        if dt == "pop_injury_split":
            m = InlineKeyboardMarkup(row_width=1)
            m.add(
                InlineKeyboardButton("ðŸš‘ Retire Striker (Retired Hurt)", callback_data="retire_str_hurt"),
                InlineKeyboardButton("ðŸš‘ Retire Runner (Retired Hurt)", callback_data="retire_nstr_hurt"),
                InlineKeyboardButton("ðŸš‘ Change Bowler (Injured)", callback_data="pop_set_bowler"),
                InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main")
            )
            return safe_edit_message("ðŸš‘ **Injury Split Options:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt in ["retire_str_hurt", "retire_nstr_hurt"]:
            is_str = (dt == "retire_str_hurt")
            p_ret = match["striker"] if is_str else match["non_striker"]
            ensure_match_player_stat(p_ret, match["batting_team"], role="bat")
            match["match_innings_data"][match["current_inning"]]["batting"][p_ret]["status"] = "Retired Hurt"
            if is_str: match["striker"] = "Select Striker"
            else: match["non_striker"] = "Select Non-Striker"
            save_data()
            avail = get_available_batsmen(match["batting_team"])
            m = InlineKeyboardMarkup(row_width=2)
            for p in avail:
                m.add(InlineKeyboardButton(f"ðŸ {p}", callback_data=f"replace_str_{p}" if is_str else f"replace_nstr_{p}"))
            m.add(InlineKeyboardButton("âž• Type Next Batsman", callback_data="type_replace_str" if is_str else "type_replace_nstr"))
            return safe_edit_message(f"ðŸš‘ **{p_ret}** marked Retired Hurt! Select Replacement:", chat_id=cid, message_id=mid, reply_markup=m)

        # ISOLATED WICKET REPLACEMENT ACTIONS
        if dt.startswith("replace_str_"):
            p_name = clean_txt(dt.replace("replace_str_", ""))
            match["striker"] = p_name
            ensure_player(p_name, match["batting_team"])
            ensure_match_player_stat(p_name, match["batting_team"], role="bat")
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt.startswith("replace_nstr_"):
            p_name = clean_txt(dt.replace("replace_nstr_", ""))
            match["non_striker"] = p_name
            ensure_player(p_name, match["batting_team"])
            ensure_match_player_stat(p_name, match["batting_team"], role="bat")
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt in ["type_replace_str", "type_replace_nstr"]:
            match["user_actions"][uid] = dt
            role_target = "Striker" if dt == "type_replace_str" else "Non-Striker (Runner)"
            return safe_edit_message(f"âœï¸ Naye **{role_target}** ka naam type karke send karein:", chat_id=cid, message_id=mid)

        # BATSMAN / BOWLER REPLACEMENTS (FILTERED)
        if dt == "pop_set_striker":
            avail = get_available_batsmen(match["batting_team"])
            m = InlineKeyboardMarkup(row_width=2)
            for p in avail:
                m.add(InlineKeyboardButton(f"ðŸ {p}", callback_data=f"sel_str_{p}"))
            m.add(InlineKeyboardButton("âž• Type New Batsman", callback_data="type_replace_str"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("ðŸ‘¤ **Select Striker:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("sel_str_"):
            p_name = clean_txt(dt.replace("sel_str_", ""))
            match["striker"] = p_name
            ensure_player(p_name, match["batting_team"])
            ensure_match_player_stat(p_name, match["batting_team"], role="bat")
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "pop_set_nonstriker":
            avail = get_available_batsmen(match["batting_team"])
            m = InlineKeyboardMarkup(row_width=2)
            for p in avail:
                m.add(InlineKeyboardButton(f"ðŸƒ {p}", callback_data=f"sel_nonstr_{p}"))
            m.add(InlineKeyboardButton("âž• Type New Non-Striker", callback_data="type_replace_nstr"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("ðŸƒ **Select Non-Striker (Runner):**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("sel_nonstr_"):
            p_name = clean_txt(dt.replace("sel_nonstr_", ""))
            match["non_striker"] = p_name
            ensure_player(p_name, match["batting_team"])
            ensure_match_player_stat(p_name, match["batting_team"], role="bat")
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "pop_set_bowler":
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["bowling_team"], []):
                m.add(InlineKeyboardButton(f"âš¾ {p}", callback_data=f"sel_bowl_{p}"))
            m.add(InlineKeyboardButton("âž• Type New Bowler", callback_data="wiz_type_bowler"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("âš¾ **Select Bowler:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("sel_bowl_"):
            p_name = clean_txt(dt.replace("sel_bowl_", ""))
            match["bowler"] = p_name
            ensure_player(p_name, match["bowling_team"])
            ensure_match_player_stat(p_name, match["bowling_team"], role="bowl")
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        # TIMER & OVER-RATE PENALTY DASHBOARD
        if dt == "menu_timer_control":
            t_info = get_timer_status_info()
            m = InlineKeyboardMarkup(row_width=2)
            if not match.get("timer_enabled"):
                m.add(InlineKeyboardButton("â±ï¸ Activate Timer Now", callback_data="tm_start_live"))
            else:
                if match.get("timer_paused"):
                    m.add(InlineKeyboardButton("â–¶ï¸ Resume Timer", callback_data="tm_resume"))
                else:
                    m.add(InlineKeyboardButton("â¸ï¸ Pause (Injury/Dead)", callback_data="tm_pause"))
                m.add(
                    InlineKeyboardButton("âž• Add +2 Mins", callback_data="tm_add_2"),
                    InlineKeyboardButton("âž• Add +5 Mins", callback_data="tm_add_5")
                )
                m.add(
                    InlineKeyboardButton("ðŸ”´ +5 Runs Penalty", callback_data="tm_pen_runs"),
                    InlineKeyboardButton("ðŸ›¡ï¸ Field Restriction", callback_data="tm_pen_field")
                )
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            
            status_txt = "âŒ Timer is OFF."
            if t_info:
                status_txt = f"â±ï¸ Allocated: `{t_info['total_mins']}m` â”‚ Remaining: `{t_info['rem_mins']}m {t_info['rem_sec']}s`\nStatus: `{'PAUSED' if t_info['paused'] else ('EXPIRED' if t_info['expired'] else 'RUNNING')}`"
                
            return safe_edit_message(f"â±ï¸ **MATCH OVER-RATE TIMER & PENALTIES:**\n\n{status_txt}", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "tm_start_live":
            match["timer_enabled"] = True
            match["timer_allocated_mins"] = calculate_allocated_time_mins(match["total_match_overs"])
            match["timer_start_epoch"] = time.time()
            match["timer_paused"] = False
            match["timer_total_paused_sec"] = 0
            match["timer_alerts_sent"] = {"midway": False, "warn5": False, "expired": False}
            save_data()
            return safe_edit_message(f"âœ… Timer activated! `{match['timer_allocated_mins']} Mins` allocated.\n\n{get_large_scoreboard_text()}", chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "tm_pause":
            if match.get("timer_enabled") and not match.get("timer_paused"):
                match["timer_paused"] = True
                match["timer_pause_epoch"] = time.time()
                save_data()
            return safe_edit_message(f"â¸ï¸ Timer Paused for Injury/Dead Time!\n\n{get_large_scoreboard_text()}", chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "tm_resume":
            if match.get("timer_enabled") and match.get("timer_paused"):
                pause_duration = time.time() - match.get("timer_pause_epoch", time.time())
                match["timer_total_paused_sec"] += pause_duration
                match["timer_paused"] = False
                save_data()
            return safe_edit_message(f"â–¶ï¸ Timer Resumed!\n\n{get_large_scoreboard_text()}", chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt.startswith("tm_add_"):
            extra = int(dt.replace("tm_add_", ""))
            match["timer_allocated_mins"] += extra
            save_data()
            return safe_edit_message(f"âœ… Added +{extra} Mins Extra Time!\n\n{get_large_scoreboard_text()}", chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "tm_pen_runs":
            save_state_for_undo()
            match["runs"] += 5
            match["extras_total"] += 5
            match["match_innings_data"][match["current_inning"]]["extras"]["total"] += 5
            match["last_event_ticker"] = "âš ï¸ +5 RUNS PENALTY awarded for Slow Over Rate!"
            save_data()
            broadcast_commentary(cid, "âš ï¸ **PENALTY ANNOUNCEMENT:** +5 Penalty Runs awarded to Batting Team for Slow Over-Rate!")
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "tm_pen_field":
            match["fielding_penalty_active"] = True
            match["last_event_ticker"] = "âš ï¸ SLOW OVER RATE: Only 4 fielders allowed outside 30-yd circle!"
            save_data()
            broadcast_commentary(cid, "âš ï¸ **FIELDING RESTRICTION PENALTY:** Slow Over-Rate penalty applied! Max 4 fielders allowed outside 30-yard circle.")
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        # SET WK & CAPTAIN HANDLER
        if dt == "menu_set_wk_cap":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("ðŸ§¤ Assign WK", callback_data="pop_assign_wk"), InlineKeyboardButton("ðŸ‘‘ Assign Captain", callback_data="pop_assign_cap"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("ðŸ§¤ðŸ‘‘ **Assign Wicketkeeper & Captain:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "pop_assign_wk":
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["bowling_team"], []) + match["squads"].get(match["batting_team"], []):
                m.add(InlineKeyboardButton(f"ðŸ§¤ {p}", callback_data=f"set_wk_{p}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_set_wk_cap"))
            return safe_edit_message("ðŸ§¤ Wicketkeeper kise banana hai?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("set_wk_"):
            p = clean_txt(dt.replace("set_wk_", ""))
            match["wicketkeeper"] = p
            save_data()
            return safe_edit_message(f"âœ… Wicketkeeper assigned to **{p}**!\n\n{get_large_scoreboard_text()}", chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "pop_assign_cap":
            m = InlineKeyboardMarkup(row_width=2)
            for p in match["squads"].get(match["batting_team"], []):
                m.add(InlineKeyboardButton(f"ðŸ‘‘ {p}", callback_data=f"set_cap_{p}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_set_wk_cap"))
            return safe_edit_message("ðŸ‘‘ Batting Captain kise banana hai?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("set_cap_"):
            p = clean_txt(dt.replace("set_cap_", ""))
            match["captain"] = p
            save_data()
            return safe_edit_message(f"âœ… Captain assigned to **{p}**!\n\n{get_large_scoreboard_text()}", chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        # FAST OPPONENT ENTRY
        if dt == "menu_quick_innings":
            m = InlineKeyboardMarkup(row_width=3)
            for ov in [2, 3, 5, 6, 7, 8, 10, 12, 15, 20]:
                m.add(InlineKeyboardButton(f"{ov} Overs", callback_data=f"q_ov_{ov}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("âš¡ **Fast Opponent Entry:** Overs kitne khele?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("q_ov_"):
            match["temp_data"]["q_overs"] = int(dt.replace("q_ov_", ""))
            m = InlineKeyboardMarkup(row_width=4)
            for w in range(min(15, match["max_wickets_limit"] + 1)):
                m.add(InlineKeyboardButton(f"{w} Wkts", callback_data=f"q_wkt_{w}"))
            return safe_edit_message("âš¡ **Fast Opponent Entry:** Wickets kitni giri?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("q_wkt_"):
            match["temp_data"]["q_wkts"] = int(dt.replace("q_wkt_", ""))
            match["user_actions"][uid] = "input_quick_runs"
            return safe_edit_message("âœï¸ Opponent ke total **Runs** type karke bhejein:", chat_id=cid, message_id=mid)

        # EXTEND SERIES MATCHES
        if dt == "menu_extend_series":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("âž• Add +1 Match", callback_data="ext_plus_1"), InlineKeyboardButton("âž• Add +2 Matches", callback_data="ext_plus_2"))
            m.add(InlineKeyboardButton("âœï¸ Manual Total Matches", callback_data="ext_set_custom"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message(f"ðŸ† **Extend Series Matches:**\nCurrent: Match {match['series_current_match_num']}/{match['series_total_matches']}", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("ext_plus_"):
            p_val = int(dt.replace("ext_plus_", ""))
            match["series_total_matches"] += p_val
            save_data()
            return safe_edit_message(f"âœ… Series matches extended! Total matches: **{match['series_total_matches']}**\n\n{get_large_scoreboard_text()}", chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "ext_set_custom":
            match["user_actions"][uid] = "input_series_custom_matches"
            return safe_edit_message("âœï¸ Naya Total Matches count type karein:", chat_id=cid, message_id=mid)

        # SQUAD & TEAM MANAGEMENT
        if dt == "menu_squads_master":
            m = InlineKeyboardMarkup(row_width=2)
            for t in match.get("teams", []):
                m.add(InlineKeyboardButton(f"ðŸ‘¥ {t} Squad", callback_data=f"sq_view_{t}"))
            m.add(InlineKeyboardButton("âž• Bulk Add Players", callback_data="menu_bulk_add_select"))
            m.add(InlineKeyboardButton("âž• Add Single Player", callback_data="menu_single_add_select"))
            m.add(InlineKeyboardButton("ðŸ”„ Transfer Player", callback_data="menu_p_transfer_select"))
            m.add(InlineKeyboardButton("âœï¸ Rename Player", callback_data="menu_p_rename_select"))
            m.add(InlineKeyboardButton("ðŸ—‘ï¸ Remove Player", callback_data="menu_p_remove_select"))
            m.add(InlineKeyboardButton("ðŸ“Š View Team Standings", callback_data="view_team_ledger"))
            m.add(InlineKeyboardButton("âž• Create New Team", callback_data="wiz_create_team"))
            m.add(InlineKeyboardButton("âœï¸ Rename Team", callback_data="menu_rename_team"))
            m.add(InlineKeyboardButton("ðŸ—‘ï¸ Delete Team", callback_data="menu_delete_team"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("ðŸ‘¥ **Squad & Teams Master Control:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "view_team_ledger":
            out = "ðŸ“Š **PERMANENT TEAM STANDINGS & RECORDS:**\nâ”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”\n"
            if not match.get("team_records"):
                out += "Abhi tak koi team records save nahi hain!"
            else:
                for t, rec in match["team_records"].items():
                    win_pct = (rec["won"] / rec["played"] * 100) if rec["played"] > 0 else 0.0
                    out += f"â€¢ **{clean_txt(t)}** â–¶ P: `{rec['played']}` â”‚ W: `{rec['won']}` â”‚ L: `{rec['lost']}` â”‚ NR: `{rec.get('no_result', 0)}` â”‚ Win%: `{win_pct:.1f}%`\n"
            m = InlineKeyboardMarkup(row_width=1)
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_squads_master"))
            return safe_edit_message(out, chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "menu_bulk_add_select":
            m = InlineKeyboardMarkup(row_width=2)
            for t in match.get("teams", []):
                m.add(InlineKeyboardButton(f"âž• {t}", callback_data=f"wiz_add_p_{t}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_squads_master"))
            return safe_edit_message("ðŸ‘¥ Kaunsi team mein bulk players add karne hain?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "menu_single_add_select":
            m = InlineKeyboardMarkup(row_width=2)
            for t in match.get("teams", []):
                m.add(InlineKeyboardButton(f"âž• {t}", callback_data=f"single_p_add_{t}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_squads_master"))
            return safe_edit_message("ðŸ‘¥ Kaunsi team mein naya player add karna hai?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("single_p_add_"):
            team_n = clean_txt(dt.replace("single_p_add_", ""))
            match["temp_data"]["target_team"] = team_n
            match["user_actions"][uid] = "input_single_player"
            return safe_edit_message(f"âœï¸ **{team_n}** ke single player ka naam type karke send karein:", chat_id=cid, message_id=mid)

        # PLAYER TRANSFER FLOW
        if dt == "menu_p_transfer_select":
            m = InlineKeyboardMarkup(row_width=2)
            for t, p_list in match.get("squads", {}).items():
                for p in p_list:
                    m.add(InlineKeyboardButton(f"ðŸ”„ {p} ({t})", callback_data=f"trf_sel_{t}_{p}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_squads_master"))
            return safe_edit_message("ðŸ”„ Kis player ko dusri team mein transfer karna hai?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("trf_sel_"):
            parts = dt.split("_", 3)
            from_t, p_name = parts[2], parts[3]
            m = InlineKeyboardMarkup(row_width=2)
            for t in match.get("teams", []):
                if t != from_t:
                    m.add(InlineKeyboardButton(f"ðŸ‘‰ Transfer to {t}", callback_data=f"trf_exec_{from_t}_{t}_{p_name}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_p_transfer_select"))
            return safe_edit_message(f"ðŸ”„ Player **{p_name}** ({from_t}) ko kaunsi team mein bhejna hai?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("trf_exec_"):
            parts = dt.split("_", 4)
            from_t, to_t, p_name = parts[2], parts[3], parts[4]
            if from_t in match.get("squads", {}) and p_name in match["squads"][from_t]:
                match["squads"][from_t].remove(p_name)
            if to_t not in match.get("squads", {}): match["squads"][to_t] = []
            if p_name not in match["squads"][to_t]: match["squads"][to_t].append(p_name)
            if p_name in match.get("career_db", {}): match["career_db"][p_name]["team"] = to_t
            save_data()
            return safe_edit_message(f"âœ… Player **{p_name}** successfully transferred to **{to_t}**!", chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "menu_p_rename_select":
            m = InlineKeyboardMarkup(row_width=2)
            for t, p_list in match.get("squads", {}).items():
                for p in p_list:
                    m.add(InlineKeyboardButton(f"âœï¸ {p} ({t})", callback_data=f"ren_p_{t}_{p}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_squads_master"))
            return safe_edit_message("âœï¸ Kis player ka naam rename karna hai?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("ren_p_"):
            parts = dt.split("_", 3)
            t_name, p_name = parts[2], parts[3]
            match["temp_data"]["rename_p_team"] = t_name
            match["temp_data"]["rename_p_old"] = p_name
            match["user_actions"][uid] = "input_player_rename_val"
            return safe_edit_message(f"âœï¸ **{p_name}** ka naya naam type karke send karein:", chat_id=cid, message_id=mid)

        if dt == "menu_p_remove_select":
            m = InlineKeyboardMarkup(row_width=2)
            for t, p_list in match.get("squads", {}).items():
                for p in p_list:
                    m.add(InlineKeyboardButton(f"ðŸ—‘ï¸ {p} ({t})", callback_data=f"del_p_{t}_{p}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_squads_master"))
            return safe_edit_message("ðŸ—‘ï¸ Kaunsa player squad se hatana hai?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("del_p_"):
            parts = dt.split("_", 3)
            t_name, p_name = parts[2], parts[3]
            if t_name in match.get("squads", {}) and p_name in match["squads"][t_name]:
                match["squads"][t_name].remove(p_name)
            save_data()
            return safe_edit_message(f"âœ… Player **{p_name}** deleted from {t_name}!", chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "menu_rename_team":
            m = InlineKeyboardMarkup(row_width=2)
            for t in match.get("teams", []):
                m.add(InlineKeyboardButton(f"âœï¸ {t}", callback_data=f"ren_t_{t}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_squads_master"))
            return safe_edit_message("âœï¸ Kis team ka naam rename karna hai?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("ren_t_"):
            t_name = clean_txt(dt.replace("ren_t_", ""))
            match["temp_data"]["rename_target_team"] = t_name
            match["user_actions"][uid] = "input_rename_team_val"
            return safe_edit_message(f"âœï¸ **{t_name}** ka naya naam type karke send karein:", chat_id=cid, message_id=mid)

        if dt == "menu_delete_team":
            m = InlineKeyboardMarkup(row_width=2)
            for t in match.get("teams", []):
                m.add(InlineKeyboardButton(f"ðŸ—‘ï¸ {t}", callback_data=f"del_t_{t}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_squads_master"))
            return safe_edit_message("ðŸ—‘ï¸ Kaunsi team delete karni hai?", chat_id=cid, message_id=mid, reply_markup=m)

        if dt.startswith("del_t_"):
            t_name = clean_txt(dt.replace("del_t_", ""))
            if t_name in match.get("teams", []): match["teams"].remove(t_name)
            if t_name in match.get("squads", {}): del match["squads"][t_name]
            save_data()
            return safe_edit_message(f"âœ… Team **{t_name}** deleted successfully!", chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt.startswith("sq_view_"):
            t_name = clean_txt(dt.replace("sq_view_", ""))
            p_list = match["squads"].get(t_name, [])
            p_txt = "\n".join([f"â€¢ {clean_txt(p)}" for p in p_list]) if p_list else "Koi player add nahi hai!"
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton(f"âž• Add Player to {t_name}", callback_data=f"wiz_add_p_{t_name}"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="menu_squads_master"))
            return safe_edit_message(f"ðŸ‘¥ **Squad: {t_name}**\n\n{p_txt}", chat_id=cid, message_id=mid, reply_markup=m)

        # SCORER MANAGEMENT
        if dt == "menu_scorers_admin":
            if not is_admin(uid): return safe_send_message(cid, "âš ï¸ Admin only!")
            m = InlineKeyboardMarkup(row_width=1)
            m.add(
                InlineKeyboardButton("âž• Add New Official Scorer", callback_data="pop_add_scorer"),
                InlineKeyboardButton("ðŸ“‹ View Active Scorers", callback_data="pop_view_scorers"),
                InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main")
            )
            return safe_edit_message("ðŸ›¡ï¸ **Official Scorer Management:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "pop_add_scorer":
            match["user_actions"][uid] = "input_add_scorer"
            return safe_edit_message("âœï¸ Naye Scorer ki **Telegram User ID** type karke bhejein:", chat_id=cid, message_id=mid)

        if dt == "pop_view_scorers":
            s_list = "\n".join([f"â€¢ `{s}`" for s in AUTHORIZED_SCORERS])
            return safe_send_message(cid, f"ðŸ“‹ **CURRENT AUTHORIZED SCORERS:**\n{s_list}")

        # EDIT MATCH AUDIT PANEL
        if dt == "menu_edit_match":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("ðŸ Edit Total Runs", callback_data="edit_tot_runs"))
            m.add(InlineKeyboardButton("âŒ Edit Total Wickets", callback_data="edit_tot_wkts"))
            m.add(InlineKeyboardButton("ðŸŽ¯ Edit Target", callback_data="edit_tot_target"))
            m.add(InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main"))
            return safe_edit_message("âœï¸ **Live Match Data Correction:**", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "edit_tot_runs":
            match["user_actions"][uid] = "input_edit_runs"
            return safe_edit_message("âœï¸ Sahi **Total Runs** type karke send karein:", chat_id=cid, message_id=mid)

        if dt == "edit_tot_wkts":
            match["user_actions"][uid] = "input_edit_wkts"
            return safe_edit_message("âœï¸ Sahi **Total Wickets** type karke send karein:", chat_id=cid, message_id=mid)

        if dt == "edit_tot_target":
            match["user_actions"][uid] = "input_edit_target"
            return safe_edit_message("âœï¸ Naya **Target** type karke send karein:", chat_id=cid, message_id=mid)

        # DLS INTERRUPTIONS ENGINE
        if dt == "menu_dls_reduction":
            m = InlineKeyboardMarkup(row_width=1)
            m.add(
                InlineKeyboardButton("ðŸŒ§ï¸ Inning 1 Rain (Overs Reduced)", callback_data="dls_inn1_cut"),
                InlineKeyboardButton("ðŸŒ§ï¸ Inning 2 Rain / Target Revision", callback_data="dls_inn2_cut"),
                InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main")
            )
            return safe_edit_message("ðŸŒ§ï¸ **DLS TARGET ENGINE:**\nKab barish hui hai select karein:", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "dls_inn1_cut":
            match["user_actions"][uid] = "input_dls_inn1_revised"
            return safe_edit_message(f"ðŸŒ§ï¸ **Inning 1 Interruption:** Match originally {match['original_match_overs']} overs ka tha.\nAb revised **Total Overs** kitne hue? (e.g. 2, 5):", chat_id=cid, message_id=mid)

        if dt == "dls_inn2_cut":
            match["user_actions"][uid] = "input_dls_inn2_revised"
            return safe_edit_message("ðŸŒ§ï¸ **Inning 2 Target Revision:** 2nd Inning ab total kitne overs ki hogi? (e.g. 5):", chat_id=cid, message_id=mid)

        # ABANDON & CANCEL (NO RESULT / DISPUTE)
        if dt == "menu_abandon_match":
            m = InlineKeyboardMarkup(row_width=1)
            m.add(
                InlineKeyboardButton("ðŸŒ§ï¸ Abandon Match (Rain / Wet Outfield - No Result)", callback_data="exec_abandon_rain"),
                InlineKeyboardButton("ðŸ›‘ Cancel Match (Lafda / Dispute - Null & Void)", callback_data="exec_cancel_dispute"),
                InlineKeyboardButton("â¬…ï¸ Back", callback_data="back_main")
            )
            return safe_edit_message("ðŸ›‘ **MATCH TERMINATION CONTROLS:**\n\nâ€¢ **Rain Abandon:** Scorecard archive hoga, team ledger me No-Result (1 pt) milega, stats safe rahenge.\nâ€¢ **Dispute/Lafda:** Match null & void ho jayega aur table me count nahi hoga.", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "exec_abandon_rain":
            match["match_status"] = "Abandoned"
            t1 = match["teams"][0] if len(match.get("teams", [])) > 0 else match["batting_team"]
            t2 = match["teams"][1] if len(match.get("teams", [])) > 1 else match["bowling_team"]
            ensure_team_record(t1)
            ensure_team_record(t2)
            match["team_records"][t1]["played"] += 1
            match["team_records"][t1]["no_result"] += 1
            match["team_records"][t2]["played"] += 1
            match["team_records"][t2]["no_result"] += 1
            
            record_h2h_result(t1, t2, tied=False, no_result=True)
            match["last_event_ticker"] = "ðŸŒ§ï¸ Match Abandoned due to Rain/Bad Weather (No Result)."
            archive_match("Abandoned (Rain)", "No Result")
            save_data()
            broadcast_commentary(cid, "ðŸŒ§ï¸ **MATCH CALLED OFF!** Match has been officially **Abandoned due to Rain**. Shared points awarded.")
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "exec_cancel_dispute":
            match["match_status"] = "Cancelled"
            match["last_event_ticker"] = "ðŸ›‘ Match Cancelled & Voided due to Dispute/Interruption."
            save_data()
            broadcast_commentary(cid, "ðŸ›‘ **MATCH CANCELLED!** Match is voided due to dispute/unavoidable issues. No stats recorded in table.")
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        # SAFE UNDO & RESTORATION
        if dt == "act_undo":
            if not match["history"]:
                return safe_send_message(cid, "âš ï¸ Undo karne ke liye koi purana state nahi hai!")
            hist_entry = match["history"].pop()
            match.update(hist_entry["match_state"])
            match["career_db"] = hist_entry["career_db"]
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "act_swap_strike":
            match["striker"], match["non_striker"] = match["non_striker"], match["striker"]
            match["last_event_ticker"] = f"ðŸ”„ Strike swapped manually to {clean_txt(match['striker'])}"
            save_data()
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

        if dt == "act_switch_innings":
            if match["current_inning"] == 1:
                match["match_innings_data"][1]["final_score"] = match["runs"]
                match["match_innings_data"][1]["final_wickets"] = match["wickets"]
                match["match_innings_data"][1]["final_overs"] = match["overs"]
                
                # If target wasn't set by DLS, standard target is runs + 1
                if match["target"] == 0:
                    match["target"] = max(1, match["runs"] + 1)
                    
                match["current_inning"] = 2
                match["match_status"] = "Active"
                other = [t for t in match["teams"] if t != match["batting_team"]]
                next_bat = other[0] if other else match["bowling_team"]
                match["bowling_team"], match["batting_team"] = match["batting_team"], next_bat
                match.update({
                    "runs": 0, "wickets": 0, "overs": 0.0, "balls": 0,
                    "extras_total": 0, "extras_wides": 0, "extras_noballs": 0, "extras_byes": 0, "extras_legbyes": 0,
                    "partnership_runs": 0, "partnership_balls": 0, "recent_balls": [], "current_over_runs": 0,
                    "striker": "Select Striker", "non_striker": "Select Non-Striker", "bowler": "Select Bowler",
                    "last_bowler": None, "last_event_ticker": f"Innings 2 Started! Target: {match['target']}"
                })
                save_data()
                return start_wizard_openers_step(cid, mid)
            else:
                # If already in Inning 2, simply ensure openers selection prompt
                return start_wizard_openers_step(cid, mid)

        # SOFT RESET (RESTART SAME MATCH)
        if dt == "act_reset_stats_confirm":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("âš ï¸ Yes, Reset", callback_data="act_reset_stats_exec"), InlineKeyboardButton("âŒ Cancel", callback_data="back_main"))
            return safe_edit_message("âš ï¸ **Kya aap current match score reset karna chahte hain?**\n_(Wahi teams aur setup se match starting se shuru hoga)_", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "act_reset_stats_exec":
            match.update({
                "runs": 0, "wickets": 0, "overs": 0.0, "balls": 0,
                "extras_total": 0, "extras_wides": 0, "extras_noballs": 0, "extras_byes": 0, "extras_legbyes": 0,
                "partnership_runs": 0, "partnership_balls": 0, "recent_balls": [], "current_over_runs": 0,
                "target": 0, "current_inning": 1,
                "history": [], "match_status": "Active", "last_event_ticker": "Match stats reset clean."
            })
            save_data()
            return start_wizard_openers_step(cid, mid)

        # HARD RESET (COMPLETE MATCH CANCEL -> NEW MATCH SETUP)
        if dt == "act_hard_reset_confirm":
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("ðŸ›‘ Yes, Hard Reset", callback_data="act_hard_reset_exec"), InlineKeyboardButton("âŒ Cancel", callback_data="back_main"))
            return safe_edit_message("ðŸ›‘ **HARD RESET CONFIRMATION:**\n\nKya aap match poora cancel karke **Step 1 New Setup Wizard** se nayi teams/toss ke sath start karna chahte hain?\n_(Squads aur database save rahega)_", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "act_hard_reset_exec":
            blank = create_blank_match()
            blank["series_list"] = match.get("series_list", [])
            blank["squads"] = match.get("squads", {})
            blank["team_records"] = match.get("team_records", {})
            blank["match_archives"] = match.get("match_archives", [])
            blank["career_db"] = match.get("career_db", {})
            blank["h2h_records"] = match.get("h2h_records", {})
            blank["matchup_db"] = match.get("matchup_db", {})
            match.clear()
            match.update(blank)
            save_data()
            
            m = InlineKeyboardMarkup(row_width=1)
            m.add(
                InlineKeyboardButton("ðŸ† Real Tournament / Bilateral Series", callback_data="wiz_mode_real"),
                InlineKeyboardButton("ðŸŸï¸ Multi-Team Tournament / League Mode", callback_data="wiz_mode_tournament"),
                InlineKeyboardButton("ðŸ§ª Practice / Fake Match", callback_data="wiz_mode_practice")
            )
            return safe_edit_message("ðŸ **NEW MATCH SETUP (HARD RESET DONE)**\n\nðŸ“Œ **Step 1:** Select Match / Tournament Mode:", chat_id=cid, message_id=mid, reply_markup=m)

        if dt == "back_main":
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

    except Exception as e:
        print(f"Callback error: {e}")

# ================= WICKET ENGINE (STRICT SINGLE-BATTER REPLACEMENT) =================
def process_wicket(cid, mid, reason, uid, target_batter="striker"):
    limit_w = match["max_wickets_limit"]
    if match["wickets"] < limit_w:
        save_state_for_undo()
        match["wickets"] += 1
        
        dismissed = match["striker"] if target_batter == "striker" else match["non_striker"]
        
        ensure_match_player_stat(dismissed, match["batting_team"], role="bat")
        ensure_match_player_stat(match["bowler"], match["bowling_team"], role="bowl")
        
        if target_batter == "striker":
            match["match_innings_data"][match["current_inning"]]["batting"][dismissed]["balls"] += 1
            if dismissed in match["career_db"]:
                match["career_db"][dismissed]["balls"] += 1
                
        match["match_innings_data"][match["current_inning"]]["batting"][dismissed]["status"] = reason
        
        if "Run Out" not in reason:
            match["match_innings_data"][match["current_inning"]]["bowling"][match["bowler"]]["wickets"] += 1
            if match["bowler"] in match["career_db"]:
                match["career_db"][match["bowler"]]["wickets"] += 1
            record_player_matchup(dismissed, match["bowler"], 0, is_out=True)
                
        if "Stumped" in reason and match["wicketkeeper"] != "Not Assigned":
            wk = match["wicketkeeper"]
            ensure_player(wk, match["bowling_team"])
            if wk in match["career_db"]:
                match["career_db"][wk]["stumpings"] = match["career_db"][wk].get("stumpings", 0) + 1
                
        ps_str = f"{to_serif_bold_num(match['wickets'])} Wkt: {to_serif_bold_num(match['partnership_runs'])} runs ({to_serif_bold_num(match['partnership_balls'])}b) â€” {clean_txt(match['striker'])} & {clean_txt(match['non_striker'])}"
        match["match_innings_data"][match["current_inning"]].setdefault("partnerships", []).append(ps_str)
        
        fow_txt = f"{to_serif_bold_num(match['runs'])}/{to_serif_bold_num(match['wickets'])} ({clean_txt(dismissed)}, {to_serif_bold_num(f'{match['overs']:.1f}')} ov)"
        match.setdefault("fall_of_wickets", []).append(fow_txt)
        match["match_innings_data"][match["current_inning"]].setdefault("fow", []).append(fow_txt)
        
        match["last_event_ticker"] = f"ðŸš¨ WICKET! {clean_txt(dismissed)} ({reason})!"
        match["partnership_runs"], match["partnership_balls"] = 0, 0
        register_legal_ball(cid, legal=True, ball_tag="W", runs_on_ball=0)
        
        if target_batter == "striker":
            match["striker"] = "Select Striker"
        else:
            match["non_striker"] = "Select Non-Striker"
            
        save_data()
        
        if match["wickets"] >= limit_w:
            check_match_completion(cid)
            if mid:
                return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))
            return
            
        # POPUP AUTOMATICALLY SHOWN FOR NEXT BATSMAN
        avail = get_available_batsmen(match["batting_team"])
        m = InlineKeyboardMarkup(row_width=2)
        for p in avail:
            m.add(InlineKeyboardButton(f"ðŸ {p}", callback_data=f"replace_str_{p}" if target_batter == "striker" else f"replace_nstr_{p}"))
        m.add(InlineKeyboardButton("âž• Type Next Batsman", callback_data="type_replace_str" if target_batter == "striker" else "type_replace_nstr"))
        safe_send_message(cid, f"ðŸ‘¤ **{clean_txt(dismissed)} OUT!** Agla Batsman ({'Striker' if target_batter == 'striker' else 'Runner'}) select karein:", reply_markup=m)
        if mid:
            return safe_edit_message(get_large_scoreboard_text(), chat_id=cid, message_id=mid, reply_markup=get_scorer_keyboard(uid))

# ================= TEXT INPUT HANDLER (ISOLATED PER USER) =================
@bot.message_handler(func=lambda m: match.get("user_actions", {}).get(m.from_user.id) is not None)
def handle_text_inputs(msg):
    uid = msg.from_user.id
    act = match.get("user_actions", {}).get(uid)
    raw_text = msg.text.strip()
    txt = clean_txt(raw_text)
    
    if txt.startswith("/"):
        match["user_actions"][uid] = None
        return
        
    match["user_actions"][uid] = None
    
    try:
        if act == "wiz_type_series_name":
            if txt not in match["series_list"]:
                match["series_list"].append(txt)
            match["series_name"] = txt
            save_data()
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("âš¡ 1 Match Standalone", callback_data="wiz_series_1"), InlineKeyboardButton("ðŸ† 2-Match Series", callback_data="wiz_series_2"))
            m.add(InlineKeyboardButton("ðŸ† 3-Match Series", callback_data="wiz_series_3"), InlineKeyboardButton("ðŸ† 5-Match Series", callback_data="wiz_series_5"))
            m.add(InlineKeyboardButton("âœï¸ Custom Series Length", callback_data="wiz_series_custom"))
            safe_send_message(msg.chat.id, f"âœ… Series Name locked to **{txt}**!\n\nðŸ“Œ **Step 1.2:** Select **Series Format:**", reply_markup=m)

        elif act == "input_max_wickets_limit":
            try:
                w_val = int(txt)
                match["max_wickets_limit"] = w_val
                m = InlineKeyboardMarkup(row_width=2)
                m.add(
                    InlineKeyboardButton("â±ï¸ Enable Over-Rate Timer", callback_data="wiz_timer_enable"),
                    InlineKeyboardButton("âš¡ No Timer (Casual)", callback_data="wiz_timer_disable")
                )
                safe_send_message(msg.chat.id, f"ðŸ“Œ **Step 6.3:** Match Timer / Over-Rate configure karein:", reply_markup=m)
            except Exception:
                match["user_actions"][uid] = "input_max_wickets_limit"
                safe_send_message(msg.chat.id, "âŒ Invalid number! Please enter valid wickets limit (e.g. 10, 14):")

        elif act == "input_rename_team_val":
            target_t = match["temp_data"].get("rename_target_team")
            if target_t in match.get("teams", []):
                idx = match["teams"].index(target_t)
                match["teams"][idx] = txt
                if target_t in match.get("squads", {}):
                    match["squads"][txt] = match["squads"].pop(target_t)
                save_data()
                safe_send_message(msg.chat.id, f"âœ… Team **{target_t}** successfully renamed to **{txt}**!", reply_markup=get_scorer_keyboard(uid))
            else:
                safe_send_message(msg.chat.id, "âŒ Team nahi mili!")

        elif act == "input_series_custom_matches":
            try:
                m_cnt = int(txt)
                match["series_total_matches"] = m_cnt
                save_data()
                m = InlineKeyboardMarkup(row_width=2)
                for t in match.get("teams", []):
                    m.add(InlineKeyboardButton(f"ðŸ“ {t}", callback_data=f"wiz_t1_{t}"))
                m.add(InlineKeyboardButton("âž• Create Team", callback_data="wiz_create_team"))
                safe_send_message(msg.chat.id, f"âœ… Series locked to **{m_cnt} Matches**!\n\nðŸ“Œ **Step 2:** Select **Team 1**:", reply_markup=m)
            except Exception:
                safe_send_message(msg.chat.id, "âŒ Invalid number of matches!")

        elif act == "input_tour_custom_teams_count":
            try:
                cnt = int(txt)
                match["temp_data"]["tour_teams_needed"] = cnt
                match["tournament_teams"] = []
                match["user_actions"][uid] = "input_tour_team_name"
                safe_send_message(msg.chat.id, f"âœï¸ Team 1 ka naam type karke send karein (1/{cnt}):")
            except Exception:
                safe_send_message(msg.chat.id, "âŒ Invalid number of teams!")

        elif act == "input_tour_team_name":
            needed = match["temp_data"].get("tour_teams_needed", 4)
            match["tournament_teams"].append(txt)
            if txt not in match["teams"]: match["teams"].append(txt)
            if txt not in match["squads"]: match["squads"][txt] = []
            cur_len = len(match["tournament_teams"])
            save_data()
            if cur_len < needed:
                match["user_actions"][uid] = "input_tour_team_name"
                safe_send_message(msg.chat.id, f"âœ… Team Added: **{txt}**\n\nâœï¸ Team {cur_len+1} ka naam type karein ({cur_len+1}/{needed}):")
            else:
                match["teams"] = [match["tournament_teams"][0], match["tournament_teams"][1]]
                m = InlineKeyboardMarkup(row_width=2)
                m.add(InlineKeyboardButton("ðŸª™ Auto Random Toss", callback_data="wiz_toss_auto"))
                m.add(InlineKeyboardButton("âœï¸ Manual Toss Selection", callback_data="wiz_toss_manual"))
                safe_send_message(msg.chat.id, f"ðŸ† **TOURNAMENT TEAMS CONFIGURED!**\nMatch 1: **{match['teams'][0]} vs {match['teams'][1]}**\n\nðŸ“Œ **Step 3:** Toss Setup:", reply_markup=m)

        elif act == "wiz_input_team":
            if txt not in match["teams"]: match["teams"].append(txt)
            match["squads"][txt] = []
            match["temp_data"]["wiz_team1"] = txt
            save_data()
            m = InlineKeyboardMarkup(row_width=2)
            for t in match["teams"]:
                if t != txt: m.add(InlineKeyboardButton(f"ðŸ“ {t}", callback_data=f"wiz_t2_{t}"))
            m.add(InlineKeyboardButton("âž• Create Team 2", callback_data="wiz_create_team_2"))
            safe_send_message(msg.chat.id, f"âœ… Team 1 set to **{txt}**!\n\nðŸ“Œ Select **Team 2**:", reply_markup=m)

        elif act == "wiz_input_team_2":
            if txt not in match["teams"]: match["teams"].append(txt)
            match["squads"][txt] = []
            t1 = match["temp_data"].get("wiz_team1", match["teams"][0])
            match["teams"] = [t1, txt]
            save_data()
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton("ðŸª™ Auto Random Toss", callback_data="wiz_toss_auto"))
            m.add(InlineKeyboardButton("âœï¸ Manual Toss Selection", callback_data="wiz_toss_manual"))
            safe_send_message(msg.chat.id, f"âœ… Team 2 set to **{txt}**!\n\nðŸ“Œ **Step 3:** Toss Setup for **{t1} vs {txt}**:", reply_markup=m)

        elif act == "input_squad_player":
            t_target = match["temp_data"].get("target_team", match["batting_team"])
            if t_target not in match["squads"]: match["squads"][t_target] = []
            
            parsed_names = [p.strip() for p in raw_text.replace("\n", ",").replace("/", ",").split(",") if p.strip()]
            for name in parsed_names:
                c_name = clean_txt(name)
                if c_name and c_name not in match["squads"][t_target]:
                    match["squads"][t_target].append(c_name)
                    ensure_player(c_name, t_target)
            save_data()
            m = InlineKeyboardMarkup(row_width=2)
            m.add(InlineKeyboardButton(f"âž• Add More ({t_target})", callback_data=f"wiz_add_p_{t_target}"))
            m.add(InlineKeyboardButton("âž¡ï¸ Continue to Ground & Overs", callback_data="wiz_ground_step"))
            safe_send_message(msg.chat.id, f"âœ… Added **{len(parsed_names)} Players** to **{t_target}**!", reply_markup=m)

        elif act == "input_single_player":
            t_target = match["temp_data"].get("target_team", match["batting_team"])
            if t_target not in match["squads"]: match["squads"][t_target] = []
            if txt not in match["squads"][t_target]:
                match["squads"][t_target].append(txt)
                ensure_player(txt, t_target)
            save_data()
            safe_send_message(msg.chat.id, f"âœ… Added **{txt}** to **{t_target}**!", reply_markup=get_scorer_keyboard(uid))

        elif act == "input_player_rename_val":
            t_name = match["temp_data"].get("rename_p_team")
            old_p = match["temp_data"].get("rename_p_old")
            if t_name in match.get("squads", {}) and old_p in match["squads"][t_name]:
                idx = match["squads"][t_name].index(old_p)
                match["squads"][t_name][idx] = txt
                if match["striker"] == old_p: match["striker"] = txt
                if match["non_striker"] == old_p: match["non_striker"] = txt
                if match["bowler"] == old_p: match["bowler"] = txt
                save_data()
                safe_send_message(msg.chat.id, f"âœ… Player **{old_p}** renamed to **{txt}**!", reply_markup=get_scorer_keyboard(uid))

        elif act == "input_add_scorer":
            try:
                s_uid = int(txt)
                AUTHORIZED_SCORERS.add(s_uid)
                safe_send_message(msg.chat.id, f"âœ… User ID `{s_uid}` is now an Authorized Scorer!")
            except Exception:
                safe_send_message(msg.chat.id, "âŒ Please enter a valid Numeric Telegram User ID!")

        elif act == "input_quick_runs":
            try:
                r = int(txt)
                ov = match["temp_data"].get("q_overs", 7)
                w = match["temp_data"].get("q_wkts", 5)
                match["target"] = max(1, r + 1)
                match["current_inning"] = 2
                match["match_innings_data"][1] = {
                    "team": match["bowling_team"],
                    "batting": {f"Opponent TopOrder": {"runs": r, "balls": ov * 6, "fours": r // 6, "sixes": r // 10, "status": "Innings Closed"}},
                    "bowling": {f"Team Bowlers": {"balls": ov * 6, "runs": r, "wickets": w, "maidens": 0}},
                    "extras": {"w": 0, "nb": 0, "b": 0, "lb": 0, "total": 0}, "fow": [], "partnerships": [], "final_score": r, "final_wickets": w, "final_overs": float(ov)
                }
                match.update({
                    "runs": 0, "wickets": 0, "overs": 0.0, "balls": 0,
                    "extras_total": 0, "partnership_runs": 0, "partnership_balls": 0,
                    "recent_balls": [], "history": [], "last_event_ticker": f"Innings 1: {r}/{w} ({ov}.0 ov). Target: {match['target']}",
                    "timer_start_epoch": time.time() if match.get("timer_enabled") else None,
                    "timer_paused": False, "timer_total_paused_sec": 0,
                    "timer_alerts_sent": {"midway": False, "warn5": False, "expired": False},
                    "fielding_penalty_active": False
                })
                save_data()
                start_wizard_openers_step(msg.chat.id, None)
            except Exception:
                safe_send_message(msg.chat.id, "âŒ Invalid run amount!")

        elif act == "input_edit_runs":
            try:
                match["runs"] = int(txt)
                save_data()
                sync_pinned_card(msg.chat.id)
                safe_send_message(msg.chat.id, f"âœ… Total Runs updated to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid))
            except Exception:
                safe_send_message(msg.chat.id, "âŒ Invalid number!")

        elif act == "input_edit_wkts":
            try:
                match["wickets"] = int(txt)
                save_data()
                sync_pinned_card(msg.chat.id)
                safe_send_message(msg.chat.id, f"âœ… Total Wickets updated to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid))
            except Exception:
                safe_send_message(msg.chat.id, "âŒ Invalid number!")

        elif act == "input_edit_target":
            try:
                match["target"] = int(txt)
                save_data()
                sync_pinned_card(msg.chat.id)
                safe_send_message(msg.chat.id, f"âœ… Target updated to **{txt}**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid))
            except Exception:
                safe_send_message(msg.chat.id, "âŒ Invalid number!")

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
                record_player_matchup(match["striker"], match["bowler"], r, is_out=False)
                match["last_event_ticker"] = f"âš¡ {r} Runs scored by {clean_txt(match['striker'])}"
                register_legal_ball(msg.chat.id, legal=True, ball_tag=f"OT+{r}", runs_on_ball=r)
                save_data()
                safe_send_message(msg.chat.id, f"âœ… Added **{r} Runs**!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid))
            except Exception:
                safe_send_message(msg.chat.id, "âŒ Invalid number of runs!")

        elif act == "input_dls_inn1_revised":
            try:
                rev_ov = int(txt)
                match["total_match_overs"] = rev_ov
                match["dls_applied"] = True
                match["last_event_ticker"] = f"ðŸŒ§ï¸ DLS: 1st Inning reduced to {rev_ov}.0 ov!"
                save_data()
                sync_pinned_card(msg.chat.id)
                safe_send_message(msg.chat.id, f"âœ… **DLS Applied for Innings 1!**\nNew Match Overs: `{rev_ov}.0`\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid))
                # If current balls already reached or exceeded new overs limit, close inning cleanly
                if match["balls"] >= rev_ov * 6:
                    check_match_completion(msg.chat.id)
            except Exception:
                safe_send_message(msg.chat.id, "âŒ Invalid overs number!")

        elif act == "input_dls_inn2_revised":
            try:
                rev_ov = int(txt)
                orig_ov = match.get("original_match_overs", match["total_match_overs"])
                t1_runs = match["match_innings_data"][1].get("final_score", match["runs"])
                r1 = get_dls_resource(orig_ov)
                r2 = get_dls_resource(rev_ov)
                rev_target = max(1, math.ceil(t1_runs * (r2 / r1)) + 1) if r1 > 0 else max(1, math.ceil(t1_runs * (rev_ov / orig_ov)) + 1)
                match["total_match_overs"] = rev_ov
                match["target"] = rev_target
                match["dls_applied"] = True
                match["last_event_ticker"] = f"ðŸŒ§ï¸ DLS Target: {rev_target} Runs ({rev_ov}.0 ov)"
                save_data()
                sync_pinned_card(msg.chat.id)
                safe_send_message(msg.chat.id, f"âœ… **DLS Applied!** Target: `{rev_target}` Runs in `{rev_ov}.0` Overs.\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid))
                if match["balls"] >= rev_ov * 6 or match["runs"] >= rev_target:
                    check_match_completion(msg.chat.id)
            except Exception:
                safe_send_message(msg.chat.id, "âŒ Invalid overs number!")

        elif act in ["type_replace_str", "type_replace_nstr"]:
            is_str = (act == "type_replace_str")
            ensure_player(txt, match["batting_team"])
            if txt not in match["squads"].get(match["batting_team"], []): 
                match["squads"][match["batting_team"]].append(txt)
            if is_str: match["striker"] = txt
            else: match["non_striker"] = txt
            ensure_match_player_stat(txt, match["batting_team"], role="bat")
            save_data()
            return safe_send_message(msg.chat.id, f"âœ… Added & Selected **{txt}** as {'Striker' if is_str else 'Runner'}!\n\n{get_large_scoreboard_text()}", reply_markup=get_scorer_keyboard(uid))

        # TYPED OPENERS CHAIN (AUTO-FLOW)
        elif act == "wiz_type_striker":
            ensure_player(txt, match["batting_team"])
            if txt not in match["squads"].get(match["batting_team"], []): 
                match["squads"][match["batting_team"]].append(txt)
            match["striker"] = txt
            ensure_match_player_stat(txt, match["batting_team"], role="bat")
            save_data()
            prompt_non_striker_step(msg.chat.id, None)

        elif act == "wiz_type_nonstriker":
            ensure_player(txt, match["batting_team"])
            if txt not in match["squads"].get(match["batting_team"], []): 
                match["squads"][match["batting_team"]].append(txt)
            match["non_striker"] = txt
            ensure_match_player_stat(txt, match["batting_team"], role="bat")
            save_data()
            prompt_opening_bowler_step(msg.chat.id, None)

        elif act == "wiz_type_bowler":
            ensure_player(txt, match["bowling_team"])
            if txt not in match["squads"].get(match["bowling_team"], []): 
                match["squads"][match["bowling_team"]].append(txt)
            match["bowler"] = txt
            match["user_actions"][uid] = None
            ensure_match_player_stat(txt, match["bowling_team"], role="bowl")
            
            # Reset ball state only on brand new match setup
            if match["balls"] == 0:
                match["runs"] = 0
                match["wickets"] = 0
                match["overs"] = 0.0
                match["extras_total"] = 0
                match["partnership_runs"] = 0
                match["partnership_balls"] = 0
                match["recent_balls"] = []
                match["current_over_runs"] = 0
                match["fall_of_wickets"] = []
                match["history"] = []
                
            match["match_status"] = "Active"
            match["last_event_ticker"] = f"Innings {match['current_inning']} Live! Striker: {match['striker']}"
            if match.get("timer_enabled") and match.get("timer_start_epoch") is None:
                match["timer_start_epoch"] = time.time()
                match["timer_paused"] = False
                match["timer_total_paused_sec"] = 0
                match["timer_alerts_sent"] = {"midway": False, "warn5": False, "expired": False}
            match["fielding_penalty_active"] = False
            
            save_data()
            msg_obj = safe_send_message(msg.chat.id, get_large_scoreboard_text(), reply_markup=get_scorer_keyboard(uid))
            try:
                bot.pin_chat_message(msg.chat.id, msg_obj.message_id)
                match["pinned_message_id"] = msg_obj.message_id
                match["pinned_chat_id"] = msg.chat.id
                save_data()
            except Exception: pass

        elif act == "wiz_type_ground":
            if txt not in match["grounds_list"]: match["grounds_list"].append(txt)
            match["ground"] = txt
            save_data()
            m = InlineKeyboardMarkup(row_width=3)
            m.add(InlineKeyboardButton("âœï¸ Custom Overs", callback_data="wiz_type_overs"))
            for ov in [2, 3, 5, 6, 7, 8, 10, 12, 15, 20]:
                m.add(InlineKeyboardButton(f"{ov} Overs", callback_data=f"wiz_set_ov_{ov}"))
            safe_send_message(msg.chat.id, f"ðŸŸï¸ Ground set to **{txt}**!\n\nðŸ“Œ **Step 6.1:** Select **Total Match Overs:**", reply_markup=m)

        elif act in ["wiz_type_overs", "input_manual_overs"]:
            try:
                ov = int(txt)
                match["total_match_overs"] = ov
                match["original_match_overs"] = ov
                m = InlineKeyboardMarkup(row_width=2)
                m.add(InlineKeyboardButton("10 Wkts (Standard)", callback_data="wiz_set_wlimit_10"))
                m.add(InlineKeyboardButton("11 Wkts (Gully)", callback_data="wiz_set_wlimit_11"))
                m.add(InlineKeyboardButton("14 Wkts (Gully Mega)", callback_data="wiz_set_wlimit_14"))
                m.add(InlineKeyboardButton("âœï¸ Custom Limit", callback_data="wiz_type_wlimit"))
                safe_send_message(msg.chat.id, f"â³ Match Overs: **{ov}.0**\n\nðŸ“Œ **Step 6.2:** Select **Max Wickets Limit:**", reply_markup=m)
            except Exception:
                safe_send_message(msg.chat.id, "âŒ Invalid number of overs!")

        elif act == "type_catch_fielder":
            ensure_player(txt, match["bowling_team"])
            if txt in match["career_db"]: match["career_db"][txt]["catches"] += 1
            save_data()
            process_wicket(msg.chat.id, None, f"c {txt} b {match['bowler']}", uid, target_batter="striker")
    except Exception as e:
        print(f"Error handling input: {e}")

# ================= 24/7 WORKER RUNNER WITH TIMER DAEMON =================
def run_telegram_worker():
    time.sleep(2)
    try: bot.remove_webhook()
    except Exception: pass
    print(">>> Telegram Bot Engine Started (Non-blocking infinity loop)...")
    while True:
        try: bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
        except Exception as e:
            print(f">>> Reconnecting Polling: {e}")
            time.sleep(5)

def run_timer_daemon():
    while True:
        time.sleep(15)
        try:
            if match.get("timer_enabled") and match.get("timer_start_epoch") and not match.get("timer_paused") and match.get("match_status") == "Active":
                cid = match.get("pinned_chat_id")
                if not cid: continue
                total_sec = match.get("timer_allocated_mins", 30) * 60
                now = time.time()
                elapsed_sec = (now - match["timer_start_epoch"]) - match.get("timer_total_paused_sec", 0)
                rem_sec = total_sec - elapsed_sec
                alerts = match.setdefault("timer_alerts_sent", {"midway": False, "warn5": False, "expired": False})
                if not alerts.get("midway") and elapsed_sec >= (total_sec / 2):
                    alerts["midway"] = True
                    broadcast_commentary(cid, f"â±ï¸ **MIDWAY TIME CHECK:** Inning half-time complete! `{int(rem_sec // 60)} Mins` remaining.")
                    save_data()
                if not alerts.get("warn5") and rem_sec <= 300 and rem_sec > 0:
                    alerts["warn5"] = True
                    broadcast_commentary(cid, f"âš ï¸ **PACE WARNING:** Only `5 Minutes` left!")
                    save_data()
                if not alerts.get("expired") and rem_sec <= 0:
                    alerts["expired"] = True
                    broadcast_commentary(cid, "ðŸš¨ **TIME EXPIRED:** Over-rate penalties can now be applied.")
                    save_data()
        except Exception as e:
            print(f"Timer daemon error: {e}")

def run_pinger_worker():
    while True:
        time.sleep(240)
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL")
            if url: urllib.request.urlopen(f"{url}/health", timeout=10)
        except Exception: pass

if __name__ == "__main__":
    threading.Thread(target=run_telegram_worker, daemon=True).start()
    threading.Thread(target=run_timer_daemon, daemon=True).start()
    threading.Thread(target=run_pinger_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    print(f">>> Render Web Service Listening on Port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)