"""
Geometry Processing Utilities
기하학적 처리 유틸리티
"""
import math
from typing import List, Tuple, Optional
from ezdxf.math import Matrix44, Vec3


class GeometryProcessor:
    """기하학적 연산 처리"""

    @staticmethod
    def calculate_area(vertices: List[Tuple[float, float]]) -> float:
        """
        Shoelace 공식으로 다각형 면적 계산

        Args:
            vertices: 꼭짓점 좌표 리스트

        Returns:
            면적 (제곱 단위)
        """
        if len(vertices) < 3:
            return 0.0

        n = len(vertices)
        area = 0.0

        for i in range(n):
            j = (i + 1) % n
            area += vertices[i][0] * vertices[j][1]
            area -= vertices[j][0] * vertices[i][1]

        return abs(area) / 2.0

    @staticmethod
    def transform_vertices(
        vertices: List[Tuple[float, float]],
        insert_point: Tuple[float, float],
        rotation: float,
        scale_x: float = 1.0,
        scale_y: float = 1.0
    ) -> List[Tuple[float, float]]:
        """
        좌표 변환 (스케일 → 회전 → 이동)

        Args:
            vertices: 원본 꼭짓점
            insert_point: 삽입 위치
            rotation: 회전 각도 (도)
            scale_x: X축 스케일
            scale_y: Y축 스케일

        Returns:
            변환된 꼭짓점 리스트
        """
        if not vertices:
            return []

        # 회전 각도를 라디안으로 변환
        rad = math.radians(rotation)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)

        transformed = []
        for x, y in vertices:
            # 1. 스케일
            x *= scale_x
            y *= scale_y

            # 2. 회전
            x_rot = x * cos_r - y * sin_r
            y_rot = x * sin_r + y * cos_r

            # 3. 이동
            x_final = x_rot + insert_point[0]
            y_final = y_rot + insert_point[1]

            transformed.append((x_final, y_final))

        return transformed

    @staticmethod
    def calculate_center(vertices: List[Tuple[float, float]]) -> Tuple[float, float]:
        """
        중심점 계산

        Args:
            vertices: 꼭짓점 리스트

        Returns:
            중심점 (x, y)
        """
        if not vertices:
            return (0.0, 0.0)

        x_coords = [v[0] for v in vertices]
        y_coords = [v[1] for v in vertices]

        return (
            sum(x_coords) / len(x_coords),
            sum(y_coords) / len(y_coords)
        )

    @staticmethod
    def extract_circle_vertices(
        center: Tuple[float, float],
        radius: float,
        segments: int = 32
    ) -> List[Tuple[float, float]]:
        """
        원을 다각형으로 근사

        Args:
            center: 원의 중심
            radius: 반지름
            segments: 분할 개수 (기본 32)

        Returns:
            근사된 꼭짓점 리스트
        """
        vertices = []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            vertices.append((x, y))

        return vertices

    @staticmethod
    def normalize_coordinates(
        vertices_list: List[List[Tuple[float, float]]]
    ) -> List[List[Tuple[float, float]]]:
        """
        좌표를 원점 기준으로 정규화

        Args:
            vertices_list: 여러 꼭짓점 리스트

        Returns:
            정규화된 좌표 리스트
        """
        if not vertices_list:
            return vertices_list

        # 모든 좌표의 최소값 찾기
        all_x = [x for vertices in vertices_list for x, y in vertices]
        all_y = [y for vertices in vertices_list for x, y in vertices]

        min_x = min(all_x) if all_x else 0
        min_y = min(all_y) if all_y else 0

        # 정규화
        normalized = []
        for vertices in vertices_list:
            normalized_vertices = [
                (x - min_x, y - min_y) for x, y in vertices
            ]
            normalized.append(normalized_vertices)

        return normalized
