import hmac
import hashlib
import urllib.parse
import json

def validate_telegram_data(init_data: str, bot_token: str) -> dict:
    if not init_data: return None
    parsed = urllib.parse.parse_qs(init_data)
    data_check = []
    for key in sorted(parsed.keys()):
        if key == 'hash': continue
        data_check.append(f"{key}={parsed[key][0]}")
    data_check_string = "\n".join(data_check)
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if computed_hash != parsed.get('hash', [''])[0]: return None
    return json.loads(parsed.get('user', ['{}'])[0])
