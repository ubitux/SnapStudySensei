# SnapStudySensei

**SnapStudySensei** is a tool to assist with capturing, extracting, translating
and recording Japanese flashcards into [Anki].

This project is inspired by [Game2Text] but takes a different technical approach.

![SnapStudySensei screenshot](.screenshot.png)


## Known limitations

- Currently **only supported on Linux and Windows**. Porting it to macOS should
  be doable by adding the ability to list windows (see `windows_list/windows_list_osx.py`, patch
  welcome)
- **No configuration**, only designed for my own needs so far
- A bit **slow to start** due to the OCR model initialization


## Installation

[Anki] and its [Anki-Connect] plugin must be installed.

```sh
python -m venv venv
. venv/bin/activate
pip install -e .
```

### Important note

This is a non-intrusive standalone installation, which means the Qt libraries
are duplicated within the virtual env. This breaks at least the fcitx input
method setup on the system. Setting `IBUS_USE_PORTAL=1 QT_IM_MODULE=ibus` in the
environment can be used as a [workaround] (ibus doesn't need to be installed).

[workaround]: https://github.com/fcitx/fcitx5/discussions/873#discussioncomment-7223614

## Running

[Anki] and its [Anki-Connect] plugin must be running.

Enter the venv (`. venv/bin/activate`) if you used that installation method, and
run `sss`.

### Important note

SnapStudySensei will automatically create a model, deck and flashcard templates
in Anki. The deck is called *SnapStudySensei* and is located in the *Japanese*
category.


## Thanks to

- [Manga OCR](https://github.com/kha-white/manga-ocr/)
- [JMdict](https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project)


[Anki]: https://apps.ankiweb.net
[Anki-Connect]: https://foosoft.net/projects/anki-connect
[Game2Text]: https://game2text.com