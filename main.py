# main.py
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

import config
import database

app = FastAPI()

# Раздача статики (папка с фото подарков)
import os
os.makedirs("gifts", exist_ok=True)
app.mount("/gifts", StaticFiles(directory="gifts"), name="gifts")

# Раздача шаблонов (HTML)
os.makedirs("templates", exist_ok=True)
templates = Jinja2Templates(directory="templates")

class UserInitData(BaseModel):
    tg_id: int
    username: str = ""
    first_name: str = ""
    photo_url: str = ""

@app.on_event("startup")
async def startup():
    await database.init_db()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/init")
async def init_user(user: UserInitData):
    # Сохраняем актуальные данные пользователя при входе в Mini App
    await database.upsert_user(user.tg_id, user.username, user.first_name, user.photo_url)
    user_gifts = await database.get_user_gifts(user.tg_id)
    return {
        "status": "ok", 
        "user_gifts": user_gifts,
        "config": config.GIFTS
    }

@app.get("/api/leaderboard")
async def get_leaderboard():
    board = await database.get_leaderboard()
    return {"leaderboard": board}

if __name__ == "__main__":
    # Запуск сервера на порту 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
