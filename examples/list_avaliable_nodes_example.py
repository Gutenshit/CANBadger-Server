import socket

UDP_IP = "0.0.0.0"  # bind on all interfaces
UDP_PORT = 13370

sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP
sock.bind((UDP_IP, UDP_PORT))

nodes = []
while True:
    data, addr = sock.recvfrom(256)
    data_split = data.split("|")
    id = data_split[1]
    version = data_split[2]
    node = [addr, id, version]
    if node not in nodes:
        nodes.append(node)
        print "discovered new node with ip=%s, id=%s, version=%s" % (addr[0], id, version)