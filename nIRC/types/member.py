from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from nIRC.irc import Bot

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
        for line in text.splitlines():
            await self.bot.send_message(self.nick, line)

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
