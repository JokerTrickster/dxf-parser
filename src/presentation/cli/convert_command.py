"""
Convert Command
DXF → CSV 변환 CLI 커맨드
"""
import sys
from typing import Dict

from ...application.use_cases.convert_dxf_to_csv import ConvertDXFToCSVUseCase
from ...infrastructure.converters.mygeodata_csv_converter import MyGeoDataCSVConverter


def execute_convert(dxf_path: str, csv_path: str) -> Dict:
    """
    DXF → CSV 변환 실행

    Args:
        dxf_path: 입력 DXF 파일 경로
        csv_path: 출력 CSV 파일 경로

    Returns:
        변환 통계

    Raises:
        ValueError: 입력 파일이 유효하지 않은 경우
        Exception: 변환 실패 시
    """
    # Dependency Injection
    converter = MyGeoDataCSVConverter()
    use_case = ConvertDXFToCSVUseCase(converter)

    # 실행
    stats = use_case.execute(dxf_path, csv_path)

    return stats


def print_stats(stats: Dict):
    """
    변환 통계 출력

    Args:
        stats: 변환 통계 딕셔너리
    """
    print(f"변환 완료!")
    print(f"  처리된 엔티티: {stats['total']}개")
    print(f"  - LWPOLYLINE: {stats['lwpolyline']}개")
    print(f"  - LINE: {stats['line']}개")
    print(f"  - ARC: {stats['arc']}개")


def main():
    """CLI 메인 함수"""
    if len(sys.argv) != 3:
        print("Usage: python -m src.presentation.cli.convert_command <input.dxf> <output.csv>")
        print("\nExample:")
        print("  python -m src.presentation.cli.convert_command osong-b1_B1_converted.dxf output.csv")
        sys.exit(1)

    dxf_path = sys.argv[1]
    csv_path = sys.argv[2]

    try:
        stats = execute_convert(dxf_path, csv_path)
        print_stats(stats)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
