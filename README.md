To get it work you need to install python 3, the pyusb, matplotlib and pyqtgraph libraries for scripts with the appropriate names (I use it under conda environment conda-forge).

Ubuntu: copy 60-hantek-6022BE.rules to /lib/udev/rules.d/ and reboot.
When connected, my device is detected with a different vendor number. After firmware loading it the changes this number to the desired one.
Therefore, it is necessary to register two devices in the rules file.

A variant of the 2-channel operation mode has been implemented.
Sample rate is set from 16 Msamples / s to 100 ksamples / s (48 Msamples / s mode have no good uniformity of collection: uniformity only for packets of 512 bytes length).
Channels are placed in the middle of the range (128 / 255 bit).
