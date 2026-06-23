import utime
import urequests
import gc
import machine
import ujson

pending_updates = {} 

def send_msg(base_url, chat_id, text):
    url = f"{base_url}/sendMessage"
    headers = {'Content-Type': 'application/json'}
    payload = {"chat_id": str(chat_id), "text": text}
    try:
        res = urequests.post(url, data=ujson.dumps(payload), headers=headers)
        res.close()
    except Exception as e:
        print(f"Send failed: {e}")

def edit_msg(base_url, chat_id, message_id, text):
    url = f"{base_url}/editMessageText"
    headers = {'Content-Type': 'application/json'}
    payload = {"chat_id": str(chat_id), "message_id": message_id, "text": text}
    try:
        res = urequests.post(url, data=ujson.dumps(payload), headers=headers)
        res.close()
    except Exception as e:
        print(f"Edit failed: {e}")

def run(token, owner_id, security_key, log_chat_id):
    # Dynamically import plugins safely
    import echo_plugin
    import start_plugin
    
    base_url = f"https://api.telegram.org/bot{token}"
    offset = 0
    
    # Send boot alert to your log chat right away
    send_msg(base_url, log_chat_id, "🟢 System Online: ESP32-CAM Booted & Sync Complete.")
    
    print("Bot engine is running rapidly...")
    
    while True:
        try:
            # Short timeout (1 sec) prevents long socket blocking so multi-users don't freeze the bot
            url = f"{base_url}/getUpdates?offset={offset}&timeout=1"
            res = urequests.get(url)
            
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
                        text = message.get("text", "").strip()
                        
                        # 1. Handle Security Key input state
                        if chat_id in pending_updates:
                            session = pending_updates[chat_id]
                            if utime.time() - session["time"] > 10:
                                send_msg(base_url, chat_id, "❌ Verification timed out. Update aborted.")
                                del pending_updates[chat_id]
                            else:
                                if text == str(security_key):
                                    del pending_updates[chat_id]
                                    trigger_update_sequence(base_url, chat_id, log_chat_id)
                                else:
                                    send_msg(base_url, chat_id, "❌ Incorrect Key. Update access denied.")
                                    del pending_updates[chat_id]
                            continue

                        # 2. Handle commands
                        if text == "/update":
                            send_msg(base_url, chat_id, "🔐 Verification Required.\nEnter your 4-digit Security Key within 10 seconds:")
                            pending_updates[chat_id] = {"time": utime.time()}
                            continue
                            
                        elif text == "/start":
                            start_plugin.handle_update(update, base_url)
                            continue
                        
                        # 3. Fallback to normal plugins
                        echo_plugin.handle_update(update, base_url)
            else:
                res.close()
        except Exception as e:
            print(f"Loop error: {e}")
            
        # Clear out expired update tracking tokens safely
        current_time = utime.time()
        for cid in list(pending_updates.keys()):
            if current_time - pending_updates[cid]["time"] > 10:
                send_msg(base_url, cid, "❌ Verification timed out. Update aborted.")
                del pending_updates[cid]
                
        gc.collect()
        utime.sleep(0.1) # Rapid sleep to prevent CPU hogging but keep updates smooth

def trigger_update_sequence(base_url, user_chat_id, log_chat_id):
    url = f"{base_url}/sendMessage"
    headers = {'Content-Type': 'application/json'}
    
    # Notify system owner
    try:
        res = urequests.post(url, data=ujson.dumps({"chat_id": str(user_chat_id), "text": "🔄 Auth success! Updating..."}), headers=headers)
        msg_data = res.json()
        res.close()
        msg_id = msg_data["result"]["message_id"]
    except:
        return

    # Log to the Dedicated Log Chat Channel
    send_msg(base_url, log_chat_id, f"⚠️ Notice: Update triggered by user session {user_chat_id}. Rebooting hardware now...")
    
    animations = [
        "📦 Pulling production branch from GitHub...",
        "💾 Overwriting local filesystem sectors...",
        "♻️ Finalizing installation. Rebooting board right now!"
    ]
    
    for step in animations:
        utime.sleep(1)
        edit_msg(base_url, user_chat_id, msg_id, step)
        
    utime.sleep(0.5)
    machine.reset()
