import logging
from enum import Enum


class LoggerConfig(Enum):
    GENERAL = ("general_logger", "general_log.log")

    @property
    def key(self):
        return self.value[0]

    @property
    def file(self):
        return self.value[1]


def create_logger(logger_config):
    logger = logging.getLogger(logger_config.key)
    logger.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(logger_config.file)
    stream_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger


general_logger = create_logger(LoggerConfig.GENERAL)
