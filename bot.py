import os, time, telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8812331993:AAEREVNSHoSAIgPMYAz1dG1rhJP_RYRV0-w"
bot = telebot.TeleBot(BOT_TOKEN)

m = {
    "act": False, "r": 0, "w": 0, "b": 0, "bat": "Team A", "bwl": "Team B",
    "str": "Batsman 1", "nstr": "Batsman 2", "bowler": "Bowler 1",
    "bats": {"Batsman 1": {"r":0,"b":0,"4":0,"6":0}, "Batsman 2": {"r":0,"b":0,"4":0,"6":0}},
    "bowlers": {"Bowler 1": {"r":0,"b":0,"w":0}}, "ov": []
}

def ov_str(b): return f"{b//6}.{b%6}"

def live_card():
    s = m["bats"].get(m["str"], {"r":0,"b":0,"4":0,"6":0})
    ns = m["bats"].get(m["nstr"], {"r":0,"b":0,"4":0,"6":0})
    bw = m["bowlers"].get(m["bowler"], {"r":0,"b":0,"w":0})
    cur = " ".join([f"[{x}]" for x in m["ov"]]) if m["ov"] else "None"
    return (
        f"🏏 {m['bat']} vs {m['bwl']} (Inn 1)\n"
        f"LIVE: {m['r']}/{m['w']} ({ov_str(m['b'])} ov)\n"
        f"--------------------------------\n"
        f"🏏 {m['str']}*: {s['r']} ({s['b']}b) [4s:{s['4']} 6s:{s['6']}]\n"
        f"🏏 {m['nstr']}: {ns['r']} ({ns['b']}b)\n"
        f"🎯 {m['bowler']}: {bw['w']}/{bw['r']} ({ov_str(bw['b'])} ov)\n"
        f"--------------------------------\n"
        f"Over: {cur}"
    )

def scorecard_txt():
    txt = f"📋 SCORECARD: {m['bat']} {m['r']}/{m['w']} ({ov_str(m['b'])} ov)\n========================\nBATSMEN:\n"
    for n, s in m["bats"].items():
        txt += f"• {n}: {s['r']} ({s['b']}b) [4s:{s['4']} 6s:{s['6']}]\n"
    return txt

def kb_score():
    k = InlineKeyboardMarkup(row_width=3)
    k.add(InlineKeyboardButton("0", callback_data="r_0"), InlineKeyboardButton("1", callback_data="r_1"), InlineKeyboardButton("2", callback_data="r_2"))
    k.add(InlineKeyboardButton("3", callback_data="r_3"), InlineKeyboardButton("4 🔥", callback_data="r_4"), InlineKeyboardButton("6 💥", callback_data="r_6"))
    k.add(InlineKeyboardButton("Wide", callback_data="r_wd"), InlineKeyboardButton("NoBall", callback_data="r_nb"), InlineKeyboardButton("WICKET", callback_data="r_w"))
    k.add(InlineKeyboardButton("📋 Card", callback_data="full_card"))
    return k

@bot.message_handler(commands=['match', 'cric', 'demo', 'start'])
def start_match(msg):
    m.update({
        "act": True, "r": 0, "w": 0, "b": 0, "ov": [],
        "bats": {"Batsman 1": {"r":0,"b":0,"4":0,"6":0}, "Batsman 2": {"r":0,"b":0,"4":0,"6":0}},
        "bowlers": {"Bowler 1": {"r":0,"b":0,"w":0}}
    })
    bot.reply_to(msg, "🏏 Match Started! Scoreboard:", reply_markup=kb_score())

@bot.message_handler(commands=['scorecard'])
def scorecard_cmd(msg):
    if not m["act"]: return bot.reply_to(msg, "No active match!")
    bot.reply_to(msg, scorecard_txt())

@bot.callback_query_handler(func=lambda c: True)
def cb_handler(c):
    cid, mid, d = c.message.chat.id, c.message.message_id, c.data
    if d == "full_card":
        bot.send_message(cid, scorecard_txt())
        return bot.answer_callback_query(c.id)
    if d.startswith("r_"):
        val = d.split("_")[1]
        if val.isdigit():
            r = int(val); m["r"] += r; m["b"] += 1
            m["bats"][m["str"]]["r"] += r; m["bats"][m["str"]]["b"] += 1
            if r == 4: m["bats"][m["str"]]["4"] += 1
            elif r == 6: m["bats"][m["str"]]["6"] += 1
            m["bowlers"][m["bowler"]]["r"] += r; m["bowlers"][m["bowler"]]["b"] += 1
            m["ov"].append(str(r))
            if r % 2 != 0: m["str"], m["nstr"] = m["nstr"], m["str"]
        elif val == "w":
            m["w"] += 1; m["b"] += 1; m["ov"].append("W")
        elif val in ["wd", "nb"]:
            m["r"] += 1; m["ov"].append(val.upper())
        bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    print("Bot is successfully running...")
    while True:
        try: bot.infinity_polling(skip_pending=True, timeout=20)
        except: time.sleep(3)
            
