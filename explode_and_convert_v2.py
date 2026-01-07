#!/usr/bin/env python3
"""
블록을 재귀적으로 펼쳐서 CSV로 변환
"""
import ezdxf
import sys

def explode_recursive(entity, depth=0, max_depth=10):
    """재귀적으로 INSERT 엔티티 펼치기"""
    if depth >= max_depth:
        return []

    if entity.dxftype() == 'INSERT':
        result = []
        try:
            for sub in entity.virtual_entities():
                if sub.dxftype() == 'INSERT':
                    # 재귀적으로 펼치기
                    result.extend(explode_recursive(sub, depth+1, max_depth))
                else:
                    result.append(sub)
        except Exception as e:
            print(f"Warning: {e}")
        return result
    else:
        return [entity]

def explode_and_convert(input_dxf, output_csv):
    """블록을 펼쳐서 CSV 변환"""

    print(f"DXF 읽기: {input_dxf}")
    doc = ezdxf.readfile(input_dxf)

    # 새 DXF 문서 생성
    new_doc = ezdxf.new(doc.dxfversion)
    new_msp = new_doc.modelspace()

    # 기존 레이어 복사
    for layer in doc.layers:
        if layer.dxf.name not in new_doc.layers:
            try:
                new_doc.layers.add(layer.dxf.name)
            except:
                pass

    print("블록 펼치기 중...")
    entity_count = 0
    skipped = 0

    # 모든 엔티티 처리
    for entity in doc.modelspace():
        exploded = explode_recursive(entity)

        for e in exploded:
            try:
                # LWPOLYLINE, LINE, ARC만 복사 (주요 도형)
                if e.dxftype() in ['LWPOLYLINE', 'LINE', 'ARC', 'CIRCLE']:
                    copy = e.copy()
                    new_msp.add_entity(copy)
                    entity_count += 1

                    if entity_count % 10000 == 0:
                        print(f"  {entity_count:,}개 처리됨...")
                else:
                    skipped += 1
            except Exception as ex:
                skipped += 1

    # 펼친 DXF 저장
    exploded_dxf = input_dxf.replace('.dxf', '_exploded.dxf')
    print(f"\n펼친 DXF 저장: {exploded_dxf}")
    new_doc.saveas(exploded_dxf)

    print(f"총 {entity_count:,}개 엔티티 펼침 완료")
    print(f"건너뜀: {skipped:,}개")

    # CSV 변환
    print(f"\nCSV 변환 중: {output_csv}")
    from src.infrastructure.converters.mygeodata_csv_converter import MyGeoDataCSVConverter

    converter = MyGeoDataCSVConverter()
    stats = converter.convert(exploded_dxf, output_csv)

    print(f"\n✅ 변환 완료!")
    print(f"  LWPOLYLINE: {stats['lwpolyline']:,}개")
    print(f"  LINE: {stats['line']:,}개")
    print(f"  ARC: {stats['arc']:,}개")
    print(f"  총: {stats['total']:,}개")

    return exploded_dxf, stats

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python explode_and_convert_v2.py <input.dxf> <output.csv>")
        sys.exit(1)

    input_dxf = sys.argv[1]
    output_csv = sys.argv[2]

    explode_and_convert(input_dxf, output_csv)
