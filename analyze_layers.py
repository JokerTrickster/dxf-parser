#!/usr/bin/env python3
"""
DXF 파일의 모든 레이어/블록 분석

Usage:
    python3 analyze_layers.py input.dxf --output analysis.json
"""
import sys
import json
import argparse
import ezdxf
from collections import defaultdict


def analyze_dxf_layers(dxf_path):
    """DXF 파일의 모든 블록 분석"""
    doc = ezdxf.readfile(dxf_path)

    # 블록 정보 수집
    block_info = []

    # INSERT 사용 횟수 카운트
    msp = doc.modelspace()
    insert_counts = defaultdict(int)

    for entity in msp:
        if entity.dxftype() == 'INSERT':
            main_block_name = entity.dxf.name
            if main_block_name in doc.blocks:
                main_block = doc.blocks[main_block_name]

                for sub_entity in main_block:
                    if sub_entity.dxftype() == 'INSERT':
                        insert_counts[sub_entity.dxf.name] += 1

    # 각 블록 상세 분석
    for block_name, count in insert_counts.items():
        if block_name not in doc.blocks:
            continue

        block = doc.blocks[block_name]

        # LWPOLYLINE 면적 계산
        max_area = 0
        for entity in block:
            if entity.dxftype() == 'LWPOLYLINE':
                vertices = list(entity.get_points())
                if len(vertices) >= 3:
                    area = 0
                    for i in range(len(vertices)):
                        j = (i + 1) % len(vertices)
                        area += vertices[i][0] * vertices[j][1]
                        area -= vertices[j][0] * vertices[i][1]
                    area = abs(area) / 2.0 / 1000000.0  # mm² → m²
                    if area > max_area:
                        max_area = area

        # 타입 추정
        suggested_type = suggest_layer_type(block_name, max_area)

        block_info.append({
            'name': block_name,
            'count': count,
            'sample_area': round(max_area, 2),
            'suggested_type': suggested_type
        })

    # 정렬 (사용 횟수 많은 순)
    block_info.sort(key=lambda x: x['count'], reverse=True)

    return {
        'blocks': block_info,
        'total_blocks': len(block_info)
    }


def suggest_layer_type(block_name, area):
    """블록 이름과 면적으로 타입 추정"""
    name_lower = block_name.lower()

    # 면적 기준
    if area < 1.0:
        # 1m² 미만은 마커로 분류
        if '장애' in name_lower or 'disabled' in name_lower or 'handicap' in name_lower:
            return 'marker-disabled'
        return 'marker'

    # 이름 기준 (주차면 타입)
    if '장애' in name_lower or 'disabled' in name_lower or 'handicap' in name_lower:
        # 면적이 10m² 이상이면 실제 주차면
        if area >= 10.0:
            return 'p-parking-disable'
        else:
            return 'marker-disabled'
    elif '확장' in name_lower or 'large' in name_lower or '대형' in name_lower:
        return 'p-parking-large'
    elif '경차' in name_lower or 'small' in name_lower or '소형' in name_lower:
        return 'p-parking-small'
    elif '전기' in name_lower or 'electric' in name_lower or 'ev' in name_lower or 'e-v' in name_lower:
        return 'p-parking-electric'
    elif '택배' in name_lower or 'delivery' in name_lower or '배송' in name_lower:
        return 'p-parking-delivery'
    elif '여성' in name_lower or 'women' in name_lower or 'woman' in name_lower:
        return 'p-parking-women'
    elif '일반' in name_lower or 'basic' in name_lower or '주차' in name_lower or 'parking' in name_lower:
        return 'p-parking-basic'
    elif '램프' in name_lower or 'ramp' in name_lower or '경사' in name_lower:
        return 's-circulation-ramp'
    elif '통로' in name_lower or 'path' in name_lower or 'corridor' in name_lower:
        return 's-circulation-path'

    # 기본값: unknown
    return 'unknown'


def main():
    parser = argparse.ArgumentParser(description='DXF 레이어 분석')
    parser.add_argument('input', help='입력 DXF 파일')
    parser.add_argument('--output', help='출력 JSON 파일', default='analysis.json')

    args = parser.parse_args()

    try:
        # 분석 실행
        result = analyze_dxf_layers(args.input)

        # JSON 저장
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"✅ 분석 완료: {result['total_blocks']}개 블록 발견")
        print(f"📄 결과 저장: {args.output}")

        # 간단한 요약 출력
        if result['total_blocks'] > 0:
            print(f"\n상위 5개 블록:")
            for block in result['blocks'][:5]:
                print(f"  - {block['name']}: {block['count']}개 ({block['suggested_type']})")

    except FileNotFoundError:
        print(f"❌ 오류: 파일을 찾을 수 없습니다 - {args.input}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
