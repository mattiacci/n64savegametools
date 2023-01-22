#!/usr/bin/env python3
"""
Tools to copy a game's savegames between formats
"""

from enum import Enum
import logging
from pathlib import Path
import shutil
from typing import Dict,List,NamedTuple,Optional,Union
from n64savegametools.byteswap import swap
from n64savegametools.n64rominfo import get_rom_info

logger = logging.getLogger(__name__)

class SaveFiles(NamedTuple):
    eeprom: Optional[Path] = None
    sram: Optional[Path] = None
    flashram: Optional[Path] = None
    mpk: Optional[Path] = None
    mpks: List[Optional[Path]] = [None, None, None, None]

class SaveFormat(str, Enum):
    ED64 = "ED64"
    PJ64 = "PJ64"
    RETROARCH = "RETROARCH"

### config that should be externalized

rom_file_pattern = "*.[nvz]64"
little_endian: Dict[SaveFormat, List[str]] = {
    SaveFormat.ED64: [],
    SaveFormat.PJ64: ["sram", "flashram"],
    SaveFormat.RETROARCH: ["sram", "flashram"],
}
unpadded: Dict[SaveFormat, List[str]] = {
    SaveFormat.ED64: [],
    SaveFormat.PJ64: ["flashram"],
    SaveFormat.RETROARCH: [],
}
overpadded: Dict[SaveFormat, List[str]] = {
    SaveFormat.ED64: [],
    SaveFormat.PJ64: [],
    SaveFormat.RETROARCH: ["eeprom"],
}
expected_bytesizes: Dict[str, Union[int, List[int]]] = {
    "eeprom": [512, 2048],
    "flashram": 131072,
}

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
    src_save_files = _get_actual_save_files(rom_path, src_save_format, src_savedir)
    if not src_save_files:
        logger.warning("No save found for: %s", rom_path.name)
        return
    logger.debug("source save files: %s", src_save_files)
    dst_possible_save_files = _get_possible_save_files(rom_path, dst_save_format, dst_savedir)
    logger.debug("destination possible save files: %s", dst_possible_save_files)
    dst_actual_save_files = _get_actual_save_files(rom_path, dst_save_format, dst_savedir)
    logger.debug("destination actual save files: %s", dst_actual_save_files)
    _backup_save_files(dst_actual_save_files)
    _copy_save_files(src_save_format, src_save_files, dst_save_format, dst_possible_save_files)
    logger.info("copy complete: %s", rom_path)

def _backup_save_files(save_files: Optional[SaveFiles]):
    if save_files:
        for key in save_files._fields:
            src_file = getattr(save_files, key)
            if isinstance(src_file, list):
                for item in src_file:
                    if item:
                        _replace_file(item, item.parent / "backup" / item.name)
            elif src_file:
                _replace_file(src_file, src_file.parent / "backup" / src_file.name)

def _copy_save_files(src_save_format: SaveFormat, src_save_files: SaveFiles, dst_save_format: SaveFormat, dst_possible_save_files: SaveFiles):
    for key in src_save_files._fields:
        src_file = getattr(src_save_files, key)
        dst_file = getattr(dst_possible_save_files, key)
        if isinstance(src_file, list):
            for index, item in enumerate(src_file):
                _copy_file(item, dst_file[index])
        else:
            swap_endianness = (key in little_endian[src_save_format]) != (key in little_endian[dst_save_format])
            pad_to = expected_bytesizes[key] if (key in unpadded[src_save_format]) else None
            _copy_file(src_file, dst_file, swap_endianness = swap_endianness, pad_to = pad_to)

def _copy_file(src_path: Optional[Path], dst_path: Optional[Path], swap_endianness = False, pad_to = None):
    if src_path is not None and dst_path is not None:
        logger.debug("copy from %s to %s", src_path, dst_path)
        dst_path.parent.mkdir(parents = True, exist_ok=True)
        if swap_endianness or pad_to:
            data = bytearray(src_path.read_bytes())
            if swap_endianness:
                swap(data)
            if pad_to:
                bytes_to_append = pad_to - len(data)
                if bytes_to_append < 0:
                    raise OSError("Savefile is too large: {} should be at most {} bytes".format(src_path, pad_to))
                elif bytes_to_append > 0:
                    data += bytearray(bytes_to_append)
            dst_path.write_bytes(data)
        else:
            shutil.copy(src_path, dst_path)
        shutil.copystat(src_path, dst_path)

def _get_actual_save_files(rom_path: Path, save_format: SaveFormat, savedir_path: Path):
    if not savedir_path.is_dir():
        return None
    possible_save_files = _get_possible_save_files(rom_path, save_format, savedir_path)
    if not possible_save_files:
        return None
    save_files = SaveFiles(
        eeprom=possible_save_files.eeprom if possible_save_files.eeprom.exists() else None,
        sram=possible_save_files.sram if possible_save_files.sram.exists() else None,
        flashram=possible_save_files.flashram if possible_save_files.flashram.exists() else None,
        mpk=possible_save_files.mpk if possible_save_files.mpk.exists() else None,
        mpks=[(x if x.exists() else None) for x in possible_save_files.mpks]
    )
    if save_files.mpk and [x for x in save_files.mpks if x != None]:
        raise OSError("No support for both a ROM-filename-matching memory pack and a controller-specific memory pack: {}".format(savedir_path))
    if save_files == SaveFiles():
        return None
    return save_files

def _get_possible_save_files(rom_path: Path, save_format: SaveFormat, savedir_path: Path):
    if not rom_path.is_file():
        raise FileNotFoundError("Provided ROM path isn't a file")
    if save_format == SaveFormat.ED64:
        game_filename_stem = rom_path.stem
    elif save_format == SaveFormat.PJ64:
        rom_info = get_rom_info(rom_path)
        if not rom_info or rom_info.hash_little_endian_md5 is None:
            return None
        savedir_path = savedir_path / "{}-{}".format(rom_info.internal_name, rom_info.hash_little_endian_md5.upper())
        game_filename_stem = rom_info.internal_name
    else:
        raise NotImplementedError("Save format isn't yet supported: {}".format(save_format))
    return SaveFiles(
        eeprom=savedir_path / "{}.eep".format(game_filename_stem),
        sram=savedir_path / ("{}.srm" if save_format == SaveFormat.ED64 else "{}.sra").format(game_filename_stem),
        flashram=savedir_path / "{}.fla".format(game_filename_stem),
        mpk=savedir_path / "{}.mpk".format(game_filename_stem),
        mpks=[savedir_path / "{}_Cont_{}.mpk".format(game_filename_stem, i) for i in range(1, 5)],
    )

def _replace_file(src_path: Optional[Path], dst_path: Optional[Path]):
    if src_path is not None and dst_path is not None:
        logger.debug("rename from %s to %s", src_path, dst_path)
        dst_path.parent.mkdir(parents = True, exist_ok=True)
        src_path.replace(dst_path)
