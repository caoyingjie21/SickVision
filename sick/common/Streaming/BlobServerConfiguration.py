# -*- coding: utf-8 -*-
"""
Implementation of BLOB client config.

Author: GBC09 / BU05 / SW
SICK AG, Waldkirch
email: techsupport0905@sick.de

Copyright note: Redistribution and use in source, with or without modification, are permitted.

Liability clause: THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import logging
import struct

from common.Control import logger


class BlobClientConfig:
    """class for the client-side configuration of the BLOB transfer"""
    def __init__(self):
        self.PROTOCOL_TCP = 0  # same number as for ENUM in CID
        self.PROTOCOL_UDP = 1  # same number as for ENUM in CID

    def setTransportProtocol(self, cntrChan, protocol):
        if protocol >= self.PROTOCOL_TCP and protocol <= self.PROTOCOL_UDP:
            cntrChan.writeVariable(b"BlobTransportProtocolAPI", struct.pack(">B", protocol))
        else:
            logger.error("ERROR: unknown protocol parameter")

    def getTransportProtocol(self, cntrChan):
        tmp = cntrChan.readVariable(b"BlobTransportProtocolAPI")
        return struct.unpack(">B", tmp)[0]

    def setBlobTcpPort(self, cntrChan, tcpPort):
        if (tcpPort >= 1025) and (tcpPort <= 65535):
            cntrChan.writeVariable(b"BlobTcpPortAPI", struct.pack(">H", tcpPort))
        else:
            logger.error("ERROR: the TCP port must be a value between 1025 and 65535!")

    def getBlobTcpPort(self, cntrChan):
        tmp = cntrChan.readVariable(b"BlobTcpPortAPI")
        return struct.unpack(">H", tmp)[0]

    def setBlobUdpReceiverPort(self, cntrChan, receiverPort):
        if receiverPort >= 1025 and receiverPort <= 65535:
            cntrChan.writeVariable(b"BlobUdpReceiverPortAPI", struct.pack(">H", receiverPort))
        else:
            logger.error("ERROR: the receiver port must be a value between 1025 and 65535!")

    def getBlobUdpReceiverPort(self, cntrChan):
        tmp = cntrChan.readVariable(b"BlobUdpReceiverPortAPI")
        return struct.unpack(">H", tmp)[0]

    def setBlobUdpReceiverIP(self, cntrChan, receiverIP):
        cntrChan.writeVariable(b"BlobUdpReceiverIPAPI", cntrChan.pack_flexstring(receiverIP.encode('utf-8')))

    def getBlobUdpReceiverIP(self, cntrChan):
        tmp = cntrChan.readVariable(b"BlobUdpReceiverIPAPI")
        offset = 0
        return self.unpack_flexstring_from(tmp, offset)[0]

    def setBlobUdpControlPort(self, cntrChan, controlPort):
        if controlPort >= 1025 and controlPort <= 65535:
            cntrChan.writeVariable(b"BlobUdpControlPortAPI", struct.pack(">H", controlPort))
        else:
            logger.error("ERROR: the control port must be a value between 1025 and 65535!")

    def getBlobUdpControlPort(self, cntrChan):
        tmp = cntrChan.readVariable(b"BlobUdpControlPortAPI")
        return struct.unpack(">H", tmp)[0]

    def setBlobUdpMaxPacketSize(self, cntrChan, maxPacketSize):
        if maxPacketSize >= 100 and maxPacketSize <= 65535:
            cntrChan.writeVariable(b"BlobUdpMaxPacketSizeAPI", struct.pack(">H", maxPacketSize))
        else:
            logger.error("ERROR: the maximal UDP packet size must be a value between 1025 and 65535!")

    def getBlobUdpMaxPacketSize(self, cntrChan):
        tmp = cntrChan.readVariable(b"BlobUdpMaxPacketSizeAPI")
        return struct.unpack(">H", tmp)[0]

    def setBlobUdpIdleTimeBetweenPackets(self, cntrChan, timeBetweenPackets):
        if timeBetweenPackets >= 0 and timeBetweenPackets <= 10000:
            cntrChan.writeVariable(b"BlobUdpIdleTimeBetweenPacketsAPI", struct.pack(">H", timeBetweenPackets))
        else:
            logging.error("ERROR: the value for the time between packets must be a value between 0 and 10000!")

    def getBlobUdpIdleTimeBetweenPackets(self, cntrChan):
        tmp = cntrChan.readVariable(b"BlobUdpIdleTimeBetweenPacketsAPI")
        return struct.unpack(">H", tmp)[0]

    def setBlobUdpHeartbeatInterval(self, cntrChan, heartBeatInterval):
        if heartBeatInterval >= 0 and heartBeatInterval <= 10000000:
            cntrChan.writeVariable(b"BlobUdpHeartbeatInterval", struct.pack(">I", heartBeatInterval))
        else:
            logging.error("ERROR: the TCP port must be a value between 0 and 10000000!")

    def getBlobUdpHeartbeatInterval(self, cntrChan):
        tmp = cntrChan.readVariable(b"BlobUdpHeartbeatInterval")
        return struct.unpack(">I", tmp)[0]

    def setBlobUdpHeaderEnabled(self, cntrChan, headerEnabled):
        cntrChan.writeVariable(b"BlobUdpHeaderEnabled", struct.pack(">?", headerEnabled))

    def isBlobUdpHeaderEnabled(self, cntrChan):
        tmp = cntrChan.readVariable(b"BlobUdpHeaderEnabled")
        return struct.unpack(">?", tmp)[0]

    def setBlobUdpFecEnabled(self, cntrChan, fecEnabled):
        cntrChan.writeVariable(b"BlobUdpFECEnabled", struct.pack(">?", fecEnabled))

    def isBlobUdpFecEnabled(self, cntrChan):
        tmp = cntrChan.readVariable(b"BlobUdpFECEnabled")
        return struct.unpack(">?", tmp)[0]

    def setBlobUdpAutoTransmit(self, cntrChan, autoTransmit):
        cntrChan.writeVariable(b"BlobUdpAutoTransmit", struct.pack(">?", autoTransmit))

    def isBlobUdpAutoTransmit(self, cntrChan):
        tmp = cntrChan.readVariable(b"BlobUdpAutoTransmit")
        return struct.unpack(">?", tmp)[0]