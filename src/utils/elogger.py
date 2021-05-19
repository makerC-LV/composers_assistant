import inspect
import io
import logging
import logging.handlers
import traceback

elogger_configured = False
_debug_var = False


def build_log_message(*args):
    f = io.StringIO()
    try:
        loc = location()
        print(*args, file=f, end='')
        return "%s %s" % (loc, f.getvalue())
    finally:
        f.close()


def info(*args):
    get_logger().info(build_log_message(*args))


def warn(*args):
    get_logger().warning(build_log_message(*args))


def error(*args):
    get_logger().error(build_log_message(*args))


def debug(*args):
    if _debug_var:
        get_logger().info(build_log_message(*args))


def exception():
    formatted_lines = traceback.format_exc().splitlines()
    for line in formatted_lines:
        print("EXC", line)


def location():
    frame = handle_stackframe_without_leak()
    return '{%s:%s} ' % (frame.filename.split('/')[-1], frame.lineno)


def handle_stackframe_without_leak():
    frame = None
    try:
        frame = inspect.stack()[4]
        return frame
    finally:
        if frame is not None:
            del frame


def get_logger():
    global elogger_configured
    if not elogger_configured:
        config_logging(console=True)
    return logging.getLogger()


def config_logging(file='', debug_on=False, console=False):
    global elogger_configured
    global _debug_var

    if elogger_configured:
        return

    _debug_var = debug_on
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)
    logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")

    if console:
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(logFormatter)
        rootLogger.addHandler(consoleHandler)

    if file != '':
        fileLogger = logging.handlers.TimedRotatingFileHandler(file, when='MIDNIGHT')
        fileLogger.setFormatter(logFormatter)
        rootLogger.addHandler(fileLogger)

    elogger_configured = True


def a():
    b()


def b():
    raise ValueError("v")


if __name__ == '__main__':
    config_logging(console=True)
    info("hello", "hello", 10)
    try:
        a()
    except Exception:
        exception()
