# 12331 is broadcast discovery port

from socket import *
import threading
import time


def printLiveNodes(alive_nodes, lock):
    while(True):
        lock.acquire()
        for node in alive_nodes:
            name = ""
            version = 1
            print("Node %s with version %d is alive!" % (name, version))
        lock.release()
        time.sleep(1)


def main():
    alive_nodes = []
    lock = threading.Semaphore()
    t = threading.Timer(1.0, printLiveNode, alive_nodes, lock)

    s = socket(AF_INET, SOCK_DGRAM)
    s.bind(('', 13370))
    while True:
        msg = s.recvfrom(128)
        if msg[0:1] = 'CB':
            lock.acquire()
            if msg not in alive_nodes:
                alive_nodes.append(msg, time.no)
            lock.release()

main()