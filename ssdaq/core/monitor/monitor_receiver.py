import asyncio
from ssdaq.core.receiver_server import ReceiverServer

import zmq

from ssdaq.core.timestamps import CDTS_pb2


class MonitorReceiver(ReceiverServer):
    def __init__(self, ip: str, port: int, publishers: list):
        super().__init__(ip, port, publishers, "MonitorReceiver")

        self.running = True
        # The ReceiverServer already has a zmq context
        self.receiver = self._context.socket(zmq.PULL)
        connectionstr = "tcp://{}:{}".format(ip, port)
        self.log.info("Setting up monitor zmq pull server at {}".format(connectionstr))
        self.receiver.bind(connectionstr)
        self._setup = True

    async def ct_subscribe(self):
        while self.running:
            packet = await self.receiver.recv()
            # for tm in tb.triggers:
            await self.publish(packet)


if __name__ == "__main__":
    from ssdaq.core import publishers

    trpl = MonitorReceiver(
        port=10002,
        ip="0.0.0.0",
        publishers=[publishers.ZMQTCPPublisher(ip="127.0.0.101", port=9005)],
    )
    trpl.run()
