#!/bin/bash

# 기본값 설정
INPUT_FILE="${1:-osong-b1.dxf}"
FLOOR="${2:-B1}"

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "=========================================="
echo "DXF 변환 시작"
echo "입력 파일: $INPUT_FILE"
echo "층: $FLOOR"
echo "=========================================="

python3 dxf_parking_with_building.py "$INPUT_FILE" --floor "$FLOOR"

echo "=========================================="
echo "변환 완료!"
