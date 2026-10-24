#!/usr/bin/env python3
"""Taishanese Wiktionary-romanization  ->  IPA.

Tables taken verbatim from
  Wiktionary:Chinese entry guidelines/Cantonese/Taishanese
which transcribes the Taicheng dialect and is the same data source that
produces the |c-t= parameter on en.wiktionary character pages.
"""
import re

# --- Initials: transcription -> IPA ---
INITIALS = {
    "lh": "ɬ",
    "ng": "ᵑɡ",
    "b": "p", "p": "pʰ", "m": "ᵐb", "f": "f", "v": "v",
    "d": "t", "t": "tʰ", "n": "ⁿd", "l": "l",
    "g": "k", "k": "kʰ",
    "z": "t͡s", "c": "t͡sʰ",
    "y": "j", "s": "s", "h": "h",
}

# --- Rhymes: transcription -> IPA (longest match wins) ---
RHYMES = {
    "uung": "ɵŋ", "uut": "ɵt̚", "uuk": "ɵk̚",
    "iang": "iaŋ", "iam": "iam", "iap": "iap̚", "iak": "iak̚", "iau": "iau",
    "ong": "ɔŋ", "ok": "ɔk̚",
    "ang": "aŋ", "am": "am", "an": "an", "ai": "ai", "au": "au",
    "ap": "ap̚", "at": "at̚", "ak": "ak̚",
    "ie": "iɛ", "iu": "iu", "im": "im", "in": "in",
    "ip": "ip̚", "it": "it̚",
    "ui": "ui", "un": "un", "ut": "ut̚",
    "ei": "ei", "eu": "eu", "em": "em", "en": "en", "ep": "ep̚", "et": "et̚",
    "oi": "ᵘɔi", "on": "ᵘɔn", "ot": "ᵘɔt̚",
    "m": "m̩",
    "a": "a", "i": "i", "u": "u", "e": "ə", "o": "ᵘɔ",
}

# --- Tones: numeral -> IPA contour ---
TONES = {"1": "˧", "2": "˥", "3": "˨", "4": "˨˩", "5": "˧˩"}
# changed tones (original -> changed contour)
CHANGED = {"1*": "˧˥", "3*": "˨˥", "4*": "˨˩˥", "5*": "˧˨˥"}
# the "-4" dipping change targets tone 4's low-falling... (per guideline: dipping = ˨˩)
DIP = "˨˩"

_INIT_KEYS = sorted(INITIALS, key=len, reverse=True)
_RHYME_KEYS = sorted(RHYMES, key=len, reverse=True)

SYL_RE = re.compile(r"^(?P<base>[a-z]+?)(?P<tone>[1-5])(?P<dip>-\d)?(?P<star>\*)?$")


def syllable_to_ipa(syl: str):
    """'lham1' -> ('ɬam˧', None). Returns (ipa, error)."""
    m = SYL_RE.match(syl.strip())
    if not m:
        return None, f"unparseable syllable: {syl!r}"
    base = m.group("base")
    tone = m.group("tone")
    dip = m.group("dip")
    star = m.group("star") or ""

    # syllabic nasals: bare "m" (or "ng") is a rhyme, not an initial
    if base in ("m", "ng"):
        ini, rest, rh_override = "", "", {"m": "m̩", "ng": "ŋ̩"}[base]
    else:
        ini, rest, rh_override = "", base, None

    if rh_override is None:
        # initial = longest matching prefix
        for k in _INIT_KEYS:
            if base.startswith(k):
                ini, rest = INITIALS[k], base[len(k):]
                break

        # rhyme = longest matching prefix of remainder (must consume all)
        rhyme_ipa = None
        for k in _RHYME_KEYS:
            if rest.startswith(k) and len(k) == len(rest):
                rhyme_ipa = RHYMES[k]
                break
        if rhyme_ipa is None and rest == "":
            rhyme_ipa = ""          # sil
        if rhyme_ipa is None:
            return None, f"unknown rhyme {rest!r} (syllable {syl!r})"
    else:
        rhyme_ipa = rh_override

    if star and dip:
        contour = CHANGED["4*"]      # combined: dip to low-falling, then rise
    elif star:
        contour = CHANGED.get(tone + "*")
        if contour is None:
            return None, f"bad changed tone {syl!r}"
    elif dip:
        contour = DIP        # dipping change
    else:
        contour = TONES[tone]

    return f"{ini}{rhyme_ipa}{contour}", None


def word_to_ipa(rt: str):
    """'lham1' or comma/space separated variants -> (ipa, errors)."""
    out, errs = [], []
    for var in re.split(r"[,，、]", rt):
        var = var.strip()
        if not var:
            continue
        ipa, e = syllable_to_ipa(var)
        if e:
            errs.append(e)
        else:
            out.append(ipa)
    return out, errs


if __name__ == "__main__":
    # Validation against the guideline page's own worked examples
    checks = [
        ("ngei", None, None),  # placeholder
    ]
    tests = {
        "lham1": "ɬam˧",     # 三
        "va5": "va˧˩",        # 話 (initial v, /a/, tone5 mid-falling)
        "ngin3": "ᵑɡin˨",     # 人
        "ni4": "ⁿdi˨˩",       # 你
        "m1": "m̩˧",           # 五/唔-ish syllabic nasal
        "hau2": "hau˥",       # 口
        "hau1": "hau˧",       # 偷
        "hong3*": "hɔŋ˨˥",    # 糖 (changed tone)
        "nguuk5-4": "ᵑɡɵk̚˨˩",  # 肉
        "cat1-4*": "t͡sʰat̚˨˩˥",  # 刷
    }
    ok = 0
    for k, want in tests.items():
        got, err = syllable_to_ipa(k)
        flag = "OK " if got == want else "!! "
        if got == want:
            ok += 1
        print(f"{flag}{k:10s} -> {got}   (expected {want})  {err or ''}")
    print(f"\n{ok}/{len(tests)} self-tests pass")
