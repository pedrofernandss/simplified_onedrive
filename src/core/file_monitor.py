import os
import time
import hashlib
import threading

class FileMonitor:
    def __init__(self, sync_dir, node_id):
        self.sync_dir = sync_dir
        self.node_id = node_id
        self.files = {}
        self.running = True

        if not os.path.exists(self.sync_dir):
            os.makedirs(self.sync_dir)


