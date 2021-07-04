#!/usr/bin/env python3
"""\

Stream g-code to grbl controller

This script differs from the simple_stream.py script by
tracking the number of characters in grbl's serial read
buffer. This allows grbl to fetch the next line directly
from the serial buffer and does not have to wait for a
response from the computer. This effectively adds another
buffer layer to prevent buffer starvation.

CHANGELOG:
- 20170531: Status report feedback at 1.0 second intervals.
    Configurable baudrate and report intervals. Bug fixes.
- 20161212: Added push message feedback for simple streaming
- 20140714: Updated baud rate to 115200. Added a settings
  write mode via simple streaming method. MIT-licensed.

TODO:
- Add realtime control commands during streaming.

---------------------
The MIT License (MIT)

Copyright (c) 2012-2017 Sungeun K. Jeon

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
---------------------
"""

import re
import serial
import time
import argparse

RX_BUFFER_SIZE = 128
BAUD_RATE = 115200

# Define command line argument interface
parser = argparse.ArgumentParser(
    description='Stream g-code file to grbl. (pySerial and argparse libraries required)')
parser.add_argument('-p', '--serial-port', dest='device_file',
                    default='/dev/ttyUSB0', help='serial device path')
parser.add_argument('action', choices=[
                    'write', 'read'], help='Read settings from grbl into file or write settings from file to grbl?')
parser.add_argument('file_name')
args = parser.parse_args()

# Initialize
serial_port = serial.Serial(args.device_file, BAUD_RATE)

# Wake up grbl
print("Initializing Grbl...")
serial_port.write("\r\n\r\n".encode())

# Wait for grbl to initialize and flush startup text in serial input
time.sleep(2)
serial_port.flushInput()

start_time = time.time()


def write_settings(in_file, port):
    # Stream settings to grbl
    l_count = 0
    error_count = 0
    # Send settings file via simple call-response streaming method. Settings must be streamed
    # in this manner since the EEPROM accessing cycles shut-off the serial interrupt.
    print(f"Writing settings from { in_file } to GRBL")
    with open(in_file, 'r') as f:
        for line in f:
            l_count += 1  # Iterate line counter
            l_block = re.sub(r'\(.*?\)', '', line).strip()  # Strip comments and extra whitespace
            print(f"send { l_count }> { l_block }")
            serial_port.write(f"{ l_block }\n".encode())  # Send g-code block to grbl
            while True:
                # Wait for grbl response with carriage return
                grbl_out = serial_port.readline().strip().decode().strip()
                print(f"recv { l_count } < { grbl_out }")
                if 'ok' == grbl_out:
                    break
                elif 'error' in grbl_out:
                    error_count += 1
                    break


def read_settings(out_file, serial_port):
    # read settings from grbl, store them in a file
    print(f"Reading settings from {{ serial_port.name }}, storing them in {{ out_file }}.")
    serial_port.write("$$\n".encode())
    with open(out_file, 'w') as f:
        while True:
            line = serial_port.readline().decode().strip()
            print(line)

            if 'ok' == line:
                break
            else:
                print(line, file=f)


actions = {'read': read_settings,
           'write': write_settings}

actions[args.action](args.file_name, serial_port)

# Close serial port
serial_port.close()
