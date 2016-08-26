from PyQt4.QtCore import *
from PyQt4.QtNetwork import *
import random
import struct

from ethernet_message import *

class NodeConnection(QObject):
    threadReady = pyqtSignal()
    connectionSucceeded = pyqtSignal()
    connectionFailed = pyqtSignal(str)
    nodeDisconnected = pyqtSignal(dict)
    ackReceived = pyqtSignal()
    nackReceived = pyqtSignal()

    # message signals
    newDebugMessage = pyqtSignal(str)
    # is actually QByteArray but this prevents pyqt from doing any conversion
    newDataMessage = pyqtSignal(object)
    newTestDataMessage = pyqtSignal(str)

    def __init__(self, node):
        super(NodeConnection, self).__init__()
        self.node = node
        self.isConnected = False
        self.port = random.randint(10000, 13372)
        # TODO: we need a dict of to-be-acked messages so we now what got sent and what didnt
        self.waitForAck = False # indicates whether there is a pending ACK
        self.testMode = False
        self.frameQueue = []

    def onRun(self):
        self.threadReady.connect(self.onThreadReady)
        self.threadReady.emit()

    def onThreadReady(self):
        # create sockets for every channel
        # action socket for sending stuff
        self.actionSocket = QUdpSocket()
        # data socket for receiving stuff
        self.dataSocket = QUdpSocket()
        if not self.dataSocket.bind(self.port, QUdpSocket.ReuseAddressHint):
            # reconnect on failure, use other port
            self.port = random.randint(10000, 13372)
            self.threadReady.emit()
            return
        self.dataSocket.readyRead.connect(self.onDataSocketReadyRead)

        self.tryConnect()

    def tryConnect(self):
        # try to initiate connection
        #self.actionSocket.writeDatagram(b'\x04' + '|' + str(self.port) + '|', QHostAddress(QString(self.node["ip"])), 13371)
        self.actionSocket.writeDatagram(b'\x04' + b'\x00' + struct.pack('<I', 4) + struct.pack('<I', self.port) + b'\x00', QHostAddress(QString(self.node["ip"])), 13371)

    def updateSettings(self, settings):
        for key, value in settings.iteritems():
            if len(key) > 127:
                print("ERROR: key %s is too long! Max Length: 127 bytes" % (key))
                continue
            if len(value) > 255:
                print("ERROR: value of %s is too long! Max Length: 255 bytes" % (key))
                continue
            if ';' in value:
                print("ERROR: value of %s is invalid: no semicolons allowed!" % (key))
                continue

            # update settings msg should look like: 3|0|key|value\NULLBYTE
            #self.actionSocket.writeDatagram(b'\x03' + '|' + b'\x01' + '|' + str(key) + ';' + str(value) + b'\x00', \
             #                               QHostAddress(QString(self.node["ip"])), 13371)
            keyval_str = "%s;%s" % (key, value)
            self.actionSocket.writeDatagram(EthernetMessage("ACTION", "SETTINGS", len(keyval_str), str(keyval_str)).serialize(),
                                            QHostAddress(QString(self.node["ip"])), 13371)
            self.waitForAck = True

    def enableTestmode(self):
        ethMsg = EthernetMessage("ACTION", "ENABLE_TESTMODE", 0, "")
        self.actionSocket.writeDatagram(ethMsg.serialize(), QHostAddress(QString(self.node["ip"])), 13371)
        self.testMode = True
        self.waitForAck = True

    def runCanloggerTest(self):
        ethMsg = EthernetMessage("ACTION", "LOG_RAW_CAN_TRAFFIC", 0, "")
        self.actionSocket.writeDatagram(ethMsg.serialize(), QHostAddress(QString(self.node["ip"])), 13371)
        self.waitForAck = True

    def stopCurrentAction(self):
        ethMsg = EthernetMessage("ACTION", "STOP_CURRENT_ACTION", 0, "")
        self.actionSocket.writeDatagram(ethMsg.serialize(), QHostAddress(QString(self.node["ip"])), 13371)
        self.waitForAck = True

    # expects integer ids, not hex strings
    def startUDS(self, own_id, target_id):
        payload = struct.pack("<II", own_id, target_id)
        self.actionSocket.writeDatagram(EthernetMessage("ACTION", "START_UDS", len(payload), payload).serialize(), QHostAddress(QString(self.node["ip"])), 13371)
        self.waitForAck = True

    # expects integer ids, not hex strings
    def startTP(self, module_id, channel_negot_id):
        payload = struct.pack("<II", module_id, channel_negot_id)
        self.actionSocket.writeDatagram(EthernetMessage("ACTION", "START_TP", len(payload), payload).serialize(), QHostAddress(QString(self.node["ip"])), 13371)
        self.waitForAck = True

    def callUDSFunction(self, function_id):
        self.actionSocket.writeDatagram(EthernetMessage("ACTION", "UDS", 1, struct.pack('>B', function_id)).serialize(),
                                        QHostAddress(QString(self.node["ip"])), 13371)
        self.waitForAck = True

    def callTPFunction(self, function_id):
        self.actionSocket.writeDatagram(EthernetMessage("ACTION", "TP", 1, struct.pack('>B', function_id)).serialize(),
                                        QHostAddress(QString(self.node["ip"])), 13371)
        self.waitForAck = True

    def sendMessage(self, msg):
        self.actionSocket.writeDatagram(msg.serialize(), QHostAddress(QString(self.node["ip"])), 13371)

    def fillFrameQueue(self, frames):
        self.frameQueue = frames

    def sendNextFrame(self):
        # takes the next frame from the queue and sends it
        if len(self.frameQueue) > 0:
            frame = self.frameQueue[0]
            self.sendMessage(EthernetMessage('ACTION', 'REPLAY', len(frame), frame))
            del self.frameQueue[0]
            return True
        else:
            return False


    @pyqtSlot()
    def onDataSocketReadyRead(self):
        pending_size = self.dataSocket.pendingDatagramSize()
        msg = self.dataSocket.readDatagram(pending_size)
        ethMsg = EthernetMessage.unserialize(msg[0])
        msg_type = ethMsg.getMsgType()
        if not self.isConnected:
            # ack is 0
            if msg_type == "ACK":
                self.isConnected = True
                self.connectionSucceeded.emit()
            else:
                self.tryConnect()
        else:
            if self.testMode:
                if msg_type == "DATA":
                    # emit data signal
                    self.newTestDataMessage.emit(ethMsg.data)
            else:
                if msg_type == "DATA":
                    data = QByteArray.fromRawData(ethMsg.data)
                    self.last_ethmsg = ethMsg
                    self.last_data = data # keep reference so qt doesnt fuck up
                    self.newDataMessage.emit(data)
                if msg_type == "DEBUG_MSG": # debug msg
                    self.newDebugMessage.emit(ethMsg.data)
                if msg_type == "ACK":
                    self.waitForAck = False
                    self.ackReceived.emit()
                if msg_type == "NACK":
                    self.waitForAck = False
                    self.nackReceived.emit()

    @pyqtSlot()
    def resetNode(self):
        if self.isConnected:
            self.actionSocket.writeDatagram(EthernetMessage("ACTION", "RESET", 0, "").serialize(),
                                            QHostAddress(QString(self.node["ip"])), 13371)
            self.isConnected = False
            self.nodeDisconnected.emit(self.node)
