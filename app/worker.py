"""Цикл воркера конвейера: опрос очереди и heartbeat-файл для healthcheck."""

import logging
import signal
import time
from pathlib import Path
from types import FrameType

from flask import current_app

log = logging.getLogger(__name__)


class StopFlag:
    """Плавная остановка по SIGTERM/SIGINT: текущая итерация дорабатывает до конца."""

    def __init__(self) -> None:
        self.stopped = False

    def stop(self, signum: int, frame: FrameType | None) -> None:
        log.info("worker stopping", extra={"signal": signum})
        self.stopped = True


def touch_heartbeat(path: str) -> None:
    Path(path).touch()


def run_worker(*, once: bool = False) -> None:
    stop = StopFlag()
    signal.signal(signal.SIGTERM, stop.stop)
    signal.signal(signal.SIGINT, stop.stop)

    poll_interval_s = current_app.config["WORKER_POLL_INTERVAL_MS"] / 1000
    heartbeat_file = current_app.config["WORKER_HEARTBEAT_FILE"]
    log.info("worker started", extra={"poll_interval_s": poll_interval_s})

    while not stop.stopped:
        touch_heartbeat(heartbeat_file)
        if once:
            break
        time.sleep(poll_interval_s)

    log.info("worker stopped")
