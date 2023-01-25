#!/usr/bin/env python3
"""
Savegame formats, with importation/exportation/conversion functionality.
"""

from __future__ import annotations

from copy import deepcopy
from enum import Enum
import logging
from pathlib import Path
from typing import Dict,List,NamedTuple,Optional,Union
from n64savegametools.byteswap import swap
from n64savegametools.n64rominfo import get_rom_info

logger = logging.getLogger(__name__)

class Endianness(Enum):
    BIG_ENDIAN = 1
    LITTLE_ENDIAN = 2

class SavegameData(NamedTuple):
    data: bytes
    endianness: Endianness = Endianness.BIG_ENDIAN

class SaveFiles(NamedTuple):
    eeprom: Path
    sram: Path
    flashram: Path
    mpks: List[Path]

class Savegames():
    eeprom: Optional[SavegameData] = None
    sram: Optional[SavegameData] = None
    flashram: Optional[SavegameData] = None
    mpks: List[Optional[SavegameData]] = [None, None, None, None]
    def export_to_disk(self, rom_path: Path, savedir_path: Path):
        pass
    def import_from_disk(self, rom_path: Path, savedir_path: Path):
        pass
    def import_from_savegames(self, other: Savegames):
        self.eeprom = deepcopy(other.eeprom)
        self.sram = deepcopy(other.sram)
        self.flashram = deepcopy(other.flashram)
        self.mpks = deepcopy(other.mpks)

class Everdrive64Savegames(Savegames):
    def export_to_disk(self, rom_path: Path, savedir_path: Path):
        files = self._get_save_files(rom_path, savedir_path)
        _export_to_file(self.eeprom, files.eeprom)
        _export_to_file(self.sram, files.sram)
        _export_to_file(self.flashram, files.flashram)
        for i, mpk in enumerate(self.mpks):
            _export_to_file(mpk, files.mpks[i])
    def import_from_disk(self, rom_path: Path, savedir_path: Path):
        files = self._get_save_files(rom_path, savedir_path)
        if files.eeprom.is_file():
            self.eeprom = SavegameData(files.eeprom.read_bytes())
        if files.sram.is_file():
            self.sram = SavegameData(files.sram.read_bytes())
        if files.flashram.is_file():
            self.flashram = SavegameData(files.flashram.read_bytes())
        self.mpks = [SavegameData(mpk.read_bytes()) if mpk.is_file() else None for mpk in files.mpks]
    def _get_save_files(self, rom_path: Path, savedir_path: Path) -> SaveFiles:
        if not rom_path.is_file():
            raise FileNotFoundError("Provided ROM path doesn't exist")
        if not savedir_path.is_dir():
            raise FileNotFoundError("Provided save directory doesn't exist")
        game_filename_stem = rom_path.stem
        return SaveFiles(
            eeprom=savedir_path / "{}.eep".format(game_filename_stem),
            sram=savedir_path / "{}.srm".format(game_filename_stem),
            flashram=savedir_path / "{}.fla".format(game_filename_stem),
            mpks=[savedir_path / ("{}.mpk".format(game_filename_stem) if i == 1 else "{}_Cont_{}.mpk".format(game_filename_stem, i)) for i in range(1, 5)],
        )

class Project64Savegames(Savegames):
    def export_to_disk(self, rom_path: Path, savedir_path: Path):
        files = self._get_save_files(rom_path, savedir_path)
        _export_to_file(self.eeprom, files.eeprom)
        _export_to_file(self.sram, files.sram, endianness=Endianness.LITTLE_ENDIAN)
        _export_to_file(self.flashram, files.flashram, endianness=Endianness.LITTLE_ENDIAN)
        for i, mpk in enumerate(self.mpks):
            _export_to_file(mpk, files.mpks[i])
    def import_from_disk(self, rom_path: Path, savedir_path: Path):
        files = self._get_save_files(rom_path, savedir_path)
        if files.eeprom.is_file():
            self.eeprom = SavegameData(files.eeprom.read_bytes())
        if files.sram.is_file():
            self.sram = SavegameData(files.sram.read_bytes(), Endianness.LITTLE_ENDIAN)
        if files.flashram.is_file():
            self.flashram = SavegameData(_pad(files.flashram.read_bytes(), _expected_bytesizes["flashram"]), Endianness.LITTLE_ENDIAN)
        self.mpks = [SavegameData(mpk.read_bytes()) if mpk.is_file() else None for mpk in files.mpks]
    def _get_save_files(self, rom_path: Path, savedir_path: Path) -> SaveFiles:
        if not rom_path.is_file():
            raise FileNotFoundError("Provided ROM path doesn't exist")
        if not savedir_path.is_dir():
            raise FileNotFoundError("Provided save directory doesn't exist")
        rom_info = get_rom_info(rom_path)
        if not rom_info or rom_info.hash_little_endian_md5 is None:
            raise IOError("Could not get info from ROM: {}".format(rom_path))
        savedir_path = savedir_path / "{}-{}".format(rom_info.internal_name, rom_info.hash_little_endian_md5.upper())
        game_filename_stem = rom_info.internal_name
        return SaveFiles(
            eeprom=savedir_path / "{}.eep".format(game_filename_stem),
            sram=savedir_path / "{}.sra".format(game_filename_stem),
            flashram=savedir_path / "{}.fla".format(game_filename_stem),
            mpks=[savedir_path / "{}_Cont_{}.mpk".format(game_filename_stem, i) for i in range(1, 5)],
        )

_expected_bytesizes: Dict[str, Union[int, List[int]]] = {
    "eeprom": [512, 2048],
    "flashram": 131072,
}

def _export_to_file(savegame_data: Optional[SavegameData], dst_path: Path, endianness = Endianness.BIG_ENDIAN):
    if savegame_data is not None and dst_path is not None:
        logger.debug("exporting to %s", dst_path)
        dst_path.parent.mkdir(parents = True, exist_ok=True)
        data = savegame_data.data
        swap_endianness = endianness != savegame_data.endianness
        if swap_endianness:
            data = bytearray(data)
            swap(data)
        dst_path.write_bytes(data)

def _pad(data: bytes, pad_to_bytesize = None):
    bytes_to_append = pad_to_bytesize - len(data)
    if bytes_to_append > 0:
        data += bytearray(bytes_to_append)
    return data
