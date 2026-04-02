# config.py
import os
import requests
import cloudscraper  # <-- Библиотека для обхода Cloudflare
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Безопасное получение токена
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения (.env)!")

BOT_USERNAME = os.getenv("BOT_USERNAME")
if not BOT_USERNAME:
    raise ValueError("BOT_USERNAME не найден в переменных окружения (.env)!") 

WEBAPP_URL = os.getenv("WEBAPP_URL")
if not WEBAPP_URL:
    raise ValueError("WEBAPP_URL не найден в переменных окружения (.env)!") 

ADMIN_ID = 1809630966

# ── Курс конвертации валют для банка ─────────────────────────────────────────
# 1 пончик = DONUTS_TO_STARS_RATE звёзд в единицах стоимости банка.
# Все пончиковые суммы умножаются на этот коэффициент перед записью в банк,
# чтобы total_deposited_value, RTP и проверки платёжеспособности были
# корректны при смешанной экономике.
DONUTS_TO_STARS_RATE: int = 115

# Комиссия за вывод подарка в звездах
WITHDRAW_FEE_STARS = 25

# ==========================================
# ЗАДАНИЯ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
# ==========================================
TASKS = {
    1: {
        "title": "Подписаться на наш канал",
        "url": "https://t.me/Space_Donut",
        "chat_id": "@Space_Donut",
        "reward": 1,
        "reward_type": "stars", 
        "type": "subscription"
    },
    2: {
        "title": "Подписаться на Dewid NFT",
        "url": "https://t.me/DewidNFT",
        "chat_id": "@DewidNFT",
        "reward": 1,
        "reward_type": "stars", 
        "type": "subscription"
    },
    3: {
        "title": "Проголосовать за канал",
        "url": "https://t.me/boost/Space_Donut",
        "chat_id": "@Space_Donut",
        "reward": 1,
        "reward_type": "stars", 
        "type": "boost"
    },
    4: {
        "title": "Пригласить 1 друга",
        "url": "", 
        "reward": 1, 
        "reward_type": "stars", 
        "type": "referral",
        "required_referrals": 1
    },
    5: {
        "title": "Пригласить 5 друзей",
        "url": "",
        "reward": 5,
        "reward_type": "stars", 
        "type": "referral",
        "required_referrals": 5
    },
    6: {
        "title": "Пригласить 10 друзей",
        "url": "",
        "reward": 10,
        "reward_type": "stars", 
        "type": "referral",
        "required_referrals": 10
    }
}

# ==========================================
# НАСТРОЙКИ РУЛЕТКИ
# ==========================================
ROULETTE_CONFIG = {
    "currency": "stars", 
    "cost": 150,
    "items": [
        {"type": "stars", "amount": 1, "photo": "gifts/stars.png", "chance": 20},
        {"type": "stars", "amount": 9, "photo": "gifts/stars.png", "chance": 30},  
        {"type": "stars", "amount": 20, "photo": "gifts/stars.png", "chance": 15},
        {"type": "stars", "amount": 50, "photo": "gifts/stars.png", "chance": 25},
        {"type": "stars", "amount": 150, "photo": "gifts/stars.png", "chance": 10}, 
        {"type": "donuts", "amount": 5, "photo": "gifts/dount.png", "chance": 5}, 
        {"type": "donuts", "amount": 10, "photo": "gifts/dount.png", "chance": 0},
        {"type": "donuts", "amount": 50, "photo": "gifts/dount.png", "chance": 0}, 
        {"type": "gift", "gift_id": 2009, "chance": 5},
        {"type": "gift", "gift_id": 2010, "chance": 5},
        {"type": "gift", "gift_id": 2007, "chance": 5},
    ]
}

# ==========================================
# БЕСПЛАТНЫЙ КЕЙС (раз в 24 часа)
# ==========================================
FREE_CASE_CONFIG = {
    "name": "Бесплатный кейс",
    "photo": "/gifts/dount.png",
    "items": [
        {"type": "stars", "amount": 1,  "chance": 50},
        {"type": "stars", "amount": 5, "chance": 10},
        {"type": "stars", "amount": 10, "chance": 5},
        {"type": "stars",  "amount": 15,  "chance": 1},
        {"type": "stars",  "amount": 50,  "chance": 0}
    ]
}

# ==========================================
# НАСТРОЙКИ КЕЙСОВ
# ==========================================
CASES_CONFIG = {
    1: {
        "name": "Новичок",
        "photo": "/gifts/donuts.png", 
        "currency": "stars", 
        "price": 15,
        "items": [
            {"type": "stars", "amount": 5, "chance": 40},
            {"type": "stars", "amount": 15, "chance": 30},
            {"type": "gift", "gift_id": 2009, "chance": 20},
            {"type": "gift", "gift_id": 2011, "chance": 40}
        ]
    },
    2: {
        "name": "Элитный",
        "photo": "/gifts/case_elite.png",
        "currency": "stars",
        "price": 50,
        "items": [
            {"type": "donuts", "amount": 20, "chance": 30},
            {"type": "donuts", "amount": 50, "chance": 25},
            {"type": "gift", "gift_id": 2007, "chance": 25},
            {"type": "gift", "gift_id": 2008, "chance": 15},
            {"type": "gift", "gift_id": 2005, "chance": 5}
        ]
    },
    3: {
        "name": "Звездный",
        "photo": "/gifts/case_space.png",
        "currency": "stars", 
        "price": 50,
        "items": [
            {"type": "donuts", "amount": 500, "chance": 40},
            {"type": "stars", "amount": 100, "chance": 30},
            {"type": "gift", "gift_id": 2000, "chance": 20},
            {"type": "gift", "gift_id": 2004, "chance": 10}
        ]
    }
}

# ==========================================
# НАСТРОЙКИ РАКЕТЫ (CRASH ИГРА)
# ==========================================
ROCKET_CONFIG = {
    "currency": "stars",          
    "min_bet": 50,                  
    "max_bet": 10000,              
    "house_edge": 0.05,            
    "max_multiplier": 1000.0,      
    "growth_speed": 1.00006        
}

# ==========================================
# БАЗОВЫЕ ПОДАРКИ
# ==========================================
BASE_GIFTS = {
    1: {"name": "Victory Medal", "photo": "https://api.changes.tg/original/VictoryMedal.png", "value": 4},
    2: {"name": "Desk Calendar", "photo": "https://api.changes.tg/original/DeskCalendar.png", "value": 5},
    3: {"name": "Homemade Cake", "photo": "https://api.changes.tg/original/HomemadeCake.png", "value": 4},
    4: {"name": "Jingle Bells", "photo": "https://api.changes.tg/original/JingleBells.png", "value": 8},
    5: {"name": "Lol Pop", "photo": "https://api.changes.tg/original/LolPop.png", "value": 4},
    6: {"name": "Sakura Flower", "photo": "https://api.changes.tg/original/SakuraFlower.png", "value": 9},
    7: {"name": "Happy Brownie", "photo": "https://api.changes.tg/original/HappyBrownie.png", "value": 4},
    8: {"name": "Instant Ramen", "photo": "https://api.changes.tg/original/InstantRamen.png", "value": 3},
    9: {"name": "Spring Basket", "photo": "https://api.changes.tg/original/SpringBasket.png", "value": 4},
    10: {"name": "Input Key", "photo": "https://api.changes.tg/original/InputKey.png", "value": 5},
    11: {"name": "Santa Hat", "photo": "https://api.changes.tg/original/SantaHat.png", "value": 4},
    12: {"name": "Signet Ring", "photo": "https://api.changes.tg/original/SignetRing.png", "value": 30},
    13: {"name": "Precious Peach", "photo": "https://api.changes.tg/original/PreciousPeach.png", "value": 380},
    14: {"name": "Spiced Wine", "photo": "https://api.changes.tg/original/SpicedWine.png", "value": 5},
    15: {"name": "Jelly Bunny", "photo": "https://api.changes.tg/original/JellyBunny.png", "value": 7},
    16: {"name": "Eternal Rose", "photo": "https://api.changes.tg/original/EternalRose.png", "value": 25},
    17: {"name": "Berry Box", "photo": "https://api.changes.tg/original/BerryBox.png", "value": 7},
    18: {"name": "Vintage Cigar", "photo": "https://api.changes.tg/original/VintageCigar.png", "value": 30},
    19: {"name": "Magic Potion", "photo": "https://api.changes.tg/original/MagicPotion.png", "value": 75},
    20: {"name": "Kissed Frog", "photo": "https://api.changes.tg/original/KissedFrog.png", "value": 55},
    21: {"name": "Hex Pot", "photo": "https://api.changes.tg/original/HexPot.png", "value": 4},
    22: {"name": "Evil Eye", "photo": "https://api.changes.tg/original/EvilEye.png", "value": 6},
    23: {"name": "Sharp Tongue", "photo": "https://api.changes.tg/original/SharpTongue.png", "value": 40},
    24: {"name": "Trapped Heart", "photo": "https://api.changes.tg/original/TrappedHeart.png", "value": 12},
    25: {"name": "Skull Flower", "photo": "https://api.changes.tg/original/SkullFlower.png", "value": 30},
    26: {"name": "Scared Cat", "photo": "https://api.changes.tg/original/ScaredCat.png", "value": 150},
    27: {"name": "Spy Agaric", "photo": "https://api.changes.tg/original/SpyAgaric.png", "value": 5},
    28: {"name": "Genie Lamp", "photo": "https://api.changes.tg/original/GenieLamp.png", "value": 50},
    29: {"name": "Lunar Snake", "photo": "https://api.changes.tg/original/LunarSnake.png", "value": 4},
    30: {"name": "Party Sparkler", "photo": "https://api.changes.tg/original/PartySparkler.png", "value": 4},
    31: {"name": "Jester Hat", "photo": "https://api.changes.tg/original/JesterHat.png", "value": 4},
    32: {"name": "Witch Hat", "photo": "https://api.changes.tg/original/WitchHat.png", "value": 5},
    33: {"name": "Hanging Star", "photo": "https://api.changes.tg/original/HangingStar.png", "value": 8},
    34: {"name": "Love Candle", "photo": "https://api.changes.tg/original/LoveCandle.png", "value": 10},
    35: {"name": "Cookie Heart", "photo": "https://api.changes.tg/original/CookieHeart.png", "value": 5},
    36: {"name": "Snow Mittens", "photo": "https://api.changes.tg/original/SnowMittens.png", "value": 6},
    37: {"name": "Voodoo Doll", "photo": "https://api.changes.tg/original/VoodooDoll.png", "value": 25},
    38: {"name": "Mad Pumpkin", "photo": "https://api.changes.tg/original/MadPumpkin.png", "value": 12},
    39: {"name": "Hypno Lollipop", "photo": "https://api.changes.tg/original/HypnoLollipop.png", "value": 4},
    40: {"name": "B-Day Candle", "photo": "https://api.changes.tg/original/BDayCandle.png", "value": 4},
    41: {"name": "Bunny Muffin", "photo": "https://api.changes.tg/original/BunnyMuffin.png", "value": 6},
    42: {"name": "Astral Shard", "photo": "https://api.changes.tg/original/AstralShard.png", "value": 185},
    43: {"name": "Flying Broom", "photo": "https://api.changes.tg/original/FlyingBroom.png", "value": 10},
    44: {"name": "Crystal Ball", "photo": "https://api.changes.tg/original/CrystalBall.png", "value": 10},
    45: {"name": "Eternal Candle", "photo": "https://api.changes.tg/original/EternalCandle.png", "value": 5},
    46: {"name": "Ginger Cookie", "photo": "https://api.changes.tg/original/GingerCookie.png", "value": 4},
    47: {"name": "Mini Oscar", "photo": "https://api.changes.tg/original/MiniOscar.png", "value": 85},
    48: {"name": "Star Notepad", "photo": "https://api.changes.tg/original/StarNotepad.png", "value": 4},
    49: {"name": "Loot Bag", "photo": "https://api.changes.tg/original/LootBag.png", "value": 150},
    50: {"name": "Love Potion", "photo": "https://api.changes.tg/original/LovePotion.png", "value": 12},
    51: {"name": "Toy Bear", "photo": "https://api.changes.tg/original/ToyBear.png", "value": 40},
    52: {"name": "Diamond Ring", "photo": "https://api.changes.tg/original/DiamondRing.png", "value": 25},
    53: {"name": "Sleigh Bell", "photo": "https://api.changes.tg/original/SleighBell.png", "value": 8},
    54: {"name": "Top Hat", "photo": "https://api.changes.tg/original/TopHat.png", "value": 10},
    55: {"name": "Record Player", "photo": "https://api.changes.tg/original/RecordPlayer.png", "value": 11},
    56: {"name": "Winter Wreath", "photo": "https://api.changes.tg/original/WinterWreath.png", "value": 4},
    57: {"name": "Snow Globe", "photo": "https://api.changes.tg/original/SnowGlobe.png", "value": 4},
    58: {"name": "Electric Skull", "photo": "https://api.changes.tg/original/ElectricSkull.png", "value": 25},
    59: {"name": "Tama Gadget", "photo": "https://api.changes.tg/original/TamaGadget.png", "value": 4},
    60: {"name": "Candy Cane", "photo": "https://api.changes.tg/original/CandyCane.png", "value": 4},
    61: {"name": "Neko Helmet", "photo": "https://api.changes.tg/original/NekoHelmet.png", "value": 35},
    62: {"name": "Jack-in-the-Box", "photo": "https://api.changes.tg/original/JackInTheBox.png", "value": 4},
    63: {"name": "Easter Egg", "photo": "https://api.changes.tg/original/EasterEgg.png", "value": 4},
    64: {"name": "Bonded Ring", "photo": "https://api.changes.tg/original/BondedRing.png", "value": 45},
    65: {"name": "Pet Snake", "photo": "https://api.changes.tg/original/PetSnake.png", "value": 4},
    66: {"name": "Snake Box", "photo": "https://api.changes.tg/original/SnakeBox.png", "value": 4},
    67: {"name": "Xmas Stocking", "photo": "https://api.changes.tg/original/XmasStocking.png", "value": 4},
    68: {"name": "Big Year", "photo": "https://api.changes.tg/original/BigYear.png", "value": 4},
    69: {"name": "Holiday Drink", "photo": "https://api.changes.tg/original/HolidayDrink.png", "value": 4},
    70: {"name": "Gem Signet", "photo": "https://api.changes.tg/original/GemSignet.png", "value": 60},
    71: {"name": "Light Sword", "photo": "https://api.changes.tg/original/LightSword.png", "value": 5},
    72: {"name": "Restless Jar", "photo": "https://api.changes.tg/original/RestlessJar.png", "value": 4},
    73: {"name": "Nail Bracelet", "photo": "https://api.changes.tg/original/NailBracelet.png", "value": 125},
    74: {"name": "Heroic Helmet", "photo": "https://api.changes.tg/original/HeroicHelmet.png", "value": 230},
    75: {"name": "Bow Tie", "photo": "https://api.changes.tg/original/BowTie.png", "value": 5},
    76: {"name": "Lush Bouquet", "photo": "https://api.changes.tg/original/LushBouquet.png", "value": 6},
    77: {"name": "Whip Cupcake", "photo": "https://api.changes.tg/original/WhipCupcake.png", "value": 4},
    78: {"name": "Joyful Bundle", "photo": "https://api.changes.tg/original/JoyfulBundle.png", "value": 7},
    79: {"name": "Cupid Charm", "photo": "https://api.changes.tg/original/CupidCharm.png", "value": 20},
    80: {"name": "Valentine Box", "photo": "https://api.changes.tg/original/ValentineBox.png", "value": 10},
    81: {"name": "Snoop Dogg", "photo": "https://api.changes.tg/original/SnoopDogg.png", "value": 4},
    82: {"name": "Swag Bag", "photo": "https://api.changes.tg/original/SwagBag.png", "value": 4},
    83: {"name": "Snoop Cigar", "photo": "https://api.changes.tg/original/SnoopCigar.png", "value": 10},
    84: {"name": "Low Rider", "photo": "https://api.changes.tg/original/LowRider.png", "value": 45},
    85: {"name": "Westside Sign", "photo": "https://api.changes.tg/original/WestsideSign.png", "value": 95},
    86: {"name": "Stellar Rocket", "photo": "https://api.changes.tg/original/StellarRocket.png", "value": 4},
    87: {"name": "Jolly Chimp", "photo": "https://api.changes.tg/original/JollyChimp.png", "value": 6},
    88: {"name": "Moon Pendant", "photo": "https://api.changes.tg/original/MoonPendant.png", "value": 4},
    89: {"name": "Ionic Dryer", "photo": "https://api.changes.tg/original/IonicDryer.png", "value": 15},
    90: {"name": "Mighty Arm", "photo": "https://api.changes.tg/original/MightyArm.png", "value": 150},
    91: {"name": "Clover Pin", "photo": "https://api.changes.tg/original/CloverPin.png", "value": 4},
    92: {"name": "Sky Stilettos", "photo": "https://api.changes.tg/original/SkyStilettos.png", "value": 13},
    93: {"name": "Fresh Socks", "photo": "https://api.changes.tg/original/FreshSocks.png", "value": 4},
    94: {"name": "Ice Cream", "photo": "https://api.changes.tg/original/IceCream.png", "value": 4},
    95: {"name": "Faith Amulet", "photo": "https://api.changes.tg/original/FaithAmulet.png", "value": 4},
    96: {"name": "Mousse Cake", "photo": "https://api.changes.tg/original/MousseCake.png", "value": 4},
    97: {"name": "Bling Binky", "photo": "https://api.changes.tg/original/BlingBinky.png", "value": 30},
    98: {"name": "Money Pot", "photo": "https://api.changes.tg/original/MoneyPot.png", "value": 4},
    99: {"name": "Pretty Posy", "photo": "https://api.changes.tg/original/PrettyPosy.png", "value": 5},
    # --- ДОБАВЛЕННЫЕ НОВЫЕ ПОДАРКИ ---
    100: {"name": "Plush Pepe", "photo": "https://api.changes.tg/original/PlushPepe.png", "value": 50},
    101: {"name": "Durov's Cap", "photo": "https://api.changes.tg/original/DurovsCap.png", "value": 50},
    102: {"name": "Perfume Bottle", "photo": "https://api.changes.tg/original/PerfumeBottle.png", "value": 50},
    103: {"name": "Swiss Watch", "photo": "https://api.changes.tg/original/SwissWatch.png", "value": 50},
    104: {"name": "Ion Gem", "photo": "https://api.changes.tg/original/IonGem.png", "value": 50},
    105: {"name": "Heart Locket", "photo": "https://api.changes.tg/original/HeartLocket.png", "value": 50},
    106: {"name": "Artisan Brick", "photo": "https://api.changes.tg/original/ArtisanBrick.png", "value": 50},
    107: {"name": "Khabib's Papakha", "photo": "https://api.changes.tg/original/KhabibsPapakha.png", "value": 50},
    108: {"name": "UFC Strike", "photo": "https://api.changes.tg/original/UFCStrike.png", "value": 50},
    109: {"name": "Rare Bird", "photo": "https://api.changes.tg/original/RareBird.png", "value": 50},
    110: {"name": "Mood Pack", "photo": "https://api.changes.tg/original/MoodPack.png", "value": 50},
    111: {"name": "Pool Float", "photo": "https://api.changes.tg/original/PoolFloat.png", "value": 50},
    112: {"name": "Timeless Book", "photo": "https://api.changes.tg/original/TimelessBook.png", "value": 50},
    113: {"name": "Chill Flame", "photo": "https://api.changes.tg/original/ChillFlame.png", "value": 50},
    114: {"name": "Vice Cream", "photo": "https://api.changes.tg/original/ViceCream.png", "value": 50}
}
    
    # ==========================================
MAIN_GIFTS = {
    1000: {"name": "Swiss Watch", "photo": "https://api.changes.tg/original/SwissWatch.png", "required_value": 50},
    1001: {"name": "Artisan Brick", "photo": "https://api.changes.tg/original/ArtisanBrick.png", "required_value": 100},
    1002: {"name": "Perfume Bottle", "photo": "https://api.changes.tg/original/PerfumeBottle.png", "required_value": 100},
    1003: {"name": "Ion Gem", "photo": "https://api.changes.tg/original/IonGem.png", "required_value": 100},
    1004: {"name": "Durov's Cap", "photo": "https://api.changes.tg/original/DurovsCap.png", "required_value": 700}
}


# ==========================================
# РЕАЛЬНЫЕ TELEGRAM GIFTS ДЛЯ ВЫИГРЫШЕЙ
# ==========================================
TG_GIFTS = {
    2000: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/6028601630662853006/Original.png", "required_value": 50,  "tg_gift_id": "6028601630662853006"},
    2001: {"name": "", "photo": "https://cdn.changes.tg/gifts/originals/5170521118301225164/Original.png", "required_value": 100, "tg_gift_id": "5170521118301225164"},
    2002: {"name": "", "photo": "https://cdn.changes.tg/gifts/originals/5170690322832818290/Original.png", "required_value": 100, "tg_gift_id": "5170690322832818290"},
    2003: {"name": "", "photo": "https://cdn.changes.tg/gifts/originals/5168043875654172773/Original.png", "required_value": 100, "tg_gift_id": "5168043875654172773"},
    2004: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5170564780938756245/Original.png", "required_value": 50,  "tg_gift_id": "5170564780938756245"},
    2005: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5170314324215857265/Original.png", "required_value": 50,  "tg_gift_id": "5170314324215857265"},
    2006: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5170144170496491616/Original.png", "required_value": 50,  "tg_gift_id": "5170144170496491616"},
    2007: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5168103777563050263/Original.png", "required_value": 25,  "tg_gift_id": "5168103777563050263"},
    2008: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5170250947678437525/Original.png", "required_value": 25,  "tg_gift_id": "5170250947678437525"},
    2009: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5170233102089322756/Original.png", "required_value": 15,  "tg_gift_id": "5170233102089322756"},
    2010: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5170145012310081615/Original.png", "required_value": 15,  "tg_gift_id": "5170145012310081615"},
    2011: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5801108895304779062/Original.png", "required_value": 50,  "tg_gift_id": "5801108895304779062"},
    2012: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5922558454332916696/Original.png", "required_value": 50,  "tg_gift_id": "5922558454332916696"},
    2013: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5956217000635139069/Original.png", "required_value": 50,  "tg_gift_id": "5956217000635139069"},
    2014: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5800655655995968830/Original.png", "required_value": 50,  "tg_gift_id": "5800655655995968830"},
    2015: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5866352046986232958/Original.png", "required_value": 50,  "tg_gift_id": "5866352046986232958"},
    2016: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5893356958802511476/Original.png", "required_value": 50,  "tg_gift_id": "5893356958802511476"},
    2017: {"name": "",  "photo": "https://cdn.changes.tg/gifts/originals/5935895822435615975/Original.png", "required_value": 50,  "tg_gift_id": "5935895822435615975"},
}


# ==========================================
# АВТООБНОВЛЕНИЕ ЦЕН БАЗОВЫХ ПОДАРКОВ ИЗ API
# ==========================================
def update_base_gifts_prices():
    """
    Динамически обновляет цены базовых подарков из API Portals.
    Новая цена = floor_price минус 20%, без дробей (округляется вниз).
    """
    print("Загрузка актуальных цен для базовых подарков из API Portals...")
    
    # Создаем скрейпер, который имитирует обычный браузер и обходит Cloudflare
    try:
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
    except Exception as e:
        print(f"Не удалось инициализировать cloudscraper: {e}")
        return

    # 1. Сначала пробуем выгрузить большой пакет популярных коллекций
    market_prices = {}
    try:
        resp = scraper.get("https://portal-market.com/api/collections", params={"limit": 300}, timeout=15)
        if resp.status_code == 200:
            collections = resp.json().get("collections", [])
            for item in collections:
                market_prices[item["name"].lower()] = float(item.get("floor_price", 0))
        else:
            print(f"⚠️ Ошибка доступа к API: {resp.status_code}")
    except Exception as e:
        print(f"Не удалось выгрузить общую базу цен: {e}. Буду запрашивать поштучно...")

    updated_count = 0
    
    # 2. Перебираем все базовые подарки
    for gift_id, gift in BASE_GIFTS.items():
        gift_name_lower = gift["name"].lower()
        floor_price = None
        
        # Если подарок нашелся в выгруженной общей базе
        if gift_name_lower in market_prices:
            floor_price = market_prices[gift_name_lower]
        else:
            # Если не нашелся — делаем отдельный точечный запрос
            try:
                resp = scraper.get(
                    "https://portal-market.com/api/collections", 
                    params={"search": gift["name"], "limit": 1}, 
                    timeout=5
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("collections") and len(data["collections"]) > 0:
                        floor_price = float(data["collections"][0].get("floor_price", 0))
            except Exception:
                pass # Пропускаем при ошибках сети
        
        # 3. Рассчитываем и применяем новую цену по твоей логике (-20% и без дробей)
        if floor_price is not None and floor_price > 0:
            new_price = int(floor_price * 0.8)
            BASE_GIFTS[gift_id]["value"] = max(1, new_price)
            updated_count += 1
            
    print(f"✅ Цены успешно обновлены! Изменено: {updated_count} из {len(BASE_GIFTS)}")