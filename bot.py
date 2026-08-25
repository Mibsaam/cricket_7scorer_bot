import os
import json
import copy
import threading
import time
import urllib.request
import random
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8812331993:AAEREVNSHoSAIgPMYAz1dG1rhJP_RYRV0-w"

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is Running 24/7", 200

def auto_ping():
    while True:
        time.sleep(300)
        try:
            r_url = os.environ.get("RENDER_EXTERNAL_URL")
            if r_url:
                urllib.request.urlopen(r_url)
        except Exception:
            pass

threading.Thread(target=auto_ping, daemon=True).start()

bot = telebot.TeleBot(BOT_TOKEN)

CAREER_FILE = "career_data.json"
TEAMS_FILE = "teams_data.json"
H2H_FILE = "h2h_data.json"

def load_json(fpath):
    if os.path.exists(fpath):
        try:
            with open(fpath, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(fpath, data):
    try:
        with open(fpath, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

CAREER_DB = load_json(CAREER_FILE)
TEAMS_DB = load_json(TEAMS_FILE)
H2H_DB = load_json(H2H_FILE)

m = {
    "active": False,
    "t1": "Team A",
    "t2": "Team B",
    "max_ov": 10,
    "inn": 1,
    "bat_tm": "",
    "bowl_tm": "",
    "target": 0,
    "scorers": set(),
    "t1_squad": [],
    "t2_squad": [],
    "is_quick_mode": False,
    "is_practice": False,
    "striker": "",
    "non_striker": "",
    "bowler": "",
    "runs": 0,
    "wkts": 0,
    "balls": 0,
    "partnership_runs": 0,
    "partnership_balls": 0,
    "extras": {"wd": 0, "nb": 0, "b": 0, "lb": 0},
    "free_hit": False,
    "await_input": None,
    "cur_over": [],
    "over_history": [],
    "batsmen": {},
    "bowlers": {},
    "toss_winner": "",
    "history": [],
    "inn1_summary": "",
    "last_commentary": ""
}

def get_overs_str(b):
    return f"{b // 6}.{b % 6}"

def get_crr(r, b):
    return f"{(r / (b / 6)):.2f}" if b > 0 else "0.00"

def get_h2h_str(t1, t2):
    k1, k2 = f"{t1}_vs_{t2}", f"{t2}_vs_{t1}"
    w1 = H2H_DB.get(k1, 0)
    w2 = H2H_DB.get(k2, 0)
    return f"⚔️ H2H: {t1} ({w1}) - ({w2}) {t2}"

def get_rrr_line():
    if m["inn"] != 2 or m["target"] <= 0:
        return ""
    needed = m["target"] - m["runs"]
    rem_b = (m["max_ov"] * 6) - m["balls"]
    if needed <= 0:
        return f"\n🏆 *Target Achieved! {m['bat_tm']} won!*"
    if rem_b <= 0:
        return f"\n🏁 *Overs Finished! Need {needed} off 0 balls*"
    rrr = (needed / (rem_b / 6))
    return f"\n🎯 *Target: {m['target']}* (Need *{needed}* runs off *{rem_b}* balls | RRR: *{rrr:.2f}*)"

def live_card_text():
    s_n = m["striker"]
    ns_n = m["non_striker"]
    bw_n = m["bowler"]
    s = m["batsmen"].get(s_n, {"r": 0, "b": 0, "4s": 0, "6s": 0})
    ns = m["batsmen"].get(ns_n, {"r": 0, "b": 0, "4s": 0, "6s": 0})
    bw = m["bowlers"].get(bw_n, {"r": 0, "b": 0, "w": 0, "m": 0})
    
    fh_alert = "\n🚨 *FREE HIT BALL!* 🚨" if m["free_hit"] else ""
    ov_str = " ".join([f"[{x}]" for x in m["cur_over"]]) if m["cur_over"] else "Yet to start"
    tot_ext = sum(m["extras"].values())
    prac_tag = "🏏 [PRACTICE MATCH]\n" if m["is_practice"] else ""
    comm_box = f"\n🎙️ *Commentary:* {m['last_commentary']}\n" if m["last_commentary"] else ""
    
    txt = (
        f"{prac_tag}"
        f"🏏 *{m['bat_tm']} vs {m['bowl_tm']}* (Innings {m['inn']})\n"
        f"📊 {get_h2h_str(m['t1'], m['t2'])}\n"
        f"🔴 LIVE: *{m['runs']}/{m['wkts']}* ({get_overs_str(m['balls'])}/{m['max_ov']} ov) | CRR: *{get_crr(m['runs'], m['balls'])}*"
        f"{get_rrr_line()}{comm_box}{fh_alert}\n"
        f"-----------------------------------------\n"
        f"🏏 *{s_n}**: {s['r']} ({s['b']}b) [4s:{s['4s']} 6s:{s['6s']}]\n"
        f"🏏 *{ns_n}*: {ns['r']} ({ns['b']}b) [4s:{ns['4s']} 6s:{ns['6s']}]\n"
        f"🤝 Partnership: {m['partnership_runs']} ({m['partnership_balls']}b)\n"
        f"🎯 *{bw_n}*: {bw['w']}/{bw['r']} ({get_overs_str(bw['b'])} ov)\n"
        f"-----------------------------------------\n"
        f"Extras: {tot_ext} (Wd:{m['extras']['wd']} Nb:{m['extras']['nb']} B:{m['extras']['b']} LB:{m['extras']['lb']})\n"
        f"This Over: {ov_str}"
    )
    return txt

def full_scorecard_text():
    tot_ext = sum(m["extras"].values())
    txt = (
        f"📋 FULL MATCH SCORECARD\n"
        f"🏏 {m['bat_tm']} : {m['runs']}/{m['wkts']} ({get_overs_str(m['balls'])}/{m['max_ov']} ov)\n"
        f"Extras: {tot_ext} (Wd:{m['extras']['wd']}, Nb:{m['extras']['nb']}, B:{m['extras']['b']}, LB:{m['extras']['lb']})\n"
        f"CRR: {get_crr(m['runs'], m['balls'])}{get_rrr_line()}\n"
        f"=========================================\n"
        f"🏏 BATTING STATS:\n"
    )
    for n, s in m["batsmen"].items():
        sr = f"{(s['r']/s['b']*100):.1f}" if s['b'] > 0 else "0.0"
        status = f" (Out: {s.get('how_out', 'out')})" if s.get("out") else " (Not Out)"
        txt += f"• {n}{status}: {s['r']} ({s['b']}b) [4s:{s['4s']}, 6s:{s['6s']}] SR: {sr}\n"
    
    txt += f"-----------------------------------------\n🎯 BOWLING STATS:\n"
    for n, bw in m["bowlers"].items():
        econ = f"{(bw['r']/(bw['b']/6)):.2f}" if bw['b'] > 0 else "0.00"
        txt += f"• {n}: {get_overs_str(bw['b'])} ov | {bw['r']} runs | {bw['w']} wkts | Econ: {econ}\n"
    
    if m["over_history"]:
        txt += f"-----------------------------------------\n📈 OVER PROGRESSION:\n"
        for i, ov in enumerate(m["over_history"], 1):
            txt += f"Over {i}: {' '.join(ov['balls'])} -> {ov['runs']} Runs ({ov['bowler']})\n"
    return txt

def calculate_motm():
    best_p = "None"
    max_pts = -999
    desc = ""
    for n, s in m["batsmen"].items():
        pts = s["r"] + (s["4s"] * 2) + (s["6s"] * 3)
        if pts > max_pts:
            max_pts = pts
            best_p = n
            desc = f"{s['r']} Runs ({s['b']}b)"
    for n, bw in m["bowlers"].items():
        bw_pts = (bw["w"] * 25) - (bw["r"] // 3)
        if bw_pts > max_pts:
            max_pts = bw_pts
            best_p = n
            desc = f"{bw['w']} Wkts, {bw['r']} Runs"
    return f"{best_p} [{desc}]"

def get_career_profile(name):
    pn = name.strip().title()
    p = CAREER_DB.get(pn)
    if not p:
        return f"👤 *{pn}* (Debutant)\n• Matches: 0 | Runs: 0 | Wkts: 0"
    sr = f"{(p['runs'] / p['balls'] * 100):.1f}" if p['balls'] > 0 else "0.0"
    econ = f"{(p['bowl_r'] / (p['bowl_b'] / 6)):.2f}" if p['bowl_b'] > 0 else "0.00"
    form_tag = "🔥 IN-FORM" if p['runs'] > 150 else "⚡ Regular Player"
    return (
        f"👤 PROFILE: *{pn}* [{form_tag}]\n"
        f"• Batting: {p['runs']} Runs ({p['inns']} Inns) | SR: {sr} | HS: {p['hs']}\n"
        f"• Bowling: {p['wkts']} Wkts ({get_overs_str(p['bowl_b'])} ov) | Econ: {econ}"
    )

def get_scoring_keyboard():
    k = InlineKeyboardMarkup(row_width=3)
    k.add(
        InlineKeyboardButton("0", callback_data="sc_run_0"),
        InlineKeyboardButton("1", callback_data="sc_run_1"),
        InlineKeyboardButton("2", callback_data="sc_run_2")
    )
    k.add(
        InlineKeyboardButton("3", callback_data="sc_run_3"),
        InlineKeyboardButton("4 (Four)", callback_data="sc_run_4"),
        InlineKeyboardButton("6 (Six)", callback_data="sc_run_6")
    )
    k.add(
        InlineKeyboardButton("Wide (+1)", callback_data="sc_ext_wd_1"),
        InlineKeyboardButton("No Ball (+1)", callback_data="sc_ext_nb_1"),
        InlineKeyboardButton("☝️ WICKET", callback_data="sc_wkt_ask")
    )
    k.add(
        InlineKeyboardButton("Bye (+1)", callback_data="sc_team_bye_1"),
        InlineKeyboardButton("🔄 Strike", callback_data="sc_swap"),
        InlineKeyboardButton("🎯 Bowler", callback_data="sc_ch_bowl_mid")
    )
    k.add(
        InlineKeyboardButton("↩️ Undo", callback_data="sc_undo"),
        InlineKeyboardButton("📋 Scorecard", callback_data="sc_full_view"),
        InlineKeyboardButton("⚙️ Menu / More", callback_data="opt_edit_menu")
    )
    return k

def get_squad_picker(team_name, purpose):
    k = InlineKeyboardMarkup(row_width=2)
    squad = m["t1_squad"] if team_name == m["t1"] else m["t2_squad"]
    for p in squad:
        if purpose in ["str", "nstr", "bat"] and p in m["batsmen"] and m["batsmen"][p].get("out"):
            continue
        k.add(InlineKeyboardButton(p, callback_data=f"sel_{purpose}_{p}"))
    k.add(InlineKeyboardButton("✍️ Type Custom Name", callback_data=f"sel_custom_{purpose}"))
    return k

def save_state():
    if len(m["history"]) > 25:
        m["history"].pop(0)
    snap = copy.deepcopy({
        "runs": m["runs"],
        "wkts": m["wkts"],
        "balls": m["balls"],
        "partnership_runs": m["partnership_runs"],
        "partnership_balls": m["partnership_balls"],
        "striker": m["striker"],
        "non_striker": m["non_striker"],
        "bowler": m["bowler"],
        "extras": copy.deepcopy(m["extras"]),
        "free_hit": m["free_hit"],
        "cur_over": list(m["cur_over"]),
        "over_history": copy.deepcopy(m["over_history"]),
        "batsmen": copy.deepcopy(m["batsmen"]),
        "bowlers": copy.deepcopy(m["bowlers"]),
        "last_commentary": m["last_commentary"]
    })
    m["history"].append(snap)

def undo_state():
    if not m["history"]:
        return False
    last = m["history"].pop()
    for k, v in last.items():
        m[k] = v
    return True

def ensure_player(n, is_bat=True):
    if is_bat and n and n != "NONE" and n not in m["batsmen"]:
        m["batsmen"][n] = {"r": 0, "b": 0, "4s": 0, "6s": 0, "out": False, "how_out": ""}
    elif not is_bat and n and n not in m["bowlers"]:
        m["bowlers"][n] = {"r": 0, "b": 0, "w": 0, "m": 0}

def update_lifetime_records(winner_tm, loser_tm):
    if m["is_practice"]:
        return
    for tm in [winner_tm, loser_tm]:
        if tm not in TEAMS_DB:
            TEAMS_DB[tm] = {"p": 0, "w": 0, "l": 0, "hs": 0, "squad": []}
        TEAMS_DB[tm]["p"] += 1
    TEAMS_DB[winner_tm]["w"] += 1
    TEAMS_DB[loser_tm]["l"] += 1
    
    if m["runs"] > TEAMS_DB[m["bat_tm"]].get("hs", 0):
        TEAMS_DB[m["bat_tm"]]["hs"] = m["runs"]
    save_json(TEAMS_FILE, TEAMS_DB)

    h2h_key = f"{winner_tm}_vs_{loser_tm}"
    H2H_DB[h2h_key] = H2H_DB.get(h2h_key, 0) + 1
    save_json(H2H_FILE, H2H_DB)

    for n, s in m["batsmen"].items():
        pn = n.strip().title()
        if pn not in CAREER_DB:
            CAREER_DB[pn] = {"matches": 0, "inns": 0, "runs": 0, "balls": 0, "4s": 0, "6s": 0, "50s": 0, "100s": 0, "hs": 0, "wkts": 0, "bowl_r": 0, "bowl_b": 0}
        CAREER_DB[pn]["matches"] += 1
        if s["b"] > 0 or s.get("out"):
            CAREER_DB[pn]["inns"] += 1
        CAREER_DB[pn]["runs"] += s["r"]
        CAREER_DB[pn]["balls"] += s["b"]
        CAREER_DB[pn]["4s"] += s["4s"]
        CAREER_DB[pn]["6s"] += s["6s"]
        if s["r"] >= 100:
            CAREER_DB[pn]["100s"] += 1
        elif s["r"] >= 50:
            CAREER_DB[pn]["50s"] += 1
        if s["r"] > CAREER_DB[pn]["hs"]:
            CAREER_DB[pn]["hs"] = s["r"]

    for n, bw in m["bowlers"].items():
        pn = n.strip().title()
        if pn not in CAREER_DB:
            CAREER_DB[pn] = {"matches": 1, "inns": 0, "runs": 0, "balls": 0, "4s": 0, "6s": 0, "50s": 0, "100s": 0, "hs": 0, "wkts": 0, "bowl_r": 0, "bowl_b": 0}
        CAREER_DB[pn]["wkts"] += bw["w"]
        CAREER_DB[pn]["bowl_r"] += bw["r"]
        CAREER_DB[pn]["bowl_b"] += bw["b"]

    save_json(CAREER_FILE, CAREER_DB)

@bot.message_handler(commands=['start', 'match', 'menu'])
def cmd_start(msg):
    m["scorers"].add(msg.from_user.id)
    k = InlineKeyboardMarkup(row_width=2)
    k.add(
        InlineKeyboardButton("🏏 Real Match (Stats Save)", callback_data="opt_toss"),
        InlineKeyboardButton("🎯 Practice Match", callback_data="opt_practice_mode")
    )
    k.add(
        InlineKeyboardButton("⚡ Quick Opponent", callback_data="opt_quick_mode"),
        InlineKeyboardButton("🛡️ Standings", callback_data="sc_teams_view")
    )
    k.add(InlineKeyboardButton("🏆 Leaderboard", callback_data="sc_lead_view"))
    bot.reply_to(msg, "🏏 Pro Cricket Scoring & Championship Engine", reply_markup=k)

@bot.message_handler(commands=['score', 'scorecard'])
def cmd_score(msg):
    if not m["active"]:
        return bot.reply_to(msg, "⚠️ Abhi koi match active nahi hai.")
    bot.reply_to(msg, live_card_text(), reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def on_action(call):
    cid = call.message.chat.id
    mid = call.message.message_id
    cdata = call.data

    if cdata == "sc_teams_view":
        txt = "🛡️ TEAM STANDINGS 🛡️\n====================\n"
        for tname, st in TEAMS_DB.items():
            win_pct = f"{(st['w']/st['p']*100):.1f}%" if st['p'] > 0 else "0%"
            txt += f"🏆 *{tname}*\n• P: {st['p']} | W: {st['w']} | L: {st['l']} | Win%: {win_pct} | HS: {st.get('hs', 0)}\n\n"
        bot.send_message(cid, txt if TEAMS_DB else "No team records yet.", parse_mode="Markdown")
        return bot.answer_callback_query(call.id)

    if cdata == "sc_lead_view":
        top_runs = sorted(CAREER_DB.items(), key=lambda x: x[1]["runs"], reverse=True)
        top_wkts = sorted(CAREER_DB.items(), key=lambda x: x[1]["wkts"], reverse=True)
        txt = "🏆 CAREER LEADERBOARD 🏆\n=====================\n🟠 TOP RUNS:\n"
        for i, (p, s) in enumerate(top_runs[:5], 1):
            txt += f"{i}. {p}: {s['runs']} Runs ({s['inns']} Inns)\n"
        txt += "\n🟣 TOP WKTS:\n"
        for i, (p, s) in enumerate(top_wkts[:5], 1):
            txt += f"{i}. {p}: {s['wkts']} Wkts\n"
        bot.send_message(cid, txt if CAREER_DB else "No player records yet.")
        return bot.answer_callback_query(call.id)

    if cdata == "sc_full_view":
        if not m["active"]:
            return bot.answer_callback_query(call.id, "No active match!", show_alert=True)
        bot.send_message(cid, full_scorecard_text())
        return bot.answer_callback_query(call.id)

    if cdata == "opt_practice_mode":
        m["is_practice"] = True
        m["await_input"] = "setup_match_names"
        return bot.edit_message_text(
            "🎯 *PRACTICE MATCH MODE ACTIVATED!*\n\n✍️ Format: `Team A | Team B | Total Overs`\nExample: `Practice 1 | Practice 2 | 5`",
            chat_id=cid, message_id=mid, parse_mode="Markdown"
        )

    if cdata == "opt_quick_mode":
        k = InlineKeyboardMarkup(row_width=1)
        k.add(
            InlineKeyboardButton("1️⃣ Opponent Bat First (Target)", callback_data="qm_opp_bat_first"),
            InlineKeyboardButton("2️⃣ My Team Bat First (Quick 2nd Inn)", callback_data="qm_my_bat_first")
        )
        return bot.edit_message_text("⚡ QUICK OPPONENT MODE:", chat_id=cid, message_id=mid, reply_markup=k)

    if cdata == "qm_opp_bat_first":
        m["await_input"] = "qm_opp_first_input"
        return bot.edit_message_text("✍️ Bhejein: `OpponentName | TargetRuns | Overs`\nExample: `Rawalpindi XI | 85 | 8`", chat_id=cid, message_id=mid, parse_mode="Markdown")

    if cdata == "qm_my_bat_first":
        m["await_input"] = "qm_my_first_input"
        return bot.edit_message_text("✍️ Bhejein: `MyTeamName | OpponentName | TotalOvers`\nExample: `Mumbai Strikers | Local XI | 8`", chat_id=cid, message_id=mid, parse_mode="Markdown")

    if cdata == "opt_edit_menu":
        k = InlineKeyboardMarkup(row_width=2)
        k.add(
            InlineKeyboardButton("🔄 Change Striker", callback_data="pick_replace_str"),
            InlineKeyboardButton("🔄 Change Non-Striker", callback_data="pick_replace_nstr")
        )
        k.add(
            InlineKeyboardButton("🎯 Change Bowler", callback_data="pick_replace_bowl"),
            InlineKeyboardButton("🛠️ Live Score Fix", callback_data="opt_score_fix")
        )
        k.add(
            InlineKeyboardButton("➕ Add Player", callback_data="opt_add_player_mid"),
            InlineKeyboardButton("⚠️ Abandon Match", callback_data="opt_abandon_match")
        )
        k.add(InlineKeyboardButton("⬅️ Back to Scoring", callback_data="opt_live_c"))
        return bot.edit_message_text("⚙️ MATCH MENU & CONTROLS:", chat_id=cid, message_id=mid, reply_markup=k)

    if cdata == "opt_toss":
        m["is_practice"] = False
        m["await_input"] = "setup_match_names"
        return bot.edit_message_text(
            "✍️ Setup Bhejein:\n`Team A | Team B | Total Overs`\nExample: `Mumbai Strikers | Team Unity | 10`",
            chat_id=cid, message_id=mid, parse_mode="Markdown"
        )

    if cdata.startswith("toss_call_"):
        call_side = cdata.split("_")[2]
        coin = random.choice(["heads", "tails"])
        won = m["t1"] if call_side == coin else m["t2"]
        m["toss_winner"] = won
        k = InlineKeyboardMarkup(row_width=2)
        k.add(
            InlineKeyboardButton("🏏 Choose Bat", callback_data=f"toss_el_bat_{won}"),
            InlineKeyboardButton("🎯 Choose Bowl", callback_data=f"toss_el_bowl_{won}")
        )
        return bot.edit_message_text(f"🪙 Result: *{coin.upper()}*!\n🏆 *{won}* won toss!", chat_id=cid, message_id=mid, reply_markup=k, parse_mode="Markdown")

    if cdata.startswith("toss_el_"):
        parts = cdata.split("_")
        choice, won = parts[2], parts[3]
        other = m["t2"] if won == m["t1"] else m["t1"]
        m["bat_tm"] = won if choice == "bat" else other
        m["bowl_tm"] = other if choice == "bat" else won
        m["await_input"] = "setup_squad_t1"
        return bot.edit_message_text(f"📋 *{m['bat_tm']}* ke saare players comma lagakar bhejein:\n`Talha, Adeeb, Mustafa, Wasim...`", chat_id=cid, message_id=mid, parse_mode="Markdown")

    if cdata.startswith("pick_init_"):
        role = cdata.replace("pick_init_", "")
        tm = m["bat_tm"] if role in ["str", "nstr"] else m["bowl_tm"]
        lbl = "Striker" if role == "str" else ("Non-Striker" if role == "nstr" else "Opening Bowler")
        return bot.edit_message_text(f"👉 Select {lbl} ({tm}):", chat_id=cid, message_id=mid, reply_markup=get_squad_picker(tm, f"init_{role}"))

    if cdata.startswith("sel_init_"):
        parts = cdata.split("_")
        role, p_name = parts[2], parts[3]
        if role == "str":
            m["striker"] = p_name
            ensure_player(p_name, True)
            return bot.edit_message_text(f"✅ Striker: *{p_name}*\n\n👉 Ab Non-Striker select karein:", chat_id=cid, message_id=mid, reply_markup=get_squad_picker(m["bat_tm"], "init_nstr"), parse_mode="Markdown")
        elif role == "nstr":
            m["non_striker"] = p_name
            ensure_player(p_name, True)
            return bot.edit_message_text(f"✅ Non-Striker: *{p_name}*\n\n👉 Ab Opening Bowler select karein:", chat_id=cid, message_id=mid, reply_markup=get_squad_picker(m["bowl_tm"], "init_bowl"), parse_mode="Markdown")
        elif role == "bowl":
            m["bowler"] = p_name
            ensure_player(p_name, False)
            m["active"] = True
            return bot.edit_message_text(live_card_text(), chat_id=cid, message_id=mid, reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

    if cdata.startswith("pick_replace_"):
        target = cdata.replace("pick_replace_", "")
        tm = m["bat_tm"] if target in ["str", "nstr"] else m["bowl_tm"]
        return bot.edit_message_text(f"Select replacement for {target}:", chat_id=cid, message_id=mid, reply_markup=get_squad_picker(tm, target))

    if cdata.startswith("sel_"):
        parts = cdata.split("_")
        purpose, p_name = parts[1], parts[2]
        if purpose == "str":
            m["striker"] = p_name
            ensure_player(p_name, True)
        elif purpose == "nstr":
            m["non_striker"] = p_name
            ensure_player(p_name, True)
        elif purpose == "bowl":
            m["bowler"] = p_name
            ensure_player(p_name, False)
        return bot.edit_message_text(live_card_text(), chat_id=cid, message_id=mid, reply
