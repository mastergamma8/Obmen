# start.py
import subprocess
import sys
import time

def main():
    print("🚀 Запускаем FastAPI сервер...")
    # Запускаем main.py
    server_process = subprocess.Popen([sys.executable, "main.py"])
    
    # Даем серверу секунду на запуск
    time.sleep(2)
    
    print("🤖 Запускаем Telegram Бота...")
    # Запускаем bot.py
    bot_process = subprocess.Popen([sys.executable, "bot.py"])
    
    try:
        # Держим оба процесса активными
        server_process.wait()
        bot_process.wait()
    except KeyboardInterrupt:
        print("\n⏹️ Выключение...")
        server_process.terminate()
        bot_process.terminate()

if __name__ == "__main__":
    main()