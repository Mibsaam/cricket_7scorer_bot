import os, random, time, threading, urllib.request
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8670400703:AAFx9ZbF8Hzv3SCU9TyN9Mh-LlOuKzV6p-k"
ADMIN_ID = 874225351

# AUCTION TIMER CONFIGURATION (Default 30 Seconds)
DEFAULT_TIMER = 30

# 24/7 KEEP-ALIVE FLASK SERVER (Render Sleep Rokne ke liye)
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
            render_url = os.environ.get("RENDER_EXTERNAL_URL")
            if render_url: urllib.request.urlopen(render_url)
        except: pass

threading.Thread(target=auto_ping, daemon=True).start()

bot = telebot.TeleBot(BOT_TOKEN)

# DEFAULT PERMANENT PLAYERS
DEFAULT_PLAYERS = [
    {"name": "Adeeb bhai", "role": "BAT", "team": "Team Unity"},
    {"name": "Cezzane", "role": "WKB", "team": "Team Unity"},
    {"name": "Arshad bhai", "role": "AR", "team": "Team Unity"},
    {"name": "Atif bhai", "role": "BAR", "team": "Team Unity"},
    {"name": "Shayaan", "role": "BOWL", "team": "Team Unity"},
    {"name": "Ureb", "role": "BAR", "team": "Team Unity"},
    {"name": "Ismail", "role": "BOWL", "team": "Team Unity"},
    {"name": "Shadab", "role": "BAR", "team": "Team Unity"},
    {"name": "Ghulam", "role": "BOWL", "team": "Team Unity"},
    {"name": "Sarfaraaz bhai", "role": "BAT", "team": "Team Unity"},
    {"name": "Talha", "role": "BAT", "team": "Mumbai Strikers"},
    {"name": "Riyaz bhai", "role": "AR", "team": "Mumbai Strikers"},
    {"name": "Mustafa", "role": "AR", "team": "Mumbai Strikers"},
    {"name": "Wasim bhai", "role": "BAR", "team": "Mumbai Strikers"},
    {"name": "Rahman bhai", "role": "BAT", "team": "Mumbai Strikers"},
    {"name": "Taqweem", "role": "BAT", "team": "Mumbai Strikers"},
    {"name": "Tamim", "role": "BOWL", "team": "Mumbai Strikers"},
    {"name": "Zohaib", "role": "AR", "team": "Mumbai Strikers"},
    {"name": "Nishrat", "role": "BAR", "team": "Mumbai Strikers"},
    {"name": "Ashraf", "role": "BOWL", "team": "Mumbai Strikers"}
]

d = {
    "players": [], "await_cap": None, "await_name": False, "temp_name": None, "temp_role": None,
    "idx": -1, "bid": 0, "bidder": None, "active": False, "paused": False, "last_bid": 0, "last_bidder": None,
    "t_id": 0, "chat_id": None, "leaves": set(),
    "teams": {
        "Mumbai Strikers": {"cid": ADMIN_ID, "cname": "Admin", "purse": 1000000000, "squad": [{"name": "Chiku", "role": "AR", "price": 0}], "ret": []},
        "Team Unity": {"cid": None, "cname": "Not Set", "purse": 1000000000, "squad": [{"name": "Mohtasim", "role": "AR", "price": 0}], "ret": []}
    }
}

def get_bp(r):
    r = r.upper()
    return 20000000 if "BAT" in r else (10000000 if "BOWL" in r else 5000000)

def load_p():
    if not d["players"]:
        all_p = list(DEFAULT_PLAYERS)
        random.shuffle(all_p)
        d["players"] = [{"name": p["name"], "role": p["role"], "team": p["team"], "bp": get_bp(p["role"]), "status": "UPCOMING", "price": 0} for p in all_p]

load_p()

def get_msq(): return max(11, (len(d["players"]) + 2) // 2)
def fmt_c(amt):
    if amt == 0: return "Pre-Captain"
    if amt >= 10000000: return f"Rs {amt/10000000:.2f} Cr"
    return f"Rs {amt/100000:.2f} L"

def finalize_p(cid, msg_id=None):
    i = d["idx"]
    if i < 0 or i >= len(d["players"]): return
    p, msq = d["players"][i], get_msq()
    btn = InlineKeyboardMarkup().add(InlineKeyboardButton("➡️ Next Player", callback_data="act_next"))
    if d["bidder"]:
        tm, pr = d["bidder"], d["bid"]
        d["teams"][tm]["purse"] -= pr
        d["teams"][tm]["squad"].append({"name": p["name"], "role": p["role"], "price": pr})
        p["status"], d["active"] = "SOLD", False
        res_text = f"🔨 SOLD!\n\nPlayer: {p['name']} ({p['role']})\nTeam: {tm}\nPrice: {fmt_c(pr)}\nPurse Left: {fmt_c(d['teams'][tm]['purse'])}"
    else:
        p["status"], d["active"] = "UNSOLD", False
        res_text = f"❌ UNSOLD!\n\nPlayer {p['name']} ({p['role']}) went unsold."
    
    if msg_id:
        try:
            bot.edit_message_text(res_text, chat_id=cid, message_id=msg_id, reply_markup=btn)
            return
        except Exception:
            pass
    bot.send_message(cid, res_text, reply_markup=btn)

def get_bidding_m(cb):
    m = InlineKeyboardMarkup(row_width=2)
    i1, i2, l1, l2 = (500000, 1000000, "+5L", "+10L") if cb < 10000000 else ((1000000, 2500000, "+10L", "+25L") if cb < 30000000 else (2500000, 5000000, "+25L", "+50L"))
    m.add(InlineKeyboardButton(f"🔵 Mumbai ({l1})", callback_data=f"b_m_{i1}"), InlineKeyboardButton(f"🔴 Unity ({l1})", callback_data=f"b_u_{i1}"))
    m.add(InlineKeyboardButton(f"🔵 Mumbai ({l2})", callback_data=f"b_m_{i2}"), InlineKeyboardButton(f"🔴 Unity ({l2})", callback_data=f"b_u_{i2}"))
    m.add(InlineKeyboardButton("🔒 Retain Mumbai", callback_data="r_m"), InlineKeyboardButton("🔒 Retain Unity", callback_data="r_u"))
    m.add(InlineKeyboardButton("🏳️ Leave Mumbai", callback_data="lv_m"), InlineKeyboardButton("🏳️ Leave Unity", callback_data="lv_u"))
    m.add(InlineKeyboardButton("⏱️ +15s", callback_data="act_ext"), InlineKeyboardButton("↩️ Undo", callback_data="act_undo"))
    m.add(InlineKeyboardButton("⏸️ Pause", callback_data="act_pause"), InlineKeyboardButton("📊 Status", callback_data="act_stat"))
    return m

def get_menu_m():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(InlineKeyboardButton("▶️ Start / Next", callback_data="act_next"), InlineKeyboardButton("👑 Set Captains", callback_data="menu_setcap"))
    m.add(InlineKeyboardButton("➕ Add Player", callback_data="menu_addp"), InlineKeyboardButton("📋 View Squads", callback_data="act_stat"))
    m.add(InlineKeyboardButton("📋 Full Pool List", callback_data="menu_pool"), InlineKeyboardButton("🔝 Top Buys", callback_data="menu_top"))
    m.add(InlineKeyboardButton("❌ Unsold List", callback_data="menu_unsold"), InlineKeyboardButton("🔄 Re-Auction", callback_data="menu_reauct"))
    m.add(InlineKeyboardButton("🔄 Reset Auction", callback_data="menu_reset"))
    return m

@bot.message_handler(commands=['start', 'menu'])
def c_start(msg): bot.reply_to(msg, f"🏏 Cricket Auction Control Panel\nTarget: {get_msq()} Each | Purse: Rs 100 Cr", reply_markup=get_menu_m())

@bot.message_handler(commands=['next'])
def c_next(msg):
    if msg.from_user.id == ADMIN_ID: load_next(msg.chat.id)

@bot.message_handler(commands=['team'])
def c_team(msg): bot.reply_to(msg, get_rep())

@bot.message_handler(commands=['renameplayer'])
def c_rename(msg):
    if msg.from_user.id != ADMIN_ID: return
    txt = msg.text.replace("/renameplayer", "").strip()
    if "|" not in txt:
        return bot.reply_to(msg, "⚠️ Format: `/renameplayer OldName | NewName`", parse_mode="Markdown")
    old_n, new_n = [x.strip() for x in txt.split("|", 1)]
    for p in d["players"]:
        if p["name"].lower() == old_n.lower():
            p["name"] = new_n
            return bot.reply_to(msg, f"✅ Success! `{old_n}` ko `{new_n}` kar diya gaya.", parse_mode="Markdown")
    bot.reply_to(msg, f"❌ Player `{old_n}` nahi mila.", parse_mode="Markdown")

@bot.message_handler(commands=['removeplayer'])
def c_remove(msg):
    if msg.from_user.id != ADMIN_ID: return
    txt = msg.text.replace("/removeplayer", "").strip().lower()
    if not txt:
        return bot.reply_to(msg, "⚠️ Format: `/removeplayer Name`", parse_mode="Markdown")
    rem_idx = -1
    for i, p in enumerate(d["players"]):
        if p["name"].lower() == txt:
            rem_idx = i
            break
    if rem_idx == -1:
        for i, p in enumerate(d["players"]):
            if txt in p["name"].lower():
                rem_idx = i
                break
    if rem_idx != -1:
        removed = d["players"].pop(rem_idx)
        if d["idx"] >= rem_idx: d["idx"] -= 1
        return bot.reply_to(msg, f"🗑️ `{removed['name']}` ko pool se hata diya gaya!\nTotal Pool: {len(d['players'])} players", parse_mode="Markdown")
    bot.reply_to(msg, f"❌ `{txt}` naam ka player nahi mila.", parse_mode="Markdown")

@bot.message_handler(commands=['reset'])
def c_reset(msg):
    if msg.from_user.id != ADMIN_ID: return
    for tm in d["teams"]:
        d["teams"][tm]["purse"] = 1000000000
        d["teams"][tm]["squad"] = [{"name": "Chiku" if tm == "Mumbai Strikers" else "Mohtasim", "role": "AR", "price": 0}]
        d["teams"][tm]["ret"] = []
    d["players"] = []
    load_p()
    d["idx"], d["active"], d["paused"] = -1, False, False
    bot.reply_to(msg, "Auction Reset Complete!")

def load_next(cid):
    nxt = next((i for i, p in enumerate(d["players"]) if p["status"] == "UPCOMING" and i > d["idx"]), -1)
    if nxt == -1: nxt = next((i for i, p in enumerate(d["players"]) if p["status"] == "UPCOMING"), -1)
    if nxt == -1:
        u_cnt = sum(1 for p in d["players"] if p["status"] == "UNSOLD")
        return bot.send_message(cid, f"🏁 AUCTION FINISHED! ({u_cnt} Unsold)")
    d["idx"], d["bid"], d["bidder"], d["active"], d["paused"] = nxt, d["players"][nxt]["bp"], None, True, False
    d["last_bid"], d["last_bidder"], d["t_id"] = 0, None, d["t_id"] + 1
    d["leaves"].clear()
    p = d["players"][nxt]
    
    init_bar = "██████████"
    msg = bot.send_message(cid, f"🎯 Active Player:\n\n👤 {p['name']} ({p['role']})\n🏠 Team: {p['team']}\n💰 Base: {fmt_c(p['bp'])}\n\n⏳ *Time Remaining:* `[{init_bar}]` **{DEFAULT_TIMER}s**", reply_markup=get_bidding_m(d["bid"]), parse_mode="Markdown")
    
    cur_id = d["t_id"]
    def run_timer():
        time_left = DEFAULT_TIMER
        while time_left > 0:
            if not (d["active"] and d["t_id"] == cur_id): return
            while d["paused"] and d["active"]: time.sleep(1)
            
            filled = int((time_left / DEFAULT_TIMER) * 10)
            bar = "█" * filled + "░" * (10 - filled)
            
            if time_left in [30, 20, 15, 10, 5, 4, 3, 2, 1]:
                top_text = f"🎯 Active Player:\n\n👤 {p['name']} ({p['role']})\n🏠 Team: {p['team']}\n💰 Current Bid: {fmt_c(d['bid'])}\n🔥 Leader: {d['bidder'] if d['bidder'] else 'None'}"
                bottom_text = f"\n\n⏳ *Time Remaining:* `[{bar}]` **{time_left}s**"
                try:
                    bot.edit_message_text(top_text + bottom_text, chat_id=cid, message_id=msg.message_id, reply_markup=get_bidding_m(d["bid"]), parse_mode="Markdown")
                except:
                    pass
            
            time.sleep(1)
            time_left -= 1

        if d["active"] and d["t_id"] == cur_id:
            finalize_p(cid, msg.message_id)

    threading.Thread(target=run_timer, daemon=True).start()

def get_rep():
    msq = get_msq()
    t = f"📋 SQUAD LIST (Max: {msq})\n\n"
    for tm, td in d["teams"].items():
        t += f"🏆 {tm} (Cap: {td['cname']})\nPurse: {fmt_c(td['purse'])}\nSquad: {len(td['squad'])}/{msq}\n"
        for idx, p in enumerate(td["squad"], 1): t += f"{idx}. {p['name']} | {fmt_c(p['price'])}\n"
        t += "\n"
    return t

@bot.callback_query_handler(func=lambda call: True)
def on_btn(call):
    try:
        uid, un, dt = call.from_user.id, (call.from_user.username or "").lower(), call.data
        if dt == "act_stat": return bot.send_message(call.message.chat.id, get_rep()) and bot.answer_callback_query(call.id)
        if dt == "menu_pool":
            pl = [f"{idx}. {p['name']} ({p['role']}) - {p['team']} [{p['status']}]" for idx, p in enumerate(d["players"], 1)]
            chunks = [pl[i:i + 30] for i in range(0, len(pl), 30)]
            for chunk in chunks:
                bot.send_message(call.message.chat.id, "📋 FULL PLAYER POOL:\n\n" + "\n".join(chunk))
            return bot.answer_callback_query(call.id, "Pool Sent!")
        if dt == "menu_top":
            sold = sorted([p for tm in d["teams"].values() for p in tm["squad"] if p["price"] > 0], key=lambda x: x["price"], reverse=True)
            t = "🔝 Top Buys:\n" + "\n".join([f"{p['name']} - {fmt_c(p['price'])}" for p in sold[:5]]) if sold else "No sales yet."
            return bot.send_message(call.message.chat.id, t) and bot.answer_callback_query(call.id)
        if dt == "menu_unsold":
            u = [p for p in d["players"] if p["status"] == "UNSOLD"]
            t = "📋 Unsold:\n" + "\n".join([p['name'] for p in u]) if u else "No unsold players."
            return bot.send_message(call.message.chat.id, t) and bot.answer_callback_query(call.id)
        if dt == "menu_addp":
            if uid != ADMIN_ID: return bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
            d["await_name"] = True
            return bot.edit_message_text("✍️ Send player name:", chat_id=call.message.chat.id, message_id=call.message.message_id)
        if dt.startswith("r_"):
            d["temp_role"] = dt.replace("r_", "")
            m = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("Mumbai", callback_data="add_t_m"), InlineKeyboardButton("Unity", callback_data="add_t_u"))
            return bot.edit_message_text(f"Select team for {d['temp_name']}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m)
        if dt in ["add_t_m", "add_t_u"]:
            tm = "Mumbai Strikers" if dt == "add_t_m" else "Team Unity"
            new_p = {"name": d["temp_name"], "role": d["temp_role"], "team": tm, "bp": get_bp(d["temp_role"]), "status": "UPCOMING", "price": 0}
            d["players"].append(new_p)
            DEFAULT_PLAYERS.append(new_p)
            d["temp_name"] = None
            return bot.edit_message_text(f"✅ Added & Saved! Total: {len(d['players'])}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_menu_m())
        if dt == "menu_setcap":
            if uid != ADMIN_ID: return bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
            m = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("Mumbai", callback_data="cap_m"), InlineKeyboardButton("Unity", callback_data="cap_u"))
            return bot.edit_message_text("Select team:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m)
        if dt in ["cap_m", "cap_u"]:
            tm = "Mumbai Strikers" if dt == "cap_m" else "Team Unity"
            m = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("Make Me Captain", callback_data=f"set_me_{tm}"), InlineKeyboardButton("Type Username", callback_data=f"set_ask_{tm}"))
            return bot.edit_message_text(f"Option for {tm}:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=m)
        if dt.startswith("set_me_"):
            tm = dt.replace("set_me_", "")
            d["teams"][tm]["cid"], d["teams"][tm]["cname"] = uid, "Admin"
            return bot.edit_message_text(f"✅ You are captain of {tm}!", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_menu_m())
        if dt.startswith("set_ask_"):
            d["await_cap"] = dt.replace("set_ask_", "")
            return bot.edit_message_text("✍️ Send captain @username:", chat_id=call.message.chat.id, message_id=call.message.message_id)
        if dt == "menu_reauct":
            if uid != ADMIN_ID: return bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
            for p in d["players"]:
                if p["status"] == "UNSOLD": p["status"] = "UPCOMING"
            return bot.send_message(call.message.chat.id, "🔄 Unsold re-added!") and bot.answer_callback_query(call.id)
        if dt == "menu_reset":
            if uid != ADMIN_ID: return bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
            c_reset(call.message)
            return bot.edit_message_text("Reset done!", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_menu_m())
        if dt == "act_next":
            if uid != ADMIN_ID: return bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
            load_next(call.message.chat.id)
            return bot.answer_callback_query(call.id, "Loading...")

        i = d["idx"]
        if i < 0 or i >= len(d["players"]): return bot.answer_callback_query(call.id, "No active player!")
        p, msq = d["players"][i], get_msq()
        def is_cap(t): return d["teams"][t]["cid"] == uid or str(d["teams"][t]["cid"]).lower() == un

        if dt == "act_pause":
            if uid != ADMIN_ID: return bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
            d["paused"] = not d["paused"]
            return bot.send_message(call.message.chat.id, f"Auction {'Paused' if d['paused'] else 'Resumed'}") and bot.answer_callback_query(call.id)
        
        if dt == "act_ext":
            if uid != ADMIN_ID: return bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
            d["t_id"] += 1
            
            cur_id = d["t_id"]
            def run_timer_ext():
                time_left = DEFAULT_TIMER
                while time_left > 0:
                    if not (d["active"] and d["t_id"] == cur_id): return
                    while d["paused"] and d["active"]: time.sleep(1)
                    filled = int((time_left / DEFAULT_TIMER) * 10)
                    bar = "█" * filled + "░" * (10 - filled)
                    if time_left in [30, 20, 15, 10, 5, 4, 3, 2, 1]:
                        try:
                            top_text = f"🎯 Active Player:\n\n👤 {p['name']} ({p['role']})\n💰 Top Bid: {fmt_c(d['bid'])}\n🔥 Leader: {d['bidder'] if d['bidder'] else 'None'}"
                            bot.edit_message_text(top_text + f"\n\n⏳ *Time Extended (+15s):* `[{bar}]` **{time_left}s**", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_bidding_m(d["bid"]), parse_mode="Markdown")
                        except: pass
                    time.sleep(1)
                    time_left -= 1
                if d["active"] and d["t_id"] == cur_id: finalize_p(call.message.chat.id, call.message.message_id)

            threading.Thread(target=run_timer_ext, daemon=True).start()
            return bot.answer_callback_query(call.id, "+15s added successfully!")

        if dt == "act_undo":
            if uid != ADMIN_ID: return bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
            if d["last_bid"] > 0:
                d["bid"], d["bidder"] = d["last_bid"], d["last_bidder"]
                bot.edit_message_text(f"🎯 Player: {p['name']}\n💰 Top Bid (Undo): {fmt_c(d['bid'])}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_bidding_m(d["bid"]))
                d["t_id"] += 1
            return bot.answer_callback_query(call.id, "Undone")

        if dt.startswith("b_"):
            if d["paused"]: return bot.answer_callback_query(call.id, "Paused!", show_alert=True)
            tm = "Mumbai Strikers" if dt.split("_")[1] == "m" else "Team Unity"
            inc = int(dt.split("_")[2])
            if len(d["teams"][tm]["squad"]) >= msq or not is_cap(tm) or not d["active"]:
                return bot.answer_callback_query(call.id, "Not allowed!", show_alert=True)
            nb = (d["bid"] if d["bidder"] else p["bp"]) + inc
            if nb > d["teams"][tm]["purse"]: return bot.answer_callback_query(call.id, "Low purse!", show_alert=True)
            d["last_bid"], d["last_bidder"], d["bid"], d["bidder"] = d["bid"], d["bidder"], nb, tm
            d["t_id"] += 1
            d["leaves"].clear()
            
            reset_bar = "██████████"
            bot.edit_message_text(f"🎯 Active Player:\n\n👤 {p['name']} ({p['role']})\n💰 Top Bid: {fmt_c(nb)}\n🔥 Team: {tm}\n\n⏳ *Time Reset to {DEFAULT_TIMER}s:* `[{reset_bar}]`", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_bidding_m(nb), parse_mode="Markdown")
            
            cur_id = d["t_id"]
            def run_timer_reset():
                time_left = DEFAULT_TIMER
                while time_left > 0:
                    if not (d["active"] and d["t_id"] == cur_id): return
                    while d["paused"] and d["active"]: time.sleep(1)
                    
                    filled = int((time_left / DEFAULT_TIMER) * 10)
                    bar = "█" * filled + "░" * (10 - filled)
                    
                    if time_left in [30, 20, 15, 10, 5, 4, 3, 2, 1]:
                        top_text = f"🎯 Active Player:\n\n👤 {p['name']} ({p['role']})\n💰 Top Bid: {fmt_c(d['bid'])}\n🔥 Team: {d['bidder']}"
                        bottom_text = f"\n\n⏳ *Time Remaining:* `[{bar}]` **{time_left}s**"
                        try:
                            bot.edit_message_text(top_text + bottom_text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=get_bidding_m(d["bid"]), parse_mode="Markdown")
                        except:
                            pass
                    
                    time.sleep(1)
                    time_left -= 1

                if d["active"] and d["t_id"] == cur_id:
                    finalize_p(call.message.chat.id, call.message.message_id)

            threading.Thread(target=run_timer_reset, daemon=True).start()

        elif dt in ["r_m", "r_u"]:
            tm = "Mumbai Strikers" if dt == "r_m" else "Team Unity"
            if len(d["teams"][tm]["squad"]) >= msq or p["team"] != tm or not is_cap(tm):
                return bot.answer_callback_query(call.id, "Not allowed!", show_alert=True)
            d["teams"][tm]["purse"] -= 50000000
            d["teams"][tm]["squad"].append({"name": p["name"], "role": p["role"], "price": 50000000})
            p["status"], d["active"] = "SOLD", False
            bot.edit_message_text(f"🔒 RETAINED!\nTeam: {tm}\nPlayer: {p['name']}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Next", callback_data="act_next")))
        elif dt in ["lv_m", "lv_u"]:
            tm = "Mumbai Strikers" if dt == "lv_m" else "Team Unity"
            other = "Team Unity" if tm == "Mumbai Strikers" else "Mumbai Strikers"
            if not is_cap(tm) or d["bidder"] == tm: return bot.answer_callback_query(call.id, "Not allowed!", show_alert=True)
            d["leaves"].add(tm)
            bot.send_message(call.message.chat.id, f"🏳️ {tm} left bidding!")
            if d["bidder"] == other or len(d["leaves"]) >= 2: finalize_p(call.message.chat.id, call.message.message_id)

    except Exception as e:
        try:
            bot.answer_callback_query(call.id, "⚠️ Yeh button expire ho gaya hai!", show_alert=True)
        except:
            pass

@bot.message_handler(func=lambda m: d["await_name"] or d["await_cap"] is not None)
def c_inp(msg):
    if msg.from_user.id != ADMIN_ID: return
    if d["await_name"]:
        d["await_name"] = False
        d["temp_name"] = msg.text.strip()
        m = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("BAT", callback_data="r_BAT"), InlineKeyboardButton("BOWL", callback_data="r_BOWL"), InlineKeyboardButton("AR", callback_data="r_AR"), InlineKeyboardButton("WKB", callback_data="r_WKB"))
        return bot.reply_to(msg, f"Select role for {d['temp_name']}:", reply_markup=m)
    if d["await_cap"]:
        tm, d["await_cap"] = d["await_cap"], None
        un = msg.text.replace("@", "").strip().lower()
        d["teams"][tm]["cname"], d["teams"][tm]["cid"] = f"@{un}", un
        bot.reply_to(msg, f"✅ @{un} is now captain of {tm}!", reply_markup=get_menu_m())

if __name__ == "__main__":
    try: bot.remove_webhook()
    except Exception: pass
    print("Bot is running 24/7...")
    bot.infinity_polling(skip_pending=True, timeout=20)