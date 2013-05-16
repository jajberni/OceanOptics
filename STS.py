
""" File:           devices.py
    Author:         Andreas Poehlmann
    Last change:    2012/09/04

    Python Interface for OceanOptics Spectometers.
    Current device classes:
        * USB2000+
"""

#----------------------------------------------------------
import usb.core
import struct
from _defines import OceanOpticsError as _OOError
import numpy as np
import time
import sys
#----------------------------------------------------------




class STS(object):
    """ class STS:

            Serial --> serial_number
            acquire_spectrum() --> np.array
            device_temperature() --> float celcius
            integration_time(time_us=None) --> returns / sets the ~
    """

    def __init__(self):

        self._dev = usb.core.find(idVendor=0x2457, idProduct=0x4000)
        if self._dev is None:
            raise _OOError('No OceanOptics STS spectrometer found!')
        else:
            print ('*NOTE*: Currently the first device matching the '
                   'Vendor/Product id is used')

        # This information comes from the OEM-Datasheet
        # "http://www.oceanoptics.com/technical"
        #       "/engineering/OEM%20Data%20Sheet%20--%20USB2000+.pdf"
        self._EP1_out = 0x01
        self._EP1_in = 0x81
        self._EP2_in = 0x82
        self._EP2_out = 0x02
        self._EP3_interrupt = 0x83
        self._EP1_in_size = 64
        self._EP2_in_size = 64
        self._EP1_out_size = 64
        self._EP2_out_size = 64


        self._START_BYTES = 0xC0C1
        self._END_BYTES = 0xC2C3C4C5
        self._PROTOCOL_VERSION = 0x0100

        self._MSG_GET_CORRECTED_SPECTRUM = 0x00101000
        self._MSG_SET_INTEGRATION_TIME = 0x00110010

        self._MSG_GET_HW_VERSION=0x00000080
        self._MSG_GET_SW_VERSION=0x00000090
        self._MSG_GET_SERIAL_NUMBER=0x00000100

        self._MSG_GET_AVG_SCANS=0x00110510
        self._MSG_SET_AVG_SCANS=0x00120010

        self._MSG_GET_TEMPERATURE=0x00400001
        self._MSG_GET_ALL_TEMPERATURE=0x00400002

        self._MSG_GET_WAVELENGTH_COEFF_COUNT = 0x00180100
        self._MSG_GET_WAVELENGTH_COEFF = 0x00180101

        self._MSG_GET_NONLINEAR_COEFF_COUNT = 0x00181100
        self._MSG_GET_NONLINEAR_COEFF = 0x00181101


        # This part makes the initialization a little bit more robust
        self._dev.set_configuration()
        print "HW Version: %i" % self._get_hw_version()
        print "HW Version: %i" % self._get_hw_version()
        self.integration_time(10000) # sets self._it
        self._request_spectrum()
        self._wl = self._get_wavelength_calibration()
        self._nl = self._get_nonlinearity_calibration()
        import pdb; pdb.set_trace()
        sys.exit(0)

        self._initialize()
        #<robust>#
        for i in range(10):
            try:
                self._usbcomm = self._query_status()['usb_speed']
                break
            except usb.core.USBError: pass
        else: raise _OOError('Initialization USBCOM')


        for i in range(10):
            try:
                self._request_spectrum()
                break
            except: pass
        else: raise _OOError('Initialization SPECTRUM')
        #</robust>#

        self._wl = self._get_wavelength_calibration()
        self._nl = self._get_nonlinearity_calibration()


        self._st = self._get_saturation_calibration()

        self.Serial = self._get_serial()


    def integration_time(self, time_us=None):
        if not (time_us is None):
            self._set_integration_time(time_us)
        #self._it = self._query_status()['integration_time']
        return time_us

    def device_temperature(self):
        return self._read_pcb_temperature()

    def acquire_spectrum(self):
        raw_intensity = np.array(self._request_spectrum(), dtype=np.float)[20:]
        wavelength = sum( self._wl[i] * np.arange(20,2048)**i for i in range(4) )
        # fixed linearization, see documentation at:
        # --> http://www.oceanoptics.com/technical/OOINLCorrect%20Linearity%20Coeff%20Proc.pdf
        intensity =  raw_intensity / sum( self._nl[i] * raw_intensity**i for i in range(8) ) * self._st
        return np.vstack([wavelength, intensity])


    #-----------------------------
    # The user doesn't need to see this
    #-----------------------------
    def _initialize(self):
        """ 0x01 initialize """
        self._dev.write(self._EP1_out, struct.pack('<B', 0x01))

    def _get_hw_version(self):
        self._dev.write(self._EP1_out, struct.pack('<HHHHLLLHBB16sL16sL', \
        self._START_BYTES,self._PROTOCOL_VERSION,0x0000,0x0000,\
        self._MSG_GET_HW_VERSION,0x00000000,0x00000000,0x0000,0x00,0x00,'',\
        0x14,'',self._END_BYTES))
        ret = self._dev.read(self._EP1_in, self._EP1_in_size)

        if len(ret) == 64:
            ack = struct.unpack('<HHHHLL6sBBB15sL16sL', ret)
            if ack[3] == 0:
                return ack[9]
            else:
                print "Error code: %i" % ack[3]
                return -1
        else:
            print "Unexpected msg lenght: %i vs 64" % len(ret)
            return -1


    def _set_integration_time(self, time_us):
        """
        Sets the integration time in us.

        :param time_us: Integration time in us.
        :returns: The actual integration time returned by the spectrometer or -1 in case of error

        """


        self._dev.write(self._EP1_out, struct.pack('<HHHHLLLHBBL12sL16sL', \
        self._START_BYTES,self._PROTOCOL_VERSION,0x0000,0x0000,\
        self._MSG_SET_INTEGRATION_TIME,0x00000000,0x00000000,0x0000,0x00,0x04,time_us,'',\
        0x14,'',self._END_BYTES))

        try:
            ret = self._dev.read(self._EP1_in, self._EP1_in_size)
            if len(ret) == 64:
                ack = struct.unpack('<HHHHLL6sBBL12sL16sL', ret)
                if ack[3] == 0:
                    time_us = ack[9]
                    print "Error setting integration time"
                    return -1
                else:
                    print "Error code: %i" % ack[3]
                    return -1
            else:
                print "Unexpected msg lenght: %i vs 64" % len(ret)
                return -1
        except Exception:
            self._it = time_us
            print "Probably set..."


    def _read_pcb_temperature(self):
        """ 0x6C read pcb temperature """
        self._dev.write(self._EP1_out, struct.pack('<B', 0x6C))
        ret = self._dev.read(self._EP1_in, self._EP1_in_size)
        if ret[0] != 0x08:
            raise Exception('read_pcb_temperature: Wrong answer')
        adc, = struct.unpack('<h', ret[1:])
        return 0.003906*adc


    def _request_spectrum(self):
        """
        Return the spectrum array.

        :returns: An array with 1024 unsigned short elements and the spectral intensity.
        """
        # XXX: 100000 was an arbitary choice. Should probably be a little less than the USB timeout
        self._dev.write(self._EP1_out, struct.pack('<HHHHLLLHBB16sL16sL', \
        self._START_BYTES,self._PROTOCOL_VERSION,0x0000,0x0000,\
        self._MSG_GET_CORRECTED_SPECTRUM,0x00000000,0x00000000,0x0000,0x00,0x00,'',\
        0x14,'',self._END_BYTES))

        time.sleep( max(self._it , 0) * 1e-6 )
        ret = [self._dev.read(self._EP1_in, self._EP1_in_size) for _ in range(33)]
        ret = sum(ret[1:], ret[0])
        #print "".join('%02x' % i for i in ret)
        spectrum = struct.unpack('<HHHHLLLHBB16sL1024H16sL', ret)
        print(spectrum[12:1036])
        return spectrum[12:1036]


    def _get_wavelength_calibration(self):
        return [float(self._query_coefficient(i,self._MSG_GET_WAVELENGTH_COEFF)) for i in range(4)]

    def _get_nonlinearity_calibration(self):
        nl_coef = int(self._query_coefficient_count(self._MSG_GET_NONLINEAR_COEFF_COUNT))
        if nl_coef != 8:
            # Don't care about this right now
            raise _OOError('This spectrometer has less correction factors')
        return [float(self._query_coefficient(i,self._MSG_GET_NONLINEAR_COEFF)) for i in range(nl_coef)]

    def _get_saturation_calibration(self):
        ret = self._query_information(0x11, raw=True)
        return 65535.0/float(struct.unpack('<h',ret[6:8])[0])

    def _read_irradiance_calibration(self):
        """ 0x6D read irradiance calib factors """
        raise NotImplementedError


    def _query_coefficient_count(self, command):
        """
        Gets the coefficient count for a given command.

        :param command: E.g. Wavelength calibration, stray light...
        :returns: The value of the coefficient count stored in EEPROM.

        """
        self._dev.write(self._EP1_out, struct.pack('<HHHHLLLHBB16sL16sL', \
        self._START_BYTES,self._PROTOCOL_VERSION,0x0000,0x0000,\
        command,0x00000000,0x00000000,0x0000,0x00,0x00,'',\
        0x14,'',self._END_BYTES))
        ret = self._dev.read(self._EP1_in, self._EP1_in_size)

        if len(ret) == 64:
            ack = struct.unpack('<HHHHLL6sBBB15sL16sL', ret)
            if ack[3] == 0:
                return ack[9]
            else:
                print "Error code: %i" % ack[3]
                return -1
        else:
            print "Unexpected msg lenght: %i vs 64" % len(ret)
            return -1


    def _query_coefficient(self, index, command):
        """
        Sets the integration time in us.

        :param index: Index of the coefficient to retrieve.

        :param command: E.g. Wavelength calibration, stray light...
        :returns: The value of the coefficient stored in EEPROM.

        """
        self._dev.write(self._EP1_out, struct.pack('<HHHHLLLHBBB15sL16sL', \
        self._START_BYTES,self._PROTOCOL_VERSION,0x0000,0x0000,\
        command,0x00000000,0x00000000,0x0000,0x00,0x01,index,'',\
        0x14,'',self._END_BYTES))
        ret = self._dev.read(self._EP1_in, self._EP1_in_size)

        if len(ret) == 64:
            ack = struct.unpack('<HHHHLL6sBBf12sL16sL', ret)
            if ack[3] == 0:
                return ack[9]
            else:
                print "Error code: %i" % ack[3]
                return -1
        else:
            print "Unexpected msg lenght: %i vs 64" % len(ret)
            return -1


    #-------------------------------------------
    # This stuff is not implemented yet.
    # Don't really need it ...
    #-------------------------------------------
    def _set_strobe_enable_status(self):
        """ 0x03 set strobe enable status """
        raise NotImplementedError

    def _set_shutdown_mode(self):
        """ 0x04 set shutdown mode """
        raise NotImplementedError

    def _write_information(self, address):
        """ 0x06 write info """
        raise NotImplementedError

    def _set_trigger_mode(self, mode):
        """ 0x0A set trigger mode """
        raise NotImplementedError

    def _query_plugin_num(self):
        """ 0x0B query number of plugin accessories """
        raise NotImplementedError

    def _query_plugin_ident(self):
        """ 0x0C query plugin identifiers """
        raise NotImplementedError

    def _detect_plugins(self):
        """ 0x0D detect plugins """
        raise NotImplementedError

    def _i2c_read(self):
        """ 0x60 I2C read """
        raise NotImplementedError

    def _i2c_write(self, data):
        """ 0x61 I2C write """
        raise NotImplementedError

    def _spi_io(self):
        """ 0x62 spi io """
        raise NotImplementedError

    def _write_register_info(self):
        """ 0x6A write register info """
        raise NotImplementedError



if __name__ == '__main__':
    sts = STS()

