from nIRC.irc import Bot, Context

@Bot.command("get_topic")
async def cmd_get_topic(ctx: Context):
    res= await ctx.channel_obj.get_topic()
    await ctx.send("chan top: "+ res)
