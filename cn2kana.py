from __future__ import annotations

from pypinyin import Style, pinyin
from pypinyin.contrib.tone_convert import to_normal
from pypinyin.pinyin_dict import pinyin_dict

INITIALS = (
    "zh",
    "ch",
    "sh",
    "b",
    "p",
    "m",
    "f",
    "d",
    "t",
    "n",
    "l",
    "g",
    "k",
    "h",
    "j",
    "q",
    "x",
    "r",
    "z",
    "c",
    "s",
    "y",
    "w",
)

ROWS = {
    "": {"a": "ア", "i": "イ", "u": "ウ", "e": "エ", "o": "オ"},
    "b": {"a": "バ", "i": "ビ", "u": "ブ", "e": "ベ", "o": "ボ"},
    "p": {"a": "パ", "i": "ピ", "u": "プ", "e": "ペ", "o": "ポ"},
    "m": {"a": "マ", "i": "ミ", "u": "ム", "e": "メ", "o": "モ"},
    "f": {"a": "ファ", "i": "フィ", "u": "フ", "e": "フェ", "o": "フォ"},
    "d": {"a": "ダ", "i": "ディ", "u": "ドゥ", "e": "デ", "o": "ド"},
    "t": {"a": "タ", "i": "ティ", "u": "トゥ", "e": "テ", "o": "ト"},
    "n": {"a": "ナ", "i": "ニ", "u": "ヌ", "e": "ネ", "o": "ノ"},
    "l": {"a": "ラ", "i": "リ", "u": "ル", "e": "レ", "o": "ロ"},
    "g": {"a": "ガ", "i": "ギ", "u": "グ", "e": "ゲ", "o": "ゴ"},
    "k": {"a": "カ", "i": "キ", "u": "ク", "e": "ケ", "o": "コ"},
    "h": {"a": "ハ", "i": "ヒ", "u": "フ", "e": "ヘ", "o": "ホ"},
    "j": {"a": "ジャ", "i": "ジ", "u": "ジュ", "e": "ジェ", "o": "ジョ"},
    "q": {"a": "チャ", "i": "チ", "u": "チュ", "e": "チェ", "o": "チョ"},
    "x": {"a": "シャ", "i": "シ", "u": "シュ", "e": "シェ", "o": "ショ"},
    "zh": {"a": "ジャ", "i": "ジ", "u": "ジュ", "e": "ジェ", "o": "ジョ"},
    "ch": {"a": "チャ", "i": "チ", "u": "チュ", "e": "チェ", "o": "チョ"},
    "sh": {"a": "シャ", "i": "シ", "u": "シュ", "e": "シェ", "o": "ショ"},
    "r": {"a": "ラ", "i": "リ", "u": "ル", "e": "レ", "o": "ロ"},
    "z": {"a": "ザ", "i": "ズ", "u": "ズ", "e": "ゼ", "o": "ゾ"},
    "c": {"a": "ツァ", "i": "ツ", "u": "ツ", "e": "ツェ", "o": "ツォ"},
    "s": {"a": "サ", "i": "ス", "u": "ス", "e": "セ", "o": "ソ"},
    "y": {"a": "ヤ", "i": "イ", "u": "ユ", "e": "イェ", "o": "ヨ"},
    "w": {"a": "ワ", "i": "ウィ", "u": "ウ", "e": "ウェ", "o": "ウォ"},
}

FINALS = {
    "a": ("a", ""),
    "o": ("o", ""),
    "e": ("e", ""),
    "i": ("i", ""),
    "u": ("u", ""),
    "ai": ("a", "イ"),
    "ei": ("e", "イ"),
    "ao": ("a", "オ"),
    "ou": ("o", "ウ"),
    "an": ("a", "ン"),
    "en": ("e", "ン"),
    "ang": ("a", "ン"),
    "eng": ("e", "ン"),
    "ong": ("o", "ン"),
    "ia": ("i", "ア"),
    "ie": ("i", "エ"),
    "iao": ("i", "アオ"),
    "iu": ("i", "ウ"),
    "ian": ("i", "エン"),
    "in": ("i", "ン"),
    "iang": ("i", "アン"),
    "ing": ("i", "ン"),
    "iong": ("i", "オン"),
    "ua": ("u", "ア"),
    "uo": ("u", "オ"),
    "uai": ("u", "アイ"),
    "ui": ("u", "イ"),
    "uan": ("u", "アン"),
    "un": ("u", "ン"),
    "uang": ("u", "アン"),
    "ueng": ("u", "エン"),
    "ue": ("u", "エ"),
    "ve": ("u", "エ"),
    "van": ("u", "アン"),
    "vn": ("u", "ン"),
}

JQ_FINALS = {
    "ia": ("a", ""),
    "ie": ("e", ""),
    "iao": ("a", "オ"),
    "iu": ("u", "ウ"),
    "ian": ("i", "エン"),
    "in": ("i", "ン"),
    "iang": ("a", "ン"),
    "ing": ("i", "ン"),
    "iong": ("o", "ン"),
    "uan": ("u", "エン"),
    "un": ("u", "ン"),
    "ue": ("u", "エ"),
}

SPECIAL = {
    "er": "アル",
    "m": "ム",
    "n": "ン",
    "ng": "ン",
    "hm": "フム",
    "hng": "フン",
}

PUNCTUATION = str.maketrans(
    {
        "，": "、",
        "；": "、",
        "：": "、",
    }
)


def _syllables() -> frozenset[str]:
    values: set[str] = set()
    for raw in pinyin_dict.values():
        values.update(to_normal(item) for item in raw.split(","))
    return frozenset(values)


SYLLABLES = _syllables()


def _v_base(initial: str) -> str:
    if not initial:
        return "ユ"
    if initial in ("l", "n"):
        return ROWS[initial]["i"] + "ュ"
    return ROWS[initial]["u"]


def _syllable_to_kana(syllable: str) -> str:
    if syllable in SPECIAL:
        return SPECIAL[syllable]

    initial = ""
    final = syllable
    for candidate in INITIALS:
        if syllable.startswith(candidate):
            initial = candidate
            final = syllable[len(candidate) :]
            break

    if not final:
        return ROWS[initial]["i"]

    if final.startswith("v"):
        base = _v_base(initial)
        suffix = {"": "", "e": "エ", "an": "アン", "n": "ン"}.get(final[1:])
        return base + suffix if suffix is not None else syllable

    if initial in ("j", "q", "x") and final in JQ_FINALS:
        vowel, suffix = JQ_FINALS[final]
        return ROWS[initial][vowel] + suffix

    if initial == "y" and final == "uan":
        return "ユエン"

    if final not in FINALS:
        return syllable

    vowel, suffix = FINALS[final]
    return ROWS[initial][vowel] + suffix


def convert(text: str) -> str:
    if not text:
        return text

    groups = pinyin(text, style=Style.NORMAL, errors=lambda value: [value])
    output: list[str] = []
    for group in groups:
        if len(group) == 1 and group[0] in SYLLABLES:
            output.append(_syllable_to_kana(group[0]))
        else:
            output.append("".join(group))
    return "".join(output).translate(PUNCTUATION)
