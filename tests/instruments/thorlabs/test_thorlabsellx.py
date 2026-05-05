#
# This file is part of the PyMeasure package.
#
# Copyright (c) 2013-2026 PyMeasure Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import pytest

from pymeasure.test import expected_protocol
from pymeasure.instruments.thorlabs.thorlabsellx import ThorlabsEllx, EllxStatus
from pymeasure.instruments.thorlabs.thorlabsell14 import ThorlabsELL14


# --- Hex conversion unit tests ---


class TestHexConversion:
    """Test the static hex encoding/decoding helpers."""

    def test_position_to_hex_positive(self):
        assert ThorlabsEllx._position_to_hex(35840) == "00008C00"

    def test_position_to_hex_zero(self):
        assert ThorlabsEllx._position_to_hex(0) == "00000000"

    def test_position_to_hex_negative(self):
        assert ThorlabsEllx._position_to_hex(-17920) == "FFFFBA00"

    def test_position_to_hex_large(self):
        assert ThorlabsEllx._position_to_hex(143360) == "00023000"

    def test_hex_to_position_positive(self):
        assert ThorlabsEllx._hex_to_position("00008C00") == 35840

    def test_hex_to_position_zero(self):
        assert ThorlabsEllx._hex_to_position("00000000") == 0

    def test_hex_to_position_negative(self):
        assert ThorlabsEllx._hex_to_position("FFFFBA00") == -17920

    def test_hex_roundtrip_positive(self):
        val = 71680
        assert ThorlabsEllx._hex_to_position(
            ThorlabsEllx._position_to_hex(val)
        ) == val

    def test_hex_roundtrip_negative(self):
        val = -35840
        assert ThorlabsEllx._hex_to_position(
            ThorlabsEllx._position_to_hex(val)
        ) == val


# --- Degree/pulse conversion tests (using ELL14 defaults) ---


class TestDegreeConversion:
    """Test degree-to-pulse conversion with ELL14's 143360 pulses/rev."""

    def setup_method(self):
        self.ppr = 143360

    def test_degrees_to_pulses_90(self):
        # 90/360 * 143360 = 35840
        inst = ThorlabsEllx.__new__(ThorlabsEllx)
        inst._pulses_per_revolution = self.ppr
        assert inst._degrees_to_pulses(90.0) == 35840

    def test_degrees_to_pulses_180(self):
        inst = ThorlabsEllx.__new__(ThorlabsEllx)
        inst._pulses_per_revolution = self.ppr
        assert inst._degrees_to_pulses(180.0) == 71680

    def test_degrees_to_pulses_negative(self):
        inst = ThorlabsEllx.__new__(ThorlabsEllx)
        inst._pulses_per_revolution = self.ppr
        assert inst._degrees_to_pulses(-45.0) == -17920

    def test_pulses_to_degrees_90(self):
        inst = ThorlabsEllx.__new__(ThorlabsEllx)
        inst._pulses_per_revolution = self.ppr
        assert inst._pulses_to_degrees(35840) == pytest.approx(90.0)

    def test_pulses_to_degrees_roundtrip(self):
        inst = ThorlabsEllx.__new__(ThorlabsEllx)
        inst._pulses_per_revolution = self.ppr
        degrees = 123.456
        pulses = inst._degrees_to_pulses(degrees)
        result = inst._pulses_to_degrees(pulses)
        assert result == pytest.approx(degrees, abs=0.003)


# --- Protocol tests ---


def test_get_position():
    """Test reading position via gp command."""
    protocol = [("0gp", "0PO00008C00")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        pos = inst.position
        assert pos == pytest.approx(90.0)


def test_set_position():
    """Test moving to absolute position via ma command."""
    # 90 degrees -> 35840 pulses -> "00008C00"
    protocol = [("0ma00008C00", "0PO00008C00")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.position = 90.0


def test_set_position_zero():
    """Test moving to position 0."""
    protocol = [("0ma00000000", "0PO00000000")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.position = 0.0


def test_get_status_ok():
    """Test reading OK status."""
    protocol = [("0gs", "0GS00")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        s = inst.status
        assert s == EllxStatus.OK


def test_get_status_busy():
    """Test reading busy status."""
    protocol = [("0gs", "0GS09")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        s = inst.status
        assert s == EllxStatus.BUSY


def test_home():
    """Test homing command (clockwise)."""
    protocol = [("0ho0", "0PO00000000")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.home(direction=0)


def test_home_ccw():
    """Test homing command (counter-clockwise)."""
    protocol = [("0ho1", "0PO00000000")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.home(direction=1)


def test_move_relative():
    """Test relative move."""
    # 45 degrees -> 17920 pulses -> "00004600"
    protocol = [("0mr00004600", "0PO00004600")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.move_relative(45.0)


def test_move_relative_negative():
    """Test negative relative move uses 2's complement."""
    # -45 degrees -> -17920 pulses -> "FFFFBA00"
    protocol = [("0mrFFFFBA00", "0PO00004600")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.move_relative(-45.0)


def test_stop():
    """Test stop command."""
    protocol = [("0st", "0GS00")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.stop()


def test_get_velocity():
    """Test reading velocity percentage."""
    # 0x64 = 100 decimal = 100%
    protocol = [("0gv", "0GV64")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        v = inst.velocity
        assert v == 100


def test_set_velocity():
    """Test setting velocity to 50%."""
    # 50 decimal = 0x32
    protocol = [("0sv32", "0GS00")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.velocity = 50


def test_get_jog_step_size():
    """Test reading jog step size."""
    # 35840 pulses = 90 degrees
    protocol = [("0gj", "0GJ00008C00")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        j = inst.jog_step_size
        assert j == pytest.approx(90.0)


def test_set_jog_step_size():
    """Test setting jog step size."""
    protocol = [("0sj00008C00", "0GS00")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.jog_step_size = 90.0


def test_forward():
    """Test forward jog."""
    protocol = [("0fw", "0PO00008C00")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.forward()


def test_backward():
    """Test backward jog."""
    protocol = [("0bw", "0PO00000000")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.backward()


def test_save_user_data():
    """Test save user data command."""
    protocol = [("0us", "0GS00")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.save_user_data()


def test_get_device_info():
    """Test get device info command."""
    protocol = [("0in", "0IN0E123456782026010100B700023000")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        info = inst.get_device_info()
        assert info.startswith("0E")


def test_address_a():
    """Test that a non-default address is prepended correctly."""
    protocol = [("Agp", "APO00000000")]
    with expected_protocol(
        ThorlabsELL14, protocol, address="A"
    ) as inst:
        pos = inst.position
        assert pos == pytest.approx(0.0)


def test_position_error_raises():
    """Test that an error status in response raises RuntimeError."""
    protocol = [("0ma00008C00", "0GS0C")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        with pytest.raises(RuntimeError, match="OUT_OF_RANGE"):
            inst.position = 90.0


def test_search_frequency():
    """Test frequency search on both motors."""
    protocol = [("0s1", "0GS00"), ("0s2", "0GS00")]
    with expected_protocol(ThorlabsELL14, protocol) as inst:
        inst.search_frequency()
