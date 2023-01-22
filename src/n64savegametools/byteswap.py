#!/usr/bin/env python3
"""
Byteswapping functionality
"""

def swap(arr: bytearray, byteswap: bool = True, halfwordswap: bool = True):
    if len(arr) % 4 != 0:
        raise IOError("Expected bytearray to be a multiple of 4 bytes")
    if byteswap and halfwordswap:
        arr[0::4], arr[1::4], arr[2::4], arr[3::4] = arr[3::4], arr[2::4], arr[1::4], arr[0::4]
    elif byteswap:
        arr[0::2], arr[1::2] = arr[1::2], arr[0::2]
    elif halfwordswap:
        arr[0::4], arr[1::4], arr[2::4], arr[3::4] = arr[2::4], arr[3::4], arr[0::4], arr[1::4]
