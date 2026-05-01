import subprocess
import sys
import time
import os
import signal

def kill_port(port):
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True
        )
        pids = result.stdout.strip().split()
        for pid in pids:
            if pid:
                os.kill(int(pid), signal.SIGKILL)
    except Exception:
        pass

def kill_script(name):
    try:
        # Используем точное совпадение имени скрипта, чтобы "bot.py"
        # не матчил "support_bot.py" как подстроку.
        subprocess.run(
            ["pkill", "-9", "-f", f"python.*{name}$"],
            capture_output=True
        )
    except Exception:
        pass

def main():
    print("🧹 Завершаем старые процессы...")
    kill_port(8080)
    kill_script("main.py")
    # Сначала support_bot.py, потом bot.py — порядок важен,
    # чтобы pkill не матчил "bot.py" внутри "support_bot.py".
    kill_script("support_bot.py")
    kill_script("bot.py")
    # Даём Telegram-серверу закрыть старые long-polling соединения.
    # 1 секунды недостаточно — используем 4 секунды.
    time.sleep(4)

    print("🚀 Запускаем FastAPI сервер...")
    server_process = subprocess.Popen([sys.executable, "main.py"])

    time.sleep(2)

    print("🤖 Запускаем Telegram Бота...")
    bot_process = subprocess.Popen([sys.executable, "bot.py"])

    # Небольшой сдвиг между запусками ботов, чтобы они не стучались
    # к Telegram одновременно и не мешали друг другу при инициализации.
    time.sleep(1)

    print("🆘 Запускаем Бота поддержки...")
    support_process = subprocess.Popen([sys.executable, "support_bot.py"])

    try:
        server_process.wait()
        bot_process.wait()
        support_process.wait()
    except KeyboardInterrupt:
        print("\n⏹️ Выключение...")
        server_process.terminate()
        bot_process.terminate()
        support_process.terminate()

if __name__ == "__main__":
    main()
