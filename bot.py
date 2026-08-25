import os, json, copy, time, random, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

class H(BaseHTTPRequestHandler):
    def do_GET(self): self.send_response(200); self.end_headers(); self.wfile.write(b"OK")

threading.Thread(target=lambda: HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), H).serve_forever(), daemon=True).start()

BOT_TOKEN = "8812331993:AAEREVNSHoSAIgPMYAz1dG1rhJP_RYRV0-w"
bot = telebot.TeleBot(BOT_TOKEN)

m = {
    "act": False, "t1": "Team A", "t2": "Team B", "max_ov": 10, "inn": 1, "bat": "", "bwl": "", "tgt": 0,
    "sq1": [], "sq2": [], "str": "Striker 1", "nstr": "Non-Striker 2", "bowler": "Bowler 1", "r": 0, "w": 0, "b": 0,
    "pr": 0, "pb": 0, "ext": {"wd":0,"nb":0,"b":0,"1d":0}, "fh": False, "inp": None, "ov": [], "bats": {}, "bowlers": {}, "hist": []
}

def ov_str(b): return f"{b//6}.{b%6}"
def live_card():
    s = m["bats"].get(m["str"], {"r":0,"b":0,"4":0,"6":0})
    ns = m["bats"].get(m["nstr"], {"r":0,"b":0,"4":0,"6":0})
    bw = m["bowlers"].get(m["bowler"], {"r":0,"b":0,"w":0})
    cur = " ".join([f"[{x}]" for x in m["ov"]]) if m["ov"] else "None"
    return f"🏏 {m['bat']} vs {m['bwl']} (Inn {m['inn']})\nLIVE: {m['r']}/{m['w']} ({ov_str(m['b'])}/{m['max_ov']} ov)\n--------------------------------\n🏏 {m['str']}*: {s['r']} ({s['b']}b) [4s:{s['4']} 6s:{s['6']}]\n🏏 {m['nstr']}: {ns['r']} ({ns['b']}b)\n🎯 {m['bowler']}: {bw['w']}/{bw['r']} ({ov_str(bw['b'])} ov)\n--------------------------------\nOver: {cur}"

def kb_score():
    k = InlineKeyboardMarkup(row_width=3)
    k.add(InlineKeyboardButton("0", callback_data="r_0"), InlineKeyboardButton("1", callback_data="r_1"), InlineKeyboardButton("2", callback_data="r_2"))
    k.add(InlineKeyboardButton("4 🔥", callback_data="r_4"), InlineKeyboardButton("6 💥", callback_data="r_6"), InlineKeyboardButton("WICKET", callback_data="r_w"))
    k.add(InlineKeyboardButton("Wide", callback_data="r_wd"), InlineKeyboardButton("NoBall", callback_data="r_nb"), InlineKeyboardButton("Undo", callback_data="undo"))
    return k

@bot.message_handler(commands=['match', 'cric', 'demo'])
def cmd_start(msg):
    m.update({
        "act": True, "bat": "Team A", "bwl": "Team B", "str": "Batsman 1", "nstr": "Batsman 2", "bowler": "Bowler 1",
        "r": 0, "w": 0, "b": 0, "bats": {"Batsman 1": {"r":0,"b":0,"4":0,"6":0}, "Batsman 2": {"r":0,"b":0,"4":0,"6":0}},
        "bowlers": {"Bowler 1": {"r":0,"b":0,"w":0}}, "ov": [], "hist": []
    })
    bot.reply_to(msg, "🏏 Match Started! Scoreboard:", reply_markup=kb_score())

@bot.callback_query_handler(func=lambda c: True)
def cb_handler(c):
    cid, mid, d = c.message.chat.id, c.message.message_id, c.data
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
            m["r"] += 1; m["ext"][val] += 1; m["ov"].append(val.upper())
        bot.edit_message_text(live_card(), chat_id=cid, message_id=mid, reply_markup=kb_score())
    elif d == "undo":
        bot.answer_callback_query(c.id, "Undo clicked!")

if __name__ == "__main__":
    try: bot.remove_webhook()
    except: pass
    print("Bot is running...")
    while True:
        try: bot.infinity_polling(skip_pending=True, timeout=20)
        except: time.sleep(3)
            
