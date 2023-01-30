#!/usr/bin/env python3
"""
Tools to copy a game's savegames between formats
"""

from enum import Enum
import logging
from pathlib import Path
import shutil
from typing import Union
from n64savegametools.savegames import Everdrive64Savegames,Mupen64PlusSavegames,Project64Savegames,Savegames

logger = logging.getLogger(__name__)

class SaveFormat(str, Enum):
    ED64 = "EVERDRIVE64"
    MUPEN64PLUS = "MUPEN64PLUS"
    PJ64 = "PROJECT64"

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
    logger.info("ROM: %s", rom_path)
    logger.info("source: %s, %s", src_save_format, src_savedir)
    logger.info("destination: %s, %s", dst_save_format, dst_savedir)
    src_savegames = _create_new_savegames(src_save_format)
    src_savegames.import_from_disk(rom_path, src_savedir)
    if src_savegames.has_save():
        dst_savegames = _create_new_savegames(dst_save_format)
        dst_savegames.import_from_savegames(src_savegames)
        # TODO: Should this method do a backup first, or should that be a separate call?
        dst_savegames.export_to_disk(rom_path, dst_savedir)
        logger.info("copy complete: %s", rom_path)
    else:
        logger.info("no save found: %s", rom_path)

_rom_file_pattern = "*.[nvz]64"

def _create_new_savegames(format: SaveFormat) -> Savegames:
    if format == SaveFormat.ED64:
        return Everdrive64Savegames()
    elif format == SaveFormat.MUPEN64PLUS:
        return Mupen64PlusSavegames()
    elif format == SaveFormat.PJ64:
        return Project64Savegames()
    else:
        raise NotImplementedError()
