import socket
import struct
import time

from ethernet_message import *

NODE_IP = "10.0.0.113"
PORT = 13371
tport = 15555  # we will get msgs from cb after connect here
sock = socket.socket(socket.AF_INET,  # Internet
                     socket.SOCK_DGRAM) # UDP
sock.bind(('0.0.0.0', tport))
sock.sendto(b'\x04' + b'\x00' + struct.pack('<I', 4) + struct.pack('<I', tport) + b'\x00',
            (NODE_IP, PORT))
# receive ack
ack = sock.recvfrom(128)
# enable replay mode
sock.sendto(EthernetMessage("ACTION", "START_REPLAY", 0, '').serialize(), (NODE_IP, PORT))
time.sleep(1)  # sleep a second so we can see the led changing
# send a few frames
sock.sendto(EthernetMessage("ACTION", "REPLAY", 12, '00112233445566778800cafe').serialize(), (NODE_IP, PORT))
sock.sendto(EthernetMessage("ACTION", "REPLAY", 12, 'cafe11223344556677889900').serialize(), (NODE_IP, PORT))
# stop replay mode
time.sleep(0.1)
sock.sendto(EthernetMessage("ACTION", "STOP_CURRENT_ACTION", 0, '').serialize(), (NODE_IP, PORT))

