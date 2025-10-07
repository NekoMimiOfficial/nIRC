from nIRC.irc import Bot, Context, IRCConnection, Logger
from typing import Optional
import asyncio, time

BOT_NICK = "nIRC"
COMMAND_PREFIX = "!"
CHANNELS_TO_JOIN = {
    "#chat": None,
    "#logs": None,
}
SERVER = "127.0.0.1"
PORT = 6667
SERVER_PASSWORD: Optional[str] = None

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

    await ctx._bot.send_message(recipient_nick, f"PM from {ctx.author}: {message_text}")
    await ctx.reply(f"PM sent to {recipient_nick}.")

@Bot.on_message()
async def keyword_responder(ctx: Context):
    """Responds to specific keywords in a channel message."""
    message = ctx.message.lower()
    if "nirc status" in message.lower():
        await ctx.reply(f"I am nIRC exampleBot, running on {SERVER}. My command prefix is '{COMMAND_PREFIX}'.")
    elif "help" == message.strip().lower():
        await ctx.reply(f"Available commands: !calc, !mod, !pmuser. See console for raw logs (type ERROR).")

@Bot.on_join()
async def greet_joiner(ctx: Context):
    """Sends a friendly greeting when a new user joins."""
    if ctx.author != BOT_NICK:
        await ctx.reply(f"Welcome, {ctx.author}! Type '{COMMAND_PREFIX}calc 1+1' to test a command.")

@Bot.on_raw()
async def raw_logger(ctx: Context):
    """Logs the raw line to the console (for demonstration only, triggers on all lines)."""
    if "ERROR" in ctx.full_line or "NOTICE" in ctx.full_line:
        print(f"[RAW LOG] IMPORTANT LINE: {ctx.full_line}")

@Bot.task(interval=10, max_repeat=5)
async def status_announcement(bot_instance: Bot, channel_name: str):
    """
    A non-blocking task that posts a system status message to the #logs channel.
    Shows the power of context-free scheduled actions.
    """
    count = status_announcement.current_repeat

    await bot_instance.send_message(
        channel_name,
        f"[HEARTBEAT] Task iteration {count}/5. Time: {time.strftime('%H:%M:%S')}. (Interval: 10s)"
    )

@Bot.on_ready()
async def initialization_setup(bot: Bot):
    """
    Runs once after connection and IRC registration is complete (after 376).
    Starts tasks and can perform one-time setup actions.
    """
    print("[NET] Running specialized initialization setup.")

    if "#logs" in bot.channel_map:
        bot.start_task(status_announcement, "#logs")
    else:
        print("[WARN] #logs channel not configured. Heartbeat task skipped.")

    if "#chat" in bot.channel_map:
        await bot.conn.send_raw(f"MODE #chat +m")
        print("[NET] Set +m (moderated) on #chat as an example one-time setup.")


async def run_bot():
    """Main entry point to initialize and run the bot."""
    logger= Logger(file_path= "log.txt", min_level= 0)

    irc_connection = IRCConnection(SERVER, PORT, logger)

    bot = Bot(
        prefix=COMMAND_PREFIX,
        conn=irc_connection,
        nick=BOT_NICK,
        username="nirc_bot",
        realname="neko IRC bot framework example client",
        password=SERVER_PASSWORD
    )

    try:
        await bot.start(CHANNELS_TO_JOIN)
    except Exception as e:
        print(f"FATAL BOT ERROR: {e}")
    finally:
        irc_connection.close()

if __name__ == "__main__":
    print("--- Starting Live Asynchronous nIRC Bot Framework Example ---")
    print(f"Connecting as NICK: {BOT_NICK} to {SERVER}:{PORT}")
    print(f"Channels configured: {', '.join(CHANNELS_TO_JOIN.keys())}")

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n[BOT] Shutting down gracefully via Ctrl+C.")
    except RuntimeError as e:
        if "cannot run" in str(e):
            print("\n[ERROR] Event loop error. If running in an interactive session, this is normal.")
        else:
            raise
