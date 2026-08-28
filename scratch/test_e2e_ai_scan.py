"""
End-to-End Integration Verification for /ai Pipeline + FastAPI /ocr/process Endpoint.
"""

import io
import json
import urllib.request
import uuid
from PIL import Image, ImageDraw

API_BASE = "http://localhost:8000/api/v1"


def create_mock_prescription_image() -> bytes:
    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    lines = [
        "DON THUOC DIEU TRI",
        "1. Augmentin 1g - Uong Sang 1v, Toi 1v sau an - x 7 ngay",
        "2. Nexium 40mg - Uong 1 vien sang truoc an 30 phut",
        "3. Panadol Extra - Uong 1 vien khi dau dau",
    ]

    y = 50
    for line in lines:
        draw.text((40, y), line, fill=(0, 0, 0))
        y += 60

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def send_multipart_form(url: str, fields: dict, files: dict) -> dict:
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = bytearray()

    for k, v in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
        body.extend(f"{v}\r\n".encode("utf-8"))

    for k, (filename, file_bytes, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{k}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(file_bytes)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    print("=== [1/2] GENERATING MOCK PRESCRIPTION IMAGE ===")
    img_bytes = create_mock_prescription_image()
    print(f"Mock image generated: {len(img_bytes)} bytes")

    print("\n=== [2/2] CALLING POST /api/v1/ocr/process ===")
    url = f"{API_BASE}/ocr/process"
    fields = {
        "source_stream": "prescription",
        "user_age": "45",
        "user_conditions": "Hypertension, Gastritis",
        "user_allergies": "Penicillin",
    }
    files = {
        "file": ("prescription_sample.jpg", img_bytes, "image/jpeg")
    }

    res = send_multipart_form(url, fields, files)
    print("[SUCCESS] API Call 200 OK! Response received:")
    print(f"Engine: {res.get('engine')}")
    print(f"Source Stream: {res.get('sourceStream') or res.get('source_stream')}")
    print(f"Metrics: {res.get('metrics')}")
    
    extracted = res.get("extractedDrugs") or res.get("extracted_drugs", [])
    print(f"\nExtracted Drugs ({len(extracted)} items):")
    for d in extracted:
        drug_name = d.get('drugName') or d.get('drug_name')
        active = d.get('activeIngredient') or d.get('active_ingredient')
        strength = d.get('strength')
        slots = d.get('timeSlots') or d.get('time_slots')
        print(f" - {drug_name} | Ingredient: {active} | Strength: {strength} | Slots: {slots}")

    report = res.get("clinicalReport") or res.get("clinical_report", {})
    print(f"\nClinical Report Summary: {report.get('final_summary')}")
    print(f"Total Alerts: {len(report.get('alerts', []))}")
    for a in report.get("alerts", []):
        title = a.get('title')
        sev = a.get('severity')
        desc = a.get('description', '')[:70]
        print(f"   [{sev}] {title} - {desc}...")

    print("\n[SUCCESS] E2E AI SCAN PIPELINE VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
