from typing import Dict, Optional, Callable, Any, List, Tuple, Set
from datetime import datetime
from functools import wraps
import asyncio, re, sys, os
import struct

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
    "DCC": "[DCC]"
}

LOG_NET_ATTEMPT = "Attempting connection to {host}:{port}..."
LOG_NET_ESTABLISHED = "Connection established. Ready for registration."
LOG_ERROR_CONNECT_REFUSED = "Connection refused by server. Is the server running at {host}?"
LOG_ERROR_CONNECT_FAIL = "Failed to connect: {error}"
LOG_ERROR_SEND_FAIL = "Error sending data (connection likely lost): {error}"
LOG_ERROR_NOT_CONNECTED = "Cannot send raw message, not connected."
LOG_NET_CLOSED_REMOTE = "Connection closed by the remote host."
LOG_NET_CLOSED_LOCAL = "Connection closed."
LOG_ERROR_READ_FAIL = "Error reading data: {error}"
LOG_NET_PONG = "PONG sent in response to PING."
LOG_DISPATCH_COMMAND = "Running command: {command_name}"
LOG_TASK_ERROR = "Task '{task_name}' failed: {error}. Stopping task."
LOG_TASK_FINISHED = "Task '{task_name}' finished."
LOG_TASK_NOT_REGISTERED = "Error: Task function '{task_name}' is not decorated with @Bot.task."
LOG_READY_DISPATCH = "Dispatching user-defined on_ready handlers."
LOG_READY_PROTOCOL = "Running core protocol setup (NickServ, JOINs)."
LOG_READY_MOTD = "Received 376 End of MOTD. Initialization starting now."
LOG_REGISTRATION_SENT = "Bot Registration Sent. Entering Main Network Loop"
LOG_LOOP_ENDED = "Bot Main Loop Ended. Disconnecting."
LOG_READY_HANDLER_ERROR = "Error in on_ready handler '{handler_name}': {error}"
LOG_PREFIX_COMMAND_OVERWRITTEN = "Warning: Prefix command '{prefix}' is being overwritten."
LOG_DCC_TRANSFER_INITIATED = "TRANSFER INITIATED for {safe_filename} from {sender}"
LOG_DCC_CONNECT_ESTABLISHED = "Connection established. Receiving file: {safe_filename}"
LOG_DCC_TIMEOUT = "Operation timed out (Connection or Transfer)."
LOG_DCC_CONNECT_REFUSED = "Connection refused by DCC sender at {ip_address}:{port}."
LOG_DCC_SETUP_ERROR = "An unexpected error occurred during DCC transfer setup: {error}"
LOG_DCC_TRANSFER_FINISHED = "Transfer attempt for {safe_filename} finished."
LOG_DCC_SENDER_CLOSED = "Connection closed by sender after {received_bytes} bytes."
LOG_DCC_PROGRESS = "-> Progress: {percent:.2f}% ({received_bytes} / {filesize} bytes)"
LOG_DCC_SUCCESS = "SUCCESS: File '{safe_filename}' saved completely."
LOG_DCC_SIZE_MISMATCH = "TRANSFER COMPLETE with size mismatch. Expected: {filesize}, Received: {received_bytes}"
LOG_DCC_READ_STALL = "Transfer read stalled for {safe_filename}. Closing connection."
LOG_DCC_TRANSFER_LOOP_ERROR = "An unexpected error occurred during the transfer loop: {error}"
LOG_DCC_IP_CONVERT_ERROR = "ERROR converting IP: {ip_long} - {error}"
LOG_DCC_EVENT_DISPATCH = "Dispatching 'on_dcc' event for {safe_filename}..."
LOG_DOWNLOADS_DIR_INIT = "Created downloads directory: {dirname}."


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


_command_registry: Dict[str, Callable] = {}
_prefix_command_registry: Dict[str, Callable] = {}
_event_registry: Dict[str, List[Callable]] = {
    'on_message': [],
    'on_join': [],
    'on_leave': [],
    'on_raw': [],
    'on_ready': [],
    'on_dcc' : []
}
_task_registry: Dict[str, Callable] = {}

IRC_RE = re.compile(
    r'^(?:[:](\S+) )?(\S+)(?: (?!:)(.+?))?(?: :(.*))?$'
)

# PRIVMSG <recipient> :DCC SEND <filename> <ip> <port> <filesize>
DCC_SEND_REGEX = re.compile(
    r"DCC SEND (?P<filename>.+?) (?P<ip>\d+) (?P<port>\d+) (?P<filesize>\d+)",
    re.IGNORECASE
)

def ip_long_to_dotted(ip_long: int) -> str:
    """
    Converts a long integer IP representation (Network Byte Order/Big Endian)
    to a dotted string (IPv4) without relying on the synchronous 'socket' module.
    """
    # Extract the four octets using bitwise shifts and masks
    a = (ip_long >> 24) & 0xFF
    b = (ip_long >> 16) & 0xFF
    c = (ip_long >> 8) & 0xFF
    d = ip_long & 0xFF
    return f"{a}.{b}.{c}.{d}"

class IRCConnection:
    """
    Handles the asynchronous socket connection, reading, writing, and buffering
    of raw IRC data using Python's asyncio streams.
    """
    def __init__(self, host: str, port: int, logger: Optional[Logger] = None):
        """
        Initializes the connection handler.
        @arg host: The IRC server hostname or IP address.
        @arg port: The IRC server port (usually 6667).
        @kwarg logger: A logger instance for logging network events. If None, NullLogger is used. (default: None)
        @return: None
        """
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self.logger: Any = logger if logger is not None else NullLogger()

    async def connect(self):
        """
        Establishes the socket connection to the IRC server asynchronously.
        Sets self.connected to True on success.
        @return: None
        """
        try:
            self.logger.info("NET", LOG_NET_ATTEMPT, host=self.host, port=self.port)
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.connected = True
            self.logger.info("NET", LOG_NET_ESTABLISHED)
        except ConnectionRefusedError:
            self.logger.error("ERROR", LOG_ERROR_CONNECT_REFUSED, host=self.host)
            self.connected = False
        except Exception as e:
            self.logger.error("ERROR", LOG_ERROR_CONNECT_FAIL, error=e)
            self.connected = False

    async def send_raw(self, message: str):
        """
        Sends a raw IRC message (line) to the server.
        @arg message: The raw IRC protocol message (e.g., 'PRIVMSG #channel :Hello').
        @return: None
        """
        if not self.connected or not self.writer:
            self.logger.error("ERROR", LOG_ERROR_NOT_CONNECTED)
            return

        full_message = f"{message.strip()}\r\n"
        self.logger.raw_send(full_message.strip())
        try:
            self.writer.write(full_message.encode('utf-8'))
            await self.writer.drain()
        except Exception as e:
            self.logger.error("ERROR", LOG_ERROR_SEND_FAIL, error=e)
            self.connected = False

    async def read_line(self) -> Optional[str]:
        """
        Asynchronously reads a single line from the server.
        @return: The stripped IRC line, or None if the connection is closed or an error occurred.
        >>> await bot.conn.read_line()
        'PING :server.irc.net'
        """
        if not self.connected or not self.reader:
            return None

        try:
            data = await self.reader.readline()
            if not data:
                self.logger.info("NET", LOG_NET_CLOSED_REMOTE)
                self.connected = False
                return None

            line = data.decode('utf-8', errors='ignore').strip()
            return line

        except asyncio.CancelledError:
            return None
        except Exception as e:
            self.logger.error("ERROR", LOG_ERROR_READ_FAIL, error=e)
            self.connected = False
            return None

    def close(self):
        """
        Closes the network connection writer.
        @return: None
        """
        if self.writer:
            self.writer.close()
            self.logger.info("NET", LOG_NET_CLOSED_LOCAL)
            self.connected = False


class Member:
    """
    Represents an IRC user or bot, providing convenience methods for interaction.
    """
    def __init__(self, bot: 'Bot', nick: str):
        """
        Initializes a Member object.
        @arg bot: The associated bot instance.
        @arg nick: The nickname of the member.
        @return: None
        """
        self.bot = bot
        self.nick = nick

    async def send(self, text: str):
        """
        Sends a private message to this member.
        @arg text: The message content to send.
        @return: None
        """
        await self.bot.send_message(self.nick, text)

    async def kick(self, channel: str, reason: str = "Requested by bot"):
        """
        Kicks this member from the specified channel.
        @arg channel: The channel name (e.g., '#main').
        @kwarg reason: The kick message/reason. (default: "Requested by bot")
        @return: None
        """
        await self.bot.conn.send_raw(f"KICK {channel} {self.nick} :{reason}")

    async def ban(self, channel: str, reason: str = "Banned by bot"):
        """
        Bans this member's hostmask from the specified channel and then kicks them.
        @arg channel: The channel name (e.g., '#main').
        @kwarg reason: The kick message/reason. (default: "Banned by bot")
        @return: None
        """
        await self.bot.conn.send_raw(f"MODE {channel} +b {self.nick}!*@*")
        await self.kick(channel, reason)

    async def mute(self, channel: str):
        """
        Mutes the member (removes voice/sets -v mode) in the specified channel.
        @arg channel: The channel name (e.g., '#main').
        @return: None
        """
        await self.bot.conn.send_raw(f"MODE {channel} -v {self.nick}")
        self.bot._mute_status.setdefault(channel, set()).add(self.nick)

    async def unmute(self, channel: str):
        """
        Unmutes the member (gives voice/sets +v mode) in the specified channel.
        @arg channel: The channel name (e.g., '#main').
        @return: None
        """
        await self.bot.conn.send_raw(f"MODE {channel} +v {self.nick}")
        if channel in self.bot._mute_status and self.nick in self.bot._mute_status[channel]:
            self.bot._mute_status[channel].remove(self.nick)

    def is_muted(self, channel: str) -> bool:
        """
        Checks the local cache if the user is currently muted/voiced down in the channel.
        @arg channel: The channel name.
        @return: True if the member is considered muted in the channel, False otherwise.
        """
        return self.nick in self.bot._mute_status.get(channel, set())


class Channel:
    """
    Represents an IRC channel, providing methods for channel management.
    """
    def __init__(self, bot: 'Bot', name: str):
        """
        Initializes a Channel object.
        @arg bot: The associated bot instance.
        @arg name: The name of the channel (e.g., '#mychannel').
        @return: None
        """
        self.bot = bot
        self.name = name

    async def get_topic(self) -> str:
        """
        Requests the current topic of the channel from the server.
        Note: The actual topic retrieval is complex and requires waiting for a 332 numeric.
        This is a placeholder that sends the request and returns an empty string immediately.
        @return: The current topic of the channel (placeholder returns empty string).
        """
        await self.bot.conn.send_raw(f"TOPIC {self.name}")
        # In a real async bot, this would use an Event/Future to wait for the 332 numeric
        return ""

    async def set_topic(self, new_topic: str):
        """
        Sets the topic of the channel.
        @arg new_topic: The new topic string.
        @return: None
        """
        await self.bot.conn.send_raw(f"TOPIC {self.name} :{new_topic}")

    async def unban(self, user_mask: str):
        """
        Removes a ban (mode -b) from the specified user mask.
        @arg user_mask: The mask of the user to unban (e.g., 'nick!user@host').
        @return: None
        """
        await self.bot.conn.send_raw(f"MODE {self.name} -b {user_mask}")

class Context:
    """
    A context object passed to all command and event handlers, containing
    details about the received message and utility methods for responding.
    """
    def __init__(self, bot: 'Bot', target: str, author: str, message: str, command: str, full_line: str = ""):
        """
        Initializes the context object.
        @arg bot: The associated Bot instance.
        @arg target: The destination of the message (channel or bot nick).
        @arg author: The nickname of the message sender.
        @arg message: The message content.
        @arg command: The raw IRC command (e.g., 'PRIVMSG').
        @kwarg full_line: The complete raw IRC line. (default: "")
        @return: None
        """
        self.bot = bot
        self.target = target
        self.author = author
        self.logger = bot.logger
        self.message = message
        self.full_line = full_line
        self.command_type = command

        self.command_name: Optional[str] = None
        self.arg: str = message.strip()
        self.args: List[str] = self.arg.split() if self.arg else []

    async def reply(self, text: str):
        """
        Sends a message back to the originating channel or user.
        Replies privately if the message was directed to the bot's nick, otherwise replies to the channel.
        @arg text: The message content to send.
        @return: None
        """
        recipient = self.author if self.target == self.bot.nick else self.target
        await self.bot.send_message(recipient, text)

    async def send(self, text: str):
        """
        Alias for reply().
        @arg text: The message content to send.
        @return: None
        """
        await self.reply(text)

    @property
    def author_obj(self) -> Member:
        """
        Returns a Member object for the message author.
        @return: A Member object representing the sender.
        """
        return self.bot.get_member(self.author)

    @property
    def channel_obj(self) -> Channel:
        """
        Returns a Channel object for the message target (only valid for channel messages).
        @return: A Channel object.
        """
        return Channel(self.bot, self.target)

    def get_member(self, nick: str) -> Member:
        """
        Gets a Member object by nickname.
        @arg nick: The nickname of the member to retrieve.
        @return: A Member object.
        """
        return Member(self.bot, nick)

    async def unban(self, target_user: str):
        """
        Removes a ban for a target_user from the current ctx.target channel.
        This calls the underlying Channel object's unban method.
        @arg target_user: The user mask to unban (e.g., 'nick!user@host').
        @return: None
        """
        await self.channel_obj.unban(target_user)


class DCCFile:
    """
    Initializes the DCC file object.
    @arg context: The context object.
    @arg filename: The filename of the file in the DCC send request.
    @arg ip_address: The source IP address.
    @arg port: The source port.
    @arg filesize: The size of the file.
    @arg save_dir: The directory to save the file into. (defaule: ./downloads/)
    @return: None
    """
    def __init__(self, context: Context, filename: str, ip_address: str, port: int, filesize: int, save_dir: str):
        self.context = context
        self.sender = context.author
        self.filename = filename.strip().strip('"')
        self.ip_address = ip_address
        self.port = port
        self.filesize = filesize
        self.save_dir = save_dir
        self.safe_filename = os.path.basename(self.filename).replace(' ', '_')
        self.full_path = os.path.join(self.save_dir, self.safe_filename)
        _, self.extension = os.path.splitext(self.filename)
        self.is_good = True
        self.is_done = False
        self.progress = 0
        self.percent = 0

    async def start_transfer(self, connect_timeout=10, ack_chunk_size=4096):
        """
        Starts the transfer process.
        @kwarg connect_timeout: The connection timeout. (default: 10)
        @kwarg ack_chunk_size: The transfer chunk size. (default: 4096)
        @return: None
        """
        self.context.bot.logger.info("DCC", LOG_DCC_TRANSFER_INITIATED, safe_filename=self.safe_filename, sender=self.sender)

        reader, writer = None, None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip_address, self.port),
                timeout=connect_timeout
            )
            self.context.bot.logger.info("DCC", LOG_DCC_CONNECT_ESTABLISHED, safe_filename=self.safe_filename)

            await self._transfer_loop(reader, writer, ack_chunk_size)

        except asyncio.TimeoutError:
            self.context.bot.logger.error("DCC", LOG_DCC_TIMEOUT)
            self.is_good = False
        except ConnectionRefusedError:
            self.context.bot.logger.error("DCC", LOG_DCC_CONNECT_REFUSED, ip_address=self.ip_address, port=self.port)
            self.is_good = False
        except Exception as e:
            self.context.bot.logger.error("DCC", LOG_DCC_SETUP_ERROR, error=e)
            self.is_good = False
        finally:
            if writer and not writer.is_closing():
                writer.close()
                await writer.wait_closed()
            self.context.bot.logger.info("DCC", LOG_DCC_TRANSFER_FINISHED, safe_filename=self.safe_filename)

        self.is_done = True


    async def _transfer_loop(self, reader, writer, ack_chunk_size):
        received_bytes = 0

        try:
            with open(self.full_path, 'wb') as f:
                while received_bytes < self.filesize:
                    data = await asyncio.wait_for(
                        reader.read(ack_chunk_size),
                        timeout=30
                    )

                    if not data:
                        self.context.bot.logger.info("DCC", LOG_DCC_SENDER_CLOSED, received_bytes=received_bytes)
                        break

                    f.write(data)
                    received_bytes += len(data)

                    ack_message = struct.pack("!I", received_bytes)
                    writer.write(ack_message)
                    await writer.drain()

                    if received_bytes % (1024 * 1024 * 5) == 0 or received_bytes == self.filesize:
                        percent = (received_bytes / self.filesize) * 100 if self.filesize > 0 else 0
                        self.context.bot.logger.info("DCC", LOG_DCC_PROGRESS, percent=percent, received_bytes=received_bytes, filesize=self.filesize)
                        self.progress, self.percent = received_bytes, percent

            if received_bytes == self.filesize:
                self.context.bot.logger.info("DCC", LOG_DCC_SUCCESS, safe_filename=self.safe_filename)
            else:
                self.context.bot.logger.error("DCC", LOG_DCC_SIZE_MISMATCH, filesize=self.filesize, received_bytes=received_bytes)

        except asyncio.TimeoutError:
            self.context.bot.logger.error("DCC", LOG_DCC_READ_STALL, safe_filename=self.safe_filename)
        except Exception as e:
            self.context.bot.logger.error("DCC", LOG_DCC_TRANSFER_LOOP_ERROR, error=e)


class Bot:
    """
    The core IRC bot client. Manages connection state, event dispatching,
    commands, and background tasks.
    """
    def __init__(self, prefix: str, conn: IRCConnection, nick: str, username: str, realname: str, password: Optional[str] = None, downloads_dir: str = "downloads"):
        """
        Initializes the Bot instance.
        @arg prefix: The command prefix (e.g., '!' or '.').
        @arg conn: The pre-configured IRCConnection object used for I/O.
        @arg nick: The bot's primary nickname.
        @arg username: The bot's username (IDENT).
        @arg realname: The bot's real name (GECOS).
        @kwarg password: Password for NickServ identification, if required. (default: None)
        @return: None
        """
        self.prefix = prefix
        self.nick = nick
        self.username = username
        self.realname = realname
        self.password = password
        self.running = False
        self.registered = False
        self.channel_map: Dict[str, Optional[str]] = {}
        self._mute_status: Dict[str, Set[str]] = {} # {channel: {nick1, nick2}} for tracking mute status

        self.conn = conn
        self.logger = conn.logger
        self.save_dir = downloads_dir

        self.commands: Dict[str, Callable] = _command_registry.copy()
        self.prefix_commands: Dict[str, Callable] = _prefix_command_registry.copy()
        self.event_handlers: Dict[str, List[Callable]] = _event_registry.copy()
        self.task_registry: Dict[str, Callable] = _task_registry.copy()

    @staticmethod
    def command(name: str):
        """
        Decorator to register a function as a bot command.
        The decorated function must accept one argument: a Context object.
        @arg name: The command name (e.g., 'ping').
        @return: The decorator function.
        >>> @Bot.command("hello")
        >>> async def hello_cmd(ctx):
        >>>     await ctx.reply("world")
        """
        def decorator(func: Callable):
            _command_registry[name] = func
            return func
        return decorator

    @staticmethod
    def prefix_command(prefix: str):
        """
        Decorator to register a function that fires when a message starts with a specific non-command prefix (e.g., '>').
        This is useful for secondary interactions or services.
        The registered function must be an async function accepting a single Context argument.

        @arg prefix: The exact non-command prefix string (e.g., ">").
        @return: The decorated function.

        >>> @bot.prefix_command(">")
        >>> async def direct_query(ctx: Context):
        >>>     await ctx.reply(f"Query received: {ctx.arg}")
        """
        def decorator(func: Callable[[Context], Any]):
            if prefix in _prefix_command_registry:
                # Need to use an instance-agnostic logger/print for static method decorators
                print(LOG_PREFIX["CORE"] + LOG_PREFIX_COMMAND_OVERWRITTEN.format(prefix=prefix), file=sys.stderr)
            _prefix_command_registry[prefix] = func

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    @staticmethod
    def on_message():
        """
        Decorator to register a function to be called for every message not processed as a command.
        The decorated function must accept one argument: a Context object.
        @return: The decorator function.
        >>> @Bot.on_message()
        >>> async def log_message(ctx):
        >>>     print(f"[{ctx.target}] {ctx.author}: {ctx.message}")
        """
        def decorator(func: Callable):
            _event_registry['on_message'].append(func)
            return func
        return decorator

    @staticmethod
    def on_dcc():
        """
        Decorator for DCC SEND request handler.
        @return: The decorator function.
        """
        def decorator(func: Callable):
            if not asyncio.iscoroutinefunction(func):
                raise TypeError("@Bot.on_dcc function must be an async function.")
            _event_registry['on_dcc'].append(func)
            return func
        return decorator

    @staticmethod
    def on_join():
        """
        Decorator to register a function to be called when a user joins a channel.
        The decorated function must accept one argument: a Context object.
        @return: The decorator function.
        """
        def decorator(func: Callable):
            _event_registry['on_join'].append(func)
            return func
        return decorator

    @staticmethod
    def on_leave():
        """
        Decorator to register a function to be called when a user parts a channel or quits the server.
        The decorated function must accept one argument: a Context object.
        @return: The decorator function.
        """
        def decorator(func: Callable):
            _event_registry['on_leave'].append(func)
            return func
        return decorator

    @staticmethod
    def on_raw():
        """
        Decorator to register a function to be called for every single raw line received from the server.
        The decorated function must accept one argument: a Context object.
        @return: The decorator function.
        """
        def decorator(func: Callable):
            _event_registry['on_raw'].append(func)
            return func
        return decorator

    @staticmethod
    def on_ready():
        """
        Decorator to register an async function to be called once the bot is registered (receives numeric 376 MOTD end).
        The decorated function must accept one argument: the Bot instance.
        @return: The decorator function.
        """
        def decorator(func: Callable):
            if not asyncio.iscoroutinefunction(func):
                raise TypeError("@Bot.on_ready function must be an async function.")
            _event_registry['on_ready'].append(func)
            return func
        return decorator

    @staticmethod
    def task(interval: float, max_repeat: Optional[int] = None):
        """
        Decorator to register an async function as a recurring background task.
        @arg interval: The delay in seconds between consecutive runs.
        @kwarg max_repeat: The maximum number of times to run the task. Runs forever if None. (default: None)
        @return: The decorator function.
        """
        def decorator(func: Callable):
            if not asyncio.iscoroutinefunction(func):
                raise TypeError("Task function must be an async function.")
            func.interval = interval #type: ignore
            func.max_repeat = max_repeat #type: ignore
            func.current_repeat = 0 #type: ignore
            _task_registry[func.__name__] = func
            return func
        return decorator

    async def send_message(self, target: str, message: str):
        """
        Sends a PRIVMSG to a target (channel or user).
        @arg target: The channel name (e.g., '#general') or nickname.
        @arg message: The message content.
        @return: None
        """
        await self.conn.send_raw(f"PRIVMSG {target} :{message}")

    async def send_raw(self, message: str):
        """
        Sends a raw IRC protocol message directly to the server.
        @arg message: The raw IRC protocol message (e.g., 'MODE #channel +i').
        @return: None
        """
        await self.conn.send_raw(message)

    def get_member(self, nick: str) -> Member:
        """
        Returns a Member object for a given nickname.
        @arg nick: The nickname to look up.
        @return: A Member object.
        """
        return Member(self, nick)

    async def _run_task(self, task_func: Callable, args: tuple):
        task_name = task_func.__name__
        task_func.current_repeat = 0 #type: ignore
        logger = self.conn.logger
        while self.running and (task_func.max_repeat is None or task_func.current_repeat < task_func.max_repeat): #type: ignore
            try:
                task_func.current_repeat += 1 #type: ignore
                await task_func(self, *args)
                await asyncio.sleep(task_func.interval) #type: ignore
            except Exception as e:
                logger.error("TASK", LOG_TASK_ERROR, task_name=task_name, error=e)
                break
        logger.info("TASK", LOG_TASK_FINISHED, task_name=task_name)

    def start_task(self, task_func: Callable, *args: Any):
        """
        Starts a registered background task function.
        The function must have been decorated with @Bot.task.
        @arg task_func: The task function reference.
        @arg *args: Arguments to pass to the task function.
        @return: None
        """
        logger = self.conn.logger
        if task_func.__name__ not in self.task_registry:
            logger.error("TASK", LOG_TASK_NOT_REGISTERED, task_name=task_func.__name__)
            return
        asyncio.create_task(self._run_task(task_func, args))

    def _parse_line(self, line: str) -> Tuple[str, str, str, str, str]:
        match = IRC_RE.match(line)
        if not match:
            return ("", "", "", "", line)

        prefix, command, target_part, message = match.groups()

        author_nick = ""
        if prefix and '!' in prefix:
            author_nick = prefix.split('!')[0]
        elif prefix:
            author_nick = prefix

        target_system = message.strip() if message and message.startswith("#") else ""
        target = target_part.split()[0] if target_part else target_system

        return (prefix or "", command or "", target or "", author_nick or "", message or "")

    async def _handle_protocol(self, command: str, message: str):
        logger = self.conn.logger
        if command == "PING":
            await self.conn.send_raw(f"PONG :{message}")
            logger.info("NET", LOG_NET_PONG)
            return True
        return False


    async def _dispatch_line(self, line: str):
        logger = self.conn.logger

        raw_ctx = Context(self, "", "", line, "RAW", line)
        for handler in self.event_handlers['on_raw']:
            await handler(raw_ctx)

        prefix, command, target, author_nick, message = self._parse_line(line)

        if await self._handle_protocol(command, message):
            return

        if command in ["PRIVMSG", "JOIN", "PART", "QUIT"]:
            ctx = Context(
                bot=self,
                target=target,
                author=author_nick,
                message=message,
                command=command,
                full_line=line
            )

            if command == "PRIVMSG":
                await self._dispatch_message(ctx)
            elif command == "JOIN" and author_nick != self.nick:
                for handler in self.event_handlers['on_join']: await handler(ctx)
            elif command in ["PART", "QUIT"] and author_nick != self.nick:
                # Dispatch on_leave for both PART and QUIT
                for handler in self.event_handlers['on_leave']: await handler(ctx)

    async def _dispatch_message(self, ctx: Context):
        logger = self.conn.logger

        is_command_found = False

        if ctx.message.startswith(self.prefix):
            command_and_args = ctx.message[len(self.prefix):].strip()

            parts = command_and_args.split(maxsplit=1)
            command = parts[0]

            if command in self.commands:
                ctx.command_name = command
                ctx.arg = parts[1] if len(parts) > 1 else ""
                ctx.args = ctx.arg.split() if ctx.arg else []
                logger.info("DISPATCH", LOG_DISPATCH_COMMAND, command_name=f"{self.prefix}{command}")
                await self.commands[command](ctx)
                is_command_found = True

        for prefix_char, handler in self.prefix_commands.items():
            if ctx.message.startswith(prefix_char):
                if prefix_char in self.prefix_commands:
                    args = ctx.message.split(prefix_char, 1)[1]
                    parts = args.split(" ")

                    ctx.command_name = prefix_char
                    ctx.arg = args
                    ctx.args = parts if ctx.args else []
                    logger.info("DISPATCH", LOG_DISPATCH_COMMAND, command_name=f"{prefix_char}")
                    await self.prefix_commands[prefix_char](ctx)
                    is_command_found = True

        if not is_command_found and ctx.target.startswith('#'):
            for handler in self.event_handlers['on_message']:
                await handler(ctx)

        else:
            dcc_match = DCC_SEND_REGEX.search(ctx.message)

            if dcc_match:
                data = dcc_match.groupdict()

                ip_long = int(data['ip'])
                try:
                    ip_address = ip_long_to_dotted(ip_long)
                except OSError as e:
                    self.logger.error("DCC", LOG_DCC_IP_CONVERT_ERROR, ip_long=ip_long, error=e)
                    return

                file_port = int(data['port'])
                file_size = int(data['filesize'])
                file_name = data['filename']

                dcc_file = DCCFile(
                    ctx, file_name, ip_address, file_port, file_size, self.save_dir
                )

                self.logger.info("DCC", LOG_DCC_EVENT_DISPATCH, safe_filename=dcc_file.safe_filename)
                for handler in self.event_handlers['on_dcc']:
                    asyncio.create_task(handler(dcc_file))

    async def _run_on_ready_handlers(self):
        logger = self.conn.logger
        logger.info("CORE", LOG_READY_DISPATCH)
        for handler in self.event_handlers['on_ready']:
            try:
                await handler(self)
            except Exception as e:
                logger.error("ERROR", LOG_READY_HANDLER_ERROR, handler_name=handler.__name__, error=e)


    async def _on_ready_protocol_setup(self):
        logger = self.conn.logger
        logger.info("CORE", LOG_READY_PROTOCOL)

        if self.password:
            await self.conn.send_raw(f"PRIVMSG NickServ :IDENTIFY {self.password}")

        for channel, key in self.channel_map.items():
            join_cmd = f"JOIN {channel}"
            if key: join_cmd += f" {key}"
            await self.conn.send_raw(join_cmd)


    async def start(self, channel_map: Dict[str, Optional[str]]):
        """
        Starts the main asynchronous bot loop.
        This method connects, registers the bot, joins channels, and begins
        processing incoming server messages and dispatching events.
        @arg channel_map: A dictionary where keys are channel names to join (e.g., '#channel') and values are optional channel keys/passwords.
        @return: None
        """
        logger = self.conn.logger

        if not self.conn.connected:
            await self.conn.connect()
            if not self.conn.connected: return

        self.running = True
        self.channel_map = channel_map

        if self.password: await self.conn.send_raw(f"PASS {self.password}")
        await self.conn.send_raw(f"USER {self.username} 0 * :{self.realname}")
        await self.conn.send_raw(f"NICK {self.nick}")

        await asyncio.sleep(0.5)

        logger.info("CORE", LOG_REGISTRATION_SENT)
        if not os.path.exists(self.save_dir):
            os.mkdir(self.save_dir)
            self.logger.info("CORE", LOG_DOWNLOADS_DIR_INIT, dirname = self.save_dir)

        while self.running and self.conn.connected:
            line = await self.conn.read_line()

            if line is None: break

            logger.raw_recv(line)

            if " 376 " in line and not self.registered:

                self.registered = True
                logger.info("NET", LOG_READY_MOTD)

                await self._on_ready_protocol_setup()
                await self._run_on_ready_handlers()

            await self._dispatch_line(line)

        self.running = False
        logger.info("CORE", LOG_LOOP_ENDED)
        self.conn.close()
