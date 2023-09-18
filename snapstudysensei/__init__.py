def _init_ocr():
    print(":: initializing Optical Character Recognition")
    from snapstudysensei.ocr import OCRWrapper

    return OCRWrapper()


def _init_dic():
    print(":: initializing dictionary")
    from snapstudysensei.dic import JDictionary

    return JDictionary()


def _init_tts():
    print(":: initializing Text-To-Speech")
    from snapstudysensei.tts import TTSWrapper

    return TTSWrapper()


def run():
    # These initializations could be slow; having a special loading UI or
    # splashscreen during their init might make sense
    ocr = _init_ocr()
    dic = _init_dic()
    tts = _init_tts()

    from snapstudysensei.main import run as main_run

    main_run(ocr, dic, tts)
