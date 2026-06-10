from pathlib import Path
from datetime import datetime
import logging


def get_logger(
    script_name: str,
    project_root: Path,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Create a timestamped logger for pipeline scripts.

    Log files are saved under:
        logs/<script_name>_<YYYYMMDD_HHMMSS>.log
    """

    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{script_name}_{timestamp}.log"

    logger = logging.getLogger(script_name)
    logger.setLevel(level)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logger initialized")
    logger.info("Log file: %s", log_file)

    return logger