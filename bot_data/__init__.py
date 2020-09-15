import logging.handlers
import os

from .const import bot_version
from .utils import ShutdownStatusFilter, UserChannelFormatter

logger = logging.getLogger(__name__)

base = os.path.abspath(os.path.join(__file__, "..", "..", "logs"))
os.makedirs(base, exist_ok=True)

level = os.getenv("LOG_LEVEL", "INFO")
log_level = getattr(logging, level)
logger.setLevel(log_level)
handler = logging.handlers.TimedRotatingFileHandler(os.path.join(base, "bot.log"), when="midnight", encoding="utf-8", utc=True)
formatter = UserChannelFormatter()
handler.setFormatter(formatter)
handler.setLevel(log_level)
logger.addHandler(handler)
logger.info("Logging at level %s", level)

aiosqlite_logger = logging.getLogger("aiosqlite")
aiosqlite_logger.handlers = []
aiosqlite_logger.addHandler(logging.NullHandler())
