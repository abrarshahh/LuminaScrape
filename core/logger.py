import logging
import os
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to console output."""
    
    # ANSI Color Codes
    RED = "\033[91m"
    ORANGE = "\033[93m"  # Bright yellow/orange on most terminals
    BLUE = "\033[94m"
    RESET = "\033[0m"
    
    FORMAT = "%(levelname)s: %(message)s"

    LEVEL_COLORS = {
        logging.DEBUG: BLUE,
        logging.INFO: RESET,
        logging.WARNING: ORANGE,
        logging.ERROR: RED,
        logging.CRITICAL: RED,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        log_fmt = f"{color}{self.FORMAT}{self.RESET}"
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

def setup_logging():
    # 1. Master Logger Configuration (app.log)
    app_log_path = os.path.join(LOG_DIR, "app.log")
    error_log_path = os.path.join(LOG_DIR, "errors.log")
    
    # Base formatter for files (no colors in files)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )

    # App Log Handler (All details)
    app_handler = RotatingFileHandler(app_log_path, maxBytes=10*1024*1024, backupCount=5)
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(file_formatter)

    # Error Log Handler (Warnings & Errors only)
    error_handler = RotatingFileHandler(error_log_path, maxBytes=5*1024*1024, backupCount=5)
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(file_formatter)

    # Console Handler (With Colors)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter())

    # Root Logger Setup
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)

    # 2. Specialized Agent Logger (agents.log)
    agent_logger = logging.getLogger("agents")
    agent_logger.propagate = True 
    
    agent_log_path = os.path.join(LOG_DIR, "agents.log")
    agent_handler = RotatingFileHandler(agent_log_path, maxBytes=10*1024*1024, backupCount=5)
    agent_handler.setLevel(logging.INFO)
    
    agent_formatter = logging.Formatter(
        '\n' + '='*80 + '\n' +
        'TIME: %(asctime)s\n' +
        'AGENT: %(name)s\n' +
        '%(message)s\n' +
        '='*80 + '\n'
    )
    agent_handler.setFormatter(agent_formatter)
    agent_logger.addHandler(agent_handler)

    logging.info("Logging system initialized with colored terminal output.")

def get_logger(name):
    return logging.getLogger(name)

def get_agent_logger():
    return logging.getLogger("agents")

def log_agent_interaction(agent_name, task_id, query, response, is_final=False):
    logger = get_agent_logger()
    header = f"TASK ID: {task_id}\nQUERY: {query}\nTYPE: {'FINAL' if is_final else 'INTERMEDIATE'}"
    logger.info(f"{header}\n\nRESPONSE:\n{response}")
