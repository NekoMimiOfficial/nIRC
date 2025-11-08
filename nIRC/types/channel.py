from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from nIRC.irc import Bot

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
    
    async def oper(self):
        """
        Requests OPER for the current channel
        @return: None
        """
        await self.bot.send_raw(f"MODE {self.name} +o {self.bot.nick}")

    async def get_topic(self) -> str:
        """
        Requests the current topic of the channel from the server.
        Note: The actual topic retrieval is complex and requires waiting for a 332 numeric.
        This is a placeholder that sends the request and returns an empty string immediately.
        @return: The current topic of the channel or an empty string in case of failure.
        """
        await self.bot.conn.send_raw(f"TOPIC {self.name}")
        topic_line= await self.bot.conn.read_line() or ""
        if self.bot.nick in topic_line and self.name in topic_line:
            return topic_line.split(":", 2)[2]
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
