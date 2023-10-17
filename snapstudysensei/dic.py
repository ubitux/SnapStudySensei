import colorsys
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
        self._markers = self._get_frequency_markers()

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
                    e_pri = ele.findall(source + "e_pri")
                    priority = self._get_priority_score(e_pri)
                    self._index[eb.text].append((priority, i))

    @staticmethod
    def _report_progress(chunk_nr: int, max_chunk_size: int, total_size: int):
        if total_size == -1:
            return
        progress = chunk_nr * max_chunk_size / total_size * 100
        sys.stdout.write(f"{JDictionary.DB_NAME}: {progress:.1f}%\r")
        sys.stdout.flush()

    @staticmethod
    def _get_priority_score(element_priorities) -> int:
        # TODO build a better score using the other keys
        for priority in element_priorities:
            if priority.text.startswith("nf"):
                return int(priority.text[2:])
        return 100

    @staticmethod
    def _mix(a, b, x):
        return a * (1 - x) + b * x

    @staticmethod
    def _linear(a, b, x):
        return (x - a) / (b - a)

    @classmethod
    def _remap(cls, a, b, c, d, x):
        return cls._mix(c, d, cls._linear(a, b, x))

    @staticmethod
    def _clamp(x, a, b):
        return min(b, max(a, x))

    @classmethod
    def _get_frequency_markers(cls) -> list[str]:
        numbers = "❶ ❷ ❸ ❹ ❺ ❻ ❼ ❽ ❾ ❿"
        markers = []
        for i, number in enumerate(numbers):
            hue = cls._remap(0, len(numbers) - 1, 0.4, 1.0, i)
            color = colorsys.hls_to_rgb(hue, 0.4, 1.0)
            color = tuple(round(c * 255) & 0xFF for c in color)
            color = "#" + "".join(f"{c:02x}" for c in color)
            markers.append(f'<font color="{color}">{number}</font> ')
        return markers

    def _get_frequency_marker(self, priority: int) -> str:
        if priority == 100:
            return ""
        # grep -o 'nf[0-9][0-9]' JMdict_e_examp.xml|sort|uniq -c
        # shows that nfXX doesn't go above nf48 (which we round to 50)
        marker_id = int(self._remap(1, 50, 0, len(self._markers) - 1, priority))
        marker_id = self._clamp(marker_id, 0, len(self._markers) - 1)
        return self._markers[marker_id]

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
        for priority, entry_id in entries:
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

            rich_title = self._get_frequency_marker(priority) + ", ".join(keys)
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
