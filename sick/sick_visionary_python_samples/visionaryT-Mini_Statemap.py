#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This sample visualizes the available state maps. For each map a different image is created.
In the individual stat maps you can see which pixels are filtered out by which filter configuration.

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

import matplotlib.pyplot as plt
import numpy as np

from common.Control import Control
from common.Stream import Streaming
from common.Streaming import Data
from common.Streaming.BlobServerConfiguration import BlobClientConfig

# === Device specific protocol & control_port mapping ===
# Visionary-T Mini CX      => CoLa2 / Port 2122
# handle argument parsing from cmd arguments
parser = argparse.ArgumentParser(description="Exemplary data reception from SICK Visionary devices.")
parser.add_argument('-i', '--ipAddress', required=False, type=str,
                    default="192.168.1.10", help="The ip address of the device.")
parser.add_argument('-p', '--protocol', required=False, choices=['ColaB', 'Cola2'],
                    default="Cola2", help="The SICK CoLa protocol version.")
parser.add_argument('-c', '--control-port', required=False, type=int,
                    default=2122, help="The control port to change settings.")
parser.add_argument('-s', '--streaming-port', required=False, type=int,
                    default=2114, help="The tcp port of the data channel.")
args = parser.parse_args()

# connect to the device and login
deviceControl = Control(ipAddress=args.ipAddress, protocol=args.protocol, control_port=args.control_port)

# open connection to device
deviceControl.open()
deviceControl.login(Control.USERLEVEL_SERVICE, 'CUST_SERV')

# streaming settings:
streamingSettings = BlobClientConfig()
streamingSettings.setTransportProtocol(deviceControl, streamingSettings.PROTOCOL_TCP)
streamingSettings.setBlobTcpPort(deviceControl, args.streaming_port)

# start streaming
streaming_device = Streaming(args.ipAddress, args.streaming_port)
streaming_device.openStream()

# logout after settings have been done
deviceControl.logout()

myData = Data.Data()

# Names of the state maps
mapNames = [
    'Isolated pixel filter',
    'Remission based filter lower threshold',
    'Remission based filter upper threshold',
    'Distance based filter lower threshold',
    'Distance based filter upper threshold',
    'Ambiguity based filter ',
    'Intensity based filter lower threshold',
    'Intensity based filter upper threshold',
    'Saturated pixel'
]

# convert and visualize the state map
streaming_device.getFrame()
wholeFrame = streaming_device.frame
myData.read(wholeFrame)

if myData.hasDepthMap:
    print("Frame number: {}".format(myData.depthmap.frameNumber))

    numCols = myData.cameraParams.width
    numRows = myData.cameraParams.height
    channels = 16

    # Get state map
    statemap = np.array(myData.depthmap.confidence, dtype=np.uint16)
    statemap = statemap.reshape([numRows, numCols])

    # Convert image to bitwise map
    xshape = list(statemap.shape)
    statemap = statemap.reshape([-1, 1])
    mask = 2 ** np.arange(channels, dtype=statemap.dtype).reshape([1, channels])
    maps = (statemap & mask).astype(bool).astype(int).reshape(xshape + [channels])

    # Init plot
    rows = 3
    columns = 3
    fig = plt.figure(figsize=(16, 9))
    fig.suptitle("State Maps")

    # Visualize each state map
    for mapName, state_index, i in zip(mapNames, range(7, maps.shape[-1] + 1), range(len(mapNames))):
        fig.add_subplot(rows, columns, i+1)
        plt.imshow(maps[..., state_index], cmap="gray")
        plt.title(mapName)
    plt.tight_layout()
    plt.show()

streaming_device.closeStream()
