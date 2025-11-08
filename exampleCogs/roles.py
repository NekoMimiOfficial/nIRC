from nIRC.irc import Bot, Context
from nIRC.permissions import Permissions, perm_remove_user_on_leave

perm_list= {
        'nekomimi': 100,
        'NekoMimi': 100,
        'disuser': 20
}

perms= Permissions(perm_list)

@Bot.command("login")
async def cmd_login(ctx: Context):
    if ctx.arg == "usermod":
        perms.add_user(ctx.author)
        await ctx.send("logged in successfullyy :3")
    else:
        await ctx.send("wrong password!!! baka >:T")

@Bot.on_leave()
async def cog_role_leave(ctx: Context):
    await perm_remove_user_on_leave(ctx, perms)

@Bot.command("sudo")
@perms.safeguard(90)
async def cog_admin_cmd(ctx: Context):
    await ctx.send("oooo an admin is running this com!!")
