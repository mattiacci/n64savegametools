import hashlib
from pathlib import Path
from n64savegametools.byteswap import swap
from n64savegametools.savecopy import copy_saves_for_all_roms, SaveFormat

def test_convert_ed64_to_all_others(tmp_path_factory):
    romdir = tmp_path_factory.mktemp("roms")
    rom_hash = create_rom(romdir/"Game.z64" , b"GAMENAME")
    origdir = tmp_path_factory.mktemp("orig")
    create_file(origdir/"Game.eep", b"eepr", 0x200)
    create_file(origdir/"Game.mpk", b"mpk1", 0x8000)
    create_file(origdir/"Game_Cont_2.mpk", b"mpk2", 0x8000)
    create_file(origdir/"Game_Cont_3.mpk", b"mpk3", 0x8000)
    create_file(origdir/"Game_Cont_4.mpk", b"mpk4", 0x8000)
    create_file(origdir/"Game.srm", b"sram", 0x8000)
    create_file(origdir/"Game.fla", b"flas", 0x20000)

    ed64dir = tmp_path_factory.mktemp("ed64")
    copy_saves_for_all_roms(romdir, False, SaveFormat.EVERDRIVE, origdir, SaveFormat.EVERDRIVE, ed64dir)
    ed64_eeprom = read_file(ed64dir/"Game.eep")
    # Everdrive EEPROM length will match original
    assert len(ed64_eeprom) == 0x200
    # Everdrive EEPROM will match original
    assert ed64_eeprom[0:0x4] == b"eepr"
    # Everdrive MPKs will match original
    assert read_file(ed64dir/"Game.mpk")[0:0x4] == b"mpk1"
    assert read_file(ed64dir/"Game_Cont_2.mpk")[0:0x4] == b"mpk2"
    assert read_file(ed64dir/"Game_Cont_3.mpk")[0:0x4] == b"mpk3"
    assert read_file(ed64dir/"Game_Cont_4.mpk")[0:0x4] == b"mpk4"
    # Everdrive SRAM will match original
    assert read_file(ed64dir/"Game.srm")[0:0x4] == b"sram"
    # Everdrive flash RAM will match original
    assert read_file(ed64dir/"Game.fla")[0:0x4] == b"flas"

    mupendir = tmp_path_factory.mktemp("mupen")
    copy_saves_for_all_roms(romdir, False, SaveFormat.EVERDRIVE, origdir, SaveFormat.MUPEN64PLUS, mupendir)
    mupen_savefile = read_file(mupendir/"Game.srm")
    # Mupen SRMs are always the length of all possible files, combined
    assert len(mupen_savefile) == 296960
    # Mupen EEPROM will match Everdrive
    assert mupen_savefile[0:0x4] == b"eepr"
    # Mupen MPKs will match Everdrive
    assert mupen_savefile[0x800:0x804] == b"mpk1"
    assert mupen_savefile[0x8800:0x8804] == b"mpk2"
    assert mupen_savefile[0x10800:0x10804] == b"mpk3"
    assert mupen_savefile[0x18800:0x18804] == b"mpk4"
    # Mupen SRAM uses little-endian
    assert mupen_savefile[0x20800:0x20804] == b"mars"
    # Mupen flash RAM uses little-endian
    assert mupen_savefile[0x28800:0x28804] == b"salf"

    pj64basedir = tmp_path_factory.mktemp("pj64")
    copy_saves_for_all_roms(romdir, False, SaveFormat.EVERDRIVE, origdir, SaveFormat.PROJECT64, pj64basedir)
    pj64dir = pj64basedir / ("GAMENAME-" + rom_hash.upper())
    pj64_eeprom = read_file(pj64dir/"GAMENAME.eep")
    # Project64 EEPROM length will match Everdrive
    assert len(pj64_eeprom) == 0x200
    # Project64 EEPROM will match Everdrive
    assert pj64_eeprom[0:0x4] == b"eepr"
    # Project64 MPKs will match Everdrive
    assert read_file(pj64dir/"GAMENAME_Cont_1.mpk")[0:0x4] == b"mpk1"
    assert read_file(pj64dir/"GAMENAME_Cont_2.mpk")[0:0x4] == b"mpk2"
    assert read_file(pj64dir/"GAMENAME_Cont_3.mpk")[0:0x4] == b"mpk3"
    assert read_file(pj64dir/"GAMENAME_Cont_4.mpk")[0:0x4] == b"mpk4"
    # Project64 SRAM uses little-endian
    assert read_file(pj64dir/"GAMENAME.sra")[0:0x4] == b"mars"
    # Project64 flash RAM uses little-endian
    assert read_file(pj64dir/"GAMENAME.fla")[0:0x4] == b"salf"


def create_rom(path, game_name_bytestring):
    data = b"\x80\x37\x12\x40".ljust(0x20, b"\x00")
    data += game_name_bytestring.ljust(0x14, b"\x20")
    data += b"\x00" * 7
    data += b"NXXE"
    data = data.ljust(0x200, b"\x00")
    create_file(path, data, 0x200)
    # file is created, now calculate and return hash
    rom_bytearray = bytearray(data)
    swap(rom_bytearray, True, True)
    hash_md5 = hashlib.md5()
    hash_md5.update(rom_bytearray)
    return hash_md5.hexdigest()

def create_file(path, bytestring, total_size):
    path.write_bytes(bytestring.ljust(total_size, b"\x00"))

def read_file(path):
    return path.read_bytes()
