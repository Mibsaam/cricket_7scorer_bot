import os
import json
import copy
import time
import random
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8812331993:AAEREVNSHoSAIgPMYAz1dG1rhJP_RYRV0-w"

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
    "last_commentary": ""
}

def get_overs_str(b):
    return str(b // 6) + "." + str(b % 6)

def get_crr(r, b):
    if b > 0:
        return "{:.2f}".format(r / (b / 6))
    return "0.00"

def get_h2h_str(t1, t2):
    k1 = t1 + "_vs_" + t2
    k2 = t2 + "_vs_" + t1
    w1 = H2H_DB.get(k1, 0)
    w2 = H2H_DB.get(k2, 0)
    return "H2H: " + t1 + " (" + str(w1) + ") - (" + str(w2) + ") " + t2

def get_rrr_line():
    if m["inn"] != 2 or m["target"] <= 0:
        return ""
    needed = m["target"] - m["runs"]
    rem_b = (m["max_ov"] * 6) - m["balls"]
    if needed <= 0:
        return "\nTarget Achieved! " + m["bat_tm"] + " won!"
    if rem_b <= 0:
        return "\nOvers Finished! Need " + str(needed) + " off 0 balls"
    rrr = needed / (rem_b / 6)
    return "\nTarget: " + str(m["target"]) + " (Need " + str(needed) + " off " + str(rem_b) + "b | RRR: " + "{:.2f}".format(rrr) + ")"

def live_card_text():
    s_n = m["striker"] or "Bat 1"
    ns_n = m["non_striker"] or "Bat 2"
    bw_n = m["bowler"] or "Bowler 1"
    s = m["batsmen"].get(s_n, {"r": 0, "b": 0, "4s": 0, "6s": 0})
    ns = m["batsmen"].get(ns_n, {"r": 0, "b": 0, "4s": 0, "6s": 0})
    bw = m["bowlers"].get(bw_n, {"r": 0, "b": 0, "w": 0, "m": 0})
    
    fh_alert = "\nFREE HIT BALL!" if m["free_hit"] else ""
    if m["cur_over"]:
        ov_str = " ".join(["[" + str(x) + "]" for x in m["cur_over"]])
    else:
        ov_str = "Yet to start"
    tot_ext = sum(m["extras"].values())
    prac_tag = "[TEST / PRACTICE MODE]\n" if m["is_practice"] else ""
    comm_box = "\nCommentary: " + m["last_commentary"] + "\n" if m["last_commentary"] else ""
    
    txt = (
        prac_tag +
        m["bat_tm"] + " vs " + m["bowl_tm"] + " (Innings " + str(m["inn"]) + ")\n" +
        get_h2h_str(m["t1"], m["t2"]) + "\n" +
        "LIVE: " + str(m["runs"]) + "/" + str(m["wkts"]) + " (" + get_overs_str(m["balls"]) + "/" + str(m["max_ov"]) + " ov) | CRR: " + get_crr(m["runs"], m["balls"]) +
        get_rrr_line() + comm_box + fh_alert + "\n" +
        "-----------------------------------------\n" +
        s_n + "*: " + str(s["r"]) + " (" + str(s["b"]) + "b) [4s:" + str(s["4s"]) + " 6s:" + str(s["6s"]) + "]\n" +
        ns_n + ": " + str(ns["r"]) + " (" + str(ns["b"]) + "b) [4s:" + str(ns["4s"]) + " 6s:" + str(ns["6s"]) + "]\n" +
        "Partnership: " + str(m["partnership_runs"]) + " (" + str(m["partnership_balls"]) + "b)\n" +
        bw_n + ": " + str(bw["w"]) + "/" + str(bw["r"]) + " (" + get_overs_str(bw["b"]) + " ov)\n" +
        "-----------------------------------------\n" +
        "Extras: " + str(tot_ext) + " (Wd:" + str(m["extras"]["wd"]) + " Nb:" + str(m["extras"]["nb"]) + " B:" + str(m["extras"]["b"]) + " LB:" + str(m["extras"]["lb"]) + ")\n" +
        "This Over: " + ov_str
    )
    return txt

def full_scorecard_text():
    tot_ext = sum(m["extras"].values())
    txt = (
        "FULL MATCH SCORECARD\n" +
        m["bat_tm"] + " : " + str(m["runs"]) + "/" + str(m["wkts"]) + " (" + get_overs_str(m["balls"]) + "/" + str(m["max_ov"]) + " ov)\n" +
        "Extras: " + str(tot_ext) + "\n" +
        "CRR: " + get_crr(m["runs"], m["balls"]) + get_rrr_line() + "\n" +
        "=========================================\n" +
        "BATTING STATS:\n"
    )
    for n, s in m["batsmen"].items():
        if s["b"] > 0:
            sr = "{:.1f}".format(s["r"] / s["b"] * 100)
        else:
            sr = "0.0"
        status = " (Out: " + s.get("how_out", "out") + ")" if s.get("out") else " (Not Out)"
        txt += "- " + n + status + ": " + str(s["r"]) + " (" + str(s["b"]) + "b) [4s:" + str(s["4s"]) + ", 6s:" + str(s["6s"]) + "] SR: " + sr + "\n"
    
    txt += "-----------------------------------------\nBOWLING STATS:\n"
    for n, bw in m["bowlers"].items():
        if bw["b"] > 0:
            econ = "{:.2f}".format(bw["r"] / (bw["b"] / 6))
        else:
            econ = "0.00"
        txt += "- " + n + ": " + get_overs_str(bw["b"]) + " ov | " + str(bw["r"]) + " runs | " + str(bw["w"]) + " wkts | Econ: " + econ + "\n"
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
            desc = str(s["r"]) + " Runs (" + str(s["b"]) + "b)"
    for n, bw in m["bowlers"].items():
        bw_pts = (bw["w"] * 25) - (bw["r"] // 3)
        if bw_pts > max_pts:
            max_pts = bw_pts
            best_p = n
            desc = str(bw["w"]) + " Wkts, " + str(bw["r"]) + " Runs"
    return best_p + " [" + desc + "]"

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
        InlineKeyboardButton("WICKET", callback_data="sc_wkt_ask")
    )
    k.add(
        InlineKeyboardButton("Bye (+1)", callback_data="sc_team_bye_1"),
        InlineKeyboardButton("Strike", callback_data="sc_swap"),
        InlineKeyboardButton("Bowler", callback_data="sc_ch_bowl_mid")
    )
    k.add(
        InlineKeyboardButton("Undo", callback_data="sc_undo"),
        InlineKeyboardButton("Scorecard", callback_data="sc_full_view"),
        InlineKeyboardButton("Options", callback_data="opt_edit_menu")
    )
    return k

def get_squad_picker(team_name, purpose):
    k = InlineKeyboardMarkup(row_width=2)
    squad = m["t1_squad"] if team_name == m["t1"] else m["t2_squad"]
    for p in squad:
        if purpose in ["str", "nstr", "bat"] and p in m["batsmen"] and m["batsmen"][p].get("out"):
            continue
        k.add(InlineKeyboardButton(p, callback_data="sel_" + purpose + "_" + p))
    k.add(InlineKeyboardButton("Type Custom Name", callback_data="sel_custom_" + purpose))
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

    h2h_key = winner_tm + "_vs_" + loser_tm
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
    k = InlineKeyboardMarkup(row_width=2)
    k.add(
        InlineKeyboardButton("Real Match", callback_data="opt_toss"),
        InlineKeyboardButton("Test / Tour Mode", callback_data="opt_test_mode")
    )
    k.add(
        InlineKeyboardButton("Quick Opponent", callback_data="opt_quick_mode"),
        InlineKeyboardButton("Standings", callback_data="sc_teams_view")
    )
    k.add(InlineKeyboardButton("Leaderboard", callback_data="sc_lead_view"))
    bot.reply_to(msg, "Cricket Scoring System:\nSelect an option below:", reply_markup=k)

@bot.message_handler(commands=['score', 'scorecard'])
def cmd_score(msg):
    if not m["active"]:
        return bot.reply_to(msg, "No match active. Type /start to begin.")
    txt = live_card_text()
    kb = get_scoring_keyboard()
    bot.reply_to(msg, txt, reply_markup=kb)

@bot.callback_query_handler(func=lambda call: True)
def on_action(call):
    cid = call.message.chat.id
    mid = call.message.message_id
    cdata = call.data

    if cdata == "opt_test_mode":
        m["active"] = True
        m["is_practice"] = True
        m["t1"] = "Test Team A"
        m["t2"] = "Test Team B"
        m["max_ov"] = 5
        m["inn"] = 1
        m["bat_tm"] = "Test Team A"
        m["bowl_tm"] = "Test Team B"
        m["striker"] = "Demo Striker"
        m["non_striker"] = "Demo Non-Striker"
        m["bowler"] = "Demo Bowler"
        m["t1_squad"] = ["Demo Striker", "Demo Non-Striker", "Player 3", "Player 4"]
        m["t2_squad"] = ["Demo Bowler", "Bowler 2", "Bowler 3"]
        m["runs"] = 0
        m["wkts"] = 0
        m["balls"] = 0
        m["partnership_runs"] = 0
        m["partnership_balls"] = 0
        m["extras"] = {"wd": 0, "nb": 0, "b": 0, "lb": 0}
        m["cur_over"].clear()
        m["over_history"].clear()
        m["batsmen"].clear()
        m["bowlers"].clear()
        m["history"].clear()
        ensure_player(m["striker"], True)
        ensure_player(m["non_striker"], True)
        ensure_player(m["bowler"], False)
        txt = "TEST / DEMO MODE ACTIVATED\n\n" + live_card_text()
        kb = get_scoring_keyboard()
        return bot.edit_message_text(txt, chat_id=cid, message_id=mid, reply_markup=kb)

    if cdata == "sc_teams_view":
        txt = "TEAM STANDINGS\n====================\n"
        for tname, st in TEAMS_DB.items():
            if st["p"] > 0:
                win_pct = "{:.1f}".format(st["w"] / st["p"] * 100) + "%"
            else:
                win_pct = "0%"
            txt += tname + "\nP: " + str(st["p"]) + " | W: " + str(st["w"]) + " | L: " + str(st["l"]) + " | Win%: " + win_pct + "\n\n"
        res_txt = txt if TEAMS_DB else "No team records yet."
        bot.send_message(cid, res_txt)
        return bot.answer_callback_query(call.id)

    if cdata == "sc_lead_view":
        top_runs = sorted(CAREER_DB.items(), key=lambda x: x[1]["runs"], reverse=True)
        top_wkts = sorted(CAREER_DB.items(), key=lambda x: x[1]["wkts"], reverse=True)
        txt = "CAREER LEADERBOARD\n=====================\nTOP RUNS:\n"
        for i, (p, s) in enumerate(top_runs[:5], 1):
            txt += str(i) + ". " + p + ": " + str(s["runs"]) + " Runs (" + str(s["inns"]) + " Inns)\n"
        txt += "\nTOP WKTS:\n"
        for i, (p, s) in enumerate(top_wkts[:5], 1):
            txt += str(i) + ". " + p + ": " + str(s["wkts"]) + " Wkts\n"
        res_txt = txt if CAREER_DB else "No player records yet."
        bot.send_message(cid, res_txt)
        return bot.answer_callback_query(call.id)

    if cdata == "sc_full_view":
        if not m["active"]:
            return bot.answer_callback_query(call.id, "No active match!", show_alert=True)
        txt = full_scorecard_text()
        bot.send_message(cid, txt)
        return bot.answer_callback_query(call.id)

    if cdata == "opt_edit_menu":
        k = InlineKeyboardMarkup(row_width=2)
        k.add(
            InlineKeyboardButton("Add Player", callback_data="opt_add_player_mid"),
            InlineKeyboardButton("Rename Player", callback_data="opt_rename_player")
        )
        k.add(
            InlineKeyboardButton("Change Striker", callback_data="pick_replace_str"),
            InlineKeyboardButton("Change Non-Striker", callback_data="pick_replace_nstr")
        )
        k.add(
            InlineKeyboardButton("Change Bowler", callback_data="pick_replace_bowl"),
            InlineKeyboardButton("Fix Score (+/-)", callback_data="opt_score_fix")
        )
        k.add(
            InlineKeyboardButton("Abandon Match", callback_data="opt_abandon_match"),
            InlineKeyboardButton("Back to Scoring", callback_data="opt_live_c")
        )
        return bot.edit_message_text("SCORER CONTROLS:", chat_id=cid, message_id=mid, reply_markup=k)

    if cdata == "opt_add_player_mid":
        m["await_input"] = "add_player_mid"
        txt = "Add Player:\nSend in format: PlayerName | TeamName"
        return bot.edit_message_text(txt, chat_id=cid, message_id=mid)

    if cdata == "opt_rename_player":
        m["await_input"] = "rename_player_input"
        txt = "Rename Player:\nSend in format: OldName | NewName"
        return bot.edit_message_text(txt, chat_id=cid, message_id=mid)

    if cdata == "opt_score_fix":
        m["await_input"] = "fix_match_score"
        txt = "Fix Score:\nSend delta: RunsDelta | WicketsDelta\nExample: -5 | 0"
        return bot.edit_message_text(txt, chat_id=cid, message_id=mid)

    if cdata == "opt_abandon_match":
        m["active"] = False
        return bot.edit_message_text("Match cancelled / abandoned.", chat_id=cid, message_id=mid)

    if cdata == "opt_quick_mode":
        k = InlineKeyboardMarkup(row_width=1)
        k.add(
            InlineKeyboardButton("Opponent Bat First (Target)", callback_data="qm_opp_bat_first"),
            InlineKeyboardButton("My Team Bat First", callback_data="qm_my_bat_first")
        )
        return bot.edit_message_text("QUICK OPPONENT MODE:", chat_id=cid, message_id=mid, reply_markup=k)

    if cdata == "qm_opp_bat_first":
        m["await_input"] = "qm_opp_first_input"
        txt = "Send: OpponentName | TargetRuns | Overs\nExample: Opponent XI | 85 | 8"
        return bot.edit_message_text(txt, chat_id=cid, message_id=mid)

    if cdata == "qm_my_bat_first":
        m["await_input"] = "qm_my_first_input"
        txt = "Send: MyTeamName | OpponentName | TotalOvers\nExample: Team A | Team B | 8"
        return bot.edit_message_text(txt, chat_id=cid, message_id=mid)

    if cdata == "opt_toss":
        m["is_practice"] = False
        m["await_input"] = "setup_match_names"
        txt = "Setup: Team A | Team B | Total Overs\nExample: Mumbai | Unity | 10"
        return bot.edit_message_text(txt, chat_id=cid, message_id=mid)

    if cdata.startswith("toss_call_"):
        call_side = cdata.split("_")[2]
        coin = random.choice(["heads", "tails"])
        won = m["t1"] if call_side == coin else m["t2"]
        m["toss_winner"] = won
        k = InlineKeyboardMarkup(row_width=2)
        k.add(
            InlineKeyboardButton("Choose Bat", callback_data="toss_el_bat_" + won),
            InlineKeyboardButton("Choose Bowl", callback_data="toss_el_bowl_" + won)
        )
        txt = "Toss Result: " + coin.upper() + "\n" + won + " won toss!"
        return bot.edit_message_text(txt, chat_id=cid, message_id=mid, reply_markup=k)

    if cdata.startswith("toss_el_"):
        parts = cdata.split("_")
        choice = parts[2]
        won = parts[3]
        other = m["t2"] if won == m["t1"] else m["t1"]
        m["bat_tm"] = won if choice == "bat" else other
        m["bowl_tm"] = other if choice == "bat" else won
        m["await_input"] = "setup_squad_t1"
        txt = "Send squad for " + m["bat_tm"] + " (comma separated):\nExample: Talha, Adeeb, Mustafa, Wasim"
        return bot.edit_message_text(txt, chat_id=cid, message_id=mid)

    if cdata.startswith("pick_init_"):
        role = cdata.replace("pick_init_", "")
        tm = m["bat_tm"] if role in ["str", "nstr"] else m["bowl_tm"]
        if role == "str":
            lbl = "Striker"
        elif role == "nstr":
            lbl = "Non-Striker"
        else:
            lbl = "Opening Bowler"
        picker_kb = get_squad_picker(tm, "init_" + role)
        return bot.edit_message_text("Select " + lbl + " (" + tm + "):", chat_id=cid, message_id=mid, reply_markup=picker_kb)

    if cdata.startswith("sel_init_"):
        parts = cdata.split("_")
        role = parts[2]
        p_name = parts[3]
        if role == "str":
            m["striker"] = p_name
            ensure_player(p_name, True)
            next_kb = get_squad_picker(m["bat_tm"], "init_nstr")
            txt = "Striker: " + p_name + "\nNow select Non-Striker:"
            return bot.edit_message_text(txt, chat_id=cid, message_id=mid, reply_markup=next_kb)
        elif role == "nstr":
            m["non_striker"] = p_name
            ensure_player(p_name, True)
            next_kb = get_squad_picker(m["bowl_tm"], "init_bowl")
            txt = "Non-Striker: " + p_name + "\nNow select Opening Bowler:"
            return bot.edit_message_text(txt, chat_id=cid, message_id=mid, reply_markup=next_kb)
        elif role == "bowl":
            m["bowler"] = p_name
            ensur
