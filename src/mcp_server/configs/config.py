import os

LOG_DIR = "logs"
STEP_LOG_FILE = os.path.join(LOG_DIR, "step_logs.txt")
CLIENT_LOG_FILE = os.path.join(LOG_DIR, "client_logs.txt")
SERVER_LOG_FILE = os.path.join(LOG_DIR, "server_logs.txt")

os.makedirs(LOG_DIR, exist_ok=True)