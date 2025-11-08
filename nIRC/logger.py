from typing import Optional, Any
from datetime import datetime
import sys

class LogLevel:
    """
    Defines standard logging levels used by the Logger class.
    """
    DEBUG = 10
    INFO = 20
    ERROR = 40

LOG_PREFIX = {
    "NET": "[NET]",
    "ERROR": "[ERROR]",
    "RAW": "[RAW]",
    "DISPATCH": "[DISPATCH]",
    "TASK": "[TASK]",
    "CORE": "[CORE]",
    "USER": "[USER]",
    "COMMAND": "[COMMAND]",
    "DCC": "[DCC]",
    "COG": "[COG]",
    "PERM": "[PERMISSION]"
}


class Logger:
    """
    Handles logging output to the console and optionally to a file, filtered by log level.
    """
    def __init__(self, file_path: Optional[str] = None, min_level: int = LogLevel.INFO):
        """
        Initializes the Logger.
        @kwarg file_path: Path to the log file. If provided, logs are appended to this file. (default: None)
        @kwarg min_level: The minimum LogLevel (e.g., LogLevel.INFO) required for a message to be processed. (default: LogLevel.INFO)
        @return: None
        """
        self.file_path = file_path
        self.min_level = min_level
        self.log_file = None

        if self.file_path:
            try:
                self.log_file = open(self.file_path, 'a', encoding='utf-8', buffering=1)
            except Exception as e:
                print(f"[LOGGER INIT ERROR] Could not open log file '{file_path}': {e}", file=sys.stderr)
                self.file_path = None

    def _format_message(self, log_constant: str, prefix: str, **kwargs: Any) -> str:
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            message = log_constant.format(**kwargs)
            return f"{timestamp} {prefix} {message}"
        except Exception as e:
            return f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [LOGGER FATAL] Failed to format: {log_constant}. Error: {e}"

    def _write(self, level: int, prefix_key: str, log_constant: str, **kwargs: Any):
        if level < self.min_level:
            return

        prefix = LOG_PREFIX.get(prefix_key, "[UNKNOWN]")
        formatted_line = self._format_message(log_constant, prefix, **kwargs)

        print(formatted_line)

        if self.log_file:
            try:
                self.log_file.write(formatted_line + '\n')
            except Exception:
                print(f"[LOGGER FILE WRITE ERROR] Failed to write to log file.", file=sys.stderr)

    def debug(self, prefix_key: str, log_constant: str, **kwargs: Any):
        """
        Logs a message at the DEBUG level.
        @arg prefix_key: A key mapping to a log prefix (e.g., "NET").
        @arg log_constant: The message template string.
        @kwarg kwargs: Formatting arguments for the log_constant string.
        @return: None
        """
        self._write(LogLevel.DEBUG, prefix_key, log_constant, **kwargs)

    def info(self, prefix_key: str, log_constant: str, **kwargs: Any):
        """
        Logs a message at the INFO level.
        @arg prefix_key: A key mapping to a log prefix (e.g., "NET").
        @arg log_constant: The message template string.
        @kwarg kwargs: Formatting arguments for the log_constant string.
        @return: None
        """
        self._write(LogLevel.INFO, prefix_key, log_constant, **kwargs)

    def error(self, prefix_key: str, log_constant: str, **kwargs: Any):
        """
        Logs a message at the ERROR level.
        @arg prefix_key: A key mapping to a log prefix (e.g., "ERROR").
        @arg log_constant: The message template string.
        @kwarg kwargs: Formatting arguments for the log_constant string.
        @return: None
        """
        self._write(LogLevel.ERROR, prefix_key, log_constant, **kwargs)

    def raw_recv(self, line: str):
        """
        Logs a raw line received from the server at DEBUG level.
        @arg line: The raw IRC line received.
        @return: None
        """
        if LogLevel.DEBUG >= self.min_level:
            self._write(LogLevel.DEBUG, "RAW", "<- {line}", line=line)

    def raw_send(self, message: str):
        """
        Logs a raw message being sent to the server at DEBUG level.
        @arg message: The raw IRC message being sent.
        @return: None
        """
        if LogLevel.DEBUG >= self.min_level:
            self._write(LogLevel.DEBUG, "RAW", "-> {message}", message=message)

    def __del__(self):
        if self.log_file:
            self.log_file.close()


class NullLogger:
    """
    A logger implementation that discards all log messages. Used when logging is disabled.
    """
    def __init__(self, *args, **kwargs): pass
    def debug(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def raw_recv(self, *args, **kwargs): pass
    def raw_send(self, *args, **kwargs): pass

