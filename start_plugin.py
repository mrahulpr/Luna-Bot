import urequests
import ujson

def handle_update(update, base_url):
    message = update["message"]
    chat_id = message["chat"]["id"]
    
    welcome = (
        "🤖 *Luna-Bot Active*\n\n"
        "Available options:\n"
        "• `/start` \- Display this control matrix\n"
        "• `/update` \- Securely pull code updates"
    )
    
    url = f"{base_url}/sendMessage"
    payload = {
        "chat_id": str(chat_id),
        "text": welcome,
        "parse_mode": "MarkdownV2"
    }
    try:
        res = urequests.post(url, data=ujson.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=5)
        res.close()
    except Exception as e:
        raise Exception(f"StartPlugin Error: {e}")
