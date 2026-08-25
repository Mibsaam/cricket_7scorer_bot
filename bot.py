import os, json, copy, threading, time, urllib.request, random
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8812331993:AAEREVNSHoSAIgPMYAz1dG1rhJP_RYRV0-w"
ADMIN_ID = 874225351

app = Flask(__name__)
@app.route("/")
def h(): return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

def auto_ping():
    while True:
        time.sleep(300)
        try:
            r_url = os.environ.get("RENDER_EXTERNAL_URL")
            if r_url: urllib.request.urlopen(r_url)
        except: pass

threading.Thread(target=auto_ping, daemon=True).start()

bot = telebot.TeleBot(BOT_TOKEN)

CAREER_FILE = "career_data.json"
TEAMS_FILE = "teams_data.json"
H2H_FILE = "h2h_data.json"

def load_json(fpath):
    if os.path.exists(fpath):
        try:
            with open(fpath, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_json(fpath, data):
    try:
        with open(fpath, "w") as f: json.dump(data, f)
    except: pass

CAREER_DB = load_json(CAREER_FILE)
TEAMS_DB = load_json(TEAMS_FILE)
H2H_DB = load_json(H2H_FILE)

m = {
    "active": False, "t1": "Team A", "t2": "Team B", "max_ov": 10, "inn": 1,
    "bat_tm": "", "bowl_tm": "", "target": 0, "scorers": set([ADMIN_ID]),
    "t1_squad": [], "t2_squad": [], "is_quick_mode": False, "is_practice": False,
    "striker": "Bat 1", "non_striker": "Bat 2", "bowler": "Bowler 1",
    "runs": 0, "wkts": 0, "balls": 0,
    "partnership_runs": 0, "partnership_balls": 0,
    "extras": {"wd": 0, "nb": 0, "b": 0, "lb": 0},
    "free_hit": False, "await_input": None,
    "cur_over": [], "over_history": [],
    "batsmen": {}, "bowlers": {},
    "toss_winner": "", "history": [], "inn1_summary": "", "last_commentary": ""
}

def is_scorer(uid, un):
    return uid == ADMIN_ID or uid in m["scorers"] or un in m["scorers"]

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
    if m["inn"] != 2 or m["target"] <= 0: return ""
    needed = m["target"] - m["runs"]
    rem_b = (m["max_ov"] * 6) - m["balls"]
    if needed <= 0: return f"\n🏆 *Target Achieved! {m['bat_tm']} won!*"
    if rem_b <= 0: return f"\n🏁 *Overs Finished! Need {needed} off 0 balls*"
    rrr = (needed / (rem_b / 6))
    return f"\n🎯 *Target: {m['target']}* (Need *{needed}* runs off *{rem_b}* balls | RRR: *{rrr:.2f}*)"

def live_card_text():
    s_n, ns_n, bw_n = m["striker"], m["non_striker"], m["bowler"]
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
    best_p, max_pts, desc = "None", -999, ""
    for n, s in m["batsmen"].items():
        pts = s["r"] + (s["4s"] * 2) + (s["6s"] * 3)
        if pts > max_pts:
            max_pts, best_p, desc = pts, n, f"{s['r']} Runs ({s['b']}b)"
    for n, bw in m["bowlers"].items():
        bw_pts = (bw["w"] * 25) - (bw["r"] // 3)
        if bw_pts > max_pts:
            max_pts, best_p, desc = bw_pts, n, f"{bw['w']} Wkts, {bw['r']} Runs"
    return f"{best_p} [{desc}]"

def get_career_profile(name):
    pn = name.strip().title()
    p = CAREER_DB.get(pn)
    if not p:
        return f"👤 *{pn}* (Debutant)\n• Matches: 0 | Runs: 0 | Wkts: 0"
    sr = f"{(p['runs'] / p['balls'] * 100):.1f}" if p['balls'] > 0 else "0.0"
    econ = f"{(p['bowl_r'] / (p['bowl_b'] / 6)):.2f}" if p['bowl_b'] > 0 else "0.00"
    form_tag = "🔥 IN-FORM (Danger Man)" if p['runs'] > 150 else "⚡ Regular Player"
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
        if purpose in ["str", "nstr", "bat"] and p in m["batsmen"] and m["batsmen"][p].get("out"): continue
        k.add(InlineKeyboardButton(p, callback_data=f"sel_{purpose}_{p}"))
    k.add(InlineKeyboardButton("✍️ Type Custom Name", callback_data=f"sel_custom_{purpose}"))
    return k

def save_state():
    if len(m["history"]) > 25: m["history"].pop(0)
    snap = copy.deepcopy({
        "runs": m["runs"], "wkts": m["wkts"], "balls": m["balls"],
        "partnership_runs": m["partnership_runs"], "partnership_balls": m["partnership_balls"],
        "striker": m["striker"], "non_striker": m["non_striker"], "bowler": m["bowler"],
        "extras": copy.deepcopy(m["extras"]), "free_hit": m["free_hit"],
        "cur_over": list(m["cur_over"]), "over_history": copy.deepcopy(m["over_history"]),
        "batsmen": copy.deepcopy(m["batsmen"]), "bowlers": copy.deepcopy(m["bowlers"]),
        "last_commentary": m["last_commentary"]
    })
    m["history"].append(snap)

def undo_state():
    if not m["history"]: return False
    last = m["history"].pop()
    for k, v in last.items(): m[k] = v
    return True

def ensure_player(n, is_bat=True):
    if is_bat and n != "NONE" and n not in m["batsmen"]:
        m["batsmen"][n] = {"r": 0, "b": 0, "4s": 0, "6s": 0, "out": False, "how_out": ""}
    elif not is_bat and n not in m["bowlers"]:
        m["bowlers"][n] = {"r": 0, "b": 0, "w": 0, "m": 0}

def update_lifetime_records(winner_tm, loser_tm):
    if m["is_practice"]: return
    for tm in [winner_tm, loser_tm]:
        if tm not in TEAMS_DB: TEAMS_DB[tm] = {"p": 0, "w": 0, "l": 0, "hs": 0, "squad": []}
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
        if s["b"] > 0 or s.get("out"): CAREER_DB[pn]["inns"] += 1
        CAREER_DB[pn]["runs"] += s["r"]
        CAREER_DB[pn]["balls"] += s["b"]
        CAREER_DB[pn]["4s"] += s["4s"]
        CAREER_DB[pn]["6s"] += s["6s"]
        if s["r"] >= 100: CAREER_DB[pn]["100s"] += 1
        elif s["r"] >= 50: CAREER_DB[pn]["50s"] += 1
        if s["r"] > CAREER_DB[pn]["hs"]: CAREER_DB[pn]["hs"] = s["r"]

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
        InlineKeyboardButton("🏏 Real Match (Stats Save)", callback_data="opt_toss"),
        InlineKeyboardButton("🎯 Practice Match", callback_data="opt_practice_mode")
    )
    k.add(
        InlineKeyboardButton("⚡ Quick Opponent", callback_data="opt_quick_mode"),
        InlineKeyboardButton("👑 Add Scorer", callback_data="opt_add_sc")
    )
    k.add(
        InlineKeyboardButton("🛡️ Standings", callback_data="sc_teams_view"),
        InlineKeyboardButton("🏆 Leaderboard", callback_data="sc_lead_view")
    )
    bot.reply_to(msg, "🏏 Pro Cricket Scoring & Championship Engine", reply_markup=k)

@bot.message_handler(commands=['score', 'scorecard'])
def cmd_score(msg):
    if not m["active"]: return bot.reply_to(msg, "⚠️ Abhi koi match active nahi hai.")
    bot.reply_to(msg, live_card_text(), reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

@bot.message_handler(commands=['player', 'profile'])
def cmd_prof(msg):
    pname = msg.text.replace("/player", "").replace("/profile", "").strip()
    if not pname: return bot.reply_to(msg, "Format: `/player Name`", parse_mode="Markdown")
    bot.reply_to(msg, get_career_profile(pname), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def on_action(call):
    uid, un = call.from_user.id, (call.from_user.username or "").lower()
    cid, mid, cdata = call.message.chat.id, call.message.message_id, call.data

    if cdata == "sc_teams_view":
        txt = "🛡️ TEAM STANDINGS 🛡️\n====================\n"
        for tname, st in TEAMS_DB.items():
            win_pct = f"{(st['w']/st['p']*100):.1f}%" if st['p'] > 0 else "0%"
            txt += f"🏆 *{tname}*\n• P: {st['p']} | W: {st['w']} | L: {st['l']} | Win%: {win_pct} | HS: {st.get('hs', 0)}\n\n"
        bot.send_message(cid, txt, parse_mode="Markdown")
        return bot.answer_callback_query(call.id)

    if cdata == "sc_lead_view":
        top_runs = sorted(CAREER_DB.items(), key=lambda x: x[1]["runs"], reverse=True)
        top_wkts = sorted(CAREER_DB.items(), key=lambda x: x[1]["wkts"], reverse=True)
        txt = "🏆 CAREER LEADERBOARD 🏆\n=====================\n🟠 TOP RUNS:\n"
        for i, (p, s) in enumerate(top_runs[:5], 1): txt += f"{i}. {p}: {s['runs']} Runs ({s['inns']} Inns)\n"
        txt += "\n🟣 TOP WKTS:\n"
        for i, (p, s) in enumerate(top_wkts[:5], 1): txt += f"{i}. {p}: {s['wkts']} Wkts\n"
        bot.send_message(cid, txt)
        return bot.answer_callback_query(call.id)

    if cdata == "sc_full_view":
        if not m["active"]: return bot.answer_callback_query(call.id, "No active match!", show_alert=True)
        bot.send_message(cid, full_scorecard_text())
        return bot.answer_callback_query(call.id)

    if not is_scorer(uid, un):
        return bot.answer_callback_query(call.id, "⚠️ Authorized scorers only!", show_alert=True)

    if cdata == "opt_practice_mode":
        m["is_practice"] = True
        m["await_input"] = "setup_match_names"
        return bot.edit_message_text(
            "🎯 *PRACTICE MATCH MODE ACTIVATED!*\n(Is match ka data leaderboard mein count nahi hoga).\n\n✍️ Setup Bhejein:\n`Team A | Team B | Total Overs`\nExample: `Practice 1 | Practice 2 | 5`",
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
        return bot.edit_message_text("✍️ Opponent Score Bhejein:\n`OpponentName | TargetRuns | Overs`\nExample: `Rawalpindi XI | 85 | 8`", chat_id=cid, message_id=mid, parse_mode="Markdown")

    if cdata == "qm_my_bat_first":
        m["await_input"] = "qm_my_first_input"
        return bot.edit_message_text("✍️ Setup Bhejein:\n`MyTeamName | OpponentName | TotalOvers`\nExample: `Mumbai Strikers | Local XI | 8`", chat_id=cid, message_id=mid, parse_mode="Markdown")

    if cdata == "opt_edit_menu":
        k = InlineKeyboardMarkup(row_width=2)
        k.add(
            InlineKeyboardButton("🔄 Change Striker", callback_data="pick_replace_str"),
            InlineKeyboardButton("🔄 Change Non-Striker", callback_data="pick_replace_nstr")
        )
        k.add(
            InlineKeyboardButton("🎯 Change Bowler", callback_data="pick_replace_bowl"),
            InlineKeyboardButton("✏️ Rename / Nickname", callback_data="opt_rename_player")
        )
        k.add(
            InlineKeyboardButton("🛠️ Live Score Fix (+/-)", callback_data="opt_score_fix"),
            InlineKeyboardButton("🌧️ Rain / DLS Par Score", callback_data="opt_dls_calc")
        )
        k.add(
            InlineKeyboardButton("➕ Add Player", callback_data="opt_add_player_mid"),
            InlineKeyboardButton("⚠️ Abandon Match", callback_data="opt_abandon_match")
        )
        k.add(InlineKeyboardButton("⬅️ Back to Scoring", callback_data="opt_live_c"))
        return bot.edit_message_text("⚙️ MATCH MENU & CONTROLS:", chat_id=cid, message_id=mid, reply_markup=k)

    if cdata == "opt_rename_player":
        m["await_input"] = "rename_player_input"
        return bot.edit_message_text(
            "✏️ *Rename / Nickname Manager:*\n\nPurane naam se naye naam par stats shift karne ke liye format bhejein:\n`OldName | NewName`\nExample: `Adeeb | Adeeb Bhai (Danger)`",
            chat_id=cid, message_id=mid, parse_mode="Markdown"
        )

    if cdata == "opt_dls_calc":
        m["await_input"] = "dls_input_prompt"
        return bot.edit_message_text(
            "🌧️ *Rain Interruption / DLS Par Score Wizard*\nBhejein: `OriginalTarget | OriginalOvers | OversPlayedSoFar`\nExample: `100 | 10 | 6`",
            chat_id=cid, message_id=mid, parse_mode="Markdown"
        )

    if cdata == "opt_abandon_match":
        k = InlineKeyboardMarkup(row_width=2)
        k.add(
            InlineKeyboardButton("❌ Yes, Cancel Match", callback_data="confirm_abandon"),
            InlineKeyboardButton("✔️ No, Continue", callback_data="opt_live_c")
        )
        return bot.edit_message_text("⚠️ Kya aap match cancel (abandon) karna chahte hain?", chat_id=cid, message_id=mid, reply_markup=k)

    if cdata == "confirm_abandon":
        m["active"] = False
        return bot.edit_message_text("🛑 Match has been successfully abandoned.", chat_id=cid, message_id=mid)

    if cdata == "opt_score_fix":
        m["await_input"] = "fix_match_score"
        return bot.edit_message_text("✍️ Format: `RunsDelta | WicketsDelta` (e.g. `-5 | 0`)", chat_id=cid, message_id=mid, parse_mode="Markdown")

    if cdata == "sc_ch_bowl_mid":
        return bot.edit_message_text(f"Select Bowler ({m['bowl_tm']}):", chat_id=cid, message_id=mid, reply_markup=get_squad_picker(m["bowl_tm"], "bowl"))

    if cdata == "opt_add_player_mid":
        m["await_input"] = "add_player_mid"
        return bot.edit_message_text("✍️ Naye player ka naam aur team:\n`PlayerName | TeamName`", chat_id=cid, message_id=mid, parse_mode="Markdown")

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

    if cdata == "opt_add_sc":
        m["await_input"] = "add_scorer"
        return bot.edit_message_text("✍️ Naye Scorer ka @username bhejein:", chat_id=cid, message_id=mid)

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
            bot.send_message(cid, f"📢 *New Batsman Arrival:*\n{get_career_profile(p_name)}", parse_mode="Markdown")
        elif purpose == "nstr":
            m["non_striker"] = p_name
            ensure_player(p_name, True)
        elif purpose == "bowl":
            m["bowler"] = p_name
            ensure_player(p_name, False)
        return bot.edit_message_text(live_card_text(), chat_id=cid, message_id=mid, reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

    if cdata == "opt_live_c":
        if not m["active"]: return bot.answer_callback_query(call.id, "No match active!", show_alert=True)
        return bot.edit_message_text(live_card_text(), chat_id=cid, message_id=mid, reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

    if not m["active"]: return bot.answer_callback_query(call.id, "Start match with /menu first!", show_alert=True)

    # DIRECT RUN SCORING
    if cdata.startswith("sc_run_"):
        save_state()
        r = int(cdata.split("_")[2])
        m["runs"] += r
        m["balls"] += 1
        m["partnership_runs"] += r
        m["partnership_balls"] += 1
        s_n, bw_n = m["striker"], m["bowler"]
        ensure_player(s_n, True)
        ensure_player(bw_n, False)

        m["batsmen"][s_n]["r"] += r
        m["batsmen"][s_n]["b"] += 1
        
        if r == 4:
            m["batsmen"][s_n]["4s"] += 1
            m["last_commentary"] = f"🔥 CRACKING SHOT! {s_n} hits a magnificent FOUR!"
        elif r == 6:
            m["batsmen"][s_n]["6s"] += 1
            m["last_commentary"] = f"💥 MASSIVE! {s_n} sends it sailing for a HUGE SIX!"
        elif r == 0:
            m["last_commentary"] = f"Dot ball. Good bowling by {bw_n}."
        else:
            m["last_commentary"] = f"Worked around for {r} run(s)."

        m["bowlers"][bw_n]["r"] += r
        m["bowlers"][bw_n]["b"] += 1
        m["cur_over"].append(str(r))
        m["free_hit"] = False

        if r % 2 != 0: m["striker"], m["non_striker"] = m["non_striker"], m["striker"]
        check_over_or_win(cid, mid)

    elif cdata.startswith("sc_team_"):
        save_state()
        parts = cdata.split("_")
        b_type, b_runs = parts[2], int(parts[3])
        m["runs"] += b_runs
        m["balls"] += 1
        m["partnership_runs"] += b_runs
        m["partnership_balls"] += 1
        m["extras"][b_type] += b_runs
        bw_n, s_n = m["bowler"], m["striker"]
        ensure_player(bw_n, False)
        ensure_player(s_n, True)
        m["bowlers"][bw_n]["b"] += 1
        m["batsmen"][s_n]["b"] += 1
        m["cur_over"].append(f"B{b_runs}" if b_type == "bye" else f"LB{b_runs}")
        m["free_hit"] = False
        m["last_commentary"] = f"Scampered through for {b_runs} bye run(s)."

        if b_runs % 2 != 0: m["striker"], m["non_striker"] = m["non_striker"], m["striker"]
        check_over_or_win(cid, mid)

    elif cdata.startswith("sc_ext_wd_"):
        save_state()
        tot_wd = int(cdata.split("_")[3])
        m["runs"] += tot_wd
        m["partnership_runs"] += tot_wd
        m["extras"]["wd"] += tot_wd
        bw_n = m["bowler"]
        ensure_player(bw_n, False)
        m["bowlers"][bw_n]["r"] += tot_wd
        m["cur_over"].append("Wd" if tot_wd == 1 else f"Wd+{tot_wd-1}")
        m["last_commentary"] = f"Wide ball signaled."
        bot.edit_message_text(live_card_text(), chat_id=cid, message_id=mid, reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

    elif cdata.startswith("sc_ext_nb_"):
        save_state()
        m["runs"] += 1
        m["partnership_runs"] += 1
        m["extras"]["nb"] += 1
        bw_n = m["bowler"]
        ensure_player(bw_n, False)
        m["bowlers"][bw_n]["r"] += 1
        m["cur_over"].append("Nb")
        m["free_hit"] = True
        m["last_commentary"] = f"🚨 NO BALL! Free hit coming up!"
        bot.edit_message_text(live_card_text(), chat_id=cid, message_id=mid, reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

    elif cdata == "sc_swap":
        save_state()
        m["striker"], m["non_striker"] = m["non_striker"], m["striker"]
        bot.edit_message_text(live_card_text(), chat_id=cid, message_id=mid, reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

    elif cdata == "sc_undo":
        if undo_state():
            bot.edit_message_text(live_card_text(), chat_id=cid, message_id=mid, reply_markup=get_scoring_keyboard(), parse_mode="Markdown")
            bot.answer_callback_query(call.id, "Undone!")
        else:
            bot.answer_callback_query(call.id, "Nothing to undo!", show_alert=True)

    # WICKET
    elif cdata == "sc_wkt_ask":
        k = InlineKeyboardMarkup(row_width=2)
        k.add(
            InlineKeyboardButton(f"Striker ({m['striker']})", callback_data="wkt_who_str"),
            InlineKeyboardButton(f"Non-Striker ({m['non_striker']})", callback_data="wkt_who_nstr")
        )
        return bot.edit_message_text("Kaun out hua?", chat_id=cid, message_id=mid, reply_markup=k)

    elif cdata in ["wkt_who_str", "wkt_who_nstr"]:
        who = m["striker"] if cdata == "wkt_who_str" else m["non_striker"]
        k = InlineKeyboardMarkup(row_width=2)
        k.add(
            InlineKeyboardButton("Bowled", callback_data=f"wkt_do_{cdata}_Bowled"),
            InlineKeyboardButton("Caught", callback_data=f"wkt_do_{cdata}_Caught")
        )
        k.add(
            InlineKeyboardButton("Run-Out", callback_data=f"wkt_do_{cdata}_RunOut"),
            InlineKeyboardButton("LBW / Stump", callback_data=f"wkt_do_{cdata}_LBW")
        )
        return bot.edit_message_text(f"*{who}* kaise out hua?", chat_id=cid, message_id=mid, reply_markup=k, parse_mode="Markdown")

    elif cdata.startswith("wkt_do_"):
        parts = cdata.split("_")
        who_tag, how_out = parts[2], parts[3]
        out_who = m["striker"] if "str" == who_tag else m["non_striker"]
        save_state()
        m["wkts"] += 1
        m["partnership_runs"] = 0
        m["partnership_balls"] = 0
        bw_n = m["bowler"]
        ensure_player(bw_n, False)
        ensure_player(out_who, True)

        m["balls"] += 1
        m["bowlers"][bw_n]["b"] += 1
        m["batsmen"][out_who]["b"] += 1

        if how_out != "RunOut" and not m["free_hit"]:
            m["bowlers"][bw_n]["w"] += 1

        m["batsmen"][out_who]["out"] = True
        m["batsmen"][out_who]["how_out"] = how_out
        m["cur_over"].append(f"W({how_out})")
        m["free_hit"] = False
        m["last_commentary"] = f"🔥 WICKET! {out_who} is out ({how_out})!"

        squad_len = len(m["t1_squad"] if m["bat_tm"] == m["t1"] else (m["t2_squad"] if m["t2_squad"] else [1]*11))
        if m["wkts"] >= squad_len - 1 and squad_len > 1:
            return bot.edit_message_text(f"🏁 ALL OUT! ({m['runs']}/{m['wkts']})\n\n" + full_scorecard_text(), chat_id=cid, message_id=mid)

        return bot.edit_message_text(f"☝️ {out_who} is OUT!\n\nSelect New Batsman:", chat_id=cid, message_id=mid, reply_markup=get_squad_picker(m["bat_tm"], who_tag))

def check_over_or_win(cid, mid):
    if m["inn"] == 2 and m["target"] > 0 and m["runs"] >= m["target"]:
        m["active"] = False
        update_lifetime_records(m["bat_tm"], m["bowl_tm"])
        motm = calculate_motm()
        bot.send_message(cid, f"🏆 *{m['bat_tm']}* WON THE MATCH! 🎉\n🌟 Man of the Match: *{motm}*\n\n" + full_scorecard_text(), parse_mode="Markdown")
        return bot.edit_message_text("Match Finished!", chat_id=cid, message_id=mid)

    if m["balls"] > 0 and m["balls"] % 6 == 0 and len(m["cur_over"]) >= 6:
        tot_ov_r = sum([int(x) for x in m["cur_over"] if x.isdigit()])
        m["over_history"].append({
            "balls": list(m["cur_over"]),
            "runs": tot_ov_r,
            "bowler": m["bowler"]
        })
        m["cur_over"].clear()
        m["striker"], m["non_striker"] = m["non_striker"], m["striker"]
        
        if m["balls"] >= m["max_ov"] * 6:
            if m["inn"] == 1:
                if m["is_quick_mode"]:
                    m["await_input"] = "qm_quick_end_score"
                    return bot.edit_message_text(
                        f"🏁 1st Innings Over! Score: *{m['runs']}/{m['wkts']}*\n\n✍️ Opponent ka final score bhejein:\n`OpponentRuns | WicketsLost`\nExample: `74 | 5`",
                        chat_id=cid, message_id=mid, parse_mode="Markdown"
                    )
                m["target"] = m["runs"] + 1
                m["inn"] = 2
                m["inn1_summary"] = f"{m['bat_tm']}: {m['runs']}/{m['wkts']} ({get_overs_str(m['balls'])} ov)"
                m["bat_tm"], m["bowl_tm"] = m["bowl_tm"], m["bat_tm"]
                m["runs"], m["wkts"], m["balls"] = 0, 0, 0
                m["partnership_runs"] = 0
                m["partnership_balls"] = 0
                m["extras"] = {"wd": 0, "nb": 0, "b": 0, "lb": 0}
                m["batsmen"].clear()
                m["bowlers"].clear()
                m["history"].clear()
                m["await_input"] = "setup_inn2_openers"
                return bot.edit_message_text(
                    f"🏁 Innings 1 Over! Target: {m['target']}\n\n✍️ 2nd Innings Openers bhejein:\n`Striker | NonStriker | Bowler`",
                    chat_id=cid, message_id=mid, parse_mode="Markdown"
                )
            else:
                m["active"] = False
                win = m["bat_tm"] if m["runs"] >= m["target"] else m["bowl_tm"]
                lose = m["bowl_tm"] if win == m["bat_tm"] else m["bat_tm"]
                update_lifetime_records(win, lose)
                margin = (m["target"] - 1) - m["runs"]
                motm = calculate_motm()
                bot.send_message(cid, f"🏆 MATCH OVER!\n*{win}* Won by {margin} Runs!\n🌟 MOTM: *{motm}*\n\n" + full_scorecard_text(), parse_mode="Markdown")
                return bot.edit_message_text("Match Finished!", chat_id=cid, message_id=mid)

        return bot.edit_message_text(f"🏁 Over Complete!\n\n" + live_card_text() + "\n\nSelect Next Bowler:", chat_id=cid, message_id=mid, reply_markup=get_squad_picker(m["bowl_tm"], "bowl"), parse_mode="Markdown")

    bot.edit_message_text(live_card_text(), chat_id=cid, message_id=mid, reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda msg: m["await_input"] is not None)
def handle_inputs(msg):
    uid, un, txt = msg.from_user.id, (msg.from_user.username or "").lower(), msg.text.strip()
    if not is_scorer(uid, un): return

    ai = m["await_input"]
    m["await_input"] = None

    if ai == "add_scorer":
        un_s = txt.replace("@", "").strip().lower()
        m["scorers"].add(un_s)
        return bot.reply_to(msg, f"✅ Scorer @{un_s} added!")

    if ai == "rename_player_input":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 2:
            old_name, new_name = p[0].title(), p[1].title()
            if old_name in CAREER_DB:
                CAREER_DB[new_name] = CAREER_DB.pop(old_name)
                save_json(CAREER_FILE, CAREER_DB)
                bot.reply_to(msg, f"✅ Player Profile Renamed: `{old_name}` ➔ *{new_name}* (Lifetime stats safely transferred!)", parse_mode="Markdown")
            else:
                bot.reply_to(msg, f"⚠️ Player `{old_name}` DB mein nahi mila. Naya profile *{new_name}* create kiya gaya hai.", parse_mode="Markdown")
            bot.send_message(msg.chat.id, live_card_text(), reply_markup=get_scoring_keyboard(), parse_mode="Markdown")
        else:
            bot.reply_to(msg, "⚠️ Format: `OldName | NewName`")

    elif ai == "dls_input_prompt":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 3:
            orig_t, orig_ov, played_ov = int(p[0]), float(p[1]), float(p[2])
            par_score = int(orig_t * (played_ov / orig_ov))
            diff = m["runs"] - par_score
            status = f"AHEAD by {diff} runs" if diff > 0 else (f"BEHIND by {abs(diff)} runs" if diff < 0 else "LEVEL on par score")
            bot.reply_to(msg, f"🌧️ *Rain Interruption Report:*\n• Par Score at {played_ov} overs: *{par_score}*\n• Current Score: *{m['runs']}/{m['wkts']}*\n• Status: Team is *{status}*", parse_mode="Markdown")
            bot.send_message(msg.chat.id, live_card_text(), reply_markup=get_scoring_keyboard(), parse_mode="Markdown")
        else:
            bot.reply_to(msg, "⚠️ Format: `OriginalTarget | OriginalOvers | OversPlayed`")

    elif ai == "fix_match_score":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 2:
            r_delta, w_delta = int(p[0]), int(p[1])
            save_state()
            m["runs"] = max(0, m["runs"] + r_delta)
            m["wkts"] = max(0, m["wkts"] + w_delta)
            bot.reply_to(msg, f"✅ Score adjusted!")
            bot.send_message(msg.chat.id, live_card_text(), reply_markup=get_scoring_keyboard(), parse_mode="Markdown")
        else:
            bot.reply_to(msg, "⚠️ Format: `RunsDelta | WicketsDelta`")

    elif ai == "qm_opp_first_input":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 3:
            m["t2"], opp_runs, m["max_ov"] = p[0], int(p[1]), int(p[2])
            m["t1"] = "My Team"
            m["bat_tm"], m["bowl_tm"] = m["t1"], m["t2"]
            m["target"] = opp_runs + 1
            m["active"], m["inn"], m["is_quick_mode"] = True, 2, True
            m["runs"], m["wkts"], m["balls"] = 0, 0, 0
            m["partnership_runs"], m["partnership_balls"] = 0, 0
            m["extras"] = {"wd": 0, "nb": 0, "b": 0, "lb": 0}
            m["cur_over"].clear()
            m["over_history"].clear()
            m["batsmen"].clear()
            m["bowlers"].clear()
            m["history"].clear()
            m["t2_squad"] = ["Opponent Bowler"]
            m["await_input"] = "qm_my_squad_input"
            bot.reply_to(msg, f"🎯 Target Set: *{m['target']}* in {m['max_ov']} Overs!\n\n📋 Apni team ke saare players comma lagakar bhejein:\n`Talha, Adeeb, Mustafa...`", parse_mode="Markdown")
        else:
            bot.reply_to(msg, "⚠️ Format: `OpponentName | TargetRuns | Overs`", parse_mode="Markdown")

    elif ai == "qm_my_squad_input":
        m["t1_squad"] = [x.strip() for x in txt.split(",") if x.strip()]
        m["await_input"] = "qm_openers_input"
        bot.reply_to(msg, f"✅ Squad Saved!\n\n✍️ Openers aur Bowler bhejein:\n`Striker | NonStriker | Bowler`", parse_mode="Markdown")

    elif ai == "qm_my_first_input":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 3:
            m["t1"], m["t2"], m["max_ov"] = p[0], p[1], int(p[2])
            m["bat_tm"], m["bowl_tm"] = m["t1"], m["t2"]
            m["active"], m["inn"], m["is_quick_mode"] = True, 1, True
            m["runs"], m["wkts"], m["balls"] = 0, 0, 0
            m["partnership_runs"], m["partnership_balls"] = 0, 0
            m["extras"] = {"wd": 0, "nb": 0, "b": 0, "lb": 0}
            m["cur_over"].clear()
            m["over_history"].clear()
            m["batsmen"].clear()
            m["bowlers"].clear()
            m["history"].clear()
            m["t2_squad"] = ["Opponent Bowler"]
            m["await_input"] = "qm_my_squad_input"
            bot.reply_to(msg, f"🏏 Match: *{m['t1']} vs {m['t2']}*\n\n📋 Apni team ke players bhejein (comma separated):", parse_mode="Markdown")

    elif ai == "qm_openers_input":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 3:
            m["striker"], m["non_striker"], m["bowler"] = p[0], p[1], p[2]
            ensure_player(m["striker"], True)
            ensure_player(m["non_striker"], True)
            ensure_player(m["bowler"], False)
            bot.send_message(msg.chat.id, live_card_text(), reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

    elif ai == "qm_quick_end_score":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 2:
            opp_r, opp_w = int(p[0]), int(p[1])
            m["active"] = False
            win = m["bat_tm"] if m["runs"] > opp_r else m["bowl_tm"]
            margin = f"{abs(m['runs'] - opp_r)} Runs"
            update_lifetime_records(win, m["bowl_tm"] if win == m["bat_tm"] else m["bat_tm"])
            motm = calculate_motm()
            end_t = (
                f"🏆 MATCH FINISHED! 🏆\n"
                f"👉 Winner: *{win}* (Won by {margin})\n"
                f"🌟 Man of the Match: *{motm}*\n"
                f"-----------------------------------------\n"
                f"{m['bat_tm']}: {m['runs']}/{m['wkts']} ({get_overs_str(m['balls'])} ov)\n"
                f"{m['bowl_tm']}: {opp_r}/{opp_w} ({m['max_ov']}.0 ov)\n\n"
                f"{full_scorecard_text()}"
            )
            bot.send_message(msg.chat.id, end_t, parse_mode="Markdown")

    elif ai == "add_player_mid":
        parts = [x.strip() for x in txt.split("|")]
        if len(parts) >= 2:
            p_name, t_name = parts[0], parts[1]
            if t_name == m["t1"]: m["t1_squad"].append(p_name)
            else: m["t2_squad"].append(p_name)
            bot.reply_to(msg, f"✅ `{p_name}` added!", parse_mode="Markdown")
            bot.send_message(msg.chat.id, live_card_text(), reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

    elif ai == "setup_match_names":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 3:
            m["t1"], m["t2"], m["max_ov"] = p[0], p[1], int(p[2])
            m["active"] = True
            m["inn"] = 1
            m["runs"], m["wkts"], m["balls"] = 0, 0, 0
            m["partnership_runs"] = 0
            m["partnership_balls"] = 0
            m["extras"] = {"wd": 0, "nb": 0, "b": 0, "lb": 0}
            m["cur_over"].clear()
            m["over_history"].clear()
            m["batsmen"].clear()
            m["bowlers"].clear()
            m["history"].clear()
            k = InlineKeyboardMarkup(row_width=2)
            k.add(
                InlineKeyboardButton("🪙 Call Heads", callback_data="toss_call_heads"),
                InlineKeyboardButton("🪙 Call Tails", callback_data="toss_call_tails")
            )
            bot.reply_to(msg, f"🏏 *{m['t1']}* vs *{m['t2']}* ({m['max_ov']} Overs)\n\n🪙 *{m['t1']}* toss call karein:", reply_markup=k, parse_mode="Markdown")

    elif ai == "setup_squad_t1":
        m["t1_squad"] = [x.strip() for x in txt.split(",") if x.strip()]
        m["await_input"] = "setup_squad_t2"
        bot.reply_to(msg, f"✅ {m['bat_tm']} Squad saved!\n\n📋 Ab *{m['bowl_tm']}* ke players bhejein (comma separated):", parse_mode="Markdown")

    elif ai == "setup_squad_t2":
        m["t2_squad"] = [x.strip() for x in txt.split(",") if x.strip()]
        m["await_input"] = "setup_opening_players"
        bot.reply_to(msg, f"✅ Squads Saved!\n\n✍️ Opening Trio bhejein:\n`Striker | NonStriker | Bowler`", parse_mode="Markdown")

    elif ai in ["setup_opening_players", "setup_inn2_openers"]:
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 3:
            m["striker"], m["non_striker"], m["bowler"] = p[0], p[1], p[2]
            ensure_player(m["striker"], True)
            ensure_player(m["non_striker"], True)
            ensure_player(m["bowler"], False)
            bot.send_message(msg.chat.id, live_card_text(), reply_markup=get_scoring_keyboard(), parse_mode="Markdown")

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    while True:
        try: bot.infinity_polling(skip_pending=True, timeout=20)
        except: time.sleep(3)
