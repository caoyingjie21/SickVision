#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This sample converts depth information to point cloud data and saves it as PLY.
Moreover, it saves the sensor data (depth, intensity,..) as PNG images. All the output 
is written to a folder named VisionaryToPointCloud.
The user can choose whether to convert a stream of data from a sensor or from
an SSR recording via command line parameters. The script automatically detects
the type of data (TOF or Stereo).
The user can choose via the command line parameters if depth data is converted to millimeters
or if the following raw device output is used:
* Millimeters for Visionary T
* Quarter millimeters for Visionary T Mini
* Tenth millimeters for Visionary S

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

from common.Stream import Streaming
from common.Streaming import Data
from common.Control import Control
from common.PointCloud.PointCloud import convertToPointCloud, writePointCloudToFile
from common.data_io.SsrLoader import readSsrData
from common.data_io.DepthToImage import saveDepthToPng
from common.Streaming.BlobServerConfiguration import BlobClientConfig
import os
import sys

# === Device specific protocol & control_port mapping ===
# Visionary-T CX / AG / DT => CoLaB / Port 2112
# Visionary-S CX           => CoLaB / Port 2112
# Visionary-T Mini CX      => CoLa2 / Port 2122
# handle argument parsing from cmd arguments
parser = argparse.ArgumentParser(description="Converts depth information to point cloud data and saves it as PLY")
parser.add_argument('-i', '--ipAddress', required=False, type=str,
                    default="192.168.1.10", help="The ip address of the device.")
parser.add_argument('-p', '--protocol', required=False, choices=['ColaB', 'Cola2'],
                    default="ColaB", help="The SICK CoLa protocol version.")
parser.add_argument('-c', '--control-port', required=False, type=int,
                    default=2112, help="The control port to change settings.")
parser.add_argument('-s', '--streaming-port', required=False, type=int,
                    default=2114, help="The tcp port of the data channel.")
parser.add_argument('-r', '--source', required=False, type=str,
                    default='sensor', help="The source of data (sensor/SSR)")
parser.add_argument('-f', '--filename', required=False, type=str,
                    default="sample_data/visionaryS_sample.ssr", help="The filename of the SSR file")
parser.add_argument('-l', '--start-frame', required=False, type=int,
                    default=0, help="The frame to start processing the SSR file from. The first available frame has number 0.")
parser.add_argument('-m', '--frames-to-process', required=False, type=int,
                    default=0, help="The number of frames to process from the SSR file. 0 means all frames in SSR file.")
parser.add_argument('-o', '--output-millimeters', required=False, type=bool,
                    default=True, help="Converts data for saved depth map and point cloud to mm.\n \
                        Otherwise raw device output is used (mm for Visionary T, quarter mm for Visionary T Mini, tenth mm for Visionary S")
args = parser.parse_args()

# directory to save the output in 
directory = 'VisionaryToPointCloud'
try:
    os.makedirs(directory, exist_ok=True)
except OSError as e:
    sys.exit("Can't create directory ({}): {}".format(e.strerror, directory))

#check the source of data sensor or SSR recordings
if args.source == "sensor":

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

    # For the emulator, time intensive tasks (e. g. converting to point cloud) should not be done in the image receiving loop
    # otherwise you may get an invalid checksum. With a real device this limitation doesn't exist.

    # Receive images:
    nFrames = 3
    frameData = []
    for i in range(nFrames):
        frameData.append(Data.Data())
        streaming_device.getFrame()
        frameData[-1].read(streaming_device.frame, args.output_millimeters)
    streaming_device.closeStream()

    # Process images:
    for i in range(nFrames):
        if frameData[i].hasDepthMap:
            print("=== Converting image ({}) ===".format(i))
            print("Frame number: {}".format(frameData[i].depthmap.frameNumber))

            worldCoordinates,distData = convertToPointCloud(frameData[i].depthmap.distance,
                                                            frameData[i].depthmap.intensity,
                                                            frameData[i].depthmap.confidence,
                                                            frameData[i].cameraParams, frameData[i].xmlParser.stereo)
            writePointCloudToFile(os.path.join(directory, "world_coordinates{}.ply".format(i)), worldCoordinates)

            saveDepthToPng(directory, distData, frameData[i].depthmap.intensity,
                            frameData[i].depthmap.confidence,
                            frameData[i].cameraParams, i,
                            frameData[i].xmlParser.stereo)

else:
    image_distance, image_intensity, image_confidence, CamParams, isStereo = readSsrData(args.filename,
                                                                                         args.start_frame,
                                                                                         args.frames_to_process,
                                                                                         args.output_millimeters)
    for i in range(len(image_distance)):
        print("=== Converting image ({}) ===".format(i))
        print("Frame number: {}".format(args.start_frame + i))

        worldCoordinates,_ = convertToPointCloud(image_distance[i], image_intensity[i], image_confidence[i], CamParams, isStereo)
        writePointCloudToFile(os.path.join(directory, "world_coordinates{}.ply".format(i)), worldCoordinates)

        saveDepthToPng(directory, image_distance[i], image_intensity[i], image_confidence[i], CamParams, i, isStereo)
