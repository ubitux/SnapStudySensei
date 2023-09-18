import gzip
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.request import urlretrieve

from xdg_base_dirs import xdg_data_home


@dataclass(slots=True)
class _Entry:
    rich_title: str
    rich_senses: str
    reading: str
    senses: str


# https://www.edrdg.org/wiki/index.php/JMdict-EDICT_Dictionary_Project
class JDictionary:
    #  JMdict file with only English glosses with example sentence pairs from
    # the Tanaka_Corpus
    DB_NAME = "JMdict_e_examp"
    URL = f"http://ftp.edrdg.org/pub/Nihongo/{DB_NAME}.gz"

    def __init__(self):
        # Download database if needed
        db_path = xdg_data_home() / "SnapStudySensei" / (self.DB_NAME + ".xml")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if not db_path.exists():
            filename, headers = urlretrieve(self.URL, reporthook=self._report_progress)
            with open(db_path, "wb") as dst, gzip.open(filename, "rb") as src:
                dst.write(src.read())
        print(f"{self.DB_NAME}: downloaded")

        # Parse XML
        tree = ET.parse(db_path)
        self._xml_root = tree.getroot()

        # Build index
        self._index = defaultdict(list)
        for i, entry in enumerate(self._xml_root):
            assert entry.tag == "entry"
            for source in "kr":  # kanji, then reading
                for ele in entry.findall(source + "_ele"):
                    eb = ele.find(source + "eb")  # element "body"?
                    assert eb is not None
                    e_pri = ele.find(source + "e_pri")  # element priority
                    priority = self._get_priority_score(e_pri.text if e_pri else None)
                    self._index[eb.text].append((priority, i))

    @staticmethod
    def _report_progress(chunk_nr: int, max_chunk_size: int, total_size: int):
        if total_size == -1:
            return
        progress = chunk_nr * max_chunk_size / total_size * 100
        sys.stdout.write(f"{JDictionary.DB_NAME}: {progress:.1f}%\r")
        sys.stdout.flush()

    @staticmethod
    def _get_priority_score(priority: str | None) -> int:
        # TODO build a better score using the other keys
        if priority is not None and priority.startswith("nf"):
            return int(priority[2:])
        return 100

    def __call__(self, word: str) -> list[dict[str, str]]:
        entries = []

        # All potential keys
        keys = [k for k in self._index.keys() if word in k]

        # Exact match
        entries += sorted(self._index.get(word, []))

        # Other match starting with the word
        for key in keys:
            if key.startswith(word) and key != word:
                entries += sorted(self._index.get(key, []))

        # Remaining matches
        for key in keys:
            if not key.startswith(word) and key != word:
                entries += sorted(self._index.get(key, []))

        ret = []
        for _, entry_id in entries:
            xml_entry = self._xml_root[entry_id]

            keys = []
            colors = dict(k="darkslategray", r="dimgray")
            reading = ""
            for source in "kr":  # kanji, then reading
                color = colors[source]
                for ele in xml_entry.findall(source + "_ele"):
                    eb = ele.find(source + "eb")
                    assert eb is not None
                    keys.append(f'<font color="{color}">{eb.text}</font>')
                    if not reading and source == "r":
                        reading = eb.text

            rich_title = ", ".join(keys)
            assert reading is not None

            senses_list = []
            rich_content = "<ol>"
            for i, sense in enumerate(xml_entry.findall("sense")):
                tags = "".join(f'<li><font color="gray">{pos.text}</font></li>' for pos in sense.findall("pos"))
                if tags:
                    tags = f"<ul>{tags}</ul>"
                glosses = ", ".join(gloss.text for gloss in sense.findall("gloss"))
                rich_content += f"<li>{glosses}{tags}</li>"
                senses_list.append(glosses)
            rich_content += "</ol>"

            if len(senses_list) > 1:
                senses = "\n".join(f"{i}. {sense}" for i, sense in enumerate(senses_list, 1))
            else:
                senses = senses_list[0]

            ret.append(asdict(_Entry(rich_title, rich_content, reading, senses)))

        return ret
