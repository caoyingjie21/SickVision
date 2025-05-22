# -*- coding: utf-8 -*-
"""
Implementation of AutoIp scan.

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
import platform
import psutil
import random
import socket
import struct
import time
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

PAYLOAD_OFFSET = 16  # offset where data starts in the response

def to_hex(str_value):
    """ just to produce a readable output of the device responses """
    return ' '.join(hex(x) for x in str_value)

class AutoIpDevice:
    def __init__(self, macAddr):
        self.macAddr = macAddr
        self.items = {}

    def addItem(self, key, value, ro):
        self.items[key] = (value, ro)


class AutoIp:
    def __init__(self, serverIp = '192.168.1.1', serverNetMask = '255.255.255.0'):
        self.AUTOIP_PORT = 30718  # see: Sopas AutoIp Specification
        self.TIMEOUT = 1.1  # as in spec, devices may reply within 1020ms
        self.serverIp = serverIp
        self.serverNetMask = serverNetMask
        if platform.system() == 'Linux':
            addrs = psutil.net_if_addrs()
            for a in addrs:
                for c in addrs[a]:
                    if c.address == serverIp:
                        self.serverDevice = a
                        break
                else:
                    continue
                break

    def openSocket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Set a timeout so the socket does not block
        # indefinitely when trying to receive data.
        sock.settimeout(self.TIMEOUT)
        if platform.system() == 'Linux':
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, self.serverDevice.encode('utf8'))
            sock.bind(('', self.AUTOIP_PORT)) # bind on all IPs (interfaces) since linux ip stack does not forwar broadcast traffic to specific IP
        else:
            sock.bind((self.serverIp, self.AUTOIP_PORT))
        return sock

    def generateTeleId(self):
        random.seed(time.time())
        return struct.pack('>I', random.randint(0,0xffffffff))

    def decodeXmlResponse(self, rpl):
        '''Decode a CoLa-A response packet (based on XML)'''

        net_scan_result = ET.fromstring(rpl)
        dev = AutoIpDevice(net_scan_result.get('MACAddr'))
        dev.addItem('COLA_VER', '1', 'TRUE')
        for item in net_scan_result.iter('Item'):
            dev.addItem(item.get('key'), item.get('value'), item.get('readonly'))
        return dev

    def decodeBinaryResponse(self, rpl):
        '''Decode a binary (CoLa-B / 2) response'''

        offset = 0
        macAddr = None
        configTime = None
        subNet = None
        stdGw = None
        ipAddr = None

        deviceInfoVersion, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2

        cidNameLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        cidName = rpl[offset:offset + cidNameLen]
        offset += cidNameLen
        logger.debug("cidName: {}".format(cidName))

        cidMajorVersion, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        cidMinorVersion, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        cidPatchVersion, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        cidBuildVersion, = struct.unpack('>L', rpl[offset:offset + 4])
        offset += 4
        cidVersionClassifier, = struct.unpack('>B', rpl[offset:offset + 1])
        offset += 1
        logger.debug(
            "CidVersion: {}.{}.{}.{}{}".format(cidMajorVersion, cidMinorVersion, cidPatchVersion, cidBuildVersion,
                                               cidVersionClassifier))

        deviceState, = struct.unpack('>B', rpl[offset:offset + 1])
        offset += 1

        reqUserAction, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2

        deviceNameLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        deviceName = rpl[offset:offset + deviceNameLen]
        offset += deviceNameLen
        logger.debug("deviceName: {}".format(deviceName))

        appNameLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        appName = rpl[offset:offset + appNameLen]
        offset += appNameLen
        logger.debug("appName: {}".format(appName))

        projNameLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        projName = rpl[offset:offset + projNameLen]
        offset += projNameLen
        logger.debug("projName: {}".format(projName))

        serialNumLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        serialNum = rpl[offset:offset + serialNumLen]
        offset += serialNumLen
        logger.debug("serialNum: {}".format(serialNum))

        typeCodeLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        typeCode = rpl[offset:offset + typeCodeLen]
        offset += typeCodeLen
        logger.debug("typeCode: {}".format(typeCode))

        firmwareVersionLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        firmwareVersion = rpl[offset:offset + firmwareVersionLen]
        offset += firmwareVersionLen
        logger.debug("firmwareVersion: {}".format(firmwareVersion))

        orderNumberLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        orderNumber = rpl[offset:offset + orderNumberLen]
        offset += orderNumberLen
        logger.debug("orderNumber: {}".format(orderNumber))

        # unused: flags, = struct.unpack('>B', rpl[offset:offset + 1])
        offset += 1

        auxArrayLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        logger.debug("auxArrayLen: {}".format(auxArrayLen))
        for i in range(auxArrayLen):
            key = rpl[offset:offset + 4]
            offset += 4
            innerArrayLen, = struct.unpack('>H', rpl[offset:offset + 2])
            offset += 2
            logger.debug("  key: {}, innerArrayLen: {}".format(key, innerArrayLen))
            for j in range(innerArrayLen):
                v, = struct.unpack('>B', rpl[offset:offset + 1])
                offset += 1
                logger.debug("    v: {}".format(hex(v)))

        scanIfLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        logger.debug("scanIfLen: {}".format(scanIfLen))
        for i in range(scanIfLen):
            ifaceNum, = struct.unpack('>H', rpl[offset:offset + 2])
            offset += 2
            ifaceNameLen, = struct.unpack('>H', rpl[offset:offset + 2])
            offset += 2
            ifaceName = rpl[offset:offset + ifaceNameLen]
            offset += ifaceNameLen
            logger.debug("  ifaceNum: {}, ifaceName: {}".format(ifaceNum, ifaceName))

        comSettingsLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        logger.debug("comSettingsLen: {}".format(comSettingsLen))
        dhcp = "none"
        for i in range(comSettingsLen):
            key = rpl[offset:offset + 4]
            offset += 4
            innerArrayLen, = struct.unpack('>H', rpl[offset:offset + 2])
            offset += 2
            logger.debug("  key: {}, innerArrayLen: {}".format(key, innerArrayLen))
            if key == b"EMAC":
                macAddr = rpl[offset:offset + 6]
                offset += 6
                logger.debug("  EMAC: {}".format("%02x:%02x:%02x:%02x:%02x:%02x" % struct.unpack("BBBBBB", macAddr)))
            elif key == b"EIPa":
                ipAddr = rpl[offset:offset + 4]
                offset += 4
                logger.debug("  EIPa: {}".format("%u.%u.%u.%u" % struct.unpack("BBBB", ipAddr)))
            elif key == b"ENMa":
                subNet = rpl[offset:offset + 4]
                offset += 4
                logger.debug("  ENMa: {}".format("%u.%u.%u.%u" % struct.unpack("BBBB", ipAddr)))
            elif key == b"EDGa":
                stdGw = rpl[offset:offset + 4]
                offset += 4
                logger.debug("  EDGa: {}".format("%u.%u.%u.%u" % struct.unpack("BBBB", ipAddr)))
            elif key == b"EDhc":
                dhcp = rpl[offset:offset + 1]
                offset += 1
                logger.debug("  EDhc: {}".format(dhcp))
            elif key == b"ECDu":
                configTime, = struct.unpack('>L', rpl[offset:offset + 4])
                offset += 4
                logger.debug("  ECDu: {}".format(configTime))
            else:
                for j in range(innerArrayLen):
                    v, = struct.unpack('>B', rpl[offset:offset + 1])
                    offset += 1
                    logger.debug("  v: {}".format(hex(v)))

        endPointsLen, = struct.unpack('>H', rpl[offset:offset + 2])
        offset += 2
        logger.debug("endPointsLen: {}".format(endPointsLen))
        ports = []
        for i in range(endPointsLen):
            colaVersion, = struct.unpack('>B', rpl[offset:offset + 1])
            offset += 1
            logger.debug("colaVersion: {}".format(colaVersion))
            innerArrayLen, = struct.unpack('>H', rpl[offset:offset + 2])
            offset += 2
            logger.debug("innerArrayLen: {}".format(innerArrayLen))
            for j in range(innerArrayLen):
                key = rpl[offset:offset + 4]
                offset += 4
                mostInnerArrayLen, = struct.unpack('>H', rpl[offset:offset + 2])
                offset += 2
                logger.debug("  key: {}, mostInnerArrayLen: {}".format(key, mostInnerArrayLen))
                if key == "DPNo":  # PortNumber [UInt]
                    p, = struct.unpack('>H', rpl[offset:offset + 2])
                    offset += 2
                    logger.debug("  DPNo: {}".format(p))
                    ports.append({"protocol": colaVersion, "port": p})
                else:
                    for k in range(mostInnerArrayLen):
                        v, = struct.unpack('>B', rpl[offset:offset + 1])
                        offset += 1
                        logger.debug("  v: {}".format(hex(v)))

        # try to fill device info so it's compatible
        # with old XML style replies and fits the
        # requirements for our tests
        dev = AutoIpDevice("%02x:%02x:%02x:%02x:%02x:%02x" % struct.unpack("BBBBBB", macAddr))
        dev.addItem('COLA_VER', '2', 'TRUE')
        dev.addItem('IPConfigDuration', str(configTime), 'TRUE')
        dev.addItem('IPAddress', "%u.%u.%u.%u" % struct.unpack("BBBB", ipAddr), 'FALSE')
        dev.addItem('IPMask', "%u.%u.%u.%u" % struct.unpack("BBBB", subNet), 'FALSE')
        dev.addItem('IPGateway', "%u.%u.%u.%u" % struct.unpack("BBBB", stdGw), 'FALSE')
        dev.addItem('DeviceType', "%s" % cidName.decode(), 'TRUE')

        hasDhcp = 'TRUE'
        if dhcp == "none":
            hasDhcp = 'FALSE'
        else:
            dhcpEnabled = 'FALSE'
            if dhcp == b'\x01':
                dhcpEnabled = 'TRUE'
            dev.addItem('DHCPClientEnabled', dhcpEnabled, 'FALSE')
        dev.addItem('HasDHCPClient', hasDhcp, 'TRUE')

        if len(ports) > 0:
            dev.addItem('HostPortNo', ports[0]["port"], 'TRUE')
        if len(ports) > 1:
            dev.addItem('AuxPortNo', ports[1]["port"], 'TRUE')

        return dev

    def scan(self):
        """ Sends an AutoIp brodcast and listen for responses.
            Return a list of AutoIpDevice
        """
        CMD_NETSCAN = b"\x10"
        RPL_NETSCAN = b"\x90"
        RPL_NETSCAN_COLA2 = b"\x95"

        try:
            server = self.openSocket()
            TELE_ID = self.generateTeleId()

            msg = CMD_NETSCAN
            msg += b"\x00"  # not defined / rfu
            msg += b"\x00\x08"  # for serverIp and serverNetMask
            msg += b"\xff\xff\xff\xff\xff\xff"  # mac == ff:ff:ff:ff:ff:ff per specification
            msg += TELE_ID
            msg += b"\x01\x00"  # 0x01 (Cloa Scan identifier) + 0x00 (RFU)
            msg += struct.pack('>4B', *[int(x) for x in self.serverIp.split('.')])
            msg += struct.pack('>4B', *[int(x) for x in self.serverNetMask.split('.')])

            server.sendto(msg, (b'<broadcast>', self.AUTOIP_PORT))
            logger.debug("broadcast sent! with telegram id: {}".format(to_hex(TELE_ID)))

            # send braodcast and gather replies
            replies = []
            macs = []
            try:
                while (1):
                    # maximum receive size, any possible
                    # net scan result should fit in this
                    rx = server.recv(4096)
                    logger.debug("received {} bytes".format(len(rx)))
                    if bytes([rx[0]]) == RPL_NETSCAN or bytes([rx[0]]) == RPL_NETSCAN_COLA2:
                        replyLength, = struct.unpack('>H', rx[2:4])
                        replyMac = rx[4:10]
                        replyTeleId = rx[10:14]
                        if replyTeleId == TELE_ID:
                            logger.debug("Reply-> len:{} mac:{} teleId:{}".format(replyLength, to_hex(replyMac),
                                                                                  to_hex(replyTeleId)))
                            if not replyMac in macs:
                                macs.append(replyMac)
                                if bytes([rx[0]]) == RPL_NETSCAN:
                                    replies.append(rx[PAYLOAD_OFFSET:PAYLOAD_OFFSET + replyLength])
                                elif bytes([rx[0]]) == RPL_NETSCAN_COLA2:
                                    # use TELE_ID as marker that this is a binary coded reply
                                    replies.append(TELE_ID + rx[PAYLOAD_OFFSET:PAYLOAD_OFFSET + replyLength])
                    time.sleep(0.01)
            except socket.timeout:
                logger.debug("No more answers after {} seconds".format(self.TIMEOUT))

            # parse replies and return dict with results
            foundDevices = []
            for rpl in replies:
                if rpl[0:4] == TELE_ID:
                    foundDevices.append(self.decodeBinaryResponse(rpl[len(TELE_ID):]))
                else:
                    foundDevices.append(self.decodeXmlResponse(rpl))
            return foundDevices

        except Exception as e:
            logger.debug("AutoIP scan: General error occurred: {}".format(str(e)))

        finally:
            server.close()

    def assign(self, dstMac, colaVer, ipAddr, ipMask='255.255.255.0', ipGw='0.0.0.0', dhcp=False):
        CMD_IPCONFIG = b"\x11"
        RPL_IPCONFIG = b"\x91"

        # TODO: add validation of arguments

        if int(colaVer) == 1:
            top = ET.Element('IPconfig')
            top.set('MACAddr', dstMac)
            ET.SubElement(top, 'Item', {'key': 'IPAddress', 'value': ipAddr})
            ET.SubElement(top, 'Item', {'key': 'IPMask', 'value': ipMask})
            ET.SubElement(top, 'Item', {'key': 'IPGateway', 'value': ipGw})
            ET.SubElement(top, 'Item', {'key': 'DHCPClientEnabled', 'value': str(dhcp).upper()})
            payload = b'<?xml version="1.0" encoding="UTF-8"?>'
            payload += ET.tostring(top)
        elif int(colaVer) == 2:
            payload = socket.inet_aton(ipAddr)
            payload += socket.inet_aton(ipMask)
            payload += socket.inet_aton(ipGw)
            payload += struct.pack('>B', dhcp)
        else:
            raise RuntimeError("Parameter colaVer must be either 1 or 2 but is: {}".format(colaVer))

        try:
            server = self.openSocket()
            TELE_ID = self.generateTeleId()

            msg = CMD_IPCONFIG
            msg += b"\x00"  # not defined / rfu
            msg += struct.pack('>H', len(payload))
            msg += struct.pack('>6B', *[int(x, 16) for x in dstMac.split(':')])
            msg += TELE_ID
            msg += b"\xff\xff"  # not defined / rfu
            msg += payload

            server.sendto(msg, (b'<broadcast>', self.AUTOIP_PORT))
            logger.debug("IPCONFIG message sent! with telegram id: {}".format(to_hex(TELE_ID)))

            replies = []
            macs = []
            try:
                while (1):
                    # maximum receive size, any possible
                    # net scan result should fit in this
                    rx = server.recv(4096)
                    logger.debug("received {} bytes".format(len(rx)))
                    if rx[0] == RPL_IPCONFIG:
                        replyLength, = struct.unpack('>H', rx[2:4])
                        replyMac = rx[4:10]
                        replyTeleId = rx[10:14]
                        if replyTeleId == TELE_ID:
                            logger.debug(
                                "RPL_IPCONFIG -> len:{} mac:{} teleId:{}".format(replyLength, to_hex(replyMac),
                                                                                 to_hex(replyTeleId)))
                            if not replyMac in macs:
                                macs.append(replyMac)
                                replies.append(rx[PAYLOAD_OFFSET:PAYLOAD_OFFSET + replyLength])
                    time.sleep(0.01)
            except socket.timeout:
                logger.debug("No more RPL_IPCONFIG answers after {} seconds".format(self.TIMEOUT))

        finally:
            server.close()

        # TODO: how to check replies? how to differ between
        #       XML (COLA1) and binary (COLA2) reply
