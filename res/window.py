import math, logging, sys
from packet import *
from const import *

class Window():

    def __init__(self, data=""):

        self.pointer = 0
        self.length = 0
        self.frames = []

        logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y/%m/%d %H:%M:%S', stream=sys.stdout, level=logging.DEBUG)

        self.create_window(data)

    # Initial window content
    def create_window(self, data):
        # number of frames in the window
        self.length = math.ceil(len(data)/PAYLOAD_SIZE)
        # load data into window's frame
        for i in range(0, self.length):
            if i == self.length - 1:
                self.frames.append(Frame(i+1, data[i*PAYLOAD_SIZE:]))
            else:
                self.frames.append(Frame(i+1, data[i*PAYLOAD_SIZE : (i+1)*PAYLOAD_SIZE]))
        
        logging.debug(f"Create Window with Num of Packets -- {self.length}")
        #self.display_frames_content()

    # Check pending frames
    def has_pending_packet(self):

        for i in range(0, self.length):
            if not self.frames[i].ACK:
                return True
        return False
    
    # Get frames need to send in the window
    def get_process_frames(self):

        frameList = []
        for i in range(self.pointer, self.get_max_index()):
            temp = self.frames[i]
            if not temp.send:
                frameList.append(temp)
                #logging.debug(f"Sender Frame append: {str(temp)}")
        return frameList
    
    # Set frame as ACK, and move pointer index
    def update_ack_window(self, seq_num):

        self.frames[seq_num - 1].ACK = True
        offset = 0
        
        for i in range(self.pointer, self.get_max_index()):
            if self.frames[i] is not None and self.frames[i].ACK:
                offset += 1
            else:
                break
        self.pointer += offset

    # Reset frame as Not send, if time out
    def update_timeout_window(self):

        for i in range(self.pointer, self.get_max_index()):
            frame = self.frames[i]

            if frame.send and not frame.ACK:
                frame.send = False
    
    # Get validate window index
    def get_max_index(self):
        if self.pointer + WINDOW_SIZE >= self.length:
            return self.length
        else:
            return self.pointer + WINDOW_SIZE
    
    # Process received packets
    def process_packet(self, packet):

        # Initial frame with None items, or extend None at end
        if len(self.frames) < self.pointer + WINDOW_SIZE:

            count = self.pointer + WINDOW_SIZE - len(self.frames)

            self.frames.extend([None] * count)
            self.length = len(self.frames)

        index = packet.seq_num - 1

        if self.frames[index] is None and self.pointer <= index and index < self.pointer + WINDOW_SIZE:
            self.frames[index] = Frame(index+1, packet.payload)
            # Renew pointer location, and set as ACK
            self.update_ack_window(packet.seq_num)
        #self.display_frames_content()
    

    def display_frames_content(self):
        print("\n==========     Frames Content     =========")
        for i in range(0, len(self.frames)):
            print("[DEBUG] - "+(str(self.frames[i])))
        print("=============       END      ==============\n")
    

class Frame:

    def __init__(self, seq_num, payload=None):
        self.seq_num = seq_num
        self.payload = payload
        self.send = False
        self.ACK = False
    
    def __str__(self):
        return (f"Num: {self.seq_num}, Payload: {self.payload}, Send: {self.send}, ACK: {self.ACK}")