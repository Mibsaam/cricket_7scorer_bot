import os, json, copy, time, random, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

threading.Thread(target=lambda: HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), H).serve_forever(), daemon=True).start()

BOT_TOKEN = "8812331993:AAEREVNSHoSAIgPMYAz1dG1rhJP_RYRV0-w"
bot = telebot.TeleBot(BOT_TOKEN)
C_FILE, T_FILE = "career_data.json", "teams_data.json"

def load_db(f): return json.load(open(f)) if os.path.exists(f) else {}
def save_db(f, d): json.dump(d, open(f, "w"))
C_DB, T_DB = load_db(C_FILE), load_db(T_FILE)

m = {
    "act": False, "t1": "Team A", "t2": "Team B", "max_ov": 10, "inn": 1, "bat": "", "bwl": "", "tgt": 0,
    "sq1": [], "sq2": [], "test": False, "str": "", "nstr": "", "bowler": "", "r": 0, "w": 0, "b": 0,
    "pr": 0, "pb": 0, "ext": {"wd":0,"nb":0,"b":0,"1d":0}, "fh": False, "inp": None, "ov": [], "bats": {},
    "bowlers": {}, "hist": [], "comm": "", "scorers": set()
}

def ov_str(b): return f"{b//6}.{b%6}"
def crr(r, b): return f"{(r/(b/6)):.2f}" if b > 0 else "0.00"
def is_scorer(uid): return (not m["scorers"]) or (uid in m["scorers"])

def live_card():
    s = m["bats"].get(m["str"], {"r":0,"b":0,"4":0,"6":0})
    ns = m["bats"].get(m["nstr"], {"r":0,"b":0,"4":0,"6":0})
    bw = m["bowlers"].get(m["bowler"], {"r":0,"b":0,"w":0})
    fh = " [FREE HIT!]" if m["fh"] else ""
    cur = " ".join([f"[{x}]" for x in m["ov"]]) if m["ov"] else "None"
    tag = "[TEST/DEMO]\n" if m["test"] else ""
    rrr = f"\nTarget: {m['tgt']} (Need {m['tgt']-m['r']} off {(m['max_ov']*6)-m['b']}b)" if m["inn"]==2 and m["tgt"]>0 else ""
    return (
        f"{tag}🏏 {m['bat']} vs {m['bwl']} (Inn {m['inn']})\n"
        f"LIVE: {m['r']}/{m['w']} ({ov_str(m['b'])}/{m['max_ov']} ov) CRR: {crr(m['r'],m['b'])}{rrr}{fh}\n"
        f"--------------------------------\n"
        f"🏏 {m['str']}*: {s['r']} ({s['b']}b) [4s:{s['4']} 6s:{s['6']}]\n"
        f"🏏 {m['nstr']}: {ns['r']} ({ns['b']}b) [4s:{ns['4']} 6s:{ns['6']}]\n"
        f"🤝 P'ship: {m['pr']} ({m['pb']}b) | 🎯 {m['bowler']}: {bw['w']}/{bw['r']} ({ov_str(bw['b'])} ov)\n"
        f"--------------------------------\n"
        f"Extras: {sum(m['ext'].values())} | Over: {cur}\n🎙️ {m['comm']}"
    )

def scorecard_txt():
    txt = f"📋 SCORECARD: {m['bat']} {m['r']}/{m['w']} ({ov_str(m['b'])} ov)\n================================\nBATSMEN:\n"
    for n, s in m["bats"].items():
        sr = f"{(s['r']/s['b']*100):.1f}" if s['b']>0 else "0.0"
        txt += f"• {n}: {s['r']} ({s['b']}b) [4s:{s['4']} 6s:{s['6']}] SR: {sr}\n"
    txt += "--------------------------------\nBOWLERS:\n"
    for n, bw in m["bowlers"].items():
        econ = f"{(bw['r']/(bw['b']/6)):.2f}" if bw['b']>0 else "0.00"
        txt += f"• {n}: {ov_str(bw['b'])} ov | {bw['r']} r | {bw['w']} w | Econ: {econ}\n"
    return txt

def kb_score():
    k = InlineKeyboardMarkup(row_width=3)
    k.add(InlineKeyboardButton("0", callback_data="r_0"), InlineKeyboardButton("1", callback_data="r_1"), InlineKeyboardButton("2", callback_data="r_2"))
    k.add(InlineKeyboardButton("3", callback_data="r_3"), InlineKeyboardButton("4 (Four) 🔥", callback_data="r_4"), InlineKeyboardButton("6 (Six) 💥", callback_data="r_6"))
    k.add(InlineKeyboardButton("⚡ 1D (Bat)", callback_data="1d_bat_1"), InlineKeyboardButton("⚡ 2D (Bat)", callback_data="1d_bat_2"), InlineKeyboardButton("⚡ 1D (Extra)", callback_data="1d_ext_1"))
    k.add(InlineKeyboardButton("Wide Menu", callback_data="ask_wd"), InlineKeyboardButton("NoBall Menu", callback_data="ask_nb"), InlineKeyboardButton("☝️ WICKET", callback_data="wkt_ask"))
    k.add(InlineKeyboardButton("Bye (+1)", callback_data="b_1"), InlineKeyboardButton("🔄 Strike", callback_data="swap"), InlineKeyboardButton("↩️ Undo", callback_data="undo"))
    k.add(InlineKeyboardButton("🎯 Bowler", callback_data="ch_bowl"), InlineKeyboardButton("📋 Card", callback_data="full_card"), InlineKeyboardButton("⚙️ Options", callback_data="opt_menu"))
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
    if len(m["hist"]) > 20: m["hist"].pop(0)
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

@bot.message_handler(commands=['match', 'cric', 'demo', 'cscore'])
def cmd_start_custom(msg):
    m["scorers"].add(msg.from_user.id)
    k = InlineKeyboardMarkup(row_width=2)
    k.add(InlineKeyboardButton("🏏 Real Match", callback_data="start_toss"), InlineKeyboardButton("🧪 Test/Tour Mode", callback_data="start_tour"))
    k.add(InlineKeyboardButton("🛡️ Standings", callback_data="v_teams"), InlineKeyboardButton("🏆 Leaderboard", callback_data="v_lead"))
    bot.reply_to(msg, f"🏏 *Cricket Scoring Engine*\nAuthorized Scorer: @{msg.from_user.username or msg.from_user.first_name}\nChoose option:", reply_markup=k, parse_mode="Markdown")

@bot.message_handler(commands=['scorecard'])
def cmd_score(msg):
    if not m["act"]: return bot.reply_to(msg, "No active match. Start with /match or /demo")
    bot.reply_to(msg, scorecard_txt())

@bot.callback_query_handler(func=lambda c: True)
def cb_handler(c):
    cid, mid, uid, d = c.message.chat.id, c.message.message_id, c.from_user.id, c.data
    if d in ["v_lead", "v_teams", "full_card"]:
        if d == "v_lead":
            txt = "🏆 LEADERBOARD:\n" + "\n".join([f"• {p}: {s['r']} r | {s['w']} w" for p, s in sorted(C_DB.items(), key=lambda x:x[1]['r'], reverse=True)[:5]])
            bot.send_message(cid, txt if C_DB else "No career records yet.")
        elif d == "v_teams": bot.send_message(cid, "Team records synced.")
        elif d == "full_card": bot.send_message(cid, scorecard_txt() if m["act"] else "No match active!")
        return bot.answer_callback_query(c.id)

    if not is_scorer(uid): return bot.answer_callback_query(c.id, "⚠️ Only authorized Scorer can control match!", show_alert=True)

    if d == "start_tour":
        m.update({
            "act":True, "test":True, "t1":"Team A", "t2":"Team B", "max_ov":5, "inn":1,
            "bat":"Team A", "bwl":"Team B", "str":"Striker 1", "nstr":"Non-Striker 2", "bowler":"Bowler 1",
            "sq1":["Striker 1", "Non-Striker 2", "Player 3", "Player 4"], "sq2":["Bowler 1", "Bowler 2", "Bowler 3"],
            "r":0, "w":0, "b":0, "pr":0, "pb":0, "ext":{"wd":0,"nb":0,"b":0,"1d":0}, "ov":[], "bats":{}, "bowlers":{}, "hist":[], "comm":"Test mode on!"
        })
        ensure_p(m["str"],True); ensure_p(m["nstr"],True); ensure_p(m["bowler"],False)
        return bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())

    if d == "ask_nb":
        k = InlineKeyboardMarkup(row_width=3)
        k.add(InlineKeyboardButton("NB + 0", callback_data="nb_0"), InlineKeyboardButton("NB + 1", callback_data="nb_1"), InlineKeyboardButton("NB + 2", callback_data="nb_2"))
        k.add(InlineKeyboardButton("NB + 3", callback_data="nb_3"), InlineKeyboardButton("NB + 4 🔥", callback_data="nb_4"), InlineKeyboardButton("NB + 6 💥", callback_data="nb_6"))
        k.add(InlineKeyboardButton("⬅️ Back", callback_data="live_back"))
        return bot.edit_message_text("🚨 NO BALL! Bat se kitne runs bane?", chat_id=cid, message_id=mid, reply_markup=k)

    if d == "ask_wd":
        k = InlineKeyboardMarkup(row_width=3)
        k.add(InlineKeyboardButton("Wd + 0", callback_data="wd_0"), InlineKeyboardButton("Wd + 1", callback_data="wd_1"), InlineKeyboardButton("Wd + 2", callback_data="wd_2"))
        k.add(InlineKeyboardButton("Wd + 4", callback_data="wd_4"), InlineKeyboardButton("⬅️ Back", callback_data="live_back"))
        return bot.edit_message_text("⚡ WIDE BALL! Extra runs kitne aaye?", chat_id=cid, message_id=mid, reply_markup=k)

    if d.startswith("nb_"):
        snap(); bat_r = int(d.split("_")[1]); tot = bat_r + 1
        m["r"] += tot; m["pr"] += tot; m["ext"]["nb"] += 1
        ensure_p(m["bowler"], False); ensure_p(m["str"], True)
        m["bowlers"][m["bowler"]]["r"] += tot; m["bats"][m["str"]]["r"] += bat_r; m["bats"][m["str"]]["b"] += 1
        if bat_r == 4: m["bats"][m["str"]]["4"] += 1; m["comm"] = f"💥 NO BALL + FOUR! {m['str']} boundary!"
        elif bat_r == 6: m["bats"][m["str"]]["6"] += 1; m["comm"] = f"🔥 NO BALL + SIX! {m['str']} massive SIX!"
        elif bat_r > 0: m["comm"] = f"🚨 No Ball + {bat_r} runs by {m['str']}!"
        else: m["comm"] = "🚨 No Ball! 1 Extra + Free Hit!"
        m["ov"].append(f"Nb+{bat_r}" if bat_r > 0 else "Nb"); m["fh"] = True
        if bat_r % 2 != 0: m["str"], m["nstr"] = m["nstr"], m["str"]
        return check_over(cid, mid)

    if d.startswith("wd_"):
        snap(); extra_r = int(d.split("_")[1]); tot = extra_r + 1
        m["r"] += tot; m["pr"] += tot; m["ext"]["wd"] += tot
        ensure_p(m["bowler"], False); m["bowlers"][m["bowler"]]["r"] += tot
        m["ov"].append(f"Wd+{extra_r}" if extra_r > 0 else "Wd"); m["comm"] = f"Wide ball + {extra_r} extra runs!" if extra_r > 0 else "Wide ball!"
        if extra_r % 2 != 0: m["str"], m["nstr"] = m["nstr"], m["str"]
        return bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())

    if d == "opt_menu":
        k = InlineKeyboardMarkup(row_width=2)
        k.add(InlineKeyboardButton("➕ Add Scorer", callback_data="m_add_scorer"), InlineKeyboardButton("➕ Add Player", callback_data="m_add_p"))
        k.add(InlineKeyboardButton("🔄 Striker", callback_data="ch_str"), InlineKeyboardButton("🔄 Non-Str", callback_data="ch_nstr"))
        k.add(InlineKeyboardButton("🎯 Bowler", callback_data="ch_bowl"), InlineKeyboardButton("🛠️ Fix Score", callback_data="m_fix"))
        k.add(InlineKeyboardButton("🛑 Abandon", callback_data="m_abnd"), InlineKeyboardButton("⬅️ Back", callback_data="live_back"))
        return bot.edit_message_text("⚙️ SCORER CONTROLS:", chat_id=cid, message_id=mid, reply_markup=k)

    if d == "m_add_scorer": m["inp"] = "add_scorer"; return bot.edit_message_text("Naye scorer ka message reply karein:", chat_id=cid, message_id=mid)
    if d == "ch_str": return bot.edit_message_text("Select Striker:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bat"], "st"))
    if d == "ch_nstr": return bot.edit_message_text("Select Non-Striker:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bat"], "nst"))
    if d == "ch_bowl": return bot.edit_message_text("Select Bowler:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bwl"], "bw"))
    if d.startswith("cust_"): m["inp"] = "custom_" + d.replace("cust_", ""); return bot.edit_message_text("Send custom name:", chat_id=cid, message_id=mid)
    if d == "m_add_p": m["inp"] = "add_p"; return bot.edit_message_text("Send: `PlayerName, TeamName`", chat_id=cid, message_id=mid, parse_mode="Markdown")
    if d == "m_fix": m["inp"] = "fix"; return bot.edit_message_text("Send: `RunsDelta WicketsDelta` (e.g. `-5 0`)", chat_id=cid, message_id=mid, parse_mode="Markdown")
    if d == "m_abnd": m["act"] = False; return bot.edit_message_text("🛑 Match Abandoned.", chat_id=cid, message_id=mid)
    if d == "live_back": return bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())

    if d == "start_toss":
        m["test"] = False; m["inp"] = "setup"
        return bot.edit_message_text("🏏 *Teams & Overs Bhejein:*\n\nExample:\n`Strikers, Unity, 8`", chat_id=cid, message_id=mid, parse_mode="Markdown")

    if d.startswith("t_call_"):
        coin = random.choice(["heads","tails"]); won = m["t1"] if d.split("_")[2] == coin else m["t2"]
        k = InlineKeyboardMarkup(row_width=2)
        k.add(InlineKeyboardButton("🏏 Bat", callback_data=f"t_el_bat_{won}"), InlineKeyboardButton("🎯 Bowl", callback_data=f"t_el_bowl_{won}"))
        return bot.edit_message_text(f"🪙 {coin.upper()}! {won} won toss:", chat_id=cid, message_id=mid, reply_markup=k)

    if d.startswith("t_el_"):
        ch, won = d.split("_")[2], d.split("_")[3]; other = m["t2"] if won == m["t1"] else m["t1"]
        m["bat"], m["bwl"] = (won, other) if ch == "bat" else (other, won)
        m["inp"] = "sq1"; return bot.edit_message_text(f"Send squad for {m['bat']} (comma separated):", chat_id=cid, message_id=mid)

    if d.startswith("sel_"):
        _, pfx, p = d.split("_")
        if pfx == "st":
            m["str"] = p; ensure_p(p, True)
            if not m["act"] and not m["nstr"]: return bot.edit_message_text(f"Striker: {p}\nSelect Non-Striker:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bat"], "nst"))
            return bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())
        elif pfx == "nst":
            m["nstr"] = p; ensure_p(p, True)
            if not m["act"] and not m["bowler"]: return bot.edit_message_text(f"Non-Striker: {p}\nSelect Bowler:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bwl"], "bw"))
            return bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())
        elif pfx == "bw":
            m["bowler"] = p; ensure_p(p, False); m["act"] = True
            return bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())

    if not m["act"]: return bot.answer_callback_query(c.id, "No active match!")

    if d.startswith("r_"):
        snap(); r = int(d.split("_")[1]); m["r"] += r; m["b"] += 1; m["pr"] += r; m["pb"] += 1
        ensure_p(m["str"], True); ensure_p(m["bowler"], False)
        m["bats"][m["str"]]["r"] += r; m["bats"][m["str"]]["b"] += 1
        if r == 4: m["bats"][m["str"]]["4"] += 1; m["comm"] = f"🔥 SHAANDAAR FOUR by {m['str']}!"
        elif r == 6: m["bats"][m["str"]]["6"] += 1; m["comm"] = f"💥 GAGANCHUMBI SIX by {m['str']}!"
        elif r == 0: m["comm"] = f"Dot ball by {m['bowler']}."
        else: m["comm"] = f"{r} run(s) taken."
        m["bowlers"][m["bowler"]]["r"] += r; m["bowlers"][m["bowler"]]["b"] += 1
        m["ov"].append(str(r)); m["fh"] = False
        if r % 2 != 0: m["str"], m["nstr"] = m["nstr"], m["str"]
        check_over(cid, mid)

    elif d.startswith("1d_"):
        snap(); p = d.split("_"); mode, r1d = p[1], int(p[2])
        m["r"] += r1d; m["b"] += 1; m["pr"] += r1d; m["pb"] += 1
        ensure_p(m["bowler"], False); ensure_p(m["str"], True)
        m["bowlers"][m["bowler"]]["b"] += 1; m["bowlers"][m["bowler"]]["r"] += r1d
        m["bats"][m["str"]]["b"] += 1
        if mode == "bat": m["bats"][m["str"]]["r"] += r1d; m["ov"].append(f"{r1d}D"); m["comm"] = f"🏏 1D (Bat)! {m['str']} +{r1d} run!"
        else: m["ext"]["1d"] += r1d; m["ov"].append(f"E{r1d}D"); m["comm"] = f"⚡ 1D (Extra)! Gully bonus run!"
        m["fh"] = False; check_over(cid, mid)

    elif d == "b_1":
        snap(); m["r"] += 1; m["b"] += 1; m["ext"]["b"] += 1
        ensure_p(m["bowler"], False); m["bowlers"][m["bowler"]]["b"] += 1
        m["ov"].append("B1"); m["comm"] = "1 Bye run!"; m["str"], m["nstr"] = m["nstr"], m["str"]
        return check_over(cid, mid)

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
        m["ov"].append("W"); m["fh"] = False; m["comm"] = f"☝️ BIG WICKET! {out_p} is OUT!"
        sq = m["sq1"] if m["bat"] == m["t1"] else m["sq2"]
        if m["w"] >= len(sq) - 1 and len(sq) > 1: return bot.edit_message_text("🏁 ALL OUT!\n\n" + scorecard_txt(), chat_id=cid, message_id=mid)
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
                m["tgt"] = m["r"] + 1; m["inn"] = 2; m["bat"], m["bwl"] = m["bwl"], m["bat"]
                m["r"], m["w"], m["b"], m["pr"], m["pb"] = 0, 0, 0, 0, 0
                m["ext"] = {"wd":0,"nb":0,"b":0,"1d":0}; m["bats"].clear(); m["bowlers"].clear(); m["hist"].clear()
                return bot.edit_message_text(f"🏁 Innings 1 Over! Target: {m['tgt']}\nSelect Striker:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bat"], "st"))
            else:
                m["act"] = False; win = m["bat"] if m["r"] >= m["tgt"] else m["bwl"]
                save_records(win, m["bwl"] if win == m["bat"] else m["bat"])
                bot.send_message(cid, f"🏆 {win} WON! 🎉\n\n" + scorecard_txt())
                return bot.edit_message_text("Match Finished!", chat_id=cid, message_id=mid)
        return bot.edit_message_text(f"🏁 Over Done!\n\n" + live_card() + "\n\nSelect Next Bowler:", chat_id=cid, message_id=mid, reply_markup=sq_picker(m["bwl"], "bw"))
    bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())

def parse_multi(text):
    for sep in ["|", ",", "-", "/"]:
        if sep in text:
            parts = [x.strip() for x in text.split(sep) if x.strip()]
            if len(parts) >= 3: return parts[0], parts[1], parts[2]
    parts = text.split()
    if len(parts) >= 3: return " ".join(parts[:-2]), parts[-2], parts[-1]
    return None

@bot.message_handler(func=lambda msg: m["inp"] is not None)
def inp_handler(msg):
    txt, ai = msg.text.strip(), m["inp"]
    m["inp"] = None
    if ai == "add_scorer":
        if msg.reply_to_message: m["scorers"].add(msg.reply_to_message.from_user.id)
        bot.reply_to(msg, "✅ Scorer permissions granted!")
        bot.send_message(msg.chat.id, live_card(), reply_markup=kb_score())
    elif ai and ai.startswith("custom_"):
        pfx = ai.replace("custom_", "")
        if pfx == "bw": m["bowler"] = txt; ensure_p(txt, False); m["act"] = True; bot.reply_to(msg, f"Bowler: {txt}"); bot.send_message(msg.chat.id, live_card(), reply_markup=kb_score())
        elif pfx == "st": m["str"] = txt; ensure_p(txt, True); bot.send_message(msg.chat.id, live_card(), reply_markup=kb_score())
        elif pfx == "nst": m["nstr"] = txt; ensure_p(txt, True); bot.send_message(msg.chat.id, live_card(), reply_markup=kb_score())
    elif ai == "setup":
        res = parse_multi(txt)
        if res:
            t1, t2, ov = res
            try:
                ov_int = int("".join([c for c in ov if c.isdigit()]))
                m["t1"], m["t2"], m["max_ov"], m["inn"] = t1, t2, ov_int, 1
                m["r"], m["w"], m["b"], m["pr"], m["pb"] = 0, 0, 0, 0, 0
                m["ext"] = {"wd":0,"nb":0,"b":0,"1d":0}; m["ov"].clear(); m["bats"].clear(); m["bowlers"].clear(); m["hist"].clear()
                k = InlineKeyboardMarkup(row_width=2)
                k.add(InlineKeyboardButton("🪙 Heads", callback_data="t_call_heads"), InlineKeyboardButton("🪙 Tails", callback_data="t_call_tails"))
                bot.reply_to(msg, f"🏏 *{m['t1']} vs {m['t2']}* ({m['max_ov']} Overs)\n{m['t1']} call toss:", reply_markup=k, parse_mode="Markdown")
            except: bot.reply_to(msg, "⚠️ Overs ko number me likhein! Example: `Strikers, Unity, 8`")
        else: bot.reply_to(msg, "⚠️ Format: `Team1, Team2, Overs` (Example: `Strikers, Unity, 8`)")
    elif ai == "sq1":
        m["sq1"] = [x.strip() for x in txt.replace("\n", ",").split(",") if x.strip()]
        m["inp"] = "sq2"; bot.reply_to(msg, f"Saved! Send {m['bwl']} players (comma separated):")
    elif ai == "sq2":
        m["sq2"] = [x.strip() for x in txt.replace("\n", ",").split(",") if x.strip()]
        bot.reply_to(msg, "Squads Saved! Select Striker:", reply_markup=sq_picker(m["bat"], "st"))
    elif ai == "add_p":
        parts = [x.strip() for x in txt.replace("|", ",").split(",") if x.strip()]
        if len(parts) >= 2:
            (m["sq1"] if parts[1].lower() == m["t1"].lower() else m["sq2"]).append(parts[0])
            bot.reply_to(msg, f"Added {parts[0]} to {parts[1]}!"); bot.send_message(msg.chat.id, live_card(), reply_markup=kb_score())
    elif ai == "fix":
        parts = [int(s) for s in txt.split() if s.lstrip("-").isdigit()]
        if len(parts) >= 2:
            snap(); m["r"] = max(0, m["r"] + parts[0]); m["w"] = max(0, m["w"] + parts[1])
            bot.reply_to(msg, "Score fixed!"); bot.send_message(msg.chat.id, live_card(), reply_markup=kb_score())

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    print("Bot is successfully running...")
    while True:
        try: bot.infinity_polling(skip_pending=True, timeout=20)
        except Exception: time.sleep(3)
                                                                                                                                                                      
