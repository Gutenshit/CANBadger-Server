from PyQt4.QtCore import *

import struct

class CanParser:
    ##
    # data is supposed to be a QByteArray
    @staticmethod
    def parseSingleFrame(data):
        # first 4 bytes are the timestamp in ticks
        tickCount = str((data[0:4]).toHex())
        id = str((data[4:6]).toHex())
        if len(data) > 6:
            length = struct.unpack('<B', data[6])
        payload = (data[7:]).toHex()
        return {'id': id, 'payload': payload}
