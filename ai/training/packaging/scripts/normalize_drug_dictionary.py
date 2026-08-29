"""Normalize the canonical drug dictionary for packaging annotation."""
from __future__ import annotations
import argparse, json, re, unicodedata
from pathlib import Path

def clean(value: str) -> str:
    """Normalize Unicode, whitespace, and supported strength units."""
    value = unicodedata.normalize("NFKC", str(value)).strip()
    value = re.sub(r"\s+", " ", value)
    return re.sub(r"(?i)(mcg|mg|ml|iu|g|%)", lambda match: "IU" if match.group(1).lower() == "iu" else match.group(1).lower(), value)


def normalize(source: Path, destination: Path) -> int:
    data = json.loads(source.read_text(encoding="utf-8")); drugs = []; seen: set[tuple[str, str, str]] = set()
    for item in data["drugs"]:
        brand = clean(item["brand_name"])
        ingredients = [clean(part) for part in item["active_ingredient"].split("+") if clean(part)]
        strengths = [clean(part) for part in item["strength"].split("/") if clean(part)]
        key = (brand.casefold(), "+".join(ingredients).casefold(), "/".join(strengths).casefold())
        if key in seen: continue
        seen.add(key)
        aliases = {clean(alias) for alias in item.get("aliases", []) if clean(alias)}
        aliases.add(clean(f"{brand} {'/'.join(strengths)}"))
        drugs.append({"id": f"drug_{len(drugs) + 1:06d}", "brand_name": brand, "active_ingredient": ingredients, "strength": strengths, "dosage_form": clean(item.get("dosage_form", "")), "package_description": "Medicine packaging", "registration_number": None, "aliases": sorted(aliases)})
    destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(json.dumps({"version": data.get("version", "1.0.0"), "source": str(source), "drugs": drugs}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); return len(drugs)

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--source", type=Path, default=Path("ai/data/drug_dictionary.json")); parser.add_argument("--destination", type=Path, default=Path("ai/training/packaging/drug_dictionary.json")); args = parser.parse_args(); print(normalize(args.source, args.destination))
if __name__ == "__main__": main()
