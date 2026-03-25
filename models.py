from pydantic import BaseModel

class UserInitData(BaseModel):
    tg_id: int
    username: str = ""
    first_name: str = ""
    photo_url: str = ""

class ActionData(BaseModel):
    tg_id: int
    gift_id: int

class TaskCheckData(BaseModel):
    tg_id: int
    task_id: int

class SpinData(BaseModel):
    tg_id: int

class RocketBetData(BaseModel):
    tg_id: int
    bet: int

class RocketCashoutData(BaseModel):
    tg_id: int
    multiplier: float

class TopupData(BaseModel):
    tg_id: int
    stars_amount: int