# -*- coding: CP1251 -*-
# uav_control.py

from pymavlink import mavutil
import time
import math
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UAVControl:
    """
    ����� ��� ���������� ���� ����� MAVLink.
    """

    def __init__(self, connection_string: str):
        """
        ������������� ����������� � ����.

        Args:
            connection_string (str): ������ ����������� MAVLink.
        """
        try:
            self.master = mavutil.mavlink_connection(connection_string)
            self.master.wait_heartbeat()
            logger.info("���������� �����������")
            self.seq = 0  # ������������� ����������������� ������ ������
        except Exception as e:
            logger.error(f"������ �����������: {e}")
            raise

    def arm(self) -> None:
        """
        ��������� (Arm) ���� ��� ������ ������ ����������.
        """
        try:
            self.master.arducopter_arm()
            self.master.motors_armed_wait()
            logger.info("���� ������")
        except Exception as e:
            logger.error(f"������ ��������� ����: {e}")
            raise

    def disarm(self) -> None:
        """
        ����������� (Disarm) ���� ��� ��������� ����������.
        """
        try:
            self.master.arducopter_disarm()
            self.master.motors_disarmed_wait()
            logger.info("���� ��������")
        except Exception as e:
            logger.error(f"������ ����������� ����: {e}")
            raise

    def takeoff(self, altitude: float) -> None:
        """
        ������� �� ���� �� �������� ������.

        Args:
            altitude (float): ������� ������ ����� � ������.
        """
        if altitude <= 0:
            raise ValueError("������ ������ ���� �������������")

        try:
            self.set_mode('GUIDED')

            # ��������� ������� ���������
            msg = self.master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=5)
            if msg:
                current_lat = msg.lat / 1e7
                current_lon = msg.lon / 1e7
            else:
                raise Exception("�� ������� �������� ������� ���������� ��� �����")

            self.master.mav.command_long_send(
                self.master.target_system,
                self.master.target_component,
                mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                0,
                0, 0, 0, 0,
                current_lat,  # param5: ������ �����
                current_lon,  # param6: ������� �����
                altitude      # param7: ������ �����
            )

            if not self.wait_command_ack(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF):
                raise Exception("������� ����� �� ������������")
            logger.info(f"���� �� ������ {altitude} ������")
        except Exception as e:
            logger.error(f"������ �����: {e}")
            raise

    def set_mode(self, mode: str) -> None:
        """
        ��������� ������ ����� ����.

        Args:
            mode (str): �������� ������ (��������, 'GUIDED', 'LAND').
        """
        mode_mapping = self.master.mode_mapping()
        if not isinstance(mode_mapping, dict):
            logger.error("������: mode_mapping() �� ������ �������")
            raise Exception("�� ������� �������� ������ ������� �����")

        mode_id = mode_mapping.get(mode)
        if mode_id is None:
            raise ValueError(f"����������� �����: {mode}")

        try:
            self.master.set_mode(mode_id)
            logger.info(f"����� ����������: {mode}")
        except Exception as e:
            logger.error(f"������ ��������� ������ {mode}: {e}")
            raise

    def get_telemetry(self) -> Optional[Dict[str, float]]:
        """
        ��������� ��������������� ������ �� ����.

        Returns:
            Optional[Dict[str, float]]: ������� � ���������������� ������� ��� None.
        """
        try:
            msg = self.master.recv_match(
                type=['GLOBAL_POSITION_INT', 'ATTITUDE'], blocking=True, timeout=5)
            if msg:
                telemetry = {}
                if msg.get_type() == 'GLOBAL_POSITION_INT':
                    telemetry['lat'] = msg.lat / 1e7
                    telemetry['lon'] = msg.lon / 1e7
                    telemetry['alt'] = msg.alt / 1000
                    if not -90.0 <= telemetry['lat'] <= 90.0:
                        raise ValueError("������������ ������")
                    if not -180.0 <= telemetry['lon'] <= 180.0:
                        raise ValueError("������������ �������")
                elif msg.get_type() == 'ATTITUDE':
                    telemetry['roll'] = msg.roll
                    telemetry['pitch'] = msg.pitch
                    telemetry['yaw'] = msg.yaw
                    if not -math.pi <= telemetry['roll'] <= math.pi:
                        raise ValueError("������������ ����")
                    if not -math.pi/2 <= telemetry['pitch'] <= math.pi/2:
                        raise ValueError("������������ ������")
                    if not -math.pi <= telemetry['yaw'] <= math.pi:
                        raise ValueError("������������ ��������")
                return telemetry
            else:
                logger.warning("���������� ����������")
                return None
        except Exception as e:
            logger.error(f"������ ��������� ����������: {e}")
            return None

    def wait_command_ack(self, command: int, timeout: int = 10) -> bool:
        """
        �������� ������������� ���������� �������.

        Args:
            command (int): ��� ������� MAVLink.
            timeout (int): ����� �������� � ��������.

        Returns:
            bool: True, ���� ������� ������������, False � ��������� ������.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            ack_msg = self.master.recv_match(type='COMMAND_ACK', blocking=True, timeout=1)
            if ack_msg and ack_msg.command == command:
                if ack_msg.result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                    logger.info(f"������� {command} ������������")
                    return True
                else:
                    logger.error(f"������� {command} ��������� � ����� {ack_msg.result}")
                    return False
        logger.error(f"�� �������� ������������� ��� ������� {command}")
        return False

    def goto(self, lat: float, lon: float, alt: float) -> None:
        """
        ������� �� ���� � �������� �����������.

        Args:
            lat (float): ������ ������� �����.
            lon (float): ������� ������� �����.
            alt (float): ������ ������� ����� � ������.
        """
        try:
            # �������� ���������� ������ (1 �����)
            self.master.mav.mission_count_send(
                self.master.target_system,
                self.master.target_component,
                1,  # ���������� ������� ������
                mavutil.mavlink.MAV_MISSION_TYPE_MISSION
            )
            time.sleep(1)  # �������� ��� ���������

            self.master.mav.mission_item_send(
                self.master.target_system,
                self.master.target_component,
                0,  # ���������������� ����� ������
                mavutil.mavlink.MAV_FRAME_GLOBAL_INT,  # ������������ �����
                mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                0,  # current
                1,  # autocontinue
                0, 0, 0, 0,
                lat, lon, alt
            )

            if not self.wait_command_ack(mavutil.mavlink.MAV_CMD_NAV_WAYPOINT):
                raise Exception("������� ����� � ����� �� ������������")

            logger.info(f"����� � ����� ({lat}, {lon}, {alt})")
        except Exception as e:
            logger.error(f"������ ��� ����� � �����: {e}")
            raise
