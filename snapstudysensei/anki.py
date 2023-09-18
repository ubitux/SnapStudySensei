import base64
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.request import Request, urlopen


@dataclass
class AnkiNote:
    word: str
    context_picture: Path | None
    context_sentence: str
    word_reading: str
    word_glossary: str
    word_audio: Path | None = None
    extra_info: str = ""
    anki_id: int = -1

    def get_qml_record(self):
        assert self.anki_id != -1
        reading = self.word_reading.replace("[", "「").replace("]", "」") if self.word_reading else self.word
        return dict(
            record_id=str(self.anki_id),  # QML doesn't support 64-bit integers (javascript bs)
            reading=reading,
            meaning=self.word_glossary,
        )


class AnkiConnect:
    PREFIX = "SnapStudySensei"
    DECK_NAME = f"Japanese::{PREFIX}"
    MODEL_NAME = f"{PREFIX} Word"

    def __init__(self):
        deck_ids = self.query("deckNamesAndIds")
        deck_id = deck_ids.get(self.DECK_NAME)
        if deck_id is None:
            deck_id = self.query("createDeck", deck=self.DECK_NAME)

        model_ids = self.query("modelNamesAndIds")
        model_id = model_ids.get(self.MODEL_NAME)
        if model_id is None:
            tpl_dir = Path(__file__).resolve().parent / "data"
            front = open(tpl_dir / "front.html").read()
            back = open(tpl_dir / "back.html").read()
            css = open(tpl_dir / "style.css").read()

            model_id = self.query(
                "createModel",
                modelName=self.MODEL_NAME,
                inOrderFields=[
                    "Word",
                    "ContextPicture",
                    "ContextSentence",
                    "WordReading",
                    "WordGlossary",
                    "WordAudio",
                    "ExtraInfo",
                ],
                css=css,
                cardTemplates=[dict(Front=front, Back=back)],
            )

        self.media_dir_path = Path(self.query("getMediaDirPath"))

    def add_note(self, note: AnkiNote) -> AnkiNote:
        # Craft a ruby string for Anki furigana text on the back side
        reading = note.word
        if note.word_reading and note.word_reading != note.word:
            reading += f"[{note.word_reading}]"

        params = dict(
            deckName=self.DECK_NAME,
            modelName=self.MODEL_NAME,
            fields=dict(
                Word=note.word,
                ContextSentence=note.context_sentence,
                WordReading=reading,
                WordGlossary=note.word_glossary,
                ExtraInfo=note.extra_info,
            ),
            options=dict(allowDuplicate=True),
            tags=[self.PREFIX],
        )

        if note.context_picture:
            with open(note.context_picture, "rb") as f:
                picture_filename, data_base64 = self._get_file(note.context_picture)
            params["picture"] = [dict(filename=picture_filename, data=data_base64, fields=["ContextPicture"])]

        if note.word_audio:
            with open(note.word_audio, "rb") as f:
                audio_filename, data_base64 = self._get_file(note.word_audio)
            params["audio"] = [dict(filename=audio_filename, data=data_base64, fields=["WordAudio"])]

        patched_note = AnkiNote(**asdict(note))
        patched_note.word_reading = reading
        patched_note.anki_id = self.query("addNote", note=params)
        return patched_note

    def _get_file(self, filepath: Path) -> tuple[str, str]:
        with open(filepath, "rb") as f:
            content = f.read()

            # Generate a unique filename based on the content
            picture_hash = hashlib.sha256()
            picture_hash.update(content)
            picture_hash = picture_hash.hexdigest()

            # Anki might be a sandboxed app where access to the filesystem is
            # restricted (typical usecase: a flatpak), so we use a base64 encode
            # instead of a file path.
            data_base64 = base64.b64encode(content).decode("utf-8")

        filename = f"{self.PREFIX}_{picture_hash}{filepath.suffix}"

        return filename, data_base64

    def list_notes(self) -> list[AnkiNote]:
        notes = self.query("findNotes", query=f"deck:{self.DECK_NAME}")
        notes_info = self.query("notesInfo", notes=notes)

        notes = []
        for note_info in notes_info:
            fields = note_info["fields"]

            picture_html = fields["ContextPicture"]["value"]
            match = re.search(r'src="(?P<filename>[^"]+)"', picture_html)
            picture_path = self.media_dir_path / match["filename"] if match is not None else None

            audio_markup = fields["WordAudio"]["value"]
            match = re.search(r"\[sound:(?P<filename>[^\]]+)\]", audio_markup)
            audio_path = self.media_dir_path / match["filename"] if match is not None else None

            notes.append(
                AnkiNote(
                    word=fields["Word"]["value"],
                    context_picture=picture_path,
                    context_sentence=fields["ContextSentence"]["value"],
                    word_reading=fields["WordReading"]["value"],
                    word_glossary=fields["WordGlossary"]["value"],
                    word_audio=audio_path,
                    extra_info=fields["ExtraInfo"]["value"],
                    anki_id=note_info["noteId"],
                )
            )

        return notes

    def remove_note(self, anki_id: int):
        self.query("deleteNotes", notes=[anki_id])

    @staticmethod
    def query(action, **params):
        # print(f"Anki: {action}", params)
        request_data = dict(action=action, params=params, version=6)
        request_json = json.dumps(request_data).encode("utf-8")
        response = json.load(urlopen(Request("http://localhost:8765", request_json)))
        if len(response) != 2:
            raise Exception("response has an unexpected number of fields")
        if "error" not in response:
            raise Exception("response is missing required error field")
        if "result" not in response:
            raise Exception("response is missing required result field")
        if response["error"] is not None:
            raise Exception(response["error"])
        return response["result"]


if __name__ == "__main__":
    a = AnkiConnect()
    print(a.list_notes())
