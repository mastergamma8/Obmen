# config.py
import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Безопасное получение токена
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения (.env)!")

BOT_USERNAME = "SpaceDonutBot" 
WEBAPP_URL = "https://65236da3-9e20-4a31-97c8-7fe8bda0d438-00-188grbgfvp38t.kirk.replit.dev/" 
ADMIN_ID = 1809630966

# ==========================================
# ЗАДАНИЯ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ (Подписки)
# ==========================================
# ВАЖНО: Бот должен быть администратором в этих каналах/чатах, чтобы проверять подписку!
TASKS = {
    1: {
        "title": "Подписаться на наш канал",
        "url": "https://t.me/Space_Donut", # Ссылка для перехода (которую откроет юзер)
        "chat_id": "@Space_Donut",         # ID или юзернейм для проверки ботом
        "reward": 5                    # Сколько ценности (💎) получит юзер
    },
    2: {
        "title": "Подписаться на Dewid NFT",
        "url": "https://t.me/DewidNFT",
        "chat_id": "@DewidNFT",
        "reward": 5
    }
}

# ==========================================
# НАСТРОЙКИ РУЛЕТКИ
# ==========================================
ROULETTE_CONFIG = {
    "cost": 10, # Стоимость прокрутки после бесплатной (в пончиках)
    "items": [
        {"type": "donuts", "amount": 1, "photo": "gifts/dount.png", "chance": 20},
        {"type": "donuts", "amount": 3, "photo": "gifts/dount.png", "chance": 50},  
        {"type": "donuts", "amount": 5, "photo": "gifts/dount.png", "chance": 40},  
        {"type": "donuts", "amount": 10, "photo": "gifts/dount.png", "chance": 30}, 
        {"type": "donuts", "amount": 25, "photo": "gifts/dount.png", "chance": 5}, 
        {"type": "donuts", "amount": 50, "photo": "gifts/dount.png", "chance": 0}, 
        {"type": "donuts", "amount": 100, "photo": "gifts/dount.png", "chance": 0}, 
        {"type": "gift", "gift_id": 1001, "chance": 0} # Подарок Artisan Brick, Шанс 0%
    ]
}

# ==========================================
# БАЗОВЫЕ ПОДАРКИ (Конвертируются в ценность)
# ==========================================
BASE_GIFTS = {
    # Старые базовые подарки (1 - 10)
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
    
    # Новые подарки, продолжающие нумерацию
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
    99: {"name": "Pretty Posy", "photo": "https://api.changes.tg/original/PrettyPosy.png", "value": 5}
}

# ==========================================
# ГЛАВНЫЕ ПОДАРКИ (Отображаются в профиле)
# ==========================================
MAIN_GIFTS = {
    1000: {"name": "Swiss Watch", "photo": "https://api.changes.tg/original/SwissWatch.png", "required_value": 50},
    1001: {"name": "Artisan Brick", "photo": "https://api.changes.tg/original/ArtisanBrick.png", "required_value": 100},
    1002: {"name": "Perfume Bottle", "photo": "https://api.changes.tg/original/PerfumeBottle.png", "required_value": 100},
    1003: {"name": "Ion Gem", "photo": "https://api.changes.tg/original/IonGem.png", "required_value": 100},
    1004: {"name": "Durov's Cap", "photo": "https://api.changes.tg/original/DurovsCap.png", "required_value": 700}
}