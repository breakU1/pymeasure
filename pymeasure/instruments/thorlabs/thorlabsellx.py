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

import logging
from enum import IntEnum


from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import strict_range

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class EllxStatus(IntEnum):
    """Status and error codes returned by ELLx devices."""

    OK = 0
    COMM_TIMEOUT = 1
    MECH_TIMEOUT = 2
    COMMAND_ERROR = 3
    VALUE_OUT_OF_RANGE = 4
    MODULE_ISOLATED = 5
    MODULE_OUT_OF_ISOLATION = 6
    INIT_ERROR = 7
    THERMAL_ERROR = 8
    BUSY = 9
    SENSOR_ERROR = 10
    MOTOR_ERROR = 11
    OUT_OF_RANGE = 12
    OVER_CURRENT = 13


class ThorlabsEllx(Instrument):
    """Represents a Thorlabs ELLx Elliptec piezoelectric resonant motor device.

    This is the base class for the ELLx family (ELL6, ELL9, ELL14, ELL17,
    ELL18, ELL20, etc.). It implements the shared serial protocol documented
    in the ELLx Communication Protocol (etn032283-d03).

    The protocol uses ASCII hex encoding over a 9600 baud serial link. Each
    device on the multidrop bus has a single-character hex address ('0'-'F').

    Subclasses should set device-specific defaults such as
    ``pulses_per_revolution`` and ``name``.

    :param adapter: pyvisa resource name of the instrument or adapter instance
    :param name: Name of the instrument.
    :param address: Single hex character address of the device ('0'-'F').
    :param pulses_per_revolution: Encoder pulses per full revolution (360 deg)
        or per full travel for linear stages.
    :param kwargs: Any valid key-word argument for Instrument.
    """

    def __init__(
        self,
        adapter,
        name="Thorlabs ELLx",
        address="0",
        pulses_per_revolution=143360,
        **kwargs,
    ):
        self._address = str(address)
        self._pulses_per_revolution = pulses_per_revolution
        kwargs.setdefault("write_termination", "")
        kwargs.setdefault("read_termination", "\r\n")
        # The device only responds after a move completes, so we need
        # a generous timeout to handle slow or long-travel moves.
        kwargs.setdefault("timeout", 30000)

        super().__init__(
            adapter,
            name,
            includeSCPI=False,
            asrl={"baud_rate": 9600},
            **kwargs,
        )

    # --- Low-level protocol helpers ---

    def write(self, command):
        """Write a command string with the device address prepended.

        :param command: command string without the address prefix.
        """
        super().write(f"{self._address}{command}")

    def _send_command(self, command, data=""):
        """Send a command and return the parsed response.

        Every ELLx command generates a response. This method writes the
        command and reads back the response, parsing it into the reply
        command code and data payload.

        :param command: 2-character command mnemonic (e.g. ``"gp"``, ``"ma"``).
        :param data: optional data string to append (e.g. hex position).
        :returns: tuple of ``(reply_command, reply_data)`` strings.
        """
        self.write(f"{command}{data}")
        response = self.read()
        reply_cmd = response[1:3]
        reply_data = response[3:]
        return reply_cmd, reply_data

    def _check_status(self, status_code):
        """Check a status code and raise an error if non-zero.

        :param status_code: integer status code from a GS response.
        :raises RuntimeError: if the status indicates an error.
        """
        if status_code != 0:
            try:
                status = EllxStatus(status_code)
                msg = f"{status.name} (code {status_code})"
            except ValueError:
                msg = f"Unknown error (code {status_code})"
            raise RuntimeError(f"ELLx device error: {msg}")

    # --- Hex encoding/decoding helpers ---

    @staticmethod
    def _position_to_hex(pulses):
        """Convert a signed integer pulse count to an 8-char uppercase hex string.

        Uses 32-bit two's complement representation.

        :param pulses: signed integer pulse count.
        :returns: 8-character hex string (e.g. ``"00008C00"``).
        """
        if pulses < 0:
            pulses = pulses + 0x100000000
        return f"{pulses:08X}"

    @staticmethod
    def _hex_to_position(hex_str):
        """Convert an 8-char hex string to a signed integer pulse count.

        Interprets the value as a 32-bit signed two's complement integer.

        :param hex_str: 8-character hex string.
        :returns: signed integer pulse count.
        """
        value = int(hex_str, 16)
        if value >= 0x80000000:
            value -= 0x100000000
        return value

    def _degrees_to_pulses(self, degrees):
        """Convert a position in degrees to encoder pulses.

        :param degrees: position in degrees.
        :returns: integer number of encoder pulses.
        """
        return round(degrees / 360.0 * self._pulses_per_revolution)

    def _pulses_to_degrees(self, pulses):
        """Convert encoder pulses to a position in degrees.

        :param pulses: integer number of encoder pulses.
        :returns: position in degrees (float).
        """
        return pulses / self._pulses_per_revolution * 360.0

    # --- Properties and methods ---

    @property
    def position(self):
        """Control the absolute position in degrees (float).

        Getting this property queries the current position.
        Setting it moves the device to the specified absolute position.
        The setter blocks until the move is complete.

        For rotation stages, valid range is 0 to 359.99 degrees.
        """
        cmd, data = self._send_command("gp")
        if cmd == "PO":
            return self._pulses_to_degrees(self._hex_to_position(data))
        elif cmd == "GS":
            self._check_status(int(data, 16))
        return None

    @position.setter
    def position(self, degrees):
        pulses = self._degrees_to_pulses(degrees)
        hex_pos = self._position_to_hex(pulses)
        cmd, data = self._send_command("ma", hex_pos)
        if cmd == "GS":
            self._check_status(int(data, 16))

    @property
    def status(self):
        """Get the device status as an :class:`EllxStatus` enum value.

        Reading clears any stored error code on the device.
        """
        cmd, data = self._send_command("gs")
        if cmd == "GS":
            return EllxStatus(int(data, 16))
        return None

    @property
    def velocity(self):
        """Control the velocity as a percentage of maximum (int, 0 to 100).

        Note that depending on load, velocities below 25-45% may cause the
        device to stall.
        """
        cmd, data = self._send_command("gv")
        if cmd == "GV":
            return int(data, 16)
        elif cmd == "GS":
            self._check_status(int(data, 16))
        return None

    @velocity.setter
    def velocity(self, percentage):
        strict_range(percentage, [0, 100])
        hex_vel = f"{int(percentage):02X}"
        cmd, data = self._send_command("sv", hex_vel)
        if cmd == "GS":
            self._check_status(int(data, 16))

    @property
    def jog_step_size(self):
        """Control the jog step size in degrees (float).

        Setting to 0 enables continuous motion mode (ELL14 only).
        In continuous mode, use :meth:`forward`/:meth:`backward` to start
        and :meth:`stop` to halt motion.
        """
        cmd, data = self._send_command("gj")
        if cmd == "GJ":
            return self._pulses_to_degrees(self._hex_to_position(data))
        elif cmd == "GS":
            self._check_status(int(data, 16))
        return None

    @jog_step_size.setter
    def jog_step_size(self, degrees):
        pulses = self._degrees_to_pulses(degrees)
        hex_pos = self._position_to_hex(pulses)
        cmd, data = self._send_command("sj", hex_pos)
        if cmd == "GS":
            self._check_status(int(data, 16))

    def home(self, direction=0):
        """Move the device to the home position.

        :param direction: ``0`` for clockwise, ``1`` for counter-clockwise.
            Only applies to rotation stages; ignored by other stage types.
        """
        cmd, data = self._send_command("ho", str(direction))
        if cmd == "GS":
            self._check_status(int(data, 16))

    def move_relative(self, degrees):
        """Move by a relative distance in degrees.

        Positive values move forward, negative values move backward.

        :param degrees: relative distance in degrees.
        """
        pulses = self._degrees_to_pulses(degrees)
        hex_pos = self._position_to_hex(pulses)
        cmd, data = self._send_command("mr", hex_pos)
        if cmd == "GS":
            self._check_status(int(data, 16))

    def stop(self):
        """Stop continuous motion.

        Applicable to ELL14, ELL16, ELL21, and ELL22 devices.
        """
        cmd, data = self._send_command("st")
        if cmd == "GS":
            status = int(data, 16)
            if status != 0 and status != EllxStatus.BUSY:
                self._check_status(status)

    def forward(self):
        """Jog forward by the current jog step size.

        If jog step size is 0 (continuous mode), motion continues
        until :meth:`stop` is called.
        """
        cmd, data = self._send_command("fw")
        if cmd == "GS":
            status = int(data, 16)
            if status != 0 and status != EllxStatus.BUSY:
                self._check_status(status)

    def backward(self):
        """Jog backward by the current jog step size.

        If jog step size is 0 (continuous mode), motion continues
        until :meth:`stop` is called.
        """
        cmd, data = self._send_command("bw")
        if cmd == "GS":
            status = int(data, 16)
            if status != 0 and status != EllxStatus.BUSY:
                self._check_status(status)

    def search_frequency(self):
        """Run frequency search on both motors to optimize performance.

        This may take several seconds and the device may move during the
        search. Call :meth:`save_user_data` afterwards to persist the
        new frequency settings.
        """
        cmd, data = self._send_command("s1")
        if cmd == "GS":
            status = int(data, 16)
            if status != 0:
                self._check_status(status)
        cmd, data = self._send_command("s2")
        if cmd == "GS":
            status = int(data, 16)
            if status != 0:
                self._check_status(status)

    def save_user_data(self):
        """Save current motor parameters to device EEPROM.

        Call this after changing frequency settings or other parameters
        that should persist across power cycles.
        """
        cmd, data = self._send_command("us")
        if cmd == "GS":
            self._check_status(int(data, 16))

    def get_device_info(self):
        """Get device identification information.

        :returns: raw information string from the device.
        """
        cmd, data = self._send_command("in")
        if cmd == "IN":
            return data
        elif cmd == "GS":
            self._check_status(int(data, 16))
        return None

