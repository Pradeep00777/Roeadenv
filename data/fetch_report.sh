#!/bin/sh
# Re-creates the corpus from the public PDF (MoRTH, Road Accidents in India 2024, published June 2026, 266 pages).
set -e
URL=https://morth.gov.in/backend/documents/uploaded/1781177676_V1gUW8tJWT.pdf
SHA=b45b0e4d8e14a8d4653790f9080a01b9b95b79008359ba93dc12497064be69b2
curl -sL -A "Mozilla/5.0" -o ra2024.pdf "$URL"
echo "$SHA  ra2024.pdf" | sha256sum -c -
mkdir -p pages ocr
for i in $(seq 1 266); do pdftotext -layout -f $i -l $i ra2024.pdf pages/p$(printf %03d $i).txt; done
# OCR only pages with an empty text layer (Annexures, Appendix); --psm 1 auto-detects rotated tables
for i in $(seq 164 265); do pdftoppm -png -r 200 -f $i -l $i ra2024.pdf ocr/x$i && tesseract ocr/x$i-$i.png ocr/o$i --psm 1 -l eng; done
