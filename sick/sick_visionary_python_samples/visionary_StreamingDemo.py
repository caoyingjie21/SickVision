#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script demonstrates how to retrieve data from a V3SCamera device. It
does not depend on the V3SCamera API, but the functionality is comparable.
Please have a look at the samples point cloud conversion examples in order
to get more elaborate examples (e.g. how to transform distance values into
a 3D point cloud).

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

import argparse
import socket
import struct
import traceback

from common.Control import Control
from common.Streaming import Data
from common.Stream import Streaming
from common.Streaming.BlobServerConfiguration import BlobClientConfig

# === Device specific protocol & control_port mapping ===
# Visionary-T CX / AG / DT => CoLaB / Port 2112
# Visionary-S CX           => CoLaB / Port 2112
# Visionary-T Mini CX      => CoLa2 / Port 2122
parser = argparse.ArgumentParser(description="Exemplary data reception from SICK Visionary devices.")
parser.add_argument('-i', '--ipAddress', required=False, type=str,
                    default="192.168.1.10", help="The ip address of the device.")
parser.add_argument('-r', '--ipAddressReceiver', required=False, type=str,
                    default="192.168.1.2", help="The ip address of the receiving PC (UDP only).")
parser.add_argument('-p', '--protocol', required=False, choices=['ColaB', 'Cola2'],
                    default="ColaB", help="The SICK Cola protocol version.")
parser.add_argument('-c', '--control_port', required=False, type=int,
                    default=2112, help="The control port to change settings.")
parser.add_argument('-s', '--streaming_port', required=False, type=int,
                    default=2114, help="The tcp port of the data channel.")
parser.add_argument('-t', '--transport_protocol', required=False, choices=['TCP', 'UDP'],
                    default="TCP", help="The transport protocol.")
args = parser.parse_args()

# create and open a control connection to the device
deviceControl = Control(args.ipAddress, args.protocol, args.control_port)
deviceControl.open()

# access the device via a set account to change settings
deviceControl.login(Control.USERLEVEL_SERVICE, 'CUST_SERV')

name, version = deviceControl.getIdent()

disableDMDataTransferInCleanup = False
if " AG " in name.decode('utf-8'):
    # Depth map data transfer is enabled if no data transfer (with corresponding data reduction)
    # was enabled on the device. Otherwise the AG device wouldn't stream any data.
    if not (    deviceControl.getDepthMapDataTransfer()
            or (deviceControl.getPolarDataTransfer()     and deviceControl.getPolarReduction())
            or (deviceControl.getCartesianDataTransfer() and deviceControl.getCartesianReduction()) ):
        disableDMDataTransferInCleanup = True
        deviceControl.enableDepthMapDataTransfer()

# streaming settings:
streamingSettings = BlobClientConfig()
streaming_device = None

# configure the data stream
#   the methods immediately write the setting to the device
if args.transport_protocol == "TCP":
    # set protocol and device port
    streamingSettings.setTransportProtocol(deviceControl, streamingSettings.PROTOCOL_TCP)
    streamingSettings.setBlobTcpPort(deviceControl, args.streaming_port)
    # start streaming
    streaming_device = Streaming(args.ipAddress, args.streaming_port)
    streaming_device.openStream()

elif args.transport_protocol == "UDP":
    # settings
    streamingSettings.setTransportProtocol(deviceControl, streamingSettings.PROTOCOL_UDP)  # UDP
    streamingSettings.setBlobUdpReceiverPort(deviceControl, args.streaming_port)
    streamingSettings.setBlobUdpReceiverIP(deviceControl, args.ipAddressReceiver)
    streamingSettings.setBlobUdpControlPort(deviceControl, args.streaming_port)
    streamingSettings.setBlobUdpMaxPacketSize(deviceControl, 1024)
    streamingSettings.setBlobUdpIdleTimeBetweenPackets(deviceControl, 10)  # in milliseconds
    streamingSettings.setBlobUdpHeartbeatInterval(deviceControl, 0)
    streamingSettings.setBlobUdpHeaderEnabled(deviceControl, True)
    streamingSettings.setBlobUdpFecEnabled(deviceControl, False) # forward error correction
    streamingSettings.setBlobUdpAutoTransmit(deviceControl, True)
    # open the datagram socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Bind the socket to the port
    server_address = (args.ipAddressReceiver, args.streaming_port)  # use empty hostname to listen on all adapters
    udp_socket.bind(server_address)

    udp_socket.settimeout(1)  # 1sec
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)  # 4 Megabyte of buffer size

# logout after settings have been done
deviceControl.logout()
deviceControl.startStream()

myData = Data.Data()

try:
    while True:
        if args.transport_protocol == "TCP":
            streaming_device.getFrame()
            wholeFrame = streaming_device.frame

            myData.read(wholeFrame)

            if myData.hasDepthMap:
                print()
                print("Data contains depth map data:")
                print("Frame number: {}".format(myData.depthmap.frameNumber))
                distanceData = list(myData.depthmap.distance)
                intensityData = list(myData.depthmap.intensity)
                confidenceData = list(myData.depthmap.confidence)

                numCols = myData.cameraParams.width
                numRows = myData.cameraParams.height

                midIndex = int(numCols * (numRows / 2) + numCols / 2)

                # The data maps vary on different devices types:
                # Visionary-T Mini
                if (name.decode('utf-8').find("Visionary-T Mini") != -1):
                    print("- center pixel distance: {:.2f}mm".format(distanceData[midIndex]))
                    print("- center pixel intensity: {:d}".format(intensityData[midIndex]))
                    print("- center pixel stateMap: {:016b}".format(confidenceData[midIndex]))
                # Visionary-S
                elif (name.decode('utf-8').find("Visionary-S") != -1):
                    colorMapRGBA = struct.unpack('4B', struct.pack('>I', intensityData[midIndex]))
                    print("- center pixel zMap: {:.2f}mm".format(distanceData[midIndex]))
                    print("- center pixel colorMap: R:{:d} G:{:d} B:{:d} A:{:d}".format(colorMapRGBA[0], colorMapRGBA[1], colorMapRGBA[2], colorMapRGBA[3]))
                    print("- center pixel stateMap: {:016b}".format(confidenceData[midIndex]))
                # Visionary-T
                elif (name.decode('utf-8').find("Visionary-T") != -1):
                    print("- center pixel distance: {:.2f}mm".format(distanceData[midIndex]))
                    print("- center pixel intensity: {:d}".format(intensityData[midIndex]))
                    print("- center pixel confidence: {:d}".format(confidenceData[midIndex]))
                else:
                    print("No correct device type connected!")

                maxValueUnsigned16Bit = 65535
                minValueUnsigned16Bit = 0
                minDistance = maxValueUnsigned16Bit
                maxDistance = minValueUnsigned16Bit
                meanDistance = 0.0
                validPixels = 0
                for i in range(numCols * numRows):
                    if (distanceData[i] > minValueUnsigned16Bit) and (distanceData[i] < maxValueUnsigned16Bit):
                        # valid data
                        minDistance = min(minDistance, distanceData[i])
                        maxDistance = max(maxDistance, distanceData[i])
                        meanDistance = meanDistance + distanceData[i]
                        validPixels = validPixels + 1
                if validPixels > 0:
                    meanDistance = meanDistance / validPixels
                    print("- mean distance: {:.2f}mm".format(meanDistance))
                    print("- min/max distance: {:.2f}mm/{:.2f}mm".format(minDistance, maxDistance))

            if myData.hasPolar2D:
                polarData = myData.polarData2D
                distanceData = polarData.distance
                print()
                print("Data contains polar scan data:")
                numScans = len(distanceData)
                print("- angle of first scan point: {:.2f}".format(polarData.angleFirstScanPoint))
                print("- angular resolution: {:.2f}".format(polarData.angularResolution))
                print("- number of scan points: {}".format(numScans))
                midIndex = int(numScans / 2)
                print("- distance in middle sector: {:.2f}mm".format(distanceData[midIndex]))
                print("- confidence in middle sector: {}".format(polarData.confidence[midIndex]))
                meanDistance = sum(distanceData) / numScans
                print(" -mean distance: {:.2f}mm".format(meanDistance))
                print("- min/max distance: {:.2f}mm/{:.2f}mm".format(min(distanceData), max(distanceData)))
                # Comparison to Sopas parameters
                startAngle = polarData.angleFirstScanPoint - (polarData.angularResolution / 2)
                endAngle = polarData.angleFirstScanPoint + (polarData.angularResolution * (numScans - 0.5))
                print("- start angle (Sopas): {:.2f}".format(startAngle))
                print("- end angle (Sopas): {:.2f}".format(endAngle))
                print("- number of sectors (Sopas): {}".format(numScans))

            if myData.hasCartesian:
                print()
                print("Data contains Cartesian point cloud:")
                cartesianData = myData.cartesianData
                print("- number of points: {}".format(cartesianData.numPoints))
                print("- points (x,y,z) in mm / confidence:")
                for x, y, z, conf in zip(cartesianData.x, cartesianData.y, cartesianData.z, cartesianData.confidence):
                    print("    {:+7.1f}, {:+7.1f}, {:+7.1f}, {:5.1f}%".format(x, y, z, conf))

        elif args.transport_protocol == "UDP":
            byte_arr = []
            myData, server = udp_socket.recvfrom(1024)
            print(f"========== new BLOB received ==========")
            print(f"Blob number: {((myData[1] << 8) | (myData[0]))}")
            print("server IP: {}".format(server[0]))
            print("server port: {}".format(server[1]))  # this is the port the server opens to transmit the data
            print("========================================")
            while(myData[6].to_bytes(1,byteorder='big') != b'\x80'): # FIN Flag of Statemap in header is set when new BLOB begins
                byte_arr.append(myData[14:])
                print(f"Fragment number: {((myData[2] << 8) | (myData[3]))}")
                myData, server = udp_socket.recvfrom(1024)
            print(f"Fragment number: {((myData[2] << 8) | (myData[3]))}")
            byte_arr.append(myData[14:]) # Payload begins at byteindex 14

        #break #uncomment if only one frame should be received
except KeyboardInterrupt:
    print("")
    print("Terminating")
except Exception as e:
    print(f"Exception -{e.args[0]}- occurred, check your device configuration")
    print(traceback.format_exc())

deviceControl.login(Control.USERLEVEL_AUTH_CLIENT, 'CLIENT')
if args.transport_protocol == "TCP":
    streaming_device.closeStream()
elif args.transport_protocol == "UDP":
    udp_socket.close()
    # restoring back to TCP mode
    streamingSettings.setTransportProtocol(deviceControl, streamingSettings.PROTOCOL_TCP)
    streamingSettings.setBlobTcpPort(deviceControl, args.streaming_port)

if disableDMDataTransferInCleanup:
    deviceControl.disableDepthMapDataTransfer()
deviceControl.logout()
