import datetime
from mcp_server.configs.config import STEP_LOG_FILE, CLIENT_LOG_FILE, SERVER_LOG_FILE

def step_log(message: str, duration: float = 0, console_output: int = 1):
    timestamp = datetime.datetime.now().isoformat()
    log_message = f"[{timestamp[:-3]}] [{duration:>5.1f}s] {message}\n"
    with open(STEP_LOG_FILE, "a", encoding="utf-a") as f:
        f.write(log_message)
    if console_output == 1:
        print (log_message, end="")

def client_log(message: str, duration: float = 0, console_output: int = 1):
    timestamp = datetime.datetime.now().isoformat()
    log_message = f"[{timestamp[:-3]}] [{duration:>5.1f}s] {message}\n"
    with open(CLIENT_LOG_FILE, "a", encoding="utf-a") as f:
        f.write(log_message)
    if console_output == 1:
        print (log_message, end="")

def server_log(message: str, duration: float = 0, console_output: int = 1):
    timestamp = datetime.datetime.now().isoformat()
    log_message = f"[{timestamp[:-3]}] [{duration:>5.1f}s] {message}\n"
    with open(SERVER_LOG_FILE, "a", encoding="utf-a") as f:
        f.write(log_message)
    if console_output == 1:
        print (log_message, end="")
