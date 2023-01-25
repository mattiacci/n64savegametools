#!/usr/bin/env python3
"""
Tools to copy a game's savegames between formats
"""

from enum import Enum
import logging
from pathlib import Path
import shutil
from typing import Dict,List,NamedTuple,Optional,Union
from n64savegametools.savegames import Everdrive64Savegames,Project64Savegames

logger = logging.getLogger(__name__)

class SaveFormat(str, Enum):
    ED64 = "ED64"
    PJ64 = "PJ64"
    RETROARCH = "RETROARCH"

### config that should be externalized

rom_file_pattern = "*.[nvz]64"

def copy_saves_for_all_roms(rom_dir: Union[Path, str], recursive: bool, src_save_format: SaveFormat, src_savedir: Union[Path, str], dst_save_format: SaveFormat, dst_savedir: Union[Path, str]):
    """For all games in the ROM diretory, copy the save files from one save location to another."""
    rom_dir = Path(rom_dir)
    if not rom_dir.is_dir():
        raise FileNotFoundError("Provided ROM directory isn't a directory: {}".format(rom_dir))
    rom_paths = sorted(rom_dir.rglob(rom_file_pattern) if recursive else rom_dir.glob(rom_file_pattern))
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
    logger.info("ROM: %s", rom_path)
    logger.info("source: %s, %s", src_save_format, src_savedir)
    logger.info("destination: %s, %s", dst_save_format, dst_savedir)

    src_savegames = Project64Savegames() if src_save_format == SaveFormat.PJ64 else Everdrive64Savegames()
    src_savegames.import_from_disk(rom_path, src_savedir)
    dst_savegames = Project64Savegames() if dst_save_format == SaveFormat.PJ64 else Everdrive64Savegames()
    dst_savegames.import_from_savegames(src_savegames)
    # TODO: Should this method do a backup first, or should that be a separate call?
    dst_savegames.export_to_disk(rom_path, dst_savedir)
    logger.info("copy complete: %s", rom_path)

# class OptionalSaveFiles(NamedTuple):
#     eeprom: Optional[Path] = None
#     sram: Optional[Path] = None
#     flashram: Optional[Path] = None
#     mpks: List[Optional[Path]] = [None, None, None, None]

# def _backup_save_files(save_files: Optional[OptionalSaveFiles]):
#     if save_files:
#         for key in save_files._fields:
#             src_file = getattr(save_files, key)
#             if isinstance(src_file, list):
#                 for item in src_file:
#                     if item:
#                         _replace_file(item, item.parent / "backup" / item.name)
#             elif src_file:
#                 _replace_file(src_file, src_file.parent / "backup" / src_file.name)

# def _replace_file(src_path: Optional[Path], dst_path: Optional[Path]):
#     if src_path is not None and dst_path is not None:
#         logger.debug("rename from %s to %s", src_path, dst_path)
#         dst_path.parent.mkdir(parents = True, exist_ok=True)
#         src_path.replace(dst_path)
