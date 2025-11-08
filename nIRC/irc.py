from typing import Dict, Optional, Callable, Any, List, Tuple, Set
from nIRC.logMessages import *
from nIRC.logger import Logger, NullLogger, LOG_PREFIX
from nIRC.types.member import Member
from nIRC.types.dcc import DCCFile
from nIRC.types.context import Context
from functools import wraps
import asyncio, re, sys, os
import importlib


_command_registry: Dict[str, Callable] = {}
_prefix_command_registry: Dict[str, Callable] = {}
_event_registry: Dict[str, List[Callable]] = {
    'on_message': [],
    'on_join': [],
    'on_leave': [],
    'on_raw': [],
    'on_ready': [],
    'on_nick': [],
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
    def __init__(self, host: str, port: int, logger: Optional[Logger] = None, quit_msg: Optional[str] = None):
        """
        Initializes the connection handler.
        @arg host: The IRC server hostname or IP address.
        @arg port: The IRC server port (usually 6667).
        @kwarg logger: A logger instance for logging network events. If None, NullLogger is used. (default: None)
        @return: None
        """
        self.host = host
        self.port = port
        self.quit_msg = "QUIT :"+ quit_msg if quit_msg else "QUIT"
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

    async def close(self):
        """
        Closes the network connection writer.
        @return: None
        """
        if self.writer:
            await self.send_raw(self.quit_msg)
            self.writer.close()
            self.logger.info("NET", LOG_NET_CLOSED_LOCAL)
            self.connected = False

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
        self._mute_status: Dict[str, Set[str]] = {}

        self.conn = conn
        self.logger = conn.logger
        self.save_dir = downloads_dir

        self.commands: Dict[str, Callable] = _command_registry.copy()
        self.prefix_commands: Dict[str, Callable] = _prefix_command_registry.copy()
        self.event_handlers: Dict[str, List[Callable]] = _event_registry.copy()
        self.task_registry: Dict[str, Callable] = _task_registry.copy()

        self.cogs: Dict[str, Dict[str, Any]] = {}

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
    def on_nick():
        """
        Decorator to register a function to be called when a user changes nicknames.
        The decorated function must accept one argument: a Context object.
        The context object will use the old Nick for the username and the new Nick in the text.
        @return: The decorator function.
        """
        def decorator(func: Callable):
            _event_registry['on_nick'].append(func)
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

    async def oper(self, username: str, password: str):
        """
        Requests OPER on a server
        @arg username: OPER username
        @arg password: OPER password
        @return: None
        """
        await self.send_raw(f"OPER {username} {password}")

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

    def load_cog(self, cog_name: str):
        """
        Loads a cog module.
        A cog is a Python module (e.g., 'cogs.mycommands') that uses the
        standard @Bot.command, @Bot.on_message, etc., decorators.
        @arg cog_name: The dot-path name of the module to load.
        @return: [int, Any], depending on whether it succeeded or failed to load
            0, True:        loaded successfully.
            1, False:       cogs already loaded.
            2, Exception:   general error, check logs.
        """
        if cog_name in self.cogs:
            self.logger.error("COG", LOG_CORE_COG_ALREADY_LOADED, cog_name=cog_name)
            return [1, False]

        self.logger.info("COG", LOG_CORE_COG_LOAD, cog_name=cog_name)
        before_cmds = set(_command_registry.keys())
        before_prefix = set(_prefix_command_registry.keys())
        before_tasks = set(_task_registry.keys())
        before_events = {key: list(handlers) for key, handlers in _event_registry.items()}

        try:
            module = importlib.import_module(cog_name)
            after_cmds = set(_command_registry.keys())
            new_cmds = after_cmds - before_cmds
            for cmd in new_cmds:
                self.commands[cmd] = _command_registry[cmd]
            after_prefix = set(_prefix_command_registry.keys())
            new_prefix = after_prefix - before_prefix
            for prefix in new_prefix:
                self.prefix_commands[prefix] = _prefix_command_registry[prefix]
            after_tasks = set(_task_registry.keys())
            new_tasks = after_tasks - before_tasks
            for task in new_tasks:
                self.task_registry[task] = _task_registry[task]
            new_events_map: Dict[str, List[Callable]] = {}
            for event_name, after_handlers in _event_registry.items():
                before_handler_set = set(before_events.get(event_name, []))
                added_handlers = [h for h in after_handlers if h not in before_handler_set]

                if added_handlers:
                    new_events_map[event_name] = added_handlers
                    if event_name not in self.event_handlers:
                        self.event_handlers[event_name] = []
                    for added_handlers_items in added_handlers:
                        self.event_handlers[event_name].append(added_handlers_items)

            self.cogs[cog_name] = {
                'module': module,
                'commands': new_cmds,
                'prefix_commands': new_prefix,
                'tasks': new_tasks,
                'events': new_events_map
            }

            for e_name, handlers in self.event_handlers.items():
                self.event_handlers[e_name]= []
            for e_name, handlers in before_events.items():
                for handler in handlers:
                    if not handler.__name__ in [h.__name__ for h in self.event_handlers[e_name]]:
                        self.event_handlers[e_name].append(handler)
            for e_name, handlers in new_events_map.items():
                for handler in handlers:
                    if not handler.__name__ in [h.__name__ for h in self.event_handlers[e_name]]:
                        self.event_handlers[e_name].append(handler)

            self.logger.info("COG", LOG_CORE_COG_LOAD_SUCCESS, cog_name=cog_name)
            return [0, True]

        except Exception as e:
            self.logger.error("ERROR", LOG_CORE_COG_LOAD_FAIL, cog_name=cog_name, error=e)
            if cog_name in sys.modules:
                del sys.modules[cog_name]
            return [2, e]

    def unload_cog(self, cog_name: str):
        """
        Unloads a cog module.
        Removes all commands, event handlers, and tasks registered by that cog.
        @arg cog_name: The dot-path name of the module to unload.
        @return: [int, Any], depending on whether it succeeded or failed to load
            0, True:        unloaded successfully.
            1, False:       cogs already unloaded.
            2, Exception:   general error, check logs.
        """
        if cog_name not in self.cogs:
            self.logger.error("COG", LOG_CORE_COG_NOT_LOADED, cog_name=cog_name)
            return [1, False]

        self.logger.info("COG", LOG_CORE_COG_UNLOAD, cog_name=cog_name)
        cog_data = self.cogs.pop(cog_name)

        try:
            for cmd in cog_data['commands']:
                self.commands.pop(cmd, None)
                _command_registry.pop(cmd, None)

            for prefix in cog_data['prefix_commands']:
                self.prefix_commands.pop(prefix, None)
                _prefix_command_registry.pop(prefix, None)

            for task in cog_data['tasks']:
                self.task_registry.pop(task, None)
                _task_registry.pop(task, None)

            for event_name, handlers_to_remove in cog_data['events'].items():
                for handler in handlers_to_remove:
                    if event_name in self.event_handlers and handler in self.event_handlers[event_name]:
                        self.event_handlers[event_name].remove(handler)
                    if event_name in _event_registry and handler in _event_registry[event_name]:
                        _event_registry[event_name].remove(handler)

            if cog_name in sys.modules:
                del sys.modules[cog_name]

            cogs_copy= self.cogs.copy()
            self.cogs.clear()
            for cog_name_l, cog_dispatches in cogs_copy.items():
                if not cog_name_l == cog_name:
                    self.cogs[cog_name_l]= cog_dispatches
            for e_name, _ in _event_registry.items():
                if e_name in self.event_handlers:
                    _event_registry[e_name]= self.event_handlers[e_name]
                else:
                    _event_registry[e_name]= []

            self.logger.info("COG", LOG_CORE_COG_UNLOAD_SUCCESS, cog_name=cog_name)
            return [0, True]

        except Exception as e:
            self.logger.error("ERROR", LOG_CORE_COG_UNLOAD_FAIL, cog_name=cog_name, error=e)
            return [2, e]

    def reload_cog(self, cog_name: str):
        """
        Reloads a cog module.
        This is an unload followed by a load, but uses importlib.reload.
        @arg cog_name: The dot-path name of the module to reload.
        @return: [int, Any], depending on whether it succeeded or failed to load
            0, True:        loaded successfully.
            1, False:       cogs already loaded.
            2, Exception:   general error, check logs.
        """
        if cog_name not in self.cogs:
            self.logger.info("COG", LOG_CORE_COG_RELOAD_AS_LOAD, cog_name=cog_name)
            self.load_cog(cog_name)
            return [1, False]

        self.logger.info("COG", LOG_CORE_COG_RELOAD, cog_name=cog_name)
        cog_data = self.cogs.pop(cog_name)

        try:
            for cmd in cog_data['commands']:
                self.commands.pop(cmd, None)
                _command_registry.pop(cmd, None)

            for prefix in cog_data['prefix_commands']:
                self.prefix_commands.pop(prefix, None)
                _prefix_command_registry.pop(prefix, None)

            for task in cog_data['tasks']:
                self.task_registry.pop(task, None)
                _task_registry.pop(task, None)

            for event_name, handlers_to_remove in cog_data['events'].items():
                for handler in handlers_to_remove:
                    if event_name in self.event_handlers and handler in self.event_handlers[event_name]:
                        self.event_handlers[event_name].remove(handler)
                    if event_name in _event_registry and handler in _event_registry[event_name]:
                        _event_registry[event_name].remove(handler)

            before_cmds = set(_command_registry.keys())
            before_prefix = set(_prefix_command_registry.keys())
            before_tasks = set(_task_registry.keys())
            before_events = {key: list(handlers) for key, handlers in _event_registry.items()}

            module = importlib.reload(cog_data['module'])
            after_cmds = set(_command_registry.keys())
            new_cmds = after_cmds - before_cmds
            for cmd in new_cmds:
                self.commands[cmd] = _command_registry[cmd]

            after_prefix = set(_prefix_command_registry.keys())
            new_prefix = after_prefix - before_prefix
            for prefix in new_prefix:
                self.prefix_commands[prefix] = _prefix_command_registry[prefix]

            after_tasks = set(_task_registry.keys())
            new_tasks = after_tasks - before_tasks
            for task in new_tasks:
                self.task_registry[task] = _task_registry[task]

            new_events_map: Dict[str, List[Callable]] = {}
            for event_name, after_handlers in _event_registry.items():
                before_handler_set = set(before_events.get(event_name, []))
                added_handlers = [h for h in after_handlers if h not in before_handler_set]
                if added_handlers:
                    new_events_map[event_name] = added_handlers
                    if event_name not in self.event_handlers:
                        self.event_handlers[event_name] = []
                    self.event_handlers[event_name].extend(added_handlers)

            self.cogs[cog_name] = {
                'module': module,
                'commands': new_cmds,
                'prefix_commands': new_prefix,
                'tasks': new_tasks,
                'events': new_events_map
            }
            self.logger.info("COG", LOG_CORE_COG_RELOAD_SUCCESS, cog_name=cog_name)
            return [0, True]

        except Exception as e:
            self.logger.error("ERROR", LOG_CORE_COG_RELOAD_FAIL, cog_name=cog_name, error=e)
            return [2, e]

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
        raw_ctx = Context(self, "", "", line, "RAW", line)
        for handler in self.event_handlers['on_raw']:
            await handler(raw_ctx)

        _, command, target, author_nick, message = self._parse_line(line)

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
                for handler in self.event_handlers['on_leave']: await handler(ctx)
            elif command == "NICK" and author_nick != self.nick:
                for handler in self.event_handlers['on_nick']: await handler(ctx)

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
        await self.conn.close()
        return
