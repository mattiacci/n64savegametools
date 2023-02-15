#!/usr/bin/env python3
"""
A utility that can convert Nintendo 64 savegames into various formats.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import logging
import textwrap
from n64savegametools.savecopy import copy_saves_for_all_roms, SaveFormat

def main():
    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description=textwrap.dedent("""
            A utility that can convert Nintendo 64 savegames into various formats.
            """),
        epilog=textwrap.dedent(r"""
            Example usage to convert Project64 saves into Mupen64+ (i.e. RetroArch) format:
            python app.py --rom-dir 'X:\roms\n64' \
                --src-format project64 \
                --src-dir 'C:\Program Files (x86)\Project64 3.0\Save' \
                --dst-format mupen64plus \
                --dst-dir 'C:\Program Files (x86)\Steam\steamapps\common\RetroArch\saves'
            """))
    parser.add_argument('-r', '--recursive', action="store_true",
        help="Search the provided ROM directory recursively")
    parser.add_argument('--rom-dir', required=True, action="store",
        help="Directory of N64 ROMs")
    parser.add_argument('--src-format', required=True, action="store",
        choices=('everdrive', 'mupen64plus', 'project64'),
        help="Source directory's savegame format")
    parser.add_argument('--src-dir', required=True, action="store",
        help="Source directory for savegames")
    parser.add_argument('--dst-format', required=True, action="store",
        choices=('everdrive', 'mupen64plus', 'project64'),
        help="Destination directory's savegame format")
    parser.add_argument('--dst-dir', required=True, action="store",
        help="Destination directory for savegames")
    parser.add_argument('--loglevel', action="store", default='warning',
        choices=('critical', 'error', 'warning', 'info', 'debug'),
        help="Set the log level")
    args = parser.parse_args()

    loglevel = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(loglevel, int):
        raise ValueError('Invalid log level: %s' % args.copy_saves_for_all_roms)
    src_format = getattr(SaveFormat, args.src_format.upper(), None)
    if src_format is None:
        raise ValueError('Invalid source format: %s' % args.src_format)
    dst_format = getattr(SaveFormat, args.dst_format.upper(), None)
    if dst_format is None:
        raise ValueError('Invalid destination format: %s' % args.dst_format)

    logging.basicConfig(level=loglevel)
    copy_saves_for_all_roms(args.rom_dir, args.recursive, src_format, args.src_dir, dst_format, args.dst_dir)

if __name__ == "__main__":
    main()
