from nIRC.irc import Bot, Context, DCCFile, Member


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

@Bot.prefix_command(">")
async def ai_query_command(ctx: Context):
    """
    Fires on any message starting with '>' (e.g., >what is my status).
    This is great for clean, non-standard bot interactions.
    """

    if ctx.arg:
        response = f"AI Service received query from {ctx.author}: '{ctx.arg}'. Processing..."
        await ctx.reply(response)
        await ctx.send(str(ctx.args))
        await ctx.send(str(ctx.full_line))
    else:
        await ctx.reply("Please provide a query after the '>'.")

@Bot.command("calc")
async def calculate_command(ctx: Context):
    """
    Demonstrates using ctx.arg and ctx.args.
    A simplified math evaluator.
    """

    if not ctx.arg:
        await ctx.reply("Usage: !calc <expression> (e.g., 5 + 3 * 2)")
        return

    try:
        # Warning: Using eval() is generally unsafe in production bots.
        # This is for demonstration purposes only.
        result = eval(ctx.arg)
        await ctx.reply(f"Result for '{ctx.arg}': {result}")
    except Exception:
        await ctx.reply(f"Could not calculate the expression: {ctx.arg}")

@Bot.command("mod")
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
