import urequests
import ujson

def handle_update(update, base_url):
    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    
    if text:
        url = f"{base_url}/sendMessage"
        payload = {"chat_id": chat_id, "text": f"Echo: {text}"}
        try:
            res = urequests.post(url, data=ujson.dumps(payload), headers={'Content-Type': 'application/json'})
            res.close()
        except:
            pass
