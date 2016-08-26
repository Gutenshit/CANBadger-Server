from PyQt4.QtCore import *

##
# use this to prevent exceptions when disconnecting signals
def gracefullyDisconnectSignal(t_signal):
        try:
            t_signal.disconnect()
        except TypeError:
            pass
