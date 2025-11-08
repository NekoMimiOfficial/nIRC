import io
import sys
from nIRC.irc import Bot, Context, DCCFile, Member
from nIRC.permissions import Permissions, perm_remove_user_on_leave
import ast

perm_list= {
        'nekomimi': 100,
        'NekoMimi': 100,
        'disuser': 20
}

async def fail_callback(ctx: Context, err_no: int):
    if err_no== 1:
        await ctx.send("You are not on the whitelist.")
    if err_no== 2:
        await ctx.send("You are not registered, run the following to login:")
        await ctx.send(f"/msg {ctx.bot.nick} identify PASSWORD")
    if err_no== 3:
        await ctx.send("You lack the necessary authority level to run this command")

perms= Permissions(perm_list, fail_callback)

@Bot.prefix_command("identify ")
async def cmd_login(ctx: Context):
    """Identify to get added to registered users (still doesn't allow safeguard commands unless on whitelist)"""

    if ctx.arg == "password": # Very secure amirite? :3
        # BTW you're supposed to make your own login implementation that possibly contain email registration
        # or if needed you can use the simple nIRC.register module AS A BASE for your registration system
        # contrary to belief, the nIRC.regster module isn't named after "registration" however it's considered a "register" for users and passwords
        perms.add_user(ctx.author)
        await ctx.send("logged in successfullyy :3")
    else:
        await ctx.send("wrong password!!! baka >:T")

@Bot.on_leave()
async def cog_role_leave(ctx: Context):
    """To remove users from the registered list in case of nick hijacking"""

    await perm_remove_user_on_leave(ctx, perms)

@Bot.command("hello")
async def hello_from_cog(ctx: Context):
    """A simple command loaded from a cog."""

    await ctx.reply(f"Hello {ctx.author}! This command was loaded from test.py.")

@Bot.task(interval=60.0, max_repeat=5)
async def cog_task(bot_instance: Bot):
    """A recurring task loaded from a cog."""

    current = getattr(cog_task, 'current_repeat', 0)
    total = getattr(cog_task, 'max_repeat', 0)

    bot_instance.logger.info("TASK", f"[COG] Cog task is running! Repeat {current}/{total}")
    for channel in bot_instance.channel_map:
        await bot_instance.send_message(channel, f"Cog task reporting in! (Run {current}/{total})")

@Bot.command("tasker")
@perms.safeguard(90)
async def cog_task_runner(ctx: Context):
    """Runs an nIRC bot task specifically one that requires no args"""

    task_name= ctx.arg
    if not ctx.arg:
        await ctx.reply("Usage: !tasker <task_name>")
        return

    try:
        func= ctx.bot.task_registry[task_name]
        ctx.bot.start_task(func)
        await ctx.reply(f"Running task: {task_name}")
    except Exception as e:
        await ctx.reply(f"Failed to run task: {e}")

@Bot.command("rmcmd")
@perms.safeguard(90)
async def cog_rm_cmd(ctx: Context):
    """Removes a command from the runnable commands"""

    if not ctx.arg:
        await ctx.reply("Usage: !rmcmd <command_name>")
        return
    
    removed= False
    cmd_name= ctx.arg
    old_reg= ctx.bot.commands.copy()
    ctx.bot.commands.clear()
    for cmd, func in old_reg.items():
        if not cmd == cmd_name:
            ctx.bot.commands[cmd]= func # Note: this will most likely break on a cog unload due to the main _event_registry remaining intact
        else:
            removed= True

    if removed:
        await ctx.reply(f"Removed command: '{cmd_name}'.")
    else:
        await ctx.reply(f"Commands '{cmd_name}' not found.")

@Bot.command("commands")
async def loaded_commands(ctx: Context):
    """Shows what commands you have loaded"""

    coms= ""
    pcoms= ""
    events= ""
    tasks= ""

    for com in ctx.bot.commands:
        coms+= str(com)+ " "

    for pcom in ctx.bot.prefix_commands:
        pcoms+= str(pcom)+ " "

    for event in ctx.bot.event_handlers:
        events+= str(event)+ f"({len(ctx.bot.event_handlers[event])}) "

    for task in ctx.bot.task_registry:
        tasks+= str(task)+ " "

    await ctx.send("===Registered Events=======================================")
    await ctx.send(f"Commands: {coms}")
    await ctx.send(f"Prefix Commands: {pcoms}")
    await ctx.send(f"Events: {events}")
    await ctx.send(f"Tasks: {tasks}")
    await ctx.send("===========================================================")

@Bot.prefix_command("n+ ")
@perms.safeguard(90)
async def allow_users(ctx: Context):
    if not len(ctx.args) == 2:
        await ctx.send(f"Invalid syntax: n+ NICK LVL")
        return
    perms.add_user(ctx.args[0])
    perms.add_perm(ctx.args[0], int(ctx.args[1]))
    await ctx.send(f"Gave '{ctx.args[0]}' an authority level of '{ctx.args[1]}'")

@Bot.prefix_command("n- ")
@perms.safeguard(90)
async def remove_users(ctx: Context):
    if not len(ctx.args) == 1:
        await ctx.send(f"Invalid syntax: n- NICK")
        return
    perms.rm_perm(ctx.args[0])
    await ctx.send(f"Removed '{ctx.args[0]}' from Whitelist")

@Bot.command("whitelist")
@perms.safeguard(50)
async def view_wl(ctx: Context):
    """Shows whitelist"""

    await ctx.send("==Whitelist===========")
    for name, lvl in perms.perm_list.items():
        await ctx.send(f"[{name}] @ {lvl}")
    await ctx.send("======================")

@Bot.command("reglist")
@perms.safeguard(50)
async def view_ru(ctx: Context):
    """Shows registered users"""

    await ctx.send("==Registered=Users====")
    for name in perms.registered_users:
        await ctx.send(f"[{name}]")
    await ctx.send("======================")

@Bot.prefix_command(">>")
@perms.safeguard(20)
async def ai_query_command(ctx: Context):
    """
    Fires on any message starting with '>>' (e.g., >>what is my status).
    This is great for clean, non-standard bot interactions.
    """

    if ctx.arg:
        response = f"AI Service received query from {ctx.author}: '{ctx.arg}'. Processing..."
        await ctx.reply(response)
        await ctx.send(str(ctx.args))
        await ctx.send(str(ctx.full_line))
    else:
        await ctx.reply("Please provide a query after the '>>'.")

def insert_returns(body):
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)

def split_by_nth_length(text, n):
    chunks = []
    for i in range(0, len(text), n):
        chunks.append(text[i:i + n])
    return chunks

@Bot.command("eval")
@perms.safeguard(90)
async def eval_fn(ctx: Context):
    """You most likely do NOT want to use this on a public server"""

    fn_name = "_eval_expr"

    cmd= ctx.arg
    cmd = cmd.strip("` ")
    cmd = "\n".join(f"    {i}" for i in cmd.splitlines())
    body = f"async def {fn_name}():\n{cmd}"

    parsed = ast.parse(body)
    body = parsed.body[0].body #type: ignore
    insert_returns(body)

    env = {
        'bot': ctx.bot,
        'ctx': ctx,
        '__import__': __import__
    }
    exec(compile(parsed, filename="<ast>", mode="exec"), env)
    original_output = sys.stdout
    captured_output = io.StringIO()

    sys.stdout = captured_output

    try:
        result = str(await eval(f"{fn_name}()", env))
    except Exception as e:
        await ctx.send("Failed to eval: "+ str(e))
        return
    captured_result = captured_output.getvalue()
    sys.stdout = original_output

    await ctx.send("==Eval Result=========")
    for line in result.splitlines():
        line= line.strip()
        if line and not line == "":
            for seg in split_by_nth_length(line, 300):
                await ctx.send(seg)

    await ctx.send("==STDOUT==============")
    for line in captured_result.splitlines():
        line= line.strip()
        if line and not line == "":
            for seg in split_by_nth_length(line, 300):
                await ctx.send(seg)

@Bot.command("shutdown")
@perms.safeguard(90)
async def cog_shutdown(ctx: Context):
    ctx.bot.running= False
    return

@Bot.command("mod")
@perms.safeguard(50)
async def mod_command(ctx: Context):
    """
    Handles moderation actions using Member and Channel abstractions.
    Usage: !mod <action> <target> [reason/value]
    """

    if len(ctx.args) < 2:
        await ctx.reply("Usage: !mod <kick|ban|topic|unban> <target> [value]")
        return

    action = ctx.args[0].lower()
    target_nick_or_mask = ctx.args[1]
    value_or_reason = " ".join(ctx.args[2:]) or "No reason provided."

    if action == "kick":
        member = ctx.get_member(target_nick_or_mask)
        await member.kick(ctx.target, value_or_reason)
        await ctx.reply(f"Attempted to kick {target_nick_or_mask} from {ctx.target}.")

    elif action == "ban":
        member = ctx.get_member(target_nick_or_mask)
        await member.ban(ctx.target, value_or_reason)
        await ctx.reply(f"Attempted to ban and kick {target_nick_or_mask} from {ctx.target}.")

    elif action == "topic" and ctx.target.startswith('#'):
        await ctx.channel_obj.set_topic(value_or_reason)
        await ctx.reply(f"New topic set to: {value_or_reason}")

    elif action == "unban" and ctx.target.startswith('#'):
        await ctx.channel_obj.unban(target_nick_or_mask)
        await ctx.reply(f"Attempted to remove ban mask: {target_nick_or_mask}")

    else:
        await ctx.reply(f"Unknown moderation action: {action}. Use kick, ban, topic, or unban.")

@Bot.command("pmuser")
async def pm_user_command(ctx: Context):
    """Sends a private message to a specified user."""

    if len(ctx.args) < 2:
        await ctx.reply("Usage: !pmuser <nick> <message...>")
        return

    recipient_nick = ctx.args[0]
    message_text = " ".join(ctx.args[1:])

    await ctx.bot.send_message(recipient_nick, f"PM from {ctx.author}: {message_text}")
    await ctx.reply(f"PM sent to {recipient_nick}.")

@Bot.on_message()
async def keyword_responder(ctx: Context):
    """Responds to specific keywords in a channel message."""

    message = ctx.message.lower()
    if message.strip() == ctx.bot.nick.lower():
        await ctx.reply(f"My command prefix is '{ctx.bot.prefix}'.")
        coms= ""
        for com in ctx.bot.commands:
            coms+= ctx.bot.prefix+ str(com)+ " "
        await ctx.send(f"Available commands: {coms}")

@Bot.on_join()
async def greet_joiner(ctx: Context):
    """Sends a friendly greeting when a new user joins."""

    if ctx.author != ctx.bot.nick:
        await ctx.reply(f"Welcome, {ctx.author}! Type {ctx.bot.prefix}commands to get a list of commands and events.")

@Bot.on_raw()
async def raw_logger(ctx: Context):
    """Logs the raw line to the console (for demonstration only, triggers on all lines)."""

    if "ERROR" in ctx.full_line or "NOTICE" in ctx.full_line:
        print(f"[RAW LOG] IMPORTANT LINE: {ctx.full_line}")

@Bot.prefix_command("?")
async def cog_prefix_cmd(ctx: Context):
    """A prefix command loaded from a cog."""

    await ctx.reply(f"Cog prefix command '?' triggered with: {ctx.arg}")

@Bot.on_dcc()
async def get_file(file: DCCFile):
    """DCC handler for receiving files over DCC"""

    file.context.logger.info("USER", f"Accepting file '{file.filename}' from {file.sender}.")
    user = Member(file.context.bot, file.sender)
    await user.send("Thanks for the file, it's *definitely* safe :3")
    await file.start_transfer()

@Bot.command("load")
@perms.safeguard(90)
async def load_cmd(ctx: Context):
    if not ctx.arg:
        await ctx.reply("Usage: !load <cog_name>")
        return

    cog_name = ctx.arg
    try:
        res= ctx.bot.load_cog(cog_name)
        if res[0]== 0:
            await ctx.reply(f"Cog '{cog_name}' loaded successfully.")
        elif res[0]== 1:
            await ctx.reply(f"Cog '{cog_name}' is already loaded.")
        else:
            await ctx.reply(f"Error loading Cog:")
            for line in str(res[1]).splitlines():
                await ctx.send(line)
    except Exception as e:
        await ctx.reply(f"Error loading cog '{cog_name}': {e}")

@Bot.command("unload")
@perms.safeguard(90)
async def unload_cmd(ctx: Context):
    if not ctx.arg:
        await ctx.reply("Usage: !unload <cog_name>")
        return

    cog_name = ctx.arg
    try:
        res= ctx.bot.unload_cog(cog_name)
        if res[0]== 0:
            await ctx.reply(f"Cog '{cog_name}' unloaded successfully.")
        elif res[0]== 1:
            await ctx.reply(f"Cog '{cog_name}' is not loaded.")
        else:
            await ctx.reply(f"Error unloading Cog:")
            for line in str(res[1]).splitlines():
                await ctx.send(line)
    except Exception as e:
        await ctx.reply(f"Error unloading cog '{cog_name}': {e}")

@Bot.command("reload")
@perms.safeguard(90)
async def reload_cmd(ctx: Context):
    if not ctx.arg:
        await ctx.reply("Usage: !reload <cog_name>")
        return

    cog_name = ctx.arg
    try:
        res= ctx.bot.reload_cog(cog_name)
        if res[0]== 0:
            await ctx.reply(f"Cog '{cog_name}' reloaded successfully.")
        elif res[0]== 1:
            await ctx.reply(f"Cog '{cog_name}' is not loaded.")
        else:
            await ctx.reply(f"Error reloading Cog:")
            for line in str(res[1]).splitlines():
                await ctx.send(line)
    except Exception as e:
        await ctx.reply(f"Error reloading cog '{cog_name}': {e}")

