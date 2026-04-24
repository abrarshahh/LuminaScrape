import sys
from core.logger import get_logger

logger = get_logger(__name__)

def check_platform():
    platform = sys.platform
    logger.debug(f"Tool: Checking platform... Current platform is '{platform}'")
    return platform
