import threading
from typing import Any
import logging

logger = logging.getLogger(__name__)


class Event(object):
    def __init__(self):
        self.callbacks = []

    def notify(self, *args, **kwargs):
        for callback in self.callbacks:
            callback(*args, **kwargs)

    def register(self, callback):
        self.callbacks.append(callback)
        return callback


class Observable(object):
    def __init__(self, v: Any, debug=False):
        self._value = v
        self.debug = debug
        self.changed = Event()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        old_value = self._value
        if old_value != v:
            self._value = v
            if self.debug:
                logger.info("Setting observable value: (thread:%s) %s", threading.get_ident(), v)
            self.changed.notify(old_value, v)
