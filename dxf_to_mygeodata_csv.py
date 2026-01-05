#!/usr/bin/env python3
"""
DXF to MyGeoData CSV Converter
DXF 파일을 MyGeoData.cloud와 동일한 형식의 CSV로 변환

[Backward Compatibility Wrapper]
실제 구현은 src.presentation.cli.convert_command로 이동되었습니다.

Usage:
    python dxf_to_mygeodata_csv.py input.dxf output.csv
"""

import sys
from src.presentation.cli.convert_command import execute_convert, print_stats


def convert_dxf_to_mygeodata_csv(dxf_path: str, csv_path: str):
    """
    DXF 파일을 MyGeoData.cloud 형식의 CSV로 변환 (하위 호환성 래퍼)

    Args:
        dxf_path: 입력 DXF 파일 경로
        csv_path: 출력 CSV 파일 경로
    """
    stats = execute_convert(dxf_path, csv_path)
    print_stats(stats)


def main():
    if len(sys.argv) != 3:
        print("Usage: python dxf_to_mygeodata_csv.py <input.dxf> <output.csv>")
        print("\nExample:")
        print("  python dxf_to_mygeodata_csv.py osong-b1_B1_converted.dxf output.csv")
        sys.exit(1)

    dxf_path = sys.argv[1]
    csv_path = sys.argv[2]

    try:
        convert_dxf_to_mygeodata_csv(dxf_path, csv_path)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
