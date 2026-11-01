import os
import sys
import datetime
import logging
from src.utils.project import get_log_dir

_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_CONFIGURED = False

# Logger setup
def get_logger(name: str) -> logging.Logger:
    """
    Get the logger object.
    """
    global _CONFIGURED
    if not _CONFIGURED:
        formatted_now = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        log_file = os.path.join(get_log_dir(), f"{name}_{formatted_now}.log")
        handlers: list[logging.Handler] = [
            logging.FileHandler(log_file, mode="w"),
            logging.StreamHandler(sys.stdout),
        ]
        logging.basicConfig(
            level=logging.INFO,
            format=_LOG_FORMAT,
            handlers=handlers,
        )
        _CONFIGURED = True
    logger = logging.getLogger(name)
    return logger