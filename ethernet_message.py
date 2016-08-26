import struct
# for debugging
from PyQt4.QtCore import *

class EthernetMessage:
    #types = { 'ACK' : 0, 'NACK' : 1, 'DATA' : 2, 'ACTION': 3, 'CONNECT' : 4, 'DEBUG_MSG' : 5}
    types = {0: 'ACK', 1: 'NACK', 2: 'DATA', 3: 'ACTION', 4: 'CONNECT', 5: 'DEBUG_MSG'}
    #action_types = {'NO_TYPE' : 0, 'SETTINGS' : 1, 'REPLAY' : 2, 'LOG_RAW_CAN_TRAFFIC' : 3, 'ENABLE_TESTMODE' : 4}
    action_types = {0: 'NO_TYPE', 1: 'SETTINGS', 2: 'REPLAY', 3: 'LOG_RAW_CAN_TRAFFIC',
                    4: 'ENABLE_TESTMODE', 5: 'STOP_CURRENT_ACTION', 6: 'RESET', 7: 'START_UDS',
                    8: 'START_TP', 9: 'UDS', 10: 'TP', 11: 'HIJACK', 12: 'MITM',
                    13: 'UPDATE_SD', 14: 'DOWNLOAD_FILE', 15: 'DELETE_FILE',
                    16: 'CLEAR_RULES', 17: 'ADD_RULE', 18: 'ENABLE_MITM_MODE',
                    19: 'START_REPLAY'
    }

    types_str_to_value = dict((v,k) for k,v in types.iteritems())
    action_types_str_to_value = dict((v,k) for k,v in action_types.iteritems())

    def __init__(self, msg_type, action_type, data_length, data):
        if(type(msg_type) == str):
            self.msg_type = self.types_str_to_value[msg_type]
        else:
            self.msg_type = msg_type

        if(type(action_type) == str):
            self.action_type = self.action_types_str_to_value[action_type]
        else:
            self.action_type = action_type

        self.data_length = data_length
        self.data = data

    def serialize(self):
        if self.data:
            return struct.pack("<BBI%ds" % (self.data_length), self.msg_type, self.action_type, self.data_length, self.data)
        else:
            return struct.pack('<BBI', self.msg_type, self.action_type, self.data_length)

    @staticmethod
    def unserialize(raw_data):
        # parse header
        (msg_type, action_type, data_length) = struct.unpack('<bbI', raw_data[:6])
        data = ""
        if data_length > 0:
            data = ''.join(struct.unpack("%dc" % (data_length), raw_data[6:]))
        return EthernetMessage(msg_type, action_type, data_length, data)

    # ACCESSORS
    def getMsgType(self):
        return self.types[self.msg_type]

    def getActionType(self):
        return self.action_types[self.action_type]