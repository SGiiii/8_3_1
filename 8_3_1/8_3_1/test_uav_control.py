# -*- coding: CP1251 -*-
# test_uav_control.py

import unittest
from unittest.mock import MagicMock, patch
from uav_control import UAVControl
from pymavlink import mavutil


class TestUAVControl(unittest.TestCase):
    def setUp(self):
        # �������� mock-������� ��� mavlink_connection
        self.patcher = patch('uav_control.mavutil.mavlink_connection')
        self.mock_mavlink_connection = self.patcher.start()
        self.mock_master = MagicMock()
        self.mock_mavlink_connection.return_value = self.mock_master
        self.mock_master.wait_heartbeat.return_value = True
        # ��������� mode_mapping
        self.mock_master.mode_mapping.return_value = {'GUIDED': 4, 'LAND': 9, 'RTL': 6}

        self.uav = UAVControl('tcp:127.0.0.1:5760')

    def tearDown(self):
        # ��������� �������
        self.patcher.stop()

    def test_connection(self):
        # �������� ������������ ����������
        self.mock_mavlink_connection.assert_called_with('tcp:127.0.0.1:5760')
        self.mock_master.wait_heartbeat.assert_called_once()

    def test_arm_disarm(self):
        # �������� ��������� � ����������� ����
        self.uav.arm()
        self.mock_master.arducopter_arm.assert_called_once()
        self.mock_master.motors_armed_wait.assert_called_once()

        self.uav.disarm()
        self.mock_master.arducopter_disarm.assert_called_once()
        self.mock_master.motors_disarmed_wait.assert_called_once()

    def test_set_mode_valid(self):
        # �������� ��������� ����������� ������ �����
        self.uav.set_mode('GUIDED')
        expected_mode_id = self.mock_master.mode_mapping.return_value.get('GUIDED')
        self.mock_master.set_mode.assert_called_with(expected_mode_id)

    def test_set_mode_invalid(self):
        # �������� ������� �� ��������� ������������� ������
        with self.assertRaises(ValueError):
            self.uav.set_mode('INVALID_MODE')

    def test_takeoff_positive_altitude(self):
        # �������� ����� �� ������������� ������
        # ��������� �������� ���������
        position_msg = MagicMock()
        position_msg.get_type.return_value = 'GLOBAL_POSITION_INT'
        position_msg.lat = 550000000  # 55.0 ��������
        position_msg.lon = 370000000  # 37.0 ��������
        self.mock_master.recv_match.return_value = position_msg

        self.uav.takeoff(10)
        expected_mode_id = self.mock_master.mode_mapping.return_value.get('GUIDED')
        self.mock_master.set_mode.assert_called_with(expected_mode_id)
        self.mock_master.mav.command_long_send.assert_called_once()
        self.mock_master.recv_match.assert_called_with(type='GLOBAL_POSITION_INT', blocking=True, timeout=5)

    def test_takeoff_negative_altitude(self):
        # �������� ������� �� ������������� ������
        with self.assertRaises(ValueError):
            self.uav.takeoff(-5)

    def test_goto(self):
        # �������� ������� ����� � �������� �����
        self.uav.goto(55.0, 37.0, 100.0)

        self.mock_master.mav.mission_count_send.assert_called_once()
        self.mock_master.mav.mission_item_send.assert_called_once()

        # ��������� ��������� ������ mission_item_send
        args, kwargs = self.mock_master.mav.mission_item_send.call_args

        # ���������, ��� ������������ ���������� ����� ���������
        frame = args[3]
        self.assertEqual(frame, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT)

    def test_get_telemetry(self):
        # �������� ��������� ��������������� ������
        attitude_msg = MagicMock()
        attitude_msg.get_type.return_value = 'ATTITUDE'
        attitude_msg.roll = 0.1
        attitude_msg.pitch = 0.2
        attitude_msg.yaw = 0.3

        self.mock_master.recv_match.return_value = attitude_msg

        telemetry = self.uav.get_telemetry()
        self.assertIsNotNone(telemetry)
        self.assertEqual(telemetry['roll'], 0.1)
        self.assertEqual(telemetry['pitch'], 0.2)
        self.assertEqual(telemetry['yaw'], 0.3)

    def test_wait_command_ack(self):
        # �������� �������� ������������� �������
        ack_msg = MagicMock()
        ack_msg.command = mavutil.mavlink.MAV_CMD_NAV_TAKEOFF
        ack_msg.result = mavutil.mavlink.MAV_RESULT_ACCEPTED

        self.mock_master.recv_match.return_value = ack_msg

        result = self.uav.wait_command_ack(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF)
        self.assertTrue(result)

    def test_wait_command_ack_timeout(self):
        # �������� �������� ��� �������� ������������� �������
        self.mock_master.recv_match.return_value = None

        result = self.uav.wait_command_ack(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, timeout=1)
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
