from src.connection.socket_server import BaseHandler


class PreGamePhaseHandler(BaseHandler):
    async def process_message(self, message: str):
        self.logger.info(f"Socket received: {message}")
        await self.send_ack()
