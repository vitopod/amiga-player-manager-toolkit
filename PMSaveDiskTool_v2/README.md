# PMSaveDiskTool v2

Cross-platform save disk editor for **Player Manager** (Anco, 1990) on Amiga.

This project is a cross-platform rewrite of **PMSaveDiskTool v1.2** by **UltimateBinary**
(http://www.ultimatebinary.com). All credit for the original Windows tool, the save disk format
research, and the field naming conventions goes to UltimateBinary. This version adds Mac and
Linux support, player name generation from the game disk, and a command-line interface.

---

## Requirements

- Python 3.8+
- No external dependencies (tkinter is included with Python)

## Quick Start

**GUI:**

```
python3 pm_gui.py
```

**CLI:**

```
python3 pm_cli.py list-saves Save1_PM.adf
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav --team 0
python3 pm_cli.py show-player Save1_PM.adf --save pm1.sav --id 42
python3 pm_cli.py edit-player Save1_PM.adf --save pm1.sav --id 42 --age 20 --pace 200
```

With player names (requires game disk ADF):

```
python3 pm_cli.py list-players Save1_PM.adf --save pm1.sav --team 0 \
    --game-adf PlayerManagerITA.adf
```

## Features

- Open any Player Manager save disk ADF image
- **Load game ADF to show Italian player names** (decompressed from game executable)
- Browse players by team or view all/free agents
- View and edit all player attributes: age, position, skills, career stats
- Save changes back to ADF — byte-for-byte compatible with PMSaveDiskTool v1.2
- Works on Mac, Linux, and Windows

## Project Structure

```
pm_core/          Core library (zero dependencies)
  adf.py          ADF disk image I/O
  player.py       42-byte player record parsing/serialization
  save.py         Save file and player database handling
  names.py        DEFAJAM decompressor + name generation from RNG seeds
pm_gui.py         tkinter GUI
pm_cli.py         Command-line interface
tests/            Test suite (19 tests, all verified against Save1_PM.adf)
```

## Tests

```
python3 -m pytest tests/ -v
```

## Credits

- **PMSaveDiskTool v1.2** by UltimateBinary (http://www.ultimatebinary.com) — original
  Windows tool, save disk format research, and field naming. This project would not exist
  without that work.
- **Player Manager** by Anco Software (1990) — the game.
- **Dino Dini** (https://github.com/dndn1011) — original programmer of Player Manager.
  The game that started it all.

## License

This project is not affiliated with or endorsed by Anco Software or UltimateBinary.
Reverse-engineering was performed for interoperability purposes only.
