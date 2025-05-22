# -*- coding: utf-8 -*-
"""
This module loads SSR files and returns the data as numpy arrays.

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

import numpy as np
import zipfile
from struct import unpack_from
from struct import calcsize
import logging
from common.Streaming import Data
from common.UnitConversion import convertDistanceToMM

tmpDir = "temp_folder"

def readSsrData(filename, startFrame, nFrames, convertToMM = True):
    """
    startFrame:  First frame that is read from the SSR file. Frame numbering starts with zero (0)
    nFrames:     Number of frames read from the SSR file. If not enough frames remain in the file, the available frames are read.
    convertToMM: If this is True, depthmap data is converted to millimeters after reading (can result in floating point values).
                    If this is False, the raw (integer) depth data from the device is used:
                    - Tenth millimeters for Visionary S
                    - Quarter millimeters for Visionary T Mini
                    - Millimeters for Visionary T
    """

    archive = zipfile.ZipFile(filename, 'r')

    xmlFile = archive.read('main.xml')
    myXMLParser = Data.XMLParser()
    logging.info("Parsing xml segment...")
    myXMLParser.parse(xmlFile)

    logging.info("Revision: {}".format(myXMLParser.revision))

    myCamParams = Data.CameraParameters(width=myXMLParser.imageWidth,
                                 height=myXMLParser.imageHeight,
                                 cam2worldMatrix=myXMLParser.cam2worldMatrix,
                                 fx=myXMLParser.fx, fy=myXMLParser.fy,
                                 cx=myXMLParser.cx, cy=myXMLParser.cy,
                                 k1=myXMLParser.k1, k2=myXMLParser.k2,
                                 f2rc=myXMLParser.f2rc)

    # extracting data from the binary segment (distance, intensity
    # and confidence).
    numBytesDistance = myXMLParser.imageHeight * \
                       myXMLParser.imageWidth * \
                       myXMLParser.numBytesPerDistanceValue
    numBytesIntensity = myXMLParser.imageHeight * \
                        myXMLParser.imageWidth * \
                        myXMLParser.numBytesPerIntensityValue
    numBytesConfidence = myXMLParser.imageHeight * \
                         myXMLParser.imageWidth * \
                         myXMLParser.numBytesPerConfidenceValue

    try:
        numBytesFrameNumber = myXMLParser.numBytesFrameNumber
        numBytesQuality = myXMLParser.numBytesQuality
        numBytesStatus = myXMLParser.numBytesStatus
    except AttributeError:
        numBytesFrameNumber = 0
        numBytesQuality = 0
        numBytesStatus = 0

    availableFrames = myXMLParser.availableFrames
    distType = myXMLParser.distType
    intsType = myXMLParser.intsType
    try:
        cnfiType = myXMLParser.confType
    except AttributeError:
        cnfiType = None

    if startFrame < 0 or startFrame >= availableFrames:
        logging.warning("Requested to read SSR file starting at frame %d. File only contains frame 0 to %d. Starting to read at frame 0 instead.", startFrame, availableFrames-1)
        startFrame = 0
    if nFrames <= 0 or (nFrames + startFrame) > availableFrames:
        logging.warning("Requested to read %d frames, starting at frame %d, which is invalid. Reading all remaining frames instead (frame %d to %d).", 
            nFrames, startFrame, startFrame, availableFrames-1)
        nFrames = availableFrames - startFrame

    #myBinaryParser = Data.BinaryParser() # TODO: use the same binary parser
    binFileName = myXMLParser.binFileName
    logging.debug("Binary file name: %s", binFileName)

    file = archive.open('data/'+binFileName,'r')

    # forward to start frame
    distData = []
    intsData = []
    cnfiData = []

    nRows = myCamParams.height
    nCols = myCamParams.width

    logging.info("Reading binary segment...")

    binFrameLength = unpack_from("<I",file.read(4))[0]
    # emulate rewind(), repeat open()
    file.close()
    file = archive.open('data/'+binFileName,'r')

    ssrFixup = False
    if binFrameLength != (myXMLParser.getFrameLengthDepthMap() + 8): # 4 bytes CRC, 4 bytes length (tail)
        logging.debug("Do ssr fixup for broken stereo format")
        ssrFixup = True

    skipLength = binFrameLength + 4 # 4 bytes length (head)

    if ssrFixup:
        skipLength = int(binFrameLength / availableFrames)

    # skip frames
    logging.debug("Skipping first %u frames, each has a length of %u bytes:", startFrame, skipLength)

    if ssrFixup:
        file.read(4) # skip length before first frame

    file.read(skipLength * startFrame)

    for i in range(0, nFrames, 1):
        logging.debug("Start reading frame: %d", i)

        if not ssrFixup:
            # TOF: skip framelength
            unpack_from("<I",file.read(4))

        timestamp = unpack_from("<Q",file.read(8))
        version   = unpack_from("<H",file.read(2))
        #data.logTimeStamp(timeStamp)
        logging.debug("Format version: %s", version[0])

        if version[0] == 2:
            assert numBytesFrameNumber == 4
            assert numBytesQuality == 1
            assert numBytesStatus == 1
            format2BlockSize = calcsize('<IBB')
            (frameNumber, quality, status) = unpack_from('<IBB', file.read(format2BlockSize))
            logging.debug("FrameNumber: %s", frameNumber)
            logging.debug("Data quality: %s", quality)
            logging.debug("Device status: %s", status)

        buffer_dist = file.read(numBytesDistance)
        buffer_ints = file.read(numBytesIntensity)
        buffer_cnfi = file.read(numBytesConfidence)

        distData.append(np.reshape(np.frombuffer(buffer_dist, distType), (nRows, nCols)))
        intsData.append(np.reshape(np.frombuffer(buffer_ints, intsType), (nRows, nCols)))
        if cnfiType != None:
            cnfiData.append(np.reshape(np.frombuffer(buffer_cnfi, cnfiType), (nRows, nCols)))
        else:
            cnfiData = None

        if not ssrFixup:
            # TOF: skip crc and framelength
            unpack_from("<I",file.read(4))
            unpack_from("<I",file.read(4))

    file.close()

    if convertToMM:
        distData = convertDistanceToMM(distData, myXMLParser)

    return distData, intsData, cnfiData, myCamParams, myXMLParser.stereo
