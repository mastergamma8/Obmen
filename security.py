from fastapi import HTTPException, Header
import hmac
import hashlib
from urllib.parse import parse_qsl

import config

def validate_telegram_data(init_data: str) -> bool:
    """Проверяет подлинность данных, пришедших из Telegram Web App."""
    if not init_data: return False
    try:
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data: return False
        
        hash_ = parsed_data.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        
        secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return calculated_hash == hash_
    except Exception:
        return False

async def verify_user(x_tg_data: str = Header(None)):
    if not config.BOT_TOKEN:
         raise HTTPException(status_code=500, detail="Токен бота не настроен")
         
    if not x_tg_data or not validate_telegram_data(x_tg_data):
        raise HTTPException(status_code=403, detail="Недействительные данные авторизации Telegram")
    return True