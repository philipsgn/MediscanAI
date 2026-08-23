#!/usr/bin/env node
/**
 * [P0/F4.2] Contract test FE↔BE — chống drift shape FullScanResponse.
 *
 * Cơ chế ("tương đương MSW", không cần mock server): FastAPI tự sinh OpenAPI
 * tại /openapi.json. Script này fetch schema THẬT của backend đang chạy và
 * khẳng định mọi trường mà frontend phụ thuộc vẫn tồn tại. Nếu backend đổi
 * shape (như pivot Stage 2→3 từng xảy ra) → script EXIT 1 ngay, không chờ
 * E2E thủ công phát hiện.
 *
 * Chạy: npm run verify:contract  (yêu cầu backend đang chạy)
 */
const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const OPENAPI_URL = BASE.replace(/\/api\/v1\/?$/, '') + '/openapi.json';

/** Trường mà frontend PHỤ THUỘC thực sự (không cần liệt kê 100% schema BE). */
const REQUIRED_FIELDS = {
  FullScanResponse: [
    'engine',
    'sourceType',
    'rawOcrItems',
    'mappedDrugs',
    'slaExceeded',
    'totalLatencyMs',
    'normalizationLatencyMs',
    'clinicalLatencyMs',
  ],
  MappedDrugItem: [
    'brandName',
    'strength',
    'confidenceScore',
    'isVerified',
    'matchMethod',
    'warnings',
  ],
};

async function main() {
  let doc;
  try {
    const res = await fetch(OPENAPI_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    doc = await res.json();
  } catch (err) {
    console.error(`[contract] KHÔNG tải được OpenAPI từ ${OPENAPI_URL}: ${err.message}`);
    console.error('[contract] Hãy đảm bảo backend đang chạy (docker compose up -d backend).');
    process.exit(2);
  }

  const schemas = doc?.components?.schemas || {};
  const failures = [];

  for (const [schemaName, fields] of Object.entries(REQUIRED_FIELDS)) {
    const props = schemas[schemaName]?.properties;
    if (!props) {
      failures.push(`Schema '${schemaName}' không tồn tại trong OpenAPI`);
      continue;
    }
    for (const field of fields) {
      if (!(field in props)) {
        failures.push(`${schemaName}.${field} BỊ MẤT — frontend đang phụ thuộc trường này`);
      }
    }
  }

  if (failures.length > 0) {
    console.error('[contract] ❌ CONTRACT DRIFT PHÁT HIỆN:');
    failures.forEach((f) => console.error(`  - ${f}`));
    process.exit(1);
  }

  console.log('[contract] ✅ PASS — FullScanResponse/MappedDrugItem còn đầy đủ các trường FE phụ thuộc.');
  console.log(`[contract]    (nguồn schema: ${OPENAPI_URL})`);
  process.exit(0);
}

main();
