#!/usr/bin/env python3
"""
DXF 간단 추출기 - 모든 도형 요소를 그대로 복사
블록 이름으로 필터링만 하고, 내부 도형은 모두 그대로 유지
"""

import ezdxf
from collections import defaultdict
import argparse
import os


# 추출할 블록 키워드 (대소문자 무시)
EXTRACT_KEYWORDS = [
    # 주차면
    'PARK_일반', 'PARK_확장', 'PARK_경차', 'PARK_장애인',
    'Park-환경친화', 'PARK-EC',
    '가족배려주차', '교통약자우선',

    # 계단 (이미지에서 본 것)
    '계단', 'STAIR', 'STA', 'core',

    # 출입구
    'FSD', '출입구', '비상구',

    # 외곽선
    '외곽', '건물', 'OUTLINE', 'BUILDING'
]

# 레이어 이름 매핑
LAYER_MAPPING = {
    'PARK_일반': 'p-parking-basic',
    'PARK_확장': 'p-parking-large',
    'PARK_경차': 'p-parking-small',
    'PARK_장애인': 'p-parking-disable',
    'Park-환경친화': 'p-parking-large-electric',
    'PARK-EC': 'p-parking-large-electric',
    '가족배려주차(확장형)': 'p-parking-large-women',
    '가족배려주차(일반형)': 'p-parking-large-women',
    '교통약자우선': 'p-parking-large-women',
    '계단': 's-circulation-stairs',
    'STAIR': 's-circulation-stairs',
    'STA': 's-circulation-stairs',
    'core': 's-circulation-stairs',
    'FSD': 's-circulation-exit',
    '출입구': 's-circulation-entrance',
    '비상구': 's-circulation-exit',
    '외곽': 's-structure-outline',
    '건물': 's-structure-building',
}

LAYER_COLORS = {
    'p-parking-basic': 7,
    'p-parking-large': 3,
    'p-parking-small': 4,
    'p-parking-disable': 1,
    'p-parking-large-electric': 5,
    'p-parking-large-women': 6,
    's-circulation-stairs': 2,
    's-circulation-exit': 1,
    's-circulation-entrance': 3,
    's-structure-outline': 8,
    's-structure-building': 9,
}


class SimpleDXFExtractor:
    """DXF 파일에서 블록을 필터링하고 모든 도형 요소를 복사"""

    def __init__(self, input_file):
        self.input_file = input_file
        self.doc = ezdxf.readfile(input_file)
        self.extracted_blocks = []
        self.stats = defaultdict(int)

    def should_extract(self, block_name):
        """블록명에 추출 키워드가 포함되어 있는지 확인"""
        block_upper = block_name.upper()
        for keyword in EXTRACT_KEYWORDS:
            if keyword.upper() in block_upper:
                return True
        return False

    def get_output_layer(self, block_name):
        """블록명으로 출력 레이어 결정"""
        # 긴 키워드부터 매칭 (더 구체적인 것 우선)
        for keyword in sorted(LAYER_MAPPING.keys(), key=len, reverse=True):
            if keyword.upper() in block_name.upper():
                return LAYER_MAPPING[keyword]
        return 'other'

    def extract_blocks_recursive(self, block, depth=0, max_depth=10):
        """재귀적으로 블록 탐색 및 추출"""
        if depth > max_depth:
            return

        for entity in block:
            if entity.dxftype() == 'INSERT':
                block_name = entity.dxf.name

                # 추출 대상인지 확인
                if self.should_extract(block_name):
                    output_layer = self.get_output_layer(block_name)

                    self.extracted_blocks.append({
                        'insert_entity': entity,
                        'block_name': block_name,
                        'output_layer': output_layer
                    })

                    self.stats[output_layer] += 1

                # 중첩 블록 탐색
                if block_name in self.doc.blocks:
                    nested_block = self.doc.blocks[block_name]
                    self.extract_blocks_recursive(nested_block, depth + 1, max_depth)

    def extract_all(self):
        """모든 블록 추출"""
        print("블록 추출 시작...")

        # 주요 평면도 블록
        main_blocks = ['지하1층평면도', '지하2층평면도']

        for block_name in main_blocks:
            if block_name in self.doc.blocks:
                print(f"  [{block_name}] 분석 중...")
                block = self.doc.blocks[block_name]
                self.extract_blocks_recursive(block)

        # 모델스페이스도 확인
        msp = self.doc.modelspace()
        for entity in msp:
            if entity.dxftype() == 'INSERT':
                block_name = entity.dxf.name
                if block_name in self.doc.blocks:
                    self.extract_blocks_recursive(self.doc.blocks[block_name])

        print(f"\n총 {len(self.extracted_blocks)}개 블록 추출 완료")

        # 통계 출력
        print("\n레이어별 블록 수:")
        for layer, count in sorted(self.stats.items()):
            print(f"  {layer}: {count}개")

    def calculate_normalization_offset(self):
        """모든 INSERT 포인트에서 최소 좌표 계산"""
        if not self.extracted_blocks:
            return (0, 0)

        min_x = float('inf')
        min_y = float('inf')

        for item in self.extracted_blocks:
            insert_entity = item['insert_entity']
            insert_point = insert_entity.dxf.insert

            min_x = min(min_x, insert_point.x)
            min_y = min(min_y, insert_point.y)

        return (min_x, min_y)

    def create_output_dxf(self, output_file, normalize=True):
        """새 DXF 파일 생성 - 블록 정의를 그대로 복사"""
        print(f"\n새 DXF 파일 생성: {output_file}")

        # 좌표 정규화 오프셋 계산
        offset_x, offset_y = (0, 0)
        if normalize:
            offset_x, offset_y = self.calculate_normalization_offset()
            print(f"\n좌표 정규화: 오프셋 ({offset_x:.2f}, {offset_y:.2f})")

        # 새 DXF 문서
        new_doc = ezdxf.new('R2010')
        new_msp = new_doc.modelspace()

        # 레이어 생성
        for layer_name, color in LAYER_COLORS.items():
            new_doc.layers.add(layer_name, color=color)

        # 블록 정의 복사 (중복 방지)
        copied_blocks = set()

        for item in self.extracted_blocks:
            block_name = item['block_name']

            # 블록 정의를 아직 복사하지 않았으면 복사
            if block_name not in copied_blocks and block_name in self.doc.blocks:
                source_block = self.doc.blocks[block_name]

                # 새 블록 생성
                new_block = new_doc.blocks.new(name=block_name)

                # 원본 블록의 모든 엔티티를 새 블록으로 복사
                for entity in source_block:
                    try:
                        # 엔티티 복사 (copy 메서드 사용)
                        new_entity = entity.copy()
                        new_block.add_entity(new_entity)
                    except Exception as e:
                        print(f"    경고: {block_name}의 엔티티 복사 실패: {e}")

                copied_blocks.add(block_name)

        print(f"  {len(copied_blocks)}개 블록 정의 복사 완료")

        # INSERT 엔티티 생성
        for item in self.extracted_blocks:
            insert_entity = item['insert_entity']
            output_layer = item['output_layer']

            try:
                # 원본 삽입점
                orig_point = insert_entity.dxf.insert

                # 정규화된 삽입점 (오프셋 적용)
                normalized_point = (
                    orig_point.x - offset_x,
                    orig_point.y - offset_y,
                    orig_point.z if hasattr(orig_point, 'z') else 0
                )

                # INSERT 복사 및 레이어 변경
                new_insert = new_msp.add_blockref(
                    insert_entity.dxf.name,
                    normalized_point,
                    dxfattribs={
                        'layer': output_layer,
                        'rotation': getattr(insert_entity.dxf, 'rotation', 0),
                        'xscale': getattr(insert_entity.dxf, 'xscale', 1.0),
                        'yscale': getattr(insert_entity.dxf, 'yscale', 1.0),
                        'zscale': getattr(insert_entity.dxf, 'zscale', 1.0),
                    }
                )
            except Exception as e:
                print(f"    경고: INSERT 생성 실패: {e}")

        # 저장
        new_doc.saveas(output_file)
        print(f"저장 완료: {output_file}")
        print(f"총 {len(self.extracted_blocks)}개 블록 생성됨")


def main():
    parser = argparse.ArgumentParser(description='DXF 간단 추출기 (도형 요소 그대로 복사)')
    parser.add_argument('input', help='입력 DXF 파일')
    parser.add_argument('-o', '--output', help='출력 DXF 파일', default=None)
    parser.add_argument('--max-depth', type=int, default=10, help='최대 블록 탐색 깊이')
    parser.add_argument('--normalize', action='store_true', help='좌표를 원점 기준으로 정규화')

    args = parser.parse_args()

    # 출력 파일명
    if not args.output:
        base_name = os.path.splitext(args.input)[0]
        args.output = f"{base_name}_simple_converted.dxf"

    # 추출 및 변환
    extractor = SimpleDXFExtractor(args.input)
    extractor.extract_all()
    extractor.create_output_dxf(args.output, normalize=args.normalize)

    print("\n작업 완료!")


if __name__ == '__main__':
    main()
