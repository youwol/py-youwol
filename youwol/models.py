from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Label(Enum):
    STARTED = "STARTED"
    PREPARATION = "PREPARATION"
    BASH = "BASH"
    STATUS = "STATUS"
    INFO = "INFO"
    DELETE = "DELETE"
    LOG_INFO = "LOG_INFO"
    LOG_DEBUG = "LOG_DEBUG"
    LOG_ERROR = "LOG_ERROR"
    LOG_ABORT = "LOG_ABORT"
    RUNNING = "RUNNING"
    PACKAGING = "PACKAGING"
    DONE = "DONE"


class Action(Enum):
    INSTALL = "INSTALL"
    CONF = "CONF"
    SYNC_USER = "SYNC_USER"
    BUILD = "BUILD"
    TEST = "TEST"
    CDN = "CDN"
    SYNC = "SYNC"
    SERVE = "SERVE"
    WATCH = "WATCH"
