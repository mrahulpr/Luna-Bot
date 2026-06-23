import urequests
import ujson

def handle_update(update, base_url):
    message = update["message"]
    chat_id = message["chat"]["id"]
    
    welcome_text = "👋 Welcome to your Self-Hosted ESP32 Bot!\n\nAvailable Commands:\n/start - View this welcome menu\n/update - Pull latest code from GitHub securely"
    
    url = f"{base_url}/sendMessage"
    payload = {"chat_id": str(chat_id), "text": welcome_text}
    try:
        res = urequests.post(url, data=ujson.dumps(payload), headers={'Content-Type': 'application/json'})
        res.close()
    except Exception as e:
        print(f"Start reply failed: {e}")
