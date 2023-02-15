# n64savegametools

Nintendo 64 savegame conversion and copying tools.

May be useful if you use emulators like RetroArch (which internally uses Mupen64+), Project64, or an Everdrive 64, and want to sync saves across them.

NOTE: Functional, but very much a work in progress, and I've hardly ever used Python before, so bear with me if some things are built oddly.

## How to use

Copy Project64 saves into RetroArch (Mupen64+ format):

```sh
python app.py --rom-dir 'X:\roms\n64' \
    --src-format project64 \
    --src-dir 'C:\Program Files (x86)\Project64 3.0\Save' \
    --dst-format mupen64plus \
    --dst-dir 'C:\Program Files (x86)\Steam\steamapps\common\RetroArch\saves'
```

Copy RetroArch (Mupen64+ format) saves to an Everdrive 64 SD card:

```sh
python app.py --rom-dir 'X:\roms\n64' \
    --src-format mupen64plus \
    --src-dir 'C:\Program Files (x86)\Steam\steamapps\common\RetroArch\saves' \
    --dst-format everdrive \
    --dst-dir 'F:\ED64\gamedata'
```

## Details

The app assumes the savegave files are named and organized the default way for each program. For example, if you had ROMs with the following filenames:

```
F-Zero X (USA).z64
Paper Mario (USA).n64
Perfect Dark (USA).v64
```

Everdrive 64's "gamedata" folder should look like:

```
F-Zero X (USA).srm
Paper Mario (USA).fla
Perfect Dark (USA).eep
Perfect Dark (USA).mpk
Perfect Dark (USA)_Cont_2.mpk
```

Project64's "Save" folder should look like:

```
F-ZERO X-097DD1B59B459B2EEB4D821441946768/
    F-ZERO X.sra
PAPER MARIO-BA04CD8C8B8EB7DFC698D9C4C8E40785/
    PAPER MARIO.fla
Perfect Dark-ECACDBDC93C3087627A775DCC16AEC7A/
    Perfect Dark.eep
    Perfect Dark_Cont_1.mpk
    Perfect Dark_Cont_2.mpk
```

RetroArch's "saves" folder should look like:

```
F-Zero X (USA).srm
Paper Mario (USA).srm
Perfect Dark (USA).srm
```

## Limitations

 *  Has no tests
     *  I intend to fix this first, once I learn how.
 *  Requires Python to be installed
     *  Automating the creation of executable releases via PyInstaller would be nice
 *  Has only a CLI
     *  A GUI would be more accessible; maybe someday?
 *  Has no configuration
     *  Eventually it'd be nice to set the directories in config, rather than specifying them each time.
 *  Only overwrites saves when the source save has a newer timestamp
     *  This is optional internally, but it's not yet exposed.
 *  Backs up saves before overwriting, by placing them in a "backup" folder
     *  This is optional internally, but it's not yet exposed.
