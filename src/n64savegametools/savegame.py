#!/usr/bin/env python3
"""
Savegame formats, with importation/exportation/conversion functionality.
"""

from __future__ import annotations

from base64 import b64decode
from bz2 import decompress
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
import struct
from typing import List,NamedTuple,Optional
from n64savegametools.byteswap import swap
from n64savegametools.n64rominfo import get_rom_info

_logger = logging.getLogger(__name__)

class Savegame():
    eeprom: Optional[_SaveData] = None
    sram: Optional[_SaveData] = None
    flashram: Optional[_SaveData] = None
    mpks: List[Optional[_SaveData]] = [None, None, None, None]
    def export_to_disk(self, rom_path: Path, savedir_path: Path, backup: bool):
        pass
    def import_from_disk(self, ro_path: Path, savedir_path: Path):
        pass
    def has_save(self) -> bool:
        return any((self.eeprom, self.sram, self.flashram, any(self.mpks)))
    def import_from_savegame(self, other: Savegame):
        self.eeprom = deepcopy(other.eeprom)
        self.sram = deepcopy(other.sram)
        self.flashram = deepcopy(other.flashram)
        self.mpks = deepcopy(other.mpks)
        return self

class Everdrive64Savegame(Savegame):
    def export_to_disk(self, rom_path: Path, savedir_path: Path, backup: bool):
        files = self._get_save_files(rom_path, savedir_path)
        if backup:
            _backup_save_files(files)
        _export_to_file(self.eeprom, files.eeprom)
        _export_to_file(self.sram, files.sram)
        _export_to_file(self.flashram, files.flashram)
        for i, mpk in enumerate(self.mpks):
            _export_to_file(mpk, files.mpks[i])
        return self
    def import_from_disk(self, rom_path: Path, savedir_path: Path):
        files = self._get_save_files(rom_path, savedir_path)
        if files.eeprom.is_file():
            self.eeprom = _SaveData(files.eeprom.read_bytes())
        if files.sram.is_file():
            self.sram = _SaveData(files.sram.read_bytes())
        if files.flashram.is_file():
            self.flashram = _SaveData(files.flashram.read_bytes())
        self.mpks = [_SaveData(mpk.read_bytes()) if mpk.is_file() else None for mpk in files.mpks]
        return self
    def _get_save_files(self, rom_path: Path, savedir_path: Path) -> _MultipleSaveFiles:
        if not rom_path.is_file():
            raise FileNotFoundError("Provided ROM path doesn't exist")
        if not savedir_path.is_dir():
            raise FileNotFoundError("Provided save directory doesn't exist")
        game_filename_stem = rom_path.stem
        return _MultipleSaveFiles(
            eeprom=savedir_path / "{}.eep".format(game_filename_stem),
            sram=savedir_path / "{}.srm".format(game_filename_stem),
            flashram=savedir_path / "{}.fla".format(game_filename_stem),
            mpks=[savedir_path / ("{}.mpk".format(game_filename_stem) if i == 1 else "{}_Cont_{}.mpk".format(game_filename_stem, i)) for i in range(1, 5)],
        )

class Mupen64PlusSavegame(Savegame):
    def export_to_disk(self, rom_path: Path, savedir_path: Path, backup: bool):
        dst_path = self._get_save_file(rom_path, savedir_path)
        if backup:
            _backup_save_file(dst_path)
        _logger.debug("converting savegame to Mupen64+ format")
        eeprom = self.eeprom or _SaveData(bytearray())
        eeprom.data.ljust(_EEPROM_BYTESIZES[1], b'\xff')
        sram = self.sram or _SaveData(b'\xff' * _SRAM_BYTESIZE, _Endianness.LITTLE_ENDIAN)
        flashram = self.flashram or _SaveData(b'\xff' * _FLASHRAM_BYTESIZE, _Endianness.LITTLE_ENDIAN)
        mpks = [i or _SaveData(_FORMATTED_MPK) for i in self.mpks]
        eeprom.set_endianness(_Endianness.BIG_ENDIAN)
        sram.set_endianness(_Endianness.LITTLE_ENDIAN)
        for mpk in mpks:
            mpk.set_endianness(_Endianness.BIG_ENDIAN)
        flashram.set_endianness(_Endianness.LITTLE_ENDIAN)
        data = struct.pack(_MUPEN64PLUS_SRM_STRUCT, eeprom.data, *[mpk.data for mpk in mpks], sram.data, flashram.data)
        _logger.debug("exporting to %s", dst_path)
        dst_path.parent.mkdir(parents = True, exist_ok=True)
        dst_path.write_bytes(data)
        return self
    def import_from_disk(self, rom_path: Path, savedir_path: Path):
        save_file = self._get_save_file(rom_path, savedir_path)
        if save_file.is_file():
            srm = _Mupen64PlusSrm._make(struct.unpack(_MUPEN64PLUS_SRM_STRUCT, save_file.read_bytes()))
            if eeprom := _strip_empty_data(srm.eeprom):
                # TODO: Use a memoryview to avoid doing unnecessary copies (as I believe slicing copies).
                self.eeprom = _SaveData(eeprom if not _is_empty_data(eeprom[_EEPROM_BYTESIZES[0]:_EEPROM_BYTESIZES[1]]) else eeprom[0:_EEPROM_BYTESIZES[0]])
            if sram := _strip_empty_data(srm.sram):
                self.sram = _SaveData(sram, endianness=_Endianness.LITTLE_ENDIAN)
            if flashram := _strip_empty_data(srm.flashram):
                self.flashram = _SaveData(flashram, endianness=_Endianness.LITTLE_ENDIAN)
            self.mpks = [_mpk_to_savegame_data(srm.mpk1), _mpk_to_savegame_data(srm.mpk2), _mpk_to_savegame_data(srm.mpk3), _mpk_to_savegame_data(srm.mpk4)]
        return self
    def _get_save_file(self, rom_path: Path, savedir_path: Path) -> Path:
        if not rom_path.is_file():
            raise FileNotFoundError("Provided ROM path doesn't exist")
        if not savedir_path.is_dir():
            raise FileNotFoundError("Provided save directory doesn't exist")
        return savedir_path / "{}.srm".format(rom_path.stem)

class Project64Savegame(Savegame):
    def export_to_disk(self, rom_path: Path, savedir_path: Path, backup: bool):
        files = self._get_save_files(rom_path, savedir_path)
        if backup:
            _backup_save_files(files)
        _export_to_file(self.eeprom, files.eeprom)
        _export_to_file(self.sram, files.sram, endianness=_Endianness.LITTLE_ENDIAN)
        _export_to_file(self.flashram, files.flashram, endianness=_Endianness.LITTLE_ENDIAN)
        for i, mpk in enumerate(self.mpks):
            _export_to_file(mpk, files.mpks[i])
        return self
    def import_from_disk(self, rom_path: Path, savedir_path: Path):
        files = self._get_save_files(rom_path, savedir_path)
        if files.eeprom.is_file():
            self.eeprom = _SaveData(files.eeprom.read_bytes())
        if files.sram.is_file():
            self.sram = _SaveData(files.sram.read_bytes(), _Endianness.LITTLE_ENDIAN)
        if files.flashram.is_file():
            self.flashram = _SaveData(files.flashram.read_bytes().ljust(_FLASHRAM_BYTESIZE, b'\x00'), _Endianness.LITTLE_ENDIAN)
        self.mpks = [_SaveData(mpk.read_bytes()) if mpk.is_file() else None for mpk in files.mpks]
        return self
    def _get_save_files(self, rom_path: Path, savedir_path: Path) -> _MultipleSaveFiles:
        if not rom_path.is_file():
            raise FileNotFoundError("Provided ROM path doesn't exist")
        if not savedir_path.is_dir():
            raise FileNotFoundError("Provided save directory doesn't exist")
        rom_info = get_rom_info(rom_path)
        if not rom_info or rom_info.hash_little_endian_md5 is None:
            raise IOError("Could not get info from ROM: {}".format(rom_path))
        savedir_path = savedir_path / "{}-{}".format(rom_info.internal_name, rom_info.hash_little_endian_md5.upper())
        game_filename_stem = rom_info.internal_name
        return _MultipleSaveFiles(
            eeprom=savedir_path / "{}.eep".format(game_filename_stem),
            sram=savedir_path / "{}.sra".format(game_filename_stem),
            flashram=savedir_path / "{}.fla".format(game_filename_stem),
            mpks=[savedir_path / "{}_Cont_{}.mpk".format(game_filename_stem, i) for i in range(1, 5)],
        )

_EEPROM_BYTESIZES = [512, 2048]
_SRAM_BYTESIZE = 32768
_MPK_BYTESIZE = 32768
_FLASHRAM_BYTESIZE = 131072

# The first 768 bytes of a formatted memory pak, bz2-compressed then base64-encoded.
_FORMATTED_MPK_BZ2_B64 = b"QlpoOTFBWSZTWR88mz4AATLz5P////+CAAAAgQAgACAAACAAAgAAoAB1CVTRo0AA0ZDQABJJTamI00YIaZMjNTylwRThKBxBJJOCQMnR5hRMhJJUs9g5MCgmVPRTVXZbdevDwGMblno7VYbbtOEc9ehEDgTDrEJA8DcGAIyqIB/F3JFOFCQHzybPgA=="
_FORMATTED_MPK = decompress(b64decode(_FORMATTED_MPK_BZ2_B64)).ljust(_MPK_BYTESIZE, b'\x00')
"""
uint8_t eeprom[0x800];
uint8_t mpk[4][0x8000];
uint8_t sram[0x8000];
uint8_t flashram[0x20000];
"""
_MUPEN64PLUS_SRM_STRUCT = ">{}s{}s{}s{}s{}s{}s{}s".format(_EEPROM_BYTESIZES[-1], _MPK_BYTESIZE, _MPK_BYTESIZE, _MPK_BYTESIZE, _MPK_BYTESIZE, _SRAM_BYTESIZE, _FLASHRAM_BYTESIZE)

class _Endianness(Enum):
    BIG_ENDIAN = 1
    LITTLE_ENDIAN = 2

class _Mupen64PlusSrm(NamedTuple):
    eeprom: bytes
    mpk1: bytes
    mpk2: bytes
    mpk3: bytes
    mpk4: bytes
    sram: bytes
    flashram: bytes

class _MultipleSaveFiles(NamedTuple):
    eeprom: Path
    sram: Path
    flashram: Path
    mpks: List[Path]

@dataclass
class _SaveData():
    data: bytes
    endianness: _Endianness = _Endianness.BIG_ENDIAN
    def set_endianness(self, endianness: _Endianness) -> _SaveData:
        if endianness != self.endianness:
            if not isinstance(self.data, bytearray):
                self.data = bytearray(self.data)
            swap(self.data)
            self.endianness = endianness
        return self

def _backup_save_files(save_files: _MultipleSaveFiles):
    for key in save_files._fields:
        src_file = getattr(save_files, key)
        if isinstance(src_file, list):
            for item in src_file:
                _backup_save_file(item)
        elif src_file:
            _backup_save_file(src_file)

def _backup_save_file(src_path: Optional[Path]):
    if src_path is not None and src_path.exists():
        dst_path = src_path.parent / "backup" / src_path.name
        _logger.debug("copy from %s to %s", src_path, dst_path)
        dst_path.parent.mkdir(parents = True, exist_ok=True)
        src_path.replace(dst_path)

def _export_to_file(save_data: Optional[_SaveData], dst_path: Path, endianness = _Endianness.BIG_ENDIAN):
    if save_data is not None and dst_path is not None:
        _logger.debug("exporting to %s", dst_path)
        dst_path.parent.mkdir(parents = True, exist_ok=True)
        save_data.set_endianness(endianness)
        dst_path.write_bytes(save_data.data)

def _is_effectively_empty_memory_pak(data: bytes) -> bool:
    # TODO: Use a memoryview to avoid doing unnecessary copies (as I believe slicing copies).
    if data[0:0x102] != _FORMATTED_MPK[0:0x102]:
        return False
    for byte in data[0x10a:0x200]:
        if byte != 0 and byte != 3:
            return False
    return True

def _is_empty_data(data: bytes) -> bool:
    first_byte = data[0]
    if first_byte != 0x0 and first_byte != 0xff:
        return False
    for byte in data:
        if byte != first_byte:
            return False
    return True

def _mpk_to_savegame_data(data: bytes) -> Optional[_SaveData]:
    return None if _is_effectively_empty_memory_pak(data) else _SaveData(data)

def _strip_empty_data(data: bytes) -> Optional[bytes]:
    return None if _is_empty_data(data) else data
