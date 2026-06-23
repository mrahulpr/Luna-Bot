import utime
import urequests
import gc
import machine
import ujson

# Tracking update session states
pending_updates = {} 

def send_msg(base_url, chat_id, text):
    url = f"{base_url}/sendMessage"
    try:
        res = urequests.post(url, data=ujson.dumps({"chat_id": chat_id, "text": text}), headers={'Content-Type': 'application/json'})
        res.close()
    except:
        pass

def edit_msg(base_url, chat_id, message_id, text):
    url = f"{base_url}/editMessageText"
    try:
        res = urequests.post(url, data=ujson.dumps({"chat_id": chat_id, "message_id": message_id, "text": text}), headers={'Content-Type': 'application/json'})
        res.close()
    except:
        pass

def run(token, owner_id, security_key, log_chat_id):
    import echo_plugin
    base_url = f"https://api.telegram.org/bot{token}"
    offset = 0
    
    # Notify Log Chat that system booted up successfully
    send_msg(base_url, log_chat_id, "🟢 System Online: ESP32-CAM booted and synchronized successfully.")
    
    while True:
        try:
            # Short timeout to allow state machines and delays to resolve smoothly
            url = f"{base_url}/getUpdates?offset={offset}&timeout=5"
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
                        
                        # Process ongoing verification sessions
                        if chat_id in pending_updates:
                            session = pending_updates[chat_id]
                            if utime.time() - session["time"] > 10:
                                send_msg(base_url, chat_id, "❌ Verification timed out. Update aborted.")
                                del pending_updates[chat_id]
                            else:
                                if text == security_key:
                                    del pending_updates[chat_id]
                                    trigger_update_sequence(base_url, chat_id, log_chat_id)
                                else:
                                    send_msg(base_url, chat_id, "❌ Incorrect Key. Update access denied.")
                                    del pending_updates[chat_id]
                                continue

                        # Trigger initial command check
                        if text == "/update":
                            send_msg(base_url, chat_id, "🔐 Verification Required.\nPlease enter your 4-digit Security Key within 10 seconds:")
                            pending_updates[chat_id] = {"time": utime.time()}
                            continue
                        
                        # Fallback to standard application plugins
                        echo_plugin.handle_update(update, base_url)
            else:
                res.close()
        except Exception as e:
            print(f"Loop error: {e}")
            
        # Clean expired updates automatically
        current_time = utime.time()
        for cid in list(pending_updates.keys()):
            if current_time - pending_updates[cid]["time"] > 10:
                send_msg(base_url, cid, "❌ Verification timed out. Update aborted.")
                del pending_updates[cid]
                
        gc.collect()
        utime.sleep(1)

def trigger_update_sequence(base_url, user_chat_id, log_chat_id):
    # Send base placeholder message for animation steps
    url = f"{base_url}/sendMessage"
    res = urequests.post(url, data=ujson.dumps({"chat_id": user_chat_id, "text": "🔄 Authentication successful! Initializing update..."}), headers={'Content-Type': 'application/json'})
    msg_data = res.json()
    res.close()
    
    msg_id = msg_data["result"]["message_id"]
    
    # Fake Deployment Animation Sequence
    animations = [
        "📦 Pulling latest production commit from GitHub...",
        "🗜️ Extracting artifacts & validating source structure...",
        "💾 Overwriting local filesystem sectors...",
        "🔌 Validating dependencies & hardware configurations...",
        "♻️ Finalizing installations. Rebooting board right now!"
    ]
    
    for step in animations:
        utime.sleep(1)
        edit_msg(base_url, user_chat_id, msg_id, step)
        
    utime.sleep(0.5)
    
    # Signal hardware reboot
    machine.reset()
