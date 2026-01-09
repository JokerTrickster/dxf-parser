#!/usr/bin/env python3
"""
DXF to CSV 자동 변환 스크립트

사용법:
    python3 src/convert_dxf.py input.dxf
    python3 src/convert_dxf.py input.dxf --output custom_output.csv
    python3 src/convert_dxf.py input.dxf --tolerance 5.0

워크플로우:
    1. DXF 레이어 분석 (analyze_layers.py)
    2. 주차면 블록만 자동 필터링
    3. 레이어 매핑 JSON 자동 생성
    4. CSV 변환 (process_central_dxf.py)
"""

import sys
import os
import json
import argparse
import subprocess
import tempfile
from pathlib import Path

# 현재 스크립트의 디렉토리
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

def print_step(step_num, message):
    """단계별 출력"""
    print(f"\n{'='*70}")
    print(f"STEP {step_num}: {message}")
    print('='*70)

def run_analysis(dxf_path):
    """DXF 레이어 분석 실행"""
    print_step(1, "DXF 레이어 분석 (주차면 블록만 추출)")
    
    analyze_script = SCRIPT_DIR / "analyze_layers.py"
    temp_json = tempfile.mktemp(suffix='.json')
    
    cmd = [
        sys.executable,
        str(analyze_script),
        dxf_path,
        "--parking-only",
        "--output",
        temp_json
    ]
    
    print(f"실행: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ 오류: 레이어 분석 실패")
        print(result.stderr)
        sys.exit(1)
    
    print(result.stdout)
    
    # 분석 결과 로드
    with open(temp_json, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    os.remove(temp_json)
    return analysis

def create_layer_mapping(analysis):
    """분석 결과로부터 레이어 매핑 자동 생성"""
    print_step(2, "레이어 매핑 JSON 자동 생성")
    
    mapping = {}
    for block in analysis['blocks']:
        block_name = block['name']
        suggested_type = block['suggested_type']
        count = block['count']
        
        # 주차면 관련 블록만 매핑에 추가
        if suggested_type != 'unknown' or block['sample_area'] >= 5.0:
            mapping[block_name] = suggested_type
            print(f"  ✓ {block_name}")
            print(f"    → {suggested_type} ({count}개)")
    
    print(f"\n총 {len(mapping)}개 블록을 레이어 매핑에 추가했습니다.")
    
    # 임시 매핑 파일 생성
    temp_mapping = tempfile.mktemp(suffix='.json')
    with open(temp_mapping, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    return temp_mapping

def run_conversion(dxf_path, mapping_path, output_csv, tolerance, normalize):
    """DXF to CSV 변환 실행"""
    print_step(3, "DXF → CSV 변환")
    
    process_script = SCRIPT_DIR / "process_central_dxf.py"
    
    cmd = [
        sys.executable,
        str(process_script),
        dxf_path,
        "--layer-mapping",
        mapping_path,
        "--output-csv",
        output_csv,
        "--tolerance",
        str(tolerance)
    ]
    
    if normalize:
        cmd.append("--normalize")
    
    print(f"실행: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)
    
    if result.returncode != 0:
        print(f"❌ 오류: CSV 변환 실패")
        sys.exit(1)
    
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(
        description='DXF 파일을 CSV로 자동 변환',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 기본 사용 (출력: data/csv/input_parking.csv)
  python3 src/convert_dxf.py data/dxf/central.dxf
  
  # 출력 파일명 지정
  python3 src/convert_dxf.py data/dxf/central.dxf --output result.csv
  
  # 장애인 주차 재분류 거리 조정
  python3 src/convert_dxf.py data/dxf/central.dxf --tolerance 5.0
  
  # 좌표 정규화 비활성화
  python3 src/convert_dxf.py data/dxf/central.dxf --no-normalize
        """
    )
    
    parser.add_argument('input', help='입력 DXF 파일 경로')
    parser.add_argument('--output', '-o', help='출력 CSV 파일 경로 (기본: data/csv/{파일명}_parking.csv)')
    parser.add_argument('--tolerance', '-t', type=float, default=7.0, 
                        help='장애인 주차 재분류 거리 (m, 기본: 7.0)')
    parser.add_argument('--no-normalize', action='store_true',
                        help='좌표 정규화 비활성화')
    
    args = parser.parse_args()
    
    # 입력 파일 확인
    dxf_path = Path(args.input).absolute()
    if not dxf_path.exists():
        print(f"❌ 오류: 파일을 찾을 수 없습니다 - {dxf_path}")
        sys.exit(1)
    
    # 출력 파일 경로 설정
    if args.output:
        output_csv = Path(args.output).absolute()
    else:
        # 기본 출력: data/csv/{파일명}_parking.csv
        csv_dir = PROJECT_ROOT / "data" / "csv"
        csv_dir.mkdir(parents=True, exist_ok=True)
        output_csv = csv_dir / f"{dxf_path.stem}_parking.csv"
    
    print(f"""
┌─────────────────────────────────────────────────────────────────┐
│  DXF to CSV 자동 변환                                            │
├─────────────────────────────────────────────────────────────────┤
│  입력 파일: {dxf_path.name:<50} │
│  출력 파일: {output_csv.name:<50} │
│  재분류 거리: {args.tolerance}m{' '*45} │
│  좌표 정규화: {'비활성화' if args.no_normalize else '활성화':<48} │
└─────────────────────────────────────────────────────────────────┘
    """)
    
    try:
        # STEP 1: 레이어 분석
        analysis = run_analysis(str(dxf_path))
        
        # STEP 2: 레이어 매핑 생성
        mapping_path = create_layer_mapping(analysis)
        
        # STEP 3: CSV 변환
        success = run_conversion(
            str(dxf_path),
            mapping_path,
            str(output_csv),
            args.tolerance,
            not args.no_normalize
        )
        
        # 임시 매핑 파일 삭제
        os.remove(mapping_path)
        
        if success:
            print(f"\n{'='*70}")
            print("✅ 변환 완료!")
            print('='*70)
            print(f"출력 파일: {output_csv}")
            print(f"파일 크기: {output_csv.stat().st_size / 1024:.1f} KB")
            print('='*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 작업을 취소했습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
