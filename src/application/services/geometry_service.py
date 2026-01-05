"""
Geometry Service
기하학 연산 서비스
"""
import math
from typing import List, Tuple


class GeometryService:
    """기하학 연산 서비스"""

    @staticmethod
    def calculate_polygon_area(vertices: List[Tuple[float, float]]) -> float:
        """
        Shoelace 공식을 사용한 폴리곤 면적 계산

        Args:
            vertices: 좌표 리스트 [(x1, y1), (x2, y2), ...]

        Returns:
            면적 (절댓값)
        """
        if len(vertices) < 3:
            return 0.0

        area = 0.0
        n = len(vertices)

        for i in range(n):
            j = (i + 1) % n
            area += vertices[i][0] * vertices[j][1]
            area -= vertices[j][0] * vertices[i][1]

        return abs(area) / 2.0

    @staticmethod
    def calculate_center(vertices: List[Tuple[float, float]]) -> Tuple[float, float]:
        """
        좌표 리스트의 중심점 계산

        Args:
            vertices: 좌표 리스트

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
    def rotate_point(
        point: Tuple[float, float],
        angle: float,
        origin: Tuple[float, float] = (0, 0)
    ) -> Tuple[float, float]:
        """
        2D 회전 변환

        Args:
            point: 회전할 점 (x, y)
            angle: 회전 각도 (라디안)
            origin: 회전 중심점 (기본값: 원점)

        Returns:
            회전된 점 (x', y')
        """
        ox, oy = origin
        px, py = point

        # 원점으로 이동
        qx = px - ox
        qy = py - oy

        # 회전
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        rx = qx * cos_a - qy * sin_a
        ry = qx * sin_a + qy * cos_a

        # 원래 위치로 이동
        return (rx + ox, ry + oy)

    @staticmethod
    def scale_point(
        point: Tuple[float, float],
        scale_x: float,
        scale_y: float
    ) -> Tuple[float, float]:
        """
        2D 스케일 변환

        Args:
            point: 스케일할 점 (x, y)
            scale_x: X축 스케일 계수
            scale_y: Y축 스케일 계수

        Returns:
            스케일된 점 (x', y')
        """
        return (point[0] * scale_x, point[1] * scale_y)

    @staticmethod
    def translate_point(
        point: Tuple[float, float],
        dx: float,
        dy: float
    ) -> Tuple[float, float]:
        """
        2D 이동 변환

        Args:
            point: 이동할 점 (x, y)
            dx: X축 이동 거리
            dy: Y축 이동 거리

        Returns:
            이동된 점 (x', y')
        """
        return (point[0] + dx, point[1] + dy)

    @staticmethod
    def transform_vertices(
        vertices: List[Tuple[float, float]],
        scale: Tuple[float, float],
        rotation: float,
        translation: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """
        좌표 리스트에 변환 적용 (Scale → Rotation → Translation)

        Args:
            vertices: 변환할 좌표 리스트
            scale: (scale_x, scale_y)
            rotation: 회전 각도 (라디안)
            translation: (dx, dy)

        Returns:
            변환된 좌표 리스트
        """
        result = []

        for vertex in vertices:
            # 1. Scale
            v = GeometryService.scale_point(vertex, scale[0], scale[1])

            # 2. Rotation
            v = GeometryService.rotate_point(v, rotation)

            # 3. Translation
            v = GeometryService.translate_point(v, translation[0], translation[1])

            result.append(v)

        return result
