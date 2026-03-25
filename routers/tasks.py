from fastapi import APIRouter, Depends, HTTPException
import httpx

import config
import database
from models import TaskCheckData
from security import verify_user

router = APIRouter(prefix="/api", tags=["tasks"])

@router.get("/earn_data")
async def get_earn_data(tg_id: int, is_valid: bool = Depends(verify_user)):
    referrals = await database.get_referrals(tg_id)
    completed_tasks = await database.get_completed_tasks(tg_id)
    
    tasks_list = []
    for t_id, t_data in config.TASKS.items():
        tasks_list.append({
            "id": t_id,
            "title": t_data["title"],
            "url": t_data.get("url", ""), 
            "reward": t_data["reward"],
            "reward_type": t_data.get("reward_type", "balance"), # <-- Добавлено получение типа награды
            "completed": t_id in completed_tasks
        })
        
    return {
        "referrals": referrals,
        "tasks": tasks_list
    }

@router.post("/check_task")
async def check_task(data: TaskCheckData, is_valid: bool = Depends(verify_user)):
    if data.task_id not in config.TASKS:
        raise HTTPException(status_code=400, detail="Задание не найдено")
        
    completed = await database.get_completed_tasks(data.tg_id)
    if data.task_id in completed:
        raise HTTPException(status_code=400, detail="Задание уже выполнено")
        
    task_info = config.TASKS[data.task_id]
    task_type = task_info.get("type", "subscription") 
    
    success_status = False

    if task_type == "referral":
        required_refs = task_info.get("required_referrals", 1)
        referrals = await database.get_referrals(data.tg_id)
        
        if len(referrals) >= required_refs:
            success_status = True
        else:
            remaining = required_refs - len(referrals)
            return {"status": "error", "detail": f"Вам нужно пригласить еще {remaining} чел. (Приглашено: {len(referrals)})"}
    
    else:
        chat_id = task_info.get("chat_id")
        async with httpx.AsyncClient() as client:
            try:
                if task_type == "subscription":
                    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getChatMember"
                    params = {"chat_id": chat_id, "user_id": data.tg_id}
                    
                    response = await client.get(url, params=params)
                    res_data = response.json()
                    
                    if res_data.get("ok"):
                        status = res_data["result"]["status"]
                        if status in ["member", "administrator", "creator"]:
                            success_status = True
                        else:
                            return {"status": "error", "detail": "Вы не подписаны на канал!"}
                    else:
                        return {"status": "error", "detail": "Ошибка проверки. Бот администратор в канале?"}
                
                elif task_type == "boost":
                    url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/getUserChatBoosts"
                    params = {"chat_id": chat_id, "user_id": data.tg_id}
                    
                    response = await client.get(url, params=params)
                    res_data = response.json()
                    
                    if res_data.get("ok"):
                        boosts = res_data["result"]["boosts"]
                        if len(boosts) > 0:
                            success_status = True
                        else:
                            return {"status": "error", "detail": "Вы не проголосовали за канал (нет активного буста)!"}
                    else:
                        return {"status": "error", "detail": "Ошибка проверки буста. Бот администратор в канале?"}
                else:
                    return {"status": "error", "detail": "Неизвестный тип задания."}

            except Exception as e:
                return {"status": "error", "detail": f"Ошибка соединения с Telegram API: {str(e)}"}

    if success_status:
        await database.mark_task_completed(data.tg_id, data.task_id)
        
        # --- ИЗМЕНЕНИЯ: Начисление в зависимости от типа награды ---
        reward_type = task_info.get("reward_type", "balance")
        reward_amount = task_info["reward"]
        
        if reward_type == "stars":
            await database.add_stars_to_user(data.tg_id, reward_amount)
            await database.add_history_entry(
                data.tg_id, "task_reward_stars", f"Задание выполнено (Звезды): {task_info['title']}", reward_amount
            )
        else:
            await database.add_points_to_user(data.tg_id, reward_amount)
            await database.add_history_entry(
                data.tg_id, "task_reward", f"Задание выполнено: {task_info['title']}", reward_amount
            )
        
        user_data = await database.get_user_data(data.tg_id)
        return {
            "status": "ok", 
            "balance": user_data.get("balance", 0),
            "stars": user_data.get("stars", 0)
        }