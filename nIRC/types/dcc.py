from nIRC.types.context import Context
from nIRC.logMessages import *
import os
import struct
import asyncio

class DCCFile:
    """
    Initializes the DCC file object.
    @arg context: The context object.
    @arg filename: The filename of the file in the DCC send request.
    @arg ip_address: The source IP address.
    @arg port: The source port.
    @arg filesize: The size of the file.
    @arg save_dir: The directory to save the file into. (defaule: ./downloads/)
    @return: None
    """
    def __init__(self, context: Context, filename: str, ip_address: str, port: int, filesize: int, save_dir: str):
        self.context = context
        self.sender = context.author
        self.filename = filename.strip().strip('"')
        self.ip_address = ip_address
        self.port = port
        self.filesize = filesize
        self.save_dir = save_dir
        self.safe_filename = os.path.basename(self.filename).replace(' ', '_')
        self.full_path = os.path.join(self.save_dir, self.safe_filename)
        _, self.extension = os.path.splitext(self.filename)
        self.is_good = True
        self.is_done = False
        self.progress = 0
        self.percent = 0

    async def start_transfer(self, connect_timeout=10, ack_chunk_size=4096):
        """
        Starts the transfer process.
        @kwarg connect_timeout: The connection timeout. (default: 10)
        @kwarg ack_chunk_size: The transfer chunk size. (default: 4096)
        @return: None
        """
        self.context.bot.logger.info("DCC", LOG_DCC_TRANSFER_INITIATED, safe_filename=self.safe_filename, sender=self.sender)

        reader, writer = None, None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip_address, self.port),
                timeout=connect_timeout
            )
            self.context.bot.logger.info("DCC", LOG_DCC_CONNECT_ESTABLISHED, safe_filename=self.safe_filename)

            await self._transfer_loop(reader, writer, ack_chunk_size)

        except asyncio.TimeoutError:
            self.context.bot.logger.error("DCC", LOG_DCC_TIMEOUT)
            self.is_good = False
        except ConnectionRefusedError:
            self.context.bot.logger.error("DCC", LOG_DCC_CONNECT_REFUSED, ip_address=self.ip_address, port=self.port)
            self.is_good = False
        except Exception as e:
            self.context.bot.logger.error("DCC", LOG_DCC_SETUP_ERROR, error=e)
            self.is_good = False
        finally:
            if writer and not writer.is_closing():
                writer.close()
                await writer.wait_closed()
            self.context.bot.logger.info("DCC", LOG_DCC_TRANSFER_FINISHED, safe_filename=self.safe_filename)

        self.is_done = True


    async def _transfer_loop(self, reader, writer, ack_chunk_size):
        received_bytes = 0

        try:
            with open(self.full_path, 'wb') as f:
                while received_bytes < self.filesize:
                    data = await asyncio.wait_for(
                        reader.read(ack_chunk_size),
                        timeout=30
                    )

                    if not data:
                        self.context.bot.logger.info("DCC", LOG_DCC_SENDER_CLOSED, received_bytes=received_bytes)
                        break

                    f.write(data)
                    received_bytes += len(data)

                    ack_message = struct.pack("!I", received_bytes)
                    writer.write(ack_message)
                    await writer.drain()

                    if received_bytes % (1024 * 1024 * 5) == 0 or received_bytes == self.filesize:
                        percent = (received_bytes / self.filesize) * 100 if self.filesize > 0 else 0
                        self.context.bot.logger.info("DCC", LOG_DCC_PROGRESS, percent=percent, received_bytes=received_bytes, filesize=self.filesize)
                        self.progress, self.percent = received_bytes, percent

            if received_bytes == self.filesize:
                self.context.bot.logger.info("DCC", LOG_DCC_SUCCESS, safe_filename=self.safe_filename)
            else:
                self.context.bot.logger.error("DCC", LOG_DCC_SIZE_MISMATCH, filesize=self.filesize, received_bytes=received_bytes)

        except asyncio.TimeoutError:
            self.context.bot.logger.error("DCC", LOG_DCC_READ_STALL, safe_filename=self.safe_filename)
        except Exception as e:
            self.context.bot.logger.error("DCC", LOG_DCC_TRANSFER_LOOP_ERROR, error=e)
