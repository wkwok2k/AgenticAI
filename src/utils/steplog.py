import logging
import time

logger = logging.getLogger("mcp_server")
logging.basicConfig(level=logging.INFO)


def step_log(message: str, duration: float | None = None) -> None:
    if duration is None:
        logger.info(f"[STEP] {message}")
    else:
        logger.info(f"[STEP] {message} (duration={duration:.3f}s)")


class Timer:
    def __init__(self, label: str):
        self.label = label
        self.start = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc, tb):
        end = time.time()
        step_log(self.label, end - self.start)
