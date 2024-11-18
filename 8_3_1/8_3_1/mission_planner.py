# -*- coding: CP1251 -*-
# mission_planner.py

from uav_control import UAVControl
import time
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class MissionPlanner:
    """
    ����� ��� ������������ � ���������� ������ ����.
    """

    def __init__(self, connection_string: str):
        """
        ������������� ������������ ������.

        Args:
            connection_string (str): ������ ����������� MAVLink.
        """
        self.uav = UAVControl(connection_string)

    def execute_mission(self, waypoints: List[Tuple[float, float, float]]) -> None:
        """
        ���������� ������ �� �������� ������.

        Args:
            waypoints (List[Tuple[float, float, float]]): ������ ����� (lat, lon, alt).
        """
        try:
            self.uav.arm()
            self.uav.set_mode('GUIDED')
            self.uav.takeoff(waypoints[0][2])

            # �������� ������ ������
            time.sleep(5)

            for idx, waypoint in enumerate(waypoints):
                logger.info(f"��������� � ����� {idx+1}: {waypoint}")
                self.uav.goto(*waypoint)

                # �������� ���������� ����� � ��������� ����������
                reached = False
                for _ in range(5):  # �������� 5 ��������
                    telemetry = self.uav.get_telemetry()
                    if telemetry:
                        lat_diff = abs(telemetry.get('lat', 0.0) - waypoint[0])
                        lon_diff = abs(telemetry.get('lon', 0.0) - waypoint[1])
                        alt_diff = abs(telemetry.get('alt', 0.0) - waypoint[2])
                        if lat_diff < 0.0001 and lon_diff < 0.0001 and alt_diff < 1.0:
                            reached = True
                            logger.info(f"���������� ����� {idx+1}")
                            break
                    time.sleep(1)
                if not reached:
                    logger.error(f"�� ������� ������� ����� {idx+1}")
                    raise Exception(f"�� ������� ������� ����� {idx+1}")

            # ����������� � �������
            self.uav.set_mode('RTL')
            logger.info("����������� ����� � �������")

            # �������� �������
            time.sleep(5)
            self.uav.disarm()
        except Exception as e:
            logger.error(f"������ �� ����� ���������� ������: {e}")
            self.uav.disarm()
            raise
