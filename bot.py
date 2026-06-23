import utime
import urequests
import gc
import machine
import ujson
import sys

pending_updates = {}

def send_markdown_msg(base_url, chat_id, text):
    url = f"{base_url}/sendMessage"
    payload = {"chat_id": str(chat_id), "text": text, "parse_mode": "Markdown"}
    try:
        res = urequests.post(url, data=ujson.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=5)
        res.close()
    except:
        pass

def edit_msg(base_url, chat_id, message_id, text):
    url = f"{base_url}/editMessageText"
    payload = {"chat_id": str(chat_id), "message_id": message_id, "text": text}
    try:
        res = urequests.post(url, data=ujson.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=5)
        res.close()
    except:
        pass

def report_error(base_url, log_chat_id, error, context_data):
    user_id = context_data.get("user_id", "Unknown")
    username = context_data.get("username", "N/A")
    command = context_data.get("command", "None")
    
    err_msg = (
        "🚨 *Luna-Bot Execution Error*\n\n"
        f"👤 *User ID:* `{user_id}`\n"
        f"🏷️ *Username:* @{username}\n"
        f"💻 *Input:* `{command}`\n"
        f"⚠️ *Error Details:* `{str(error)}`"
    )
    send_markdown_msg(base_url, log_chat_id, err_msg)

def load_plugins():
    plugins = []
    try:
        with open("pluginlist.txt", "r") as f:
            for line in f:
                file_name = line.strip()
                if file_name.endswith(".py"):
                    mod_name = file_name[:-3]
                    try:
                        plugins.append(__import__(mod_name))
                        print(f"✅ Mounted: {mod_name}")
                    except Exception as e:
                        print(f"❌ Failed to mount {mod_name}: {e}")
    except:
        pass
    return plugins

def run(token, owner_id, security_key, log_chat_id):
    base_url = f"https://api.telegram.org/bot{token}"
    offset = 0
    
    send_markdown_msg(base_url, log_chat_id, "🟢 *System Online:* Firmware updated and active.")
    
    # Dynamically mount everything in pluginlist.txt
    active_plugins = load_plugins()
    
    while True:
        context = {"user_id": "System", "username": "System", "command": "Polling"}
        try:
            url = f"{base_url}/getUpdates?offset={offset}&timeout=1"
            res = urequests.get(url, timeout=3)
            
            if res.status_code == 200:
                data = res.json()
                res.close()
                
                if "result" in data:
                    for update in data["result"]:
                        offset = update["update_id"] + 1
                        if "message" not in update:
                            continue
                        
                        message = update["message"]
                        chat_id = str(message["chat"]["id"])
                        user_id = str(message["from"].get("id", ""))
                        username = message["from"].get("username", "N/A")
                        text = message.get("text", "").strip()
                        
                        context = {"user_id": user_id, "username": username, "command": text}
                        
                        # 1. System Update Logic
                        if chat_id in pending_updates:
                            session = pending_updates[chat_id]
                            if utime.time() - session["time"] > 10:
                                send_markdown_msg(base_url, chat_id, "❌ *Verification timed out.*")
                                del pending_updates[chat_id]
                            else:
                                if text == str(security_key):
                                    del pending_updates[chat_id]
                                    trigger_update_sequence(base_url, chat_id, log_chat_id)
                                else:
                                    send_markdown_msg(base_url, chat_id, "❌ *Incorrect Key.* Access denied.")
                                    del pending_updates[chat_id]
                            continue

                        if text == "/update":
                            send_markdown_msg(base_url, chat_id, "🔐 *Verification Required.*\nEnter your 4-digit Security Key within 10 seconds:")
                            pending_updates[chat_id] = {"time": utime.time()}
                            continue
                            
                        # 2. Pass to Dynamic Plugins
                        for plugin in active_plugins:
                            try:
                                if hasattr(plugin, 'handle_update'):
                                    plugin.handle_update(update, base_url)
                            except Exception as e:
                                report_error(base_url, log_chat_id, e, context)
            else:
                res.close()
        except Exception as e:
            report_error(base_url, log_chat_id, e, context)
            
        current_time = utime.time()
        for cid in list(pending_updates.keys()):
            if current_time - pending_updates[cid]["time"] > 10:
                send_markdown_msg(base_url, cid, "❌ *Verification timed out.*")
                del pending_updates[cid]
                
        gc.collect()
        utime.sleep(0.1)

def trigger_update_sequence(base_url, user_chat_id, log_chat_id):
    url = f"{base_url}/sendMessage"
    try:
        res = urequests.post(url, data=ujson.dumps({"chat_id": str(user_chat_id), "text": "🔄 Auth success! Syncing..."}), headers={'Content-Type': 'application/json'}, timeout=5)
        msg_data = res.json()
        res.close()
        msg_id = msg_data["result"]["message_id"]
    except:
        machine.reset()
        return

    send_markdown_msg(base_url, log_chat_id, f"⚠️ *Notice:* System update initialized. Restarting hardware.")
    
    steps = [
        "📦 Fetching raw source files...",
        "🗑️ Running garbage collection on obsolete modules...",
        "♻️ Verification complete. Restarting ESP32-CAM!"
    ]
    
    for step in steps:
        utime.sleep(1)
        edit_msg(base_url, user_chat_id, msg_id, step)
        
    utime.sleep(0.5)
    machine.reset()
