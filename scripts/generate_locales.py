#!/usr/bin/env python3
"""Generate locale JSON files from en.json using Google Translate (via deep-translator)."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / "frontend" / "public" / "app" / "locales"
EN_FILE = LOCALES / "en.json"
LANG_FILE = LOCALES / "languages.json"

TRANSLATE_MAP = {
    "zh-CN": "zh-CN",
    "zh-TW": "zh-TW",
    "he": "iw",
    "jv": "jw",
    "ceb": "ceb",
    "eo": "eo",
    "fy": "fy",
    "gd": "gd",
    "ht": "ht",
    "lb": "lb",
    "mg": "mg",
    "mi": "mi",
    "mt": "mt",
    "ny": "ny",
    "or": "or",
    "rw": "rw",
    "sd": "sd",
    "so": "so",
    "tg": "tg",
    "tk": "tk",
    "tt": "tt",
    "ug": "ug",
}


def flatten(obj: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in obj.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten(v, key))
        else:
            out[key] = str(v)
    return out


def unflatten(flat: dict[str, str]) -> dict:
    out: dict = {}
    for key, val in flat.items():
        parts = key.split(".")
        cur = out
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = val
    return out


def protect_placeholders(text: str) -> tuple[str, list[str]]:
    placeholders: list[str] = []

    def repl(m: re.Match[str]) -> str:
        placeholders.append(m.group(0))
        return f"__PH{len(placeholders)-1}__"

    protected = re.sub(r"\{\{\w+\}\}", repl, text)
    return protected, placeholders


def restore_placeholders(text: str, placeholders: list[str]) -> str:
    for i, ph in enumerate(placeholders):
        text = text.replace(f"__PH{i}__", ph)
    return text


def prepare_for_translate(text: str) -> tuple[str, list[str]]:
    protected, placeholders = protect_placeholders(text)
    protected = protected.replace("<code>", "〈code〉").replace("</code>", "〈/code〉")
    return protected, placeholders


def finish_translate(text: str, placeholders: list[str]) -> str:
    text = (text or "").replace("〈code〉", "<code>").replace("〈/code〉", "</code>")
    return restore_placeholders(text, placeholders)


def translate_one(translator, text: str, *, retries: int = 4) -> str:
    if not text.strip():
        return text
    src, placeholders = prepare_for_translate(text)
    for attempt in range(retries):
        try:
            result = finish_translate(translator.translate(src), placeholders)
            if result and result != text:
                return result
        except Exception:
            pass
        time.sleep(0.35 * (attempt + 1))
    return text


def english_ratio(flat_en: dict[str, str], flat_loc: dict[str, str]) -> float:
    if not flat_en:
        return 1.0
    same = sum(1 for k, v in flat_en.items() if flat_loc.get(k) == v)
    return same / len(flat_en)


def untranslated_codes(flat_en: dict[str, str], threshold: float = 0.45) -> list[str]:
    codes: list[str] = []
    for path in sorted(LOCALES.glob("*.json")):
        if path.stem in ("en", "languages"):
            continue
        flat = flatten(json.loads(path.read_text(encoding="utf-8")))
        if english_ratio(flat_en, flat) >= threshold:
            codes.append(path.stem)
    return codes


def translate_batch(translator, texts: list[str], *, batch_size: int = 20) -> list[str]:
    results: list[str] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        prepared = [prepare_for_translate(t) for t in batch]
        try:
            out = translator.translate_batch([p[0] for p in prepared])
            for orig, (src, ph), tr in zip(batch, prepared, out):
                results.append(finish_translate(tr, ph))
        except Exception:
            for text in batch:
                results.append(translate_one(translator, text))
        time.sleep(0.12)
    return results


def merge_missing_language(code: str, flat_en: dict[str, str]) -> str:
    """Translate only keys missing or still English in an existing locale file."""
    from deep_translator import GoogleTranslator

    out_path = LOCALES / f"{code}.json"
    if code == "en":
        en = json.loads(EN_FILE.read_text(encoding="utf-8"))
        out_path.write_text(json.dumps(en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return f"{code} (source)"

    flat_loc: dict[str, str] = {}
    if out_path.exists():
        flat_loc = flatten(json.loads(out_path.read_text(encoding="utf-8")))

    missing = [k for k in flat_en if k not in flat_loc or flat_loc[k] == flat_en[k]]
    if not missing:
        return f"{code} (up to date)"

    target = TRANSLATE_MAP.get(code, code.split("-")[0])
    translator = GoogleTranslator(source="en", target=target)
    texts = [flat_en[k] for k in missing]
    translated = translate_batch(translator, texts)
    for key, val in zip(missing, translated):
        if val == flat_en[key]:
            val = translate_one(translator, flat_en[key], retries=5)
        flat_loc[key] = val

    out_path.write_text(
        json.dumps(unflatten(flat_loc), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return f"{code} merged {len(missing)} keys"


def translate_language(code: str, flat_en: dict[str, str], force: bool) -> str:
    from deep_translator import GoogleTranslator

    out_path = LOCALES / f"{code}.json"
    if code == "en":
        en = json.loads(EN_FILE.read_text(encoding="utf-8"))
        out_path.write_text(json.dumps(en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return f"{code} (source)"

    if out_path.exists() and not force:
        flat = flatten(json.loads(out_path.read_text(encoding="utf-8")))
        if english_ratio(flat_en, flat) < 0.45:
            return f"{code} (ok, skip)"

    target = TRANSLATE_MAP.get(code, code.split("-")[0])
    translator = GoogleTranslator(source="en", target=target)
    keys = list(flat_en.keys())
    texts = [flat_en[k] for k in keys]
    translated = translate_batch(translator, texts)
    flat_out = dict(zip(keys, translated))

    for key in keys:
        if flat_out[key] == flat_en[key]:
            flat_out[key] = translate_one(translator, flat_en[key], retries=5)

    ratio = english_ratio(flat_en, flat_out)
    if ratio >= 0.45:
        return f"{code} WARN still {ratio:.0%} English"

    out_path.write_text(
        json.dumps(unflatten(flat_out), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return f"{code} ok ({ratio:.0%} English remaining)"


def main() -> None:
    try:
        from deep_translator import GoogleTranslator  # noqa: F401
    except ImportError:
        print("Install: python3 -m pip install deep-translator", file=sys.stderr)
        sys.exit(1)

    args = sys.argv[1:]
    force = "--force" in args
    fix_untranslated = "--fix-untranslated" in args
    merge_missing = "--merge-missing" in args
    workers = 1
    if "--workers" in args:
        workers = max(1, int(args[args.index("--workers") + 1]))
    only = [a for a in args if not a.startswith("--") and a != str(workers)]

    flat_en = flatten(json.loads(EN_FILE.read_text(encoding="utf-8")))
    catalog = json.loads(LANG_FILE.read_text(encoding="utf-8"))

    if only:
        codes = only
    elif fix_untranslated:
        codes = untranslated_codes(flat_en)
        print(f"Regenerating {len(codes)} untranslated locales…", flush=True)
    else:
        codes = list(catalog["all"].keys())

    force = force or fix_untranslated

    def run_one(code: str) -> str:
        try:
            if merge_missing:
                return merge_missing_language(code, flat_en)
            return translate_language(code, flat_en, force)
        except Exception as exc:
            return f"{code} FAILED: {exc}"

    if workers > 1 and len(codes) > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(run_one, code): code for code in codes}
            for fut in as_completed(futures):
                print(fut.result(), flush=True)
    else:
        for code in codes:
            print(run_one(code), flush=True)
            time.sleep(0.15)

    print("Done.", flush=True)


if __name__ == "__main__":
    main()
