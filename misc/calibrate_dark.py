# -*- coding: utf-8 -*-
"""
Created on Thu May 16 23:43:46 2013

@author: Jose A. Jimenez-Berni

Calibrates the dark current as a function of integration time and generates
basic statistics about noise
"""

import OceanOptics
import numpy as np
import pandas

wl = []
temperatures = []
intensities = {}

spec = OceanOptics.STS()
sp = spec.acquire_spectrum()
wl = sp[0]
spec.set_scan_averages(5)
for integration_time in np.arange(1e5, 5e6, 1e5):
    print "Integrating spectrum for IT: %ims" % (integration_time*1e-3)
    spec.integration_time(integration_time)
    sp = spec.acquire_spectrum()
    detector_temperature = spec.device_temperature()
    temperatures.append(detector_temperature)
    intensities[integration_time] = sp[1]

dc_calib_df = pandas.DataFrame(intensities, index=wl)

dc_calib_df.to_csv('calib_dark_current.csv')


