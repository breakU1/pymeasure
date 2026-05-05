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

from .thorlabsellx import ThorlabsEllx


class ThorlabsELL14(ThorlabsEllx):
    """Represents the Thorlabs ELL14 Motorized SM1 Optics Rotator.

    The ELL14 is a closed-loop rotary stage driven by two Elliptec resonant
    piezoelectric motors. It provides 360 degrees of travel with a resolution
    of 0.002 degrees and a maximum speed of 430 deg/s.

    Connection is via a USB adapter (FTDI serial) at 9600 baud, 8N1.

    Example usage::

        from pymeasure.instruments.thorlabs import ThorlabsELL14

        rotator = ThorlabsELL14("ASRL3::INSTR")  # COM3
        rotator.home()
        print(f"Position: {rotator.position} degrees")
        rotator.position = 90.0  # blocks until move completes
        print(f"Position: {rotator.position} degrees")

    :param adapter: pyvisa resource name of the instrument or adapter instance.
    :param name: Name of the instrument.
    :param address: Single hex character address ('0'-'F'), default '0'.
    :param kwargs: Any valid key-word argument for Instrument.
    """

    def __init__(self, adapter, name="Thorlabs ELL14", address="0", **kwargs):
        super().__init__(
            adapter,
            name,
            address=address,
            pulses_per_revolution=143360,
            **kwargs,
        )
