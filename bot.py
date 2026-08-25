import os, json, copy, time, random, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_srv():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), H).serve_forever()

threading.Thread(target=run_srv, daemon=True).start()

BOT_TOKEN = "8812331993:AAEREVNSHoSAIgPMYAz1dG1rhJP_RYRV0-w"
bot = telebot.TeleBot(BOT_TOKEN)

C_FILE, T_FILE = "career_data.json", "teams_data.json"
def load_db(f): return json.load(open(f)) if os.path.exists(f) else {}
def save_db(f, d): json.dump(d, open(f, "w"))

C_DB, T_DB = load_db(C_FILE), load_db(T_FILE)

m = {
    "act": False, "t1": "Team A", "t2": "Team B", "max_ov": 10, "inn": 1,
    "bat": "", "bwl": "", "tgt": 0, "sq1": [], "sq2": [], "test": False,
    "str": "", "nstr": "", "bowler": "", "r": 0, "w": 0, "b": 0,
    "pr": 0, "pb": 0, "ext": {"wd":0,"nb":0,"b":0,"lb":0}, "fh": False,
    "inp": None, "ov": [], "ov_hist": [], "bats": {}, "bowlers": {},
    "hist": [], "comm": ""
}

def ov_str(b): return f"{b//6}.{b%6}"
def crr(r, b): return f"{(r/(b/6)):.2f}" if b > 0 else "0.00"

def live_card():
    s = m["bats"].get(m["str"], {"r":0,"b":0,"4":0,"6":0})
    ns = m["bats"].get(m["nstr"], {"r":0,"b":0,"4":0,"6":0})
    bw = m["bowlers"].get(m["bowler"], {"r":0,"b":0,"w":0})
    fh = " [FREE HIT!]" if m["fh"] else ""
    cur = " ".join([f"[{x}]" for x in m["ov"]]) if m["ov"] else "None"
    tag = "[TEST / PRACTICE MODE]\n" if m["test"] else ""
    rrr = ""
    if m["inn"] == 2 and m["tgt"] > 0:
        need, rem = m["tgt"] - m["r"], (m["max_ov"]*6) - m["b"]
        rrr = f"\nTarget: {m['tgt']} (Need {need} off {rem}b)"
    return (
        f"{tag}🏏 {m['bat']} vs {m['bwl']} (Inn {m['inn']})\n"
        f"LIVE: {m['r']}/{m['w']} ({ov_str(m['b'])}/{m['max_ov']} ov) CRR: {crr(m['r'],m['b'])}{rrr}{fh}\n"
        f"--------------------------------\n"
        f"🏏 {m['str']} (On Strike): {s['r']} ({s['b']}b) [4s:{s['4']} 6s:{s['6']}]\n"
        f"🏏 {m['nstr']}: {ns['r']} ({ns['b']}b) [4s:{ns['4']} 6s:{ns['6']}]\n"
        f"🤝 Partnership: {m['pr']} ({m['pb']}b) | 🎯 {m['bowler']}: {bw['w']}/{bw['r']} ({ov_str(bw['b'])} ov)\n"
        f"--------------------------------\n"
        f"Extras: {sum(m['ext'].values())} | Over: {cur}\n"
        f"🎙️ {m['comm']}"
    )

def scorecard_txt():
    txt = f"📋 SCORECARD: {m['bat']} {m['r']}/{m['w']} ({ov_str(m['b'])} ov)\n================================\nBATSMEN:\n"
    for n, s in m["bats"].items():
        sr = f"{(s['r']/s['b']*100):.1f}" if s['b']>0 else "0.0"
        txt += f"• {n}: {s['r']} ({s['b']}b) [4s:{s['4']} 6s:{s['6']}] SR: {sr}\n"
    txt += "--------------------------------\nBOWLERS:\n"
    for n, bw in m["bowlers"].items():
        txt += f"• {n}: {ov_str(bw['b'])} ov | {bw['r']} r | {bw['w']} w\n"
    return txt

def kb_score():
    k = InlineKeyboardMarkup(row_width=3)
    k.add(InlineKeyboardButton("0", callback_data="r_0"), InlineKeyboardButton("1", callback_data="r_1"), InlineKeyboardButton("2", callback_data="r_2"))
    k.add(InlineKeyboardButton("3", callback_data="r_3"), InlineKeyboardButton("4 (Four)", callback_data="r_4"), InlineKeyboardButton("6 (Six)", callback_data="r_6"))
    k.add(InlineKeyboardButton("Wide (+1)", callback_data="w_1"), InlineKeyboardButton("NoBall (+1)", callback_data="nb_1"), InlineKeyboardButton("WICKET", callback_data="wkt_ask"))
    k.add(InlineKeyboardButton("Bye (+1)", callback_data="b_1"), InlineKeyboardButton("🔄 Strike", callback_data="swap"), InlineKeyboardButton("🎯 Bowler", callback_data="ch_bowl"))
    k.add(InlineKeyboardButton("↩️ Undo", callback_data="undo"), InlineKeyboardButton("📋 Card", callback_data="full_card"), InlineKeyboardButton("⚙️ Options", callback_data="opt_menu"))
    return k

def sq_picker(tm, pfx):
    k = InlineKeyboardMarkup(row_width=2)
    squad = m["sq1"] if tm == m["t1"] else m["sq2"]
    for p in squad:
        if pfx in ["st", "nst"] and p in m["bats"] and m["bats"][p].get("out"): continue
        k.add(InlineKeyboardButton(p, callback_data=f"sel_{pfx}_{p}"))
    k.add(InlineKeyboardButton("✍️ Custom Name", callback_data=f"cust_{pfx}"))
    return k

def snap():
    if len(m["hist"]) > 25: m["hist"].pop(0)
    m["hist"].append(copy.deepcopy({k: m[k] for k in ["r","w","b","pr","pb","str","nstr","bowler","ext","fh","ov","bats","bowlers","comm"]}))

def undo():
    if not m["hist"]: return False
    d = m["hist"].pop()
    for k, v in d.items(): m[k] = v
    return True

def ensure_p(n, bat=True):
    if not n or n == "NONE": return
    if bat and n not in m["bats"]: m["bats"][n] = {"r":0,"b":0,"4":0,"6":0,"out":False}
    elif not bat and n not in m["bowlers"]: m["bowlers"][n] = {"r":0,"b":0,"w":0}

def save_records(win, los):
    if m["test"]: return
    for n, s in m["bats"].items():
        C_DB[n] = C_DB.get(n, {"r":0,"b":0,"4":0,"6":0,"w":0,"br":0,"bb":0})
        C_DB[n]["r"] += s["r"]; C_DB[n]["b"] += s["b"]; C_DB[n]["4"] += s["4"]; C_DB[n]["6"] += s["6"]
    for n, bw in m["bowlers"].items():
        C_DB[n] = C_DB.get(n, {"r":0,"b":0,"4":0,"6":0,"w":0,"br":0,"bb":0})
        C_DB[n]["w"] += bw["w"]; C_DB[n]["br"] += bw["r"]; C_DB[n]["bb"] += bw["b"]
    save_db(C_FILE, C_DB)

@bot.message_handler(commands=['start', 'match', 'menu'])
def cmd_start(msg):
    k = InlineKeyboardMarkup(row_width=2)
    k.add(InlineKeyboardButton("🏏 Real Match", callback_data="start_toss"), InlineKeyboardButton("🧪 Test/Tour Mode", callback_data="start_tour"))
    k.add(InlineKeyboardButton("🛡️ Standings", callback_data="v_teams"), InlineKeyboardButton("🏆 Leaderboard", callback_data="v_lead"))
    bot.reply_to(msg, "🏏 Cricket Scoring Engine\nChoose option:", reply_markup=k)

@bot.message_handler(commands=['score'])
def cmd_score(msg):
    if not m["act"]: return bot.reply_to(msg, "No active match. Type /start")
    bot.reply_to(msg, live_card(), reply_markup=kb_score())

@bot.callback_query_handler(func=lambda c: True)
def cb_handler(c):
    cid, mid, d = c.message.chat.id, c.message.message_id, c.data

    if d == "start_tour":
        m.update({"act":True,"test":True,"t1":"Team A","t2":"Team B","max_ov":5,"inn":1,"bat":"Team A","bwl":"Team B","str":"Striker 1","nstr":"Non-Striker 2","bowler":"Bowler 1","r":0,"w":0,"b":0,"pr":0,"pb":0,"ext":{"wd":0,"nb":0,"b":0,"lb":0},"ov":[],"bats":{},"bowlers":{},"hist":[],"comm":"Test mode on!"})
        ensure_p(m["str"],True); ensure_p(m["nstr"],True); ensure_p(m["bowler"],False)
        return bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())

    if d == "v_lead":
        txt = "🏆 LEADERBOARD:\n" + "\n".join([f"• {p}: {s['r']} r | {s['w']} w" for p, s in sorted(C_DB.items(), key=lambda x:x[1]['r'], reverse=True)[:5]])
        bot.send_message(cid, txt if C_DB else "No career records yet.")
        return bot.answer_callback_query(c.id)

    if d == "v_teams":
        bot.send_message(cid, "Team records synced.")
        return bot.answer_callback_query(c.id)

    if d == "full_card":
        return bot.send_message(cid, scorecard_txt()) if m["act"] else bot.answer_callback_query(c.id, "No match active!")

    if d == "opt_menu":
        k = InlineKeyboardMarkup(row_width=2)
        k.add(InlineKeyboardButton("➕ Add Player", callback_data="m_add_p"), InlineKeyboardButton("✏️ Rename", callback_data="m_rename"))
        k.add(InlineKeyboardButton("🔄 Change Striker", callback_data="ch_str"), InlineKeyboardButton("🔄 Change Non-Str", callback_data="ch_nstr"))
        k.add(InlineKeyboardButton("🛠️ Fix Score", callback_data="m_fix"), InlineKeyboardButton("🛑 Abandon", callback_data="m_abnd"))
        k.add(InlineKeyboardButton("⬅️ Back", callback_data="live_back"))
        return bot.edit_message_text("⚙️ SCORER CONTROLS:", chat_id=cid, message_id=mid, reply_markup=k)

    if d == "m_add_p": m["inp"] = "add_p"; return bot.edit_message_text("Send: Name | TeamName", chat_id=cid, message_id=mid)
    if d == "m_rename": m["inp"] = "rename"; return bot.edit_message_text("Send: OldName | NewName", chat_id=cid, message_id=mid)
    if d == "m_fix": m["inp"] = "fix"; return bot.edit_message_text("Send: RunsDelta | WicketsDelta (e.g. -5 | 0)", chat_id=cid, message_id=mid)
    if d == "m_abnd": m["act"] = False; return bot.edit_message_text("🛑 Match Abandoned.", chat_id=cid, message_id=mid)
    if d == "live_back": return bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())

    if d == "start_toss":
        m["test"] = False; m["inp"] = "setup"; return bot.edit_message_text("Send: Team A | Team B | Total Overs\nExample: Mumbai | Unity | 10", chat_id=cid, message_id=mid)

    if d.startswith("t_call_"):
        coin = random.choice(["heads","tails"])
        won = m["t1"] if d.split("_")[2] == coin else m["t2"]
        k = InlineKeyboardMarkup(row_width=2)
        k.add(InlineKeyboardButton("🏏 Bat", callback_data=f"t_el_bat_{won}"), InlineKeyboardButton("🎯 Bowl", callback_data=f"t_el_bowl_{won}"))
        return bot.edit_message_text(f"🪙 {coin.upper()}! {won} won toss:", chat_id=cid, message_id=mid, reply_markup=k)

    if d.startswith("t_el_"):
        ch, won = d.split("_")[2], d.split("_")[3]
        other = m["t2"] if won == m["t1"] else m["t1"]
        m["bat"], m["bwl"] = (won, other) if ch == "bat" else (other, won)
        m["inp"] = "sq1"; return bot.edit_message_text(f"Send squad for {m['bat']} (comma separated):", chat_id=cid, message_id=mid)

    if d.startswith("sel_"):
        _, pfx, p = d.split("_")
        if pfx == "st": m["str"] = p; ensure_p(p, True); return bot.edit_message_text(f"Striker: {p}\nSelect Non-Striker:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bat"], "nst"))
        elif pfx == "nst": m["nstr"] = p; ensure_p(p, True); return bot.edit_message_text(f"Non-Striker: {p}\nSelect Bowler:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bwl"], "bw"))
        elif pfx == "bw": m["bowler"] = p; ensure_p(p, False); m["act"] = True; return bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())

    if not m["act"]: return bot.answer_callback_query(c.id, "No active match!")

    if d.startswith("r_"):
        snap(); r = int(d.split("_")[1]); m["r"] += r; m["b"] += 1; m["pr"] += r; m["pb"] += 1
        ensure_p(m["str"], True); ensure_p(m["bowler"], False)
        m["bats"][m["str"]]["r"] += r; m["bats"][m["str"]]["b"] += 1
        if r == 4: m["bats"][m["str"]]["4"] += 1; m["comm"] = f"FOUR by {m['str']}!"
        elif r == 6: m["bats"][m["str"]]["6"] += 1; m["comm"] = f"SIX by {m['str']}!"
        else: m["comm"] = f"{r} run(s)"
        m["bowlers"][m["bowler"]]["r"] += r; m["bowlers"][m["bowler"]]["b"] += 1
        m["ov"].append(str(r)); m["fh"] = False
        if r % 2 != 0: m["str"], m["nstr"] = m["nstr"], m["str"]
        check_over(cid, mid)

    elif d in ["w_1", "nb_1", "b_1"]:
        snap()
        if d == "w_1":
            m["r"] += 1; m["ext"]["wd"] += 1; ensure_p(m["bowler"], False); m["bowlers"][m["bowler"]]["r"] += 1; m["ov"].append("Wd"); m["comm"] = "Wide ball"
        elif d == "nb_1":
            m["r"] += 1; m["ext"]["nb"] += 1; ensure_p(m["bowler"], False); m["bowlers"][m["bowler"]]["r"] += 1; m["ov"].append("Nb"); m["fh"] = True; m["comm"] = "No Ball! Free Hit"
        elif d == "b_1":
            m["r"] += 1; m["b"] += 1; m["ext"]["b"] += 1; ensure_p(m["bowler"], False); m["bowlers"][m["bowler"]]["b"] += 1; m["ov"].append("B1"); m["comm"] = "1 Bye run"; m["str"], m["nstr"] = m["nstr"], m["str"]
            return check_over(cid, mid)
        bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())

    elif d == "swap": snap(); m["str"], m["nstr"] = m["nstr"], m["str"]; bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())
    elif d == "undo":
        if undo(): bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())
        else: bot.answer_callback_query(c.id, "Nothing to undo!")

    elif d == "wkt_ask":
        k = InlineKeyboardMarkup(row_width=2)
        k.add(InlineKeyboardButton(f"Striker ({m['str']})", callback_data="wkt_str"), InlineKeyboardButton(f"Non-Striker ({m['nstr']})", callback_data="wkt_nstr"))
        bot.edit_message_text("Who is OUT?", chat_id=cid, message_id=mid, reply_markup=k)

    elif d in ["wkt_str", "wkt_nstr"]:
        snap(); out_p = m["str"] if d == "wkt_str" else m["nstr"]
        m["w"] += 1; m["b"] += 1; m["pr"] = 0; m["pb"] = 0
        ensure_p(m["bowler"], False); ensure_p(out_p, True)
        m["bowlers"][m["bowler"]]["b"] += 1; m["bowlers"][m["bowler"]]["w"] += 1
        m["bats"][out_p]["b"] += 1; m["bats"][out_p]["out"] = True
        m["ov"].append("W"); m["fh"] = False; m["comm"] = f"WICKET! {out_p} is OUT!"
        sq = m["sq1"] if m["bat"] == m["t1"] else m["sq2"]
        if m["w"] >= len(sq) - 1 and len(sq) > 1:
            return bot.edit_message_text("🏁 ALL OUT!\n\n" + scorecard_txt(), chat_id=cid, message_id=mid)
        bot.edit_message_text(f"☝️ {out_p} OUT!\nSelect New Batsman:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bat"], "st" if d=="wkt_str" else "nst"))

def check_over(cid, mid):
    if m["inn"] == 2 and m["tgt"] > 0 and m["r"] >= m["tgt"]:
        m["act"] = False; save_records(m["bat"], m["bwl"])
        bot.send_message(cid, f"🏆 {m['bat']} WON! 🎉\n\n" + scorecard_txt())
        return bot.edit_message_text("Match Finished!", chat_id=cid, message_id=mid)

    if m["b"] > 0 and m["b"] % 6 == 0 and len(m["ov"]) >= 6:
        m["ov"].clear(); m["str"], m["nstr"] = m["nstr"], m["str"]
        if m["b"] >= m["max_ov"] * 6:
            if m["inn"] == 1:
                m["tgt"] = m["r"] + 1; m["inn"] = 2
                m["bat"], m["bwl"] = m["bwl"], m["bat"]
                m["r"], m["w"], m["b"], m["pr"], m["pb"] = 0, 0, 0, 0, 0
                m["ext"] = {"wd":0,"nb":0,"b":0,"lb":0}; m["bats"].clear(); m["bowlers"].clear(); m["hist"].clear()
                return bot.edit_message_text(f"🏁 Innings 1 Over! Target: {m['tgt']}\nSelect Striker:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bat"], "st"))
            else:
                m["act"] = False
                win = m["bat"] if m["r"] >= m["tgt"] else m["bwl"]
                save_records(win, m["bwl"] if win == m["bat"] else m["bat"])
                bot.send_message(cid, f"🏆 {win} WON! 🎉\n\n" + scorecard_txt())
                return bot.edit_message_text("Match Finished!", chat_id=cid, message_id=mid)
        return bot.edit_message_text(f"🏁 Over Done!\n\n" + live_card() + "\n\nSelect Bowler:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bwl"], "bw"))
    bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())

@bot.message_handler(func=lambda msg: m["inp"] is not None)
def inp_handler(msg):
    txt, ai = msg.text.strip(), m["inp"]
    m["inp"] = None
    if ai == "setup":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 3:
            m["t1"], m["t2"], m["max_ov"], m["inn"] = p[0], p[1], int(p[2]), 1
            m["r"], m["w"], m["b"], m["pr"], m["pb"] = 0, 0, 0, 0, 0
            m["ext"] = {"wd":0,"nb":0,"b":0,"lb":0}; m["ov"].clear(); m["bats"].clear(); m["bowlers"].clear(); m["hist"].clear()
            k = InlineKeyboardMarkup(row_width=2)
            k.add(InlineKeyboardButton("🪙 Heads", callback_data="t_call_heads"), InlineKeyboardButton("🪙 Tails", callback_data="t_call_tails"))
            bot.reply_to(msg, f"🏏 {m['t1']} vs {m['t2']} ({m['max_ov']} Ov)\n{m['t1']} call toss:", reply_markup=k)
    elif ai == "sq1":
        m["sq1"] = [x.strip() for x in txt.split(",") if x.strip()]
        m["inp"] = "sq2"; bot.reply_to(msg, f"Saved! Now send {m['bwl']} players:")
    elif ai == "sq2":
        m["sq2"] = [x.strip() for x in txt.split(",") if x.strip()]
        bot.reply_to(msg, "Squads Saved! Select Striker:", reply_markup=sq_picker(m["bat"], "st"))
    elif ai == "add_p":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 2:
            if p[1].lower() == m["t1"].lower(): m["sq1"].append(p[0])
            else: m["sq2"].append(p[0])
            bot.reply_to(msg, f"Added {p[0]} to {p[1]}!"); bot.send_message(msg.chat.id, live_card(), reply_markup=kb_score())
    elif ai == "rename":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 2:
            if p[0] in C_DB: C_DB[p[1]] = C_DB.pop(p[0]); save_db(C_FILE, C_DB)
            if m["str"] == p[0]: m["str"] = p[1]
            if m["nstr"] == p[0]: m["nstr"] = p[1]
            if m["bowler"] == p[0]: m["bowler"] = p[1]
            bot.reply_to(msg, f"Renamed: {p[0]} -> {p[1]}"); bot.send_message(msg.chat.id, live_card(), reply_markup=kb_score())
    elif ai == "fix":
        p = [x.strip() for x in txt.split("|")]
        if len(p) >= 2:
            snap(); m["r"] = max(0, m["r"] + int(p[0])); m["w"] = max(0, m["w"] + int(p[1]))
            bot.reply_to(msg, "Score fixed!"); bot.send_message(msg.chat.id, live_card(), reply_markup=kb_score())

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    while True:
        try: bot.infinity_polling(skip_pending=True, timeout=20)
        except: time.sleep(3)
    
