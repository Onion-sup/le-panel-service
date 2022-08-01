import threading

class PostAMessage:
    def __init__(self):
        self.message = ''
        self.message_lock = threading.Lock()
    
    def set_message(self, message):
        with self.message_lock:
            self.message = message

    def get_message(self):
        with self.message_lock:
            return self.message