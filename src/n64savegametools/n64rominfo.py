#!/usr/bin/env python3
"""
Nintendo 64 ROM metadata reader
"""

from enum import Enum
import hashlib
import logging
from pathlib import Path
import struct
from typing import NamedTuple,Optional,Tuple
from n64savegametools.byteswap import swap

_logger = logging.getLogger(__name__)

class MediaFormat(str, Enum):
    CART = "N"
    EXPANDABLE_CART = "C"
    DISK = "D"
    DISK_EXPANSION = "E"
    ALECK64 = "Z"

class RegionCode(str, Enum):
    BETA = "7"
    ASIAN = "A"
    BRAZILIAN = "B"
    CHINESE = "C"
    GERMAN = "D"
    NORTH_AMERICA = "E"
    FRENCH = "F"
    GATEWAY_64_NTSC = "G"
    DUTCH = "H"
    ITALIAN = "I"
    JAPANESE = "J"
    KOREAN = "K"
    GATEWAY_64_PAL = "L"
    CANADIAN = "N"
    EUROPEAN = "P"
    SPANISH = "S"
    AUSTRALIAN = "U"
    SCANDINAVIAN = "W"
    EUROPEAN_X = "X"
    EUROPEAN_Y = "Y"

class N64RomInfo(NamedTuple):
    """Nintendo 64 ROM information, mostly from the ROM's header."""
    crc1: str
    crc2: str
    internal_name: str
    media_format: MediaFormat
    game_id: str
    region_code: RegionCode
    version: float
    hash_little_endian_md5: Optional[str]

def get_rom_info(rom_path: Path, calculate_md5_hash: bool = True) -> Optional[N64RomInfo]:
    try:
        if calculate_md5_hash:
            with open(rom_path, "rb") as f:
                rom_bytearray = bytearray(f.read())
            byteswap, halfwordswap = _get_swapping_needed_for_little_endian(rom_bytearray[0], rom_path)
            swap(rom_bytearray, byteswap, halfwordswap)
            hash_md5 = hashlib.md5()
            hash_md5.update(rom_bytearray)
            hash_little_endian_md5 = hash_md5.hexdigest()
            rom_header_bytearray = rom_bytearray[:0x40]
            # swap to big endian
            swap(rom_header_bytearray, True, True)
        else:
            with open(rom_path, "rb") as f:
                rom_header_bytearray = bytearray(f.read(0x40))
            hash_little_endian_md5 = None
            byteswap, halfwordswap = _get_swapping_needed_for_little_endian(rom_header_bytearray[0], rom_path)
            # swap to big endian
            swap(rom_header_bytearray, not byteswap, not halfwordswap)
        rom_header = _N64RomHeader._make(struct.unpack(_N64_ROM_HEADER_STRUCT, rom_header_bytearray))
        rom_info = N64RomInfo(
            crc1=rom_header.crc1.hex(),
            crc2=rom_header.crc2.hex(),
            internal_name=rom_header.internal_name.partition(b'\x00')[0].decode(encoding = "cp932", errors="replace").strip(),
            media_format=MediaFormat(rom_header.media_format.decode(encoding = "cp932")),
            game_id=rom_header.game_id.decode(encoding = "cp932"),
            region_code=RegionCode(rom_header.region_code.decode(encoding = "cp932")),
            version=rom_header.version / 10 + 1,
            hash_little_endian_md5=hash_little_endian_md5
        )
    except (OSError, ValueError):
        _logger.exception("Failed to read ROM metadata: %s", rom_path)
        return None
    if calculate_md5_hash and rom_info.hash_little_endian_md5 is None:
        _logger.error("Failed to calculate ROM MD5 hash: %s", rom_path)
        return None
    return rom_info

"""
0x0 4   intial PI settings
    80000000    indicator for endianess (nybble)
    00F00000    initial PI_BSD_DOM1_RLS_REG (nybble)
    000F0000    initial PI_BSD_DOM1_PGS_REG (nybble)
    0000FF00    initial PI_BSD_DOM1_PWD_REG
    000000FF    initial PI_BSD_DOM1_LAT_REG
0x4 4   clockrate
    FFFFFFF0    ClockRate; if 0 uses default rate
    0000000F    unknown (unused nybble, isn't read)
0x8 4   program counter a.k.a. boot address; depending on the CIC used may require alteration
0xC 4   release address; unused by all known commercial carts
0x10    4   CRC1 (checksum)
0x14    4   CRC2
0x18    8   RESERVED (unused)
0x20    20  internal name, using codepage 932; padded with space (0x20) or NUL (0x00)
0x34    7   RESERVED (unused)
0x3B    1   media format
    'N' cartridge
    'C' cartridge part of expandable game
    'D' 64DD disk
    'E' 64DD expansion for cart
    'Z' Aleck64 cart
0x3C    2   two-letter game ID
0x3E    1   region code
    '7' Beta
    'A' Asian (NTSC)
    'B' Brazilian
    'C' Chinese
    'D' German
    'E' North America
    'F' French
    'G' Gateway 64 (NTSC)
    'H' Dutch
    'I' Italian
    'J' Japanese
    'K' Korean
    'L' Gateway 64 (PAL)
    'N' Canadian
    'P' European (basic spec.)
    'S' Spanish
    'U' Australian
    'W' Scandinavian
    'X' European
    'Y' European
0x3F    1   version, fixed decimal (ie: 00 = 1.0, 15 = 2.5)
0x40    4032    boot code (to counter hacking, can be extracted with RN646CRC)
"""
_N64_ROM_HEADER_STRUCT = ">16x4s4s8x20s7xc2scB"

class _N64RomHeader(NamedTuple):
    crc1: bytes
    crc2: bytes
    internal_name: bytes
    media_format: bytes
    game_id: bytes
    region_code: bytes
    version: int

def _get_swapping_needed_for_little_endian(byte: int, filepath: Path) -> Tuple[bool, bool]:
    if byte == 0x80:  # .z64, big-endian, ABCD; so need to byte swap then word swap (a.k.a. reverse)
        return True, True
    elif byte == 0x37:  # .v64, big-endian byte-swapped, BADC; so only need to word swap
        return False, True
    elif byte == 0x40:  # .n64, little-endian, DCBA; so need to do nothing
        return False, False
    elif byte == 0x12:  # No standard format uses this, little-endian byte-swapped, CDAB; but we can handle it
        return True, False
    raise IOError("First byte of file doesn't match N64 ROM: {}".format(filepath))
