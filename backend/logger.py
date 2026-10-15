import logging
from logging.handlers import TimedRotatingFileHandler
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "system.log")

formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

logger = logging.getLogger("RAG_SYSTEM")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Avoid duplicate handlers if reloaded
if not logger.handlers:
    logger.addHandler(console_handler)
    try:
        # Rotate at midnight, keep 30 days
        file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=30)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except (PermissionError, OSError) as e:
        print(f"[LOGGER WARNING] Cannot write to log file {log_file} ({e}). Logging to console only.")

def get_logger():
    return logger
