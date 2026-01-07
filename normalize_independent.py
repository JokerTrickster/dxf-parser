#!/usr/bin/env python3
"""
X와 Y를 독립적으로 정규화하는 스크립트
각 축을 개별적으로 목표 범위에 맞춥니다.
"""

import csv
import sys
from pathlib import Path

def normalize_csv_independent(input_csv: str, output_csv: str = None, target_range: int = 160000):
    """
    CSV 파일의 X, Y 좌표를 독립적으로 정규화합니다.

    Args:
        input_csv: 입력 CSV 파일 경로
        output_csv: 출력 CSV 파일 경로 (None이면 _independent 접미사 추가)
        target_range: 각 축의 목표 범위 (기본값: 160000, -160000 ~ 160000)
    """
    # CSV 읽기
    rows = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames

        if 'X' not in headers or 'Y' not in headers:
            raise ValueError("CSV 파일에 X, Y 컬럼이 없습니다.")

        for row in reader:
            rows.append(row)

    # 좌표 값들 추출
    x_values = [float(row['X']) for row in rows]
    y_values = [float(row['Y']) for row in rows]

    # 원본 좌표 범위
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)

    print(f"📊 원본 좌표 범위:")
    print(f"   X: {x_min:,.2f} ~ {x_max:,.2f} (범위: {x_max - x_min:,.2f})")
    print(f"   Y: {y_min:,.2f} ~ {y_max:,.2f} (범위: {y_max - y_min:,.2f})")

    # 각 축의 중심점 계산
    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2

    print(f"\n🎯 중심점: ({x_center:,.2f}, {y_center:,.2f})")

    # 원점으로 이동
    x_translated = [x - x_center for x in x_values]
    y_translated = [y - y_center for y in y_values]

    # 각 축의 범위 계산
    x_range = max(x_translated) - min(x_translated)
    y_range = max(y_translated) - min(y_translated)

    # 각 축의 스케일 팩터 계산 (독립적으로!)
    x_scale = (target_range * 2) / x_range if x_range > 0 else 1.0
    y_scale = (target_range * 2) / y_range if y_range > 0 else 1.0

    print(f"\n📐 스케일 팩터 (독립):")
    print(f"   X: {x_scale:.6f}")
    print(f"   Y: {y_scale:.6f}")

    # 좌표 변환 적용 (각 축 독립적으로)
    for i, row in enumerate(rows):
        row['X'] = str(x_translated[i] * x_scale)
        row['Y'] = str(y_translated[i] * y_scale)

        if 'Z' in row:
            row['Z'] = '0'

    # 최종 좌표 범위
    final_x = [float(row['X']) for row in rows]
    final_y = [float(row['Y']) for row in rows]

    print(f"\n✅ 정규화된 좌표 범위:")
    print(f"   X: {min(final_x):,.2f} ~ {max(final_x):,.2f}")
    print(f"   Y: {min(final_y):,.2f} ~ {max(final_y):,.2f}")

    # 출력 파일명 생성
    if output_csv is None:
        input_path = Path(input_csv)
        output_csv = str(input_path.parent / f"{input_path.stem}_independent{input_path.suffix}")

    # CSV 저장
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n💾 저장 완료: {output_csv}")
    print(f"   총 {len(rows):,}개 엔티티")

    return output_csv

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python normalize_independent.py <input.csv> [output.csv] [target_range]")
        print("예시: python normalize_independent.py osong_b1_0105_final.csv")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else None
    target_range = int(sys.argv[3]) if len(sys.argv) > 3 else 160000

    normalize_csv_independent(input_csv, output_csv, target_range)
