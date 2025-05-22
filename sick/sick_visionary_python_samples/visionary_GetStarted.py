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

from common.Control import Control
from common.Streaming import Data
from common.Stream import Streaming

# === Device specific protocol & control_port mapping ===
# Visionary-T CX / AG / DT => CoLaB / Port 2112
# Visionary-S CX           => CoLaB / Port 2112
# Visionary-T Mini CX      => CoLa2 / Port 2122
parser = argparse.ArgumentParser(description="Exemplary data reception from SICK Visionary devices.")
parser.add_argument('-i', '--ipAddress', required=False, type=str,
                    default="192.168.1.10", help="The ip address of the device.")
parser.add_argument('-p', '--protocol', required=False, choices=['ColaB', 'Cola2'],
                    default="ColaB", help="The SICK Cola protocol version.")
parser.add_argument('-c', '--control_port', required=False, type=int,
                    default=2112, help="The control port to change settings.")
parser.add_argument('-s', '--streaming_port', required=False, type=int,
                    default=2114, help="The tcp port of the data channel.")
args = parser.parse_args()

# create and open a control connection to the device
deviceControl = Control(args.ipAddress, args.protocol, args.control_port)
deviceControl.open()

name, version = deviceControl.getIdent()

print()
print("DeviceIdent: {} {}".format(name.decode('utf-8'), version.decode('utf-8')))
print()

# ------------ do some exemplary device settings -----------

# access the device via a set account to change settings
deviceControl.login(Control.USERLEVEL_SERVICE, 'CUST_SERV')

# The SOPAS variable 'integrationTimeUs' doesn't exist for Visionary-T Mini devices.
# Therefore we distinquish at this point based on the device type and set another variable.

# Visionary-T / Visionary-S
if (name.decode('utf-8').find("Visionary-T Mini") == -1):
    # set integration time to 3000 us
    oldIntegrationTime = deviceControl.getIntegrationTimeUs()
    deviceControl.setIntegrationTimeUs(3000)

    # check if integration time was set successfully/correctly
    newIntegrationTime = deviceControl.getIntegrationTimeUs()
    print("Previous integration time was: {}us".format(oldIntegrationTime))
    print("Changed the integration time to: {}us".format(newIntegrationTime))
# Visionary-T Mini
else:
    # set frame period to 50000 us
    oldFramePeriod = deviceControl.getFramePeriodUs()
    deviceControl.setFramePeriodUs(50000)

    # check if frame period was set successfully/correctly
    newFramePeriod = deviceControl.getFramePeriodUs()
    print("Previous frame period was: {}us".format(oldFramePeriod))
    print("Changed the frame period to: {}us".format(newFramePeriod))

# logout after settings have been done
deviceControl.logout()

# ------------ End of "some exemplary device settings" -----------

# the device starts stream automatically int the init process
deviceControl.initStream()
# stop streaming
deviceControl.stopStream()

deviceStreaming = Streaming(args.ipAddress, args.streaming_port)

# reopen the stream
deviceStreaming.openStream()
# send binary data to blob server to initialize the communication
deviceStreaming.sendBlobRequest()
# request camera to produce a single frame
deviceControl.singleStep()
# request the whole frame data
deviceStreaming.getFrame()

# access the new frame via the corresponding class attribute
wholeFrame = deviceStreaming.frame

# create new Data object to hold/parse/handle frame data
myData = Data.Data()
# parse frame data to Data object for further data processing
myData.read(wholeFrame)

if myData.hasDepthMap:
    print()
    print("Data contains depth map data:")
    distanceData = list(myData.depthmap.distance)
    print("Frame number: {}".format(myData.depthmap.frameNumber))

    numCols = myData.cameraParams.width
    numRows = myData.cameraParams.height

    midIndex = int(numCols * (numRows/2) + numCols/2)
    print("- center pixel distance: {:.2f}mm".format(distanceData[midIndex]))
    minDistance = 10000.0
    meanDistance = 0.0
    validPixels = 0
    maxDistance = 0.0

    for i in range(numCols * numRows):
        if (distanceData[i] > 0.0) and (distanceData[i] < 10000.0):
            # valid data
            minDistance = min(minDistance, distanceData[i])
            maxDistance = max(maxDistance, distanceData[i])
            meanDistance = meanDistance + distanceData[i]
            validPixels = validPixels + 1

    if validPixels > 0:
        meanDistance = meanDistance / validPixels
        print("- mean distance: {:.2f}mm".format(meanDistance))
        print("- min/max distance: {:.2f}mm/{:.2f}mm".format(minDistance, maxDistance))
    else:
        print("  Did not receive any valid pixel!")

deviceStreaming.closeStream()

# (re-)start image  acquisition
deviceControl.startStream()
deviceControl.close()
