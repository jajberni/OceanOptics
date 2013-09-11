# -*- coding: utf-8 -*-
"""
Created on Thu May 16 22:10:56 2013

@author: jim006
"""
from matplotlib import pyplot as plt
import OceanOptics

spec = OceanOptics.STS()
test = spec._read_temperatures()
print test
spec.set_scan_averages(5)
spec.set_integration_time(2e6)
cal = spec._read_irradiance_calibration()
sp = spec.acquire_spectrum()

fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot(sp[0],sp[1])
plt.show()
