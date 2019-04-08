import asyncio
import socket
import inspect
import zmq
import zmq.asyncio
from distutils.version import LooseVersion
from ssdaq import sslogger

if LooseVersion("17") > LooseVersion(zmq.__version__):
    zmq.asyncio.install()


class ReceiverServer:
    def __init__(self, ip: str, port: int, publishers: list, name: str, loop=None):
        self.loop = asyncio.get_event_loop() if loop is None else loop
        self.log = sslogger.getChild(name)
        self._name = name
        self.publishers = publishers
        self.listen_addr = (ip, port)
        self.corrs = []
        for p in self.publishers:
            p.set_loop(self.loop)
        # setting up communications socket
        self._context = zmq.asyncio.Context()
        self._com_sock = self._context.socket(zmq.REP)
        self._com_sock.bind("ipc:///tmp/{}".format(self._name))
        self._setup = False

    def setup_stream(self, recv_protocol):
        self._setup = True
        self.log.info(
            "Settting up TCP receiver connection at %s:%d" % (tuple(self.listen_addr))
        )
        listen = self.loop.create_server(
            recv_protocol, host=self.listen_addr[0], port=self.listen_addr[1]
        )
        return self.loop.run_until_complete(listen)

    def setup_udp(self, recv_protocol):
        self._setup = True
        self.log.info(
            "Settting up UDP receiver connection at %s:%d" % (tuple(self.listen_addr))
        )
        listen = self.loop.create_datagram_endpoint(
            recv_protocol, local_addr=self.listen_addr
        )
        return self.loop.run_until_complete(listen)

    def run(self):
        if not self._setup:
            raise RuntimeError("No receiver socket setup")

        self.log.info("Number of publishers registered %d" % len(self.publishers))
        self._introspect()
        for c in self.corrs:
            self.loop.create_task(c)

        try:
            self.loop.run_forever()
        except Exception as e:
            self.log.error("Exception caught while running event loop: {}".format(e))

        self.loop.close()

    def _introspect(self):
        # Introspecting to find all methods that
        # handle commands
        method_list = inspect.getmembers(self, predicate=inspect.ismethod)
        self.cmds = {}
        for method in method_list:
            if method[0][:4] == "cmd_":
                self.cmds[method[0][4:]] = method[1]
            if method[0][:3] == "ct_":
                self.corrs.append(method[1]())

    async def handle_commands(self):
        """
        This is the server part of the receiver server that handles
        incomming control commands
        """
        while True:
            cmd = await self._com_sock.recv()
            self.log.info("Handling incoming command %s" % cmd.decode("ascii"))
            cmd = cmd.decode("ascii").split(" ")
            if cmd[0] in self.cmds.keys():
                reply = self.cmds[cmd[0]](cmd[1:])
            else:
                reply = b"Error, No command `%s` found." % (cmd[0])
                self.log.info("Incomming command `%s` not recognized")
            self._com_sock.send(reply)

    async def publish(self, packet: bytes):
        tasks = []
        for pub in self.publishers:
            tasks.append(self.loop.create_task(pub.apublish(packet)))
        for task in tasks:
            await task
