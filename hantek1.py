# -*- coding: utf-8 -*-
"""
Created on %(date)s

@author: %(username)s
"""

import numpy as np, pylab as pl, sys, os
# import pyhantek
import pyhantek6022BE as pyhantek
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import pyqtgraph as pg
import multiprocessing as mp
import time

ll = ['/home/vadter/.local/bin']

if (sys.path.count(ll) == 0):

    sys.path = sys.path + ll

import optelems3 as oe

#%% Funcs

def updateGraph(qu1):
   
    plot1 = pg.plot(title = "Plot ADC")
    
    curve1 = plot1.plot([0], [0], pen = pg.mkPen('r', width = 1))
    curve2 = plot1.plot([0], [0], pen = pg.mkPen('g', width = 1))
    
    while True:
        
        Dat = qu1.get()
        
        # curve1.setData(Data[0], Data[1])
        curve1.setData(Dat[0], Dat[1])
        curve2.setData(Dat[0], Dat[2])
        
        QtWidgets.QApplication.processEvents()
        
        time.sleep(0.01)

#%% Settings

SR = 16_000_000 # samples / s per channel

ChVDIV = [1, 1] # V / Div

#%% Apply settings

h0 = pyhantek.Hantek()

h0.set_chvdiv(ChVDIV)

h0.set_samplerate(SR)

t = 1000. * h0.get_time()

#%% Graph process

que1 = mp.Queue()

graph_process = mp.Process(target = updateGraph, args = (que1,))

graph_process.start()

#%%% Calculations

while True:
    
    Ch1, Ch2 = h0.GetData()
    
    que1.put((t, Ch1, Ch2))
    
    time.sleep(0.1)

graph_process.join()

h0.close()

#%%%

if __name__ == "__main__":
    
    pass

#%%% End