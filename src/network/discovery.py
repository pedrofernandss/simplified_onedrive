import json
import time
import socket
import threading

class DiscoveryService:
    def __init__(self, node_id):
        self.node_id = node_id
        self.udp_port = 9999
        self.peers = {}
        self.timeout = 5
        self.running = True