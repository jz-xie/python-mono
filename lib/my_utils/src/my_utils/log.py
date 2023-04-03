import atexit
import io
import logging
import sys
from enum import Enum

DEFAULT_LOGGER_NAME = "my_utils"


class LogLevel(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    NOTSET = "NOTSET"


class Logger:

    default_log_format = "%(asctime)s | %(levelname)s | %(module)s:%(funcName)s | line: %(lineno)d | %(message)s"
    default_log_formatter = logging.Formatter(default_log_format)

    def __init__(
        self,
        logger_name: str = DEFAULT_LOGGER_NAME,
        log_level: LogLevel = LogLevel.DEBUG,
    ):
        """Create a Logger object"""
        self.mylogger = logging.getLogger(logger_name)
        level_attr = logging._nameToLevel[log_level.value]
        self.mylogger.setLevel(level_attr)

        self.debug = self.mylogger.debug
        self.info = self.mylogger.info
        self.warning = self.mylogger.warning
        self.error = self.mylogger.error
        self.critical = self.mylogger.critical
        self.exception = self.mylogger.exception

    def add_console_handler(
        self,
        log_formatter: logging.Formatter = default_log_formatter,
    ) -> None:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_formatter)
        self.mylogger.addHandler(console_handler)

    def add_file_handler(
        self,
        log_file_path: str,
        log_formatter: logging.Formatter = default_log_formatter,
    ) -> None:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(log_formatter)
        self.mylogger.addHandler(file_handler)

    def add_aws_s3_handler(
        self,
        s3_bucket: str,
        s3_prefix: str,
        log_formatter: logging.Formatter = default_log_formatter,
    ) -> None:
        from my_utils.aws.s3 import write

        log_stringio = io.StringIO()
        s3_handler = logging.StreamHandler(log_stringio)
        s3_handler.setFormatter(log_formatter)

        def write_s3(body: io.StringIO) -> None:
            write(
                body=body.getvalue().encode("utf-8"),
                bucket=s3_bucket,
                key=s3_prefix,
            )

        atexit.register(
            write_s3,
            body=log_stringio,
        )
        self.mylogger.addHandler(s3_handler)
