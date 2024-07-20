# -*- coding: utf-8 -*-
"""
Created on %(date)s

@author: %(username)s
"""

import numpy as np, pylab as pl, sys, os
# import pyhantek
import pyhantek6022BE as pyhantek

#%% Settings

SR = 16_000_000 # samples / s per channel

ChVDIV = [1, 1] # V / Div

#%% Apply settings

h0 = pyhantek.Hantek()

h0.set_chvdiv(ChVDIV)

h0.set_samplerate(SR)

#%% Calculations

t = 1000. * h0.get_time() # ms

Ch1, Ch2 = h0.GetData()

# t = t[0:Ch1.size]

#%%

h0.close()

#%% Graphics

pl.figure()

# Ch1

pl.subplot(211)

pl.plot(t, Ch1, 'r', label = 'Ch1')

pl.ylim([-5. * ChVDIV[0], 5. * ChVDIV[0]])

pl.legend()

pl.grid(True)

pl.xlabel('Time, ms')
pl.ylabel('U, Volts')

# Ch2

pl.subplot(212)

pl.plot(t, Ch2, 'g', label = 'Ch2')

pl.ylim([-5. * ChVDIV[1], 5. * ChVDIV[1]])

pl.legend()

pl.grid(True)

pl.xlabel('Time, ms')
pl.ylabel('U, Volts')

pl.show()

#%%%

if __name__ == "__main__":
    
    pass

#%%% End
