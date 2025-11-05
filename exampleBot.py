from nIRC.irc import Bot, Context, IRCConnection, Logger
from typing import Optional
import asyncio

BOT_NICK = "nIRC"
COMMAND_PREFIX = "!"
CHANNELS_TO_JOIN = {
    "#chat": None,
    "#logs": None,
}
SERVER = "127.0.0.1"
PORT = 6667
SERVER_PASSWORD: Optional[str] = None

@Bot.command("load")
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

@Bot.on_ready()
async def initialization_setup(bot: Bot):
    """
    Runs once after connection and IRC registration is complete (after 376).
    Starts tasks and can perform one-time setup actions.
    """

    if "#chat" in bot.channel_map:
        await bot.conn.send_raw(f"MODE #chat +m") # Set +m (moderated) on #chat as an example one-time setup.

    # You can load cogs on startup here, try using the following:
    # bot.load_cog("cogs.test")


async def run_bot():
    """Main entry point to initialize and run the bot."""

    global logger
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
        await bot.start(CHANNELS_TO_JOIN) #type: ignore
    except Exception as e:
        print(f"FATAL BOT ERROR: {e}")

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
