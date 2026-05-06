import logging
import sys
import time
import tomllib
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent  # shared/shared/ → shared/ → personal_brand/
_CONFIG_PATH = _REPO_ROOT / "NOTION DIARY FETCHER" / "config.toml"
_initialized: set[str] = set()


def _load_logger_config() -> dict:
    defaults = {"log_dir": "logs", "level": "INFO", "retention_days": 7}
    try:
        with open(_CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
        cfg = data.get("logger", {})
        return {**defaults, **cfg}
    except Exception:
        return defaults


def _purge_old_logs(log_dir: Path, retention_days: int) -> None:
    cutoff = time.time() - retention_days * 86400
    for path in log_dir.glob("*.log*"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except Exception:
            pass


def get_logger(subsystem: str) -> logging.Logger:
    cfg = _load_logger_config()

    log_dir = _REPO_ROOT / cfg["log_dir"]
    log_dir.mkdir(parents=True, exist_ok=True)

    _purge_old_logs(log_dir, int(cfg["retention_days"]))

    if subsystem in _initialized:
        return logging.getLogger(subsystem)

    logger = logging.getLogger(subsystem)
    logger.setLevel(cfg["level"])
    logger.propagate = False

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    fh = TimedRotatingFileHandler(
        log_dir / f"{subsystem}.log",
        when="midnight",
        interval=1,
        backupCount=int(cfg["retention_days"]),
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    _initialized.add(subsystem)
    return logger
