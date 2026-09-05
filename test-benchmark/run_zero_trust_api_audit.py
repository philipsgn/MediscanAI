"""
Zero-Trust Source Capability Audit Script for MediscanAI
Executes REAL HTTP requests against RxNav/RxNorm REST API and OpenFDA REST API.
Measures exact response payloads, HTTP status codes, JSON paths, candidate lists, and brand->ingredient traversals.
"""
import sys
import os
import json
import time
from pathlib import Path
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
OPENFDA_BASE = "https://api.fda.gov/drug"

TEST_QUERIES = [
    {"type": "generic", "query": "Paracetamol", "note": "International generic (Paracetamol / Acetaminophen)"},
    {"type": "generic", "query": "Acetaminophen", "note": "US generic term"},
    {"type": "brand", "query": "Lipitor", "note": "International single-ingredient brand"},
    {"type": "brand", "query": "Tylenol", "note": "US Brand name"},
    {"type": "brand", "query": "Augmentin", "note": "International combination brand (Amoxicillin + Clavulanate)"},
    {"type": "brand", "query": "Panadol", "note": "Global brand name"},
    {"type": "brand", "query": "Vicodin", "note": "US combination brand (Hydrocodone + Acetaminophen)"},
    {"type": "ambiguous", "query": "Derma", "note": "Short/ambiguous term"},
    {"type": "vietnamese", "query": "Hapacol", "note": "Vietnamese local brand"},
    {"type": "vietnamese", "query": "Alpha Choay", "note": "Vietnamese local enzyme brand"},
    {"type": "vietnamese", "query": "Oricox", "note": "Vietnamese local NSAID brand"},
    {"type": "no_result", "query": "XyZ123FakeDrug", "note": "Non-existent drug term"}
]

async def audit_rxnav():
    print("=" * 80)
    print("1. RXNAV / RXNORM REAL API AUDIT")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for item in TEST_QUERIES:
            query = item["query"]
            print(f"\n--- [RxNav Query] '{query}' ({item['note']}) ---")

            # 1. Exact rxcui.json
            rxcui_url = f"{RXNAV_BASE}/rxcui.json"
            resp1 = await client.get(rxcui_url, params={"name": query, "allsrc": "0", "srclist": "RXNORM"})
            print(f"  • GET /rxcui.json?name={query} -> HTTP {resp1.status_code}")
            
            rxcui = None
            if resp1.status_code == 200:
                data1 = resp1.json()
                rxnorm_ids = data1.get("idGroup", {}).get("rxnormId", [])
                if rxnorm_ids:
                    rxcui = str(rxnorm_ids[0])
                    print(f"    [VERIFIED_EXACT] RxCUI Found: {rxcui} (Count: {len(rxnorm_ids)})")
                else:
                    print(f"    [NO_EXACT_RESULT] No rxnormId in idGroup")

            # 2. Properties if rxcui found
            if rxcui:
                prop_url = f"{RXNAV_BASE}/rxcui/{rxcui}/properties.json"
                resp_prop = await client.get(prop_url)
                if resp_prop.status_code == 200:
                    props = resp_prop.json().get("properties", {})
                    print(f"    [PROPERTIES] Name: '{props.get('name')}', TTY: '{props.get('tty')}'")

                # 3. Traversal: Can we get Active Ingredients via allrelated.json or related.json?
                rel_url = f"{RXNAV_BASE}/rxcui/{rxcui}/allrelated.json"
                resp_rel = await client.get(rel_url)
                print(f"  • GET /rxcui/{rxcui}/allrelated.json -> HTTP {resp_rel.status_code}")
                if resp_rel.status_code == 200:
                    rel_data = resp_rel.json()
                    groups = rel_data.get("allRelatedGroup", {}).get("conceptGroup", [])
                    ingredients = []
                    brand_names = []
                    for g in groups:
                        tty = g.get("tty")
                        concepts = g.get("conceptProperties", [])
                        if tty in ("IN", "PIN", "MIN"):
                            ingredients.extend([c.get("name") for c in concepts])
                        elif tty in ("BN",):
                            brand_names.extend([c.get("name") for c in concepts])
                    print(f"    [TRAVERSAL RESULT] Active Ingredients (IN/PIN/MIN): {ingredients}")
                    print(f"    [TRAVERSAL RESULT] Related Brands (BN): {brand_names[:3]}")

            # 4. ApproximateTerm search
            approx_url = f"{RXNAV_BASE}/approximateTerm.json"
            resp_approx = await client.get(approx_url, params={"term": query, "maxEntries": "5"})
            print(f"  • GET /approximateTerm.json?term={query} -> HTTP {resp_approx.status_code}")
            if resp_approx.status_code == 200:
                cands = resp_approx.json().get("approximateGroup", {}).get("candidate", [])
                print(f"    [APPROXIMATE CANDIDATES] Count: {len(cands)}")
                for c in cands[:3]:
                    print(f"      - RxCUI: {c.get('rxcui')}, Name: '{c.get('name')}', Score: {c.get('score')}")

async def audit_openfda():
    print("\n" + "=" * 80)
    print("2. OPENFDA REAL API AUDIT")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for item in TEST_QUERIES:
            query = item["query"]
            print(f"\n--- [OpenFDA Query] '{query}' ({item['note']}) ---")

            # 1. Label Search by brand_name
            label_url = f"{OPENFDA_BASE}/label.json"
            resp_brand = await client.get(label_url, params={"search": f'openfda.brand_name:"{query}"', "limit": 2})
            print(f"  • GET /label.json?search=openfda.brand_name:\"{query}\" -> HTTP {resp_brand.status_code}")

            if resp_brand.status_code == 200:
                data = resp_brand.json()
                results = data.get("results", [])
                print(f"    [LABEL BRAND MATCH] Returned Records: {len(results)}")
                if results:
                    rec = results[0]
                    openfda = rec.get("openfda", {})
                    b_names = openfda.get("brand_name", [])
                    g_names = openfda.get("generic_name", [])
                    s_names = openfda.get("substance_name", [])
                    rxcui = openfda.get("rxcui", [])
                    ndc = openfda.get("product_ndc", [])
                    spl_id = openfda.get("spl_id", [])
                    
                    print(f"    [OBSERVED FIELDS]")
                    print(f"      - openfda.brand_name: {b_names}")
                    print(f"      - openfda.generic_name: {g_names}")
                    print(f"      - openfda.substance_name: {s_names}")
                    print(f"      - openfda.rxcui: {rxcui}")
                    print(f"      - openfda.product_ndc: {ndc[:2]}")
                    print(f"      - openfda.spl_id: {spl_id[:2]}")
                    print(f"      - active_ingredient (text field): {bool(rec.get('active_ingredient'))}")
            else:
                print(f"    [NO_RESULT / 404] Response: {resp_brand.status_code}")

            # 2. Label Search by substance_name / ingredient
            resp_sub = await client.get(label_url, params={"search": f'openfda.substance_name:"{query}"', "limit": 1})
            print(f"  • GET /label.json?search=openfda.substance_name:\"{query}\" -> HTTP {resp_sub.status_code}")
            if resp_sub.status_code == 200:
                data_sub = resp_sub.json()
                res_sub = data_sub.get("results", [])
                if res_sub:
                    ofda = res_sub[0].get("openfda", {})
                    print(f"    [SUBSTANCE MATCH] Brand: {ofda.get('brand_name', [])[:2]}, Substance: {ofda.get('substance_name', [])[:2]}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(audit_rxnav())
    asyncio.run(audit_openfda())
