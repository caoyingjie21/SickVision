# -*- coding: utf-8 -*-
"""
This function saves depth information as a PNG.The script automatically detects
the type of data (TOF or Stereo) and saves accordingly

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

import os.path
import numpy as np
from skimage import io

def saveDepthToPng(path, distData, intsData, cnfiData, camParams, frameNo, isStereo):
    numRows = camParams.height
    numCols = camParams.width
    if isStereo:
        # ========== Z-map ==========
        zmapData = distData

        # Save Z-map as *.png-file
        zmapDataArray = np.uint16(np.reshape(zmapData, (numRows, numCols)))
        io.imsave(os.path.join(path, "z_map_image{}.png".format(frameNo)), zmapDataArray, check_contrast=False)

        # ========== RGBA image ==========
        rgbaData = intsData

        # Save RGBA image as *.png-file
        rgbaDataArray = np.uint32(np.reshape(rgbaData, (numRows, numCols)))
        rgbaDataArray = np.frombuffer(rgbaDataArray, np.uint8)
        rgbaDataArray = np.reshape(rgbaDataArray, (numRows, numCols, 4))

        io.imsave(os.path.join(path, "rgba_image{}.png".format(frameNo)), rgbaDataArray, check_contrast=False)

        # ========== Statemap ==========
        statemapData = cnfiData

        # Save Statemap as *.png-file
        statemapDataArray = np.uint16(np.reshape(statemapData, (numRows, numCols)))
        io.imsave(os.path.join(path, "statemap_image{}.png".format(frameNo)), statemapDataArray, check_contrast=False)

        # Apply the Statemap to the Z-map
        zmapData_with_statemap = zmapDataArray.copy()
        for i in range(0, numRows):
            for j in range(0, numCols):
                if (statemapDataArray[i][j] != 0):
                    zmapData_with_statemap[i][j] = 0 # Set unvalid pixels to lowest value

        # Save RGBA image with applied statemap as *.png-file
        io.imsave(os.path.join(path, "z_map_image_with_applied_statemap{}.png".format(frameNo)), zmapData_with_statemap, check_contrast=False)

    else:
        # ========== Distance ==========
        zmapData = distData

        # Save Z-map as *.png-file
        zmapDataArray = np.uint16(np.reshape(distData, (numRows, numCols)))
        io.imsave(os.path.join(path, "distance_image{}.png".format(frameNo)), zmapDataArray, check_contrast=False)

        # ========== Intensity image ==========

        # Save intensity image as *.png-file
        intensityDataArray = np.uint16(np.reshape(intsData, (numRows, numCols)))
        io.imsave(os.path.join(path, "intensity_image{}.png".format(frameNo)), intensityDataArray, check_contrast=False)

        # ========== Statemap ==========
        statemapData = cnfiData

        # Save Statemap as *.png-file
        statemapDataArray = np.uint16(np.reshape(statemapData, (numRows, numCols)))
        io.imsave(os.path.join(path, "statemap_image{}.png".format(frameNo)), statemapDataArray, check_contrast=False)
