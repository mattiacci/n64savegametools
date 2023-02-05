#!/usr/bin/env python3
"""
Tools to copy a game's savegame between formats
"""

from enum import Enum
import logging
from pathlib import Path
import shutil
from typing import Union
from n64savegametools.savegame import Everdrive64Savegame,Mupen64PlusSavegame,Project64Savegame,Savegame

_logger = logging.getLogger(__name__)

class SaveFormat(str, Enum):
    EVERDRIVE = "EVERDRIVE"
    MUPEN64PLUS = "MUPEN64PLUS"
    PROJECT64 = "PROJECT64"

def copy_saves_for_all_roms(rom_dir: Union[Path, str], recursive: bool, src_save_format: SaveFormat, src_savedir: Union[Path, str], dst_save_format: SaveFormat, dst_savedir: Union[Path, str]):
    """For all games in the ROM diretory, copy the save files from one save location to another."""
    rom_dir = Path(rom_dir)
    if not rom_dir.is_dir():
        raise FileNotFoundError("Provided ROM directory isn't a directory: {}".format(rom_dir))
    rom_paths = sorted(rom_dir.rglob(_rom_file_pattern) if recursive else rom_dir.glob(_rom_file_pattern))
    for rom_path in rom_paths:
        copy_saves_for_rom(rom_path, src_save_format, src_savedir, dst_save_format, dst_savedir)

def copy_saves_for_rom(rom_path: Union[Path, str], src_save_format: SaveFormat, src_savedir: Union[Path, str], dst_save_format: SaveFormat, dst_savedir: Union[Path, str]):
    """For the given ROM, copy the save files from one save location to another."""
    # Use the game's filename and MD5 hash to find the appropriate files/directories, then copy and convert.
    rom_path, src_savedir, dst_savedir = Path(rom_path), Path(src_savedir), Path(dst_savedir)
    if not rom_path.is_file():
        raise FileNotFoundError("Provided ROM path isn't a file: {}".format(rom_path))
    if not src_savedir.is_dir():
        raise FileNotFoundError("Provided source save path isn't a directory: {}".format(src_savedir))
    if not dst_savedir.is_dir():
        raise FileNotFoundError("Provided destination save path isn't a directory: {}".format(dst_savedir))
    if src_savedir.samefile(dst_savedir):
        raise FileExistsError("Provided source save path and destination save path are the same: {}".format(src_savedir))
    _logger.info("ROM: %s", rom_path)
    _logger.info("source: %s, %s", src_save_format, src_savedir)
    _logger.info("destination: %s, %s", dst_save_format, dst_savedir)
    src_savegame = _new_savegame(src_save_format).import_from_disk(rom_path, src_savedir)
    if src_savegame.has_save():
        dst_savegame = _new_savegame(dst_save_format).import_from_savegame(src_savegame)
        # TODO: Should this method do a backup first, or should that be a separate call?
        dst_savegame.export_to_disk(rom_path, dst_savedir, backup=True)
        _logger.info("copy complete: %s", rom_path)
    else:
        _logger.info("no save found: %s", rom_path)

_rom_file_pattern = "*.[nvz]64"

def _new_savegame(format: SaveFormat) -> Savegame:
    if format == SaveFormat.EVERDRIVE:
        return Everdrive64Savegame()
    elif format == SaveFormat.MUPEN64PLUS:
        return Mupen64PlusSavegame()
    elif format == SaveFormat.PROJECT64:
        return Project64Savegame()
    else:
        raise NotImplementedError()
