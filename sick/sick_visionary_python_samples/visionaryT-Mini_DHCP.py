#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This sample shows how to setup DHCP via CoLa on the device and to revert the device IP back to static IP.

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
import struct
import time

from common.Control import Control
from common.Protocol.AutoIp import AutoIp

def activate_dhcp(deviceControl):
    # open connection to device
    deviceControl.open()
    deviceControl.login(Control.USERLEVEL_SERVICE, 'CUST_SERV')
    # setup ethernet mode to DHCP
    deviceControl.writeVariable(b'EIAddrMode', struct.pack('B', 1))
    time.sleep(1)
    deviceControl.invokeMethod(b'mEthUpdt')
    deviceControl.logout()

    deviceControl.login(Control.USERLEVEL_SERVICE, 'CUST_SERV')
    deviceControl.writeVariable(b'EIAddrMode', struct.pack('B', 1))
    deviceControl.logout()

    deviceControl.close()

def activate_static_ip(deviceControl, ip):
    # open connection to device
    deviceControl.open()
    deviceControl.login(Control.USERLEVEL_SERVICE, 'CUST_SERV')
    # setup ethernet mode to static IP
    deviceControl.writeVariable(b'EIIpAddr', struct.pack('>4B', *[int(x) for x in ip.split(".")]))
    deviceControl.writeVariable(b'EIAddrMode', struct.pack('B', 0))
    time.sleep(1)
    deviceControl.invokeMethod(b'mEthUpdt')
    deviceControl.logout()

    deviceControl.login(Control.USERLEVEL_SERVICE, 'CUST_SERV')
    deviceControl.writeVariable(b'EIAddrMode', struct.pack('B', 0))
    deviceControl.logout()

    deviceControl.close()


# === Device specific protocol & control_port mapping ===
# Visionary-T Mini CX      => CoLa2 / Port 2122
# handle argument parsing from cmd arguments
parser = argparse.ArgumentParser(description="Exemplary DHCP activation for SICK Visionary devices.")
parser.add_argument('-i', '--interfaceIPAddress', required=False, type=str,
                    default="192.168.1.2", help="The ip address of the network interface where device is connected to.")
parser.add_argument('-n', '--interfaceNetMask', required=False, type=str,
                    default="255.255.255.0", help="The subnet mask of the network interface where device is connected to.")
parser.add_argument('-s', '--staticIPAddress', required=False, type=str,
                    default="192.168.1.10", help="The static ip address of the device.")
parser.add_argument('-p', '--protocol', required=False, choices=['ColaB', 'Cola2'],
                    default="Cola2", help="The SICK CoLa protocol version.")
parser.add_argument('-c', '--control_port', required=False, type=int,
                    default=2122, help="The control port to change settings.")
parser.add_argument('-r', '--reset_to_static', required=False, type=bool,
                    default=False, help="The option to setback ethernet mode to static ip.")
args = parser.parse_args()


if __name__ == '__main__':
    # do an initial auto IO scan
    autoIp = AutoIp(args.interfaceIPAddress, args.interfaceNetMask)
    print('Scanning for device ...')
    devices = autoIp.scan()
    if len(devices) == 0:
        print('no device found - check scan parameters')
        exit()
    elif len(devices) > 1:
        print('to prevent accidental configuration this sample only works if only one device is connected to the network')
        exit()
    device = devices[0]
    print("Initial IP Address {} of device {}".format(device.items['IPAddress'][0], device.items["DeviceType"][0]))

    # change the IP of the device to ensure the device is reachable via static IP
    autoIp.assign(device.macAddr, device.items['COLA_VER'][0], args.staticIPAddress, '255.255.255.0', '0.0.0.0')
    sleep_time = int(device.items['IPConfigDuration'][0]) / 1000
    time.sleep(sleep_time)

    # Obtain IP address from DHCP server
    print("Activating DHCP ethernet addressing mode ...")
    deviceControl = Control(ipAddress=args.staticIPAddress, protocol=args.protocol, control_port=args.control_port)
    activate_dhcp(deviceControl)
    print("Wait till IP address is obtained from DHCP server ...")
    time.sleep(30) # Default DHCP Server timeout
    devices = autoIp.scan()
    deviceIP = device.items['IPAddress'][0]
    print("IP Address of the device obtained from DHCP Server {}".format(deviceIP))

    if args.reset_to_static:
        print("Revert ethernet addressing mode to static IP {}".format(args.staticIPAddress))
        del deviceControl
        deviceControl = Control(ipAddress=deviceIP, protocol=args.protocol, control_port=args.control_port)
        activate_static_ip(deviceControl, args.staticIPAddress)
        time.sleep(5)
        devices = autoIp.scan()
        deviceIP = device.items['IPAddress'][0]
        print("IP Address of the device after setting static IP {}".format(deviceIP))
