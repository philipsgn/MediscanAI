# Model Sources & Licenses (OCR Benchmark Baseline)

This document provides provenance, official URLs, versions, and licenses for the pretrained models used in the Mediscan AI OCR baseline benchmark.

---

## 1. PP-OCR (PaddleOCR / PaddleX)

- **Model Architecture:**
  - **Detection:** PP-OCRv4 / PP-OCRv6 Mobile Detection (`PP-OCRv6_medium_det` / `PP-OCRv4_mobile_det`)
  - **Recognition:** PP-OCR Mobile Multilingual / Vietnamese Recognition (`PP-OCRv6_medium_rec`)
- **Official Repository:** [PaddlePaddle / PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
- **Model Distribution:** PaddleX Official Model Registry / ONNX Runtime Official CPU Exports
- **Version:** PaddleOCR 3.7.0 / PaddleX 3.7.2
- **License:** Apache License 2.0 (Open Source, Permissive commercial use)
- **URL:** `https://github.com/PaddlePaddle/PaddleOCR`

---

## 2. VietOCR (Pretrained vgg_seq2seq)

- **Model Architecture:** VGG19-BN backbone + Sequence-to-Sequence (Seq2Seq) Attention Decoder
- **Official Repository:** [pbcquoc/vietocr](https://github.com/pbcquoc/vietocr)
- **Checkpoint:** `vgg_seq2seq.pth` (VGG19 Seq2Seq pretrained on Vietnamese text)
- **Official Weight URL:** `https://vocr.vn/data/vietocr/vgg_seq2seq.pth` (Trạng thái: chưa xác minh được kết nối do lỗi bắt tay SSL/TLS của máy chủ, cần kiểm tra thủ công) / `https://github.com/pbcquoc/vietocr/releases`
- **Version:** VietOCR 0.3.13 / Weights: `vgg_seq2seq.pth` (89.5 MB)
- **License:** Apache License 2.0 (Open Source, Permissive commercial use)
- **URL:** [pbcquoc/vietocr](https://github.com/pbcquoc/vietocr) (Nguồn xác minh License: [LICENSE](https://github.com/pbcquoc/vietocr/blob/master/LICENSE) hoặc [README.md](https://github.com/pbcquoc/vietocr/blob/master/README.md))
