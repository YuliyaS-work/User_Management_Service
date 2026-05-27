"""
Initialize application logging with a non-blocking queue-based architecture.
"""
import logging.config
from contextlib import asynccontextmanager
from logging.handlers import QueueListener
from queue import Queue

from fastapi import FastAPI

log_queue: Queue[str] = Queue()


def setup_logging(app: FastAPI) -> None:
    """
    Configure logging based on the environment.
    """

    log_format = "%(asctime)s-%(name)s-[%(levelname)s]-%(message)s"

    #Base config for all environment
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": log_format,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "queue": {
                "class": "logging.handlers.QueueHandler",
                "queue": log_queue
            },
        },
        "loggers": {
            "": {
                "handlers": ["queue"],
                "level": "INFO",
                "propagate": True
            },
            "uvicorn.access": {
                "handlers": ["queue"],
                "level": "INFO",
                "propagate": False
            }
        }
    }

    logging.config.dictConfig(log_config)

    formatter = logging.Formatter(log_format)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    listener = QueueListener(
        log_queue,
        console_handler,
        respect_handler_level=True
    )

    listener.start()

    app.state.log_listener = listener


@asynccontextmanager
async def logging_lifespan(app: FastAPI):
    setup_logging(app)
    try:
        yield
    finally:
        app.state.log_listener.stop()