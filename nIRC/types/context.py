from nIRC.types.member import Member
from nIRC.types.channel import Channel
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from nIRC.irc import Bot

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
        for line in text.splitlines():
            await self.bot.send_message(recipient, line)

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
