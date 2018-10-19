import socket
from threading import Thread

class SSDataListener(Thread):
    """
    Slow signal data listener. Recieves UDP packets
    from TMs with slow signal data and puts it in a data queue
    for the SSEventBuilder.
    """
    def __init__(self,port,data_queue):
        Thread.__init__(self)
        self.port = int(port)
        self.data_queue = data_queue
        self.running = False
        self.npackets_from = {}
        self.npackets_tot = 0

    def run(self):
        self.running = True
        self.setName('SSDataListener')
        # Create a TCP/IP socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as data_socket:
            # Bind the socket to the port
            server_address = ('0.0.0.0', self.port)
            data_socket.bind(server_address)
            
            while(self.running):
                data, address = data_socket.recvfrom(6096)
                self.data_queue.put((address[0],data))
