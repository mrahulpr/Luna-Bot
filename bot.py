import utime
import urequests
import gc
import machine
import ujson

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
        "🚨 *Luna-Bot Error*\n"
        f"👤 *ID:* `{user_id}` | @{username}\n"
        f"💻 *Input:* `{command}`\n"
        f"⚠️ *Log:* `{str(error)}`"
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
                        print(f"❌ Plugin Error ({mod_name}): {e}")
    except:
        pass
    return plugins

def run(token, owner_id, security_key, log_chat_id):
    base_url = f"https://api.telegram.org/bot{token}"
    offset = 0
    
    send_markdown_msg(base_url, log_chat_id, "🟢 *Luna-Bot Online:* Engine running with Long Polling.")
    active_plugins = load_plugins()
    
    while True:
        context = {"user_id": "System", "username": "System", "command": "Polling"}
        try:
            # LONG POLLING: Timeout=20 tells Telegram to hold the connection open. 
            # This makes responses instant (<0.1s) without killing the ESP32 CPU.
            url = f"{base_url}/getUpdates?offset={offset}&timeout=20"
            res = urequests.get(url, timeout=25) 
            
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
                        
                        # 1. Update Authentication Pipeline
                        if chat_id in pending_updates:
                            session = pending_updates[chat_id]
                            # Increased wait time to 30s to give you time to type the code
                            if utime.time() - session["time"] > 30:
                                send_markdown_msg(base_url, chat_id, "❌ *Verification timed out.*")
                                del pending_updates[chat_id]
                            else:
                                if text == str(security_key):
                                    del pending_updates[chat_id]
                                    # We pass the 'offset' so it clears the queue before rebooting!
                                    trigger_update_sequence(base_url, chat_id, log_chat_id, offset)
                                else:
                                    send_markdown_msg(base_url, chat_id, "❌ *Incorrect Key.* Access denied.")
                                    del pending_updates[chat_id]
                            continue

                        if text == "/update":
                            send_markdown_msg(base_url, chat_id, "🔐 *Verification Required.*\nEnter your 4-digit Security Key:")
                            pending_updates[chat_id] = {"time": utime.time()}
                            continue
                            
                        # 2. Dynamic Plugin Processing
                        handled = False
                        for plugin in active_plugins:
                            try:
                                if hasattr(plugin, 'handle_update'):
                                    plugin.handle_update(update, base_url)
                                    handled = True
                            except Exception as e:
                                report_error(base_url, log_chat_id, e, context)
            else:
                res.close()
        except Exception as e:
            # Silence standard timeout drops from long polling, report real errors
            if "ETIMEDOUT" not in str(e) and "timeout" not in str(e).lower():
                report_error(base_url, log_chat_id, e, context)
            
        # Cleanup expired states safely
        current_time = utime.time()
        for cid in list(pending_updates.keys()):
            if current_time - pending_updates[cid]["time"] > 30:
                send_markdown_msg(base_url, cid, "❌ *Session expired.*")
                del pending_updates[cid]
                
        gc.collect()

def trigger_update_sequence(base_url, user_chat_id, log_chat_id, next_offset):
    # STEP 1: CLEAR THE QUEUE! 
    # Tell Telegram we read the message so it doesn't resend it after reboot.
    try:
        urequests.get(f"{base_url}/getUpdates?offset={next_offset}&timeout=1").close()
    except:
        pass

    # STEP 2: Animate and Reboot
    url = f"{base_url}/sendMessage"
    try:
        res = urequests.post(url, data=ujson.dumps({"chat_id": str(user_chat_id), "text": "🔄 Authentication successful! Syncing..."}), headers={'Content-Type': 'application/json'}, timeout=5)
        msg_id = res.json()["result"]["message_id"]
        res.close()
    except:
        machine.reset()
        return

    send_markdown_msg(base_url, log_chat_id, f"⚠️ *Update triggered.* Restarting hardware.")
    
    steps = [
        "📦 Fetching raw source files...",
        "🗑️ Purging obsolete modules...",
        "♻️ Rebooting ESP32-CAM!"
    ]
    
    for step in steps:
        utime.sleep(1)
        edit_msg(base_url, user_chat_id, msg_id, step)
        
    utime.sleep(0.5)
    machine.reset()
