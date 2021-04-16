from enum import Enum


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ActionStep(Enum):
    STARTED = "STARTED"
    PREPARATION = "PREPARATION"
    STATUS = "STATUS"
    RUNNING = "RUNNING"
    PACKAGING = "PACKAGING"
    DONE = "DONE"


class Action(Enum):
    INSTALL = "INSTALL"
    SWITCH_CONF = "SWITCH_CONF"
    SYNC_USER = "SYNC_USER"
    BUILD = "BUILD"
    TEST = "TEST"
    CDN = "CDN"
    SYNC = "SYNC"
    SERVE = "SERVE"
    WATCH = "WATCH"
