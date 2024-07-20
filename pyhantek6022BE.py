import usb.core
import usb.util
import time, struct, pprint, csv
import numpy as np

#%% Class

class Hantek:
    
    def __init__(self):
        
        dev = usb.core.find(idVendor = 0x04b4, idProduct = 0x6022)
        
        if dev is None:
            
            print('Firmware is already loaded')
        
        else:
            
            print('Firmware is loading...')

            self.dev = dev
            
            self.LoadFirmware()
            
            time.sleep(2.)
            
            print('Firmware is loaded')
            
        dev = usb.core.find(idVendor = 0x04b5, idProduct = 0x6022)

        if dev is None:
            
            raise ValueError('Device Hantek 6022BE not found')
        
        else:
            
            print('Device Hantek 6022BE is connected')
            self.dev = dev

        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        # dev.set_configuration()
        # dev.set_configuration(1)
        
        # get an endpoint instance
        cfg = dev.get_active_configuration()
        
        intf = cfg[(0,0)]
        
        # dev.set_interface_altsetting(interface = 0, alternate_setting = 0)
        
        self.ep2 = usb.util.find_descriptor(
            intf,
            custom_match = \
            lambda e: \
                e.bEndpointAddress == 0x02)
        
        self.ep6 = usb.util.find_descriptor(
            intf,
            custom_match = \
            lambda e: \
                e.bEndpointAddress == 0x86)
        
        assert self.ep2 is not None
        assert self.ep6 is not None

        # # Настройки триггера
        # self.trig_source = 0 # 0 - Ch1, 1 - Ch2, ...
        # self.h_trig_level = 50 # позиция горизонтального триггера, 0 - центр буфера, 50 - начало буфера
        # self.v_trig_level = 127 # позиция вертикального триггера, 0 - 255 ?
        # self.trig_slope = 0 # наклон 0 - RISE, 1 - FALL
        # self.trig_sweep_mode = 'NORMAL' # 'AUTO', 'SINGLE'
        # self.trig_sweep_modes = ['NORMAL', 'AUTO', 'SINGLE']
        
        # VDiv, вольт на деление для каждого канала
        self.dictVDiv_N = {1: 1, 2: 0.5, 5: 0.2, 10: 0.1}
        self.dictN_VDiv = dict(map(reversed, self.dictVDiv_N.items()))

        self.ChVDiv = [1, 1]

        # Sample rate samoles / s
        self.dictSR_N = {48: 48_000_000, 16: 16_000_000, 8: 8_000_000,
                         4: 4_000_000, 1: 1_000_000, 50: 500_000,
                         20: 200_000, 10: 100_000}
        self.dictN_SR = dict(map(reversed, self.dictSR_N.items()))
        
        self.samplerate = 16_000_000 # sample / s on one channel

        # Длина буфера данных каждого канала в АЦП
        self.dictDatLen_N = {48_000_000: 2097152, 16_000_000: 262144,
                             8_000_000: 262144, 4_000_000: 262144,
                             1_000_000: 262144, 500_000: 1048576,
                             200_000: 1048576, 100_000: 1048576}
        
        self.data_len = self.dictDatLen_N[self.samplerate] # all
        self.buf_len = self.data_len // 2 # on one channel

        # Время отсчетов
        self.time = np.linspace(0., self.buf_len - 1,
                                self.buf_len) / self.samplerate

        # Инициализация
        self.Init()

        self.SetVDiv()
        
        self.SetSampleRate()

    # USB communication
    def ctrl(self, rtype, req, data, error = None, wValue = 0):
        
        try:
            
            ret = self.dev.ctrl_transfer(rtype, req, wValue, 0, data)

        except usb.core.USBError as e:

            print("got", e.errno, e)

            if e.errno == error:

                return

            else:

                raise e

        return ret

    def bread(self, length):
        
        timeout = 1000
        
        return self.dev.read(self.ep6.bEndpointAddress, length, timeout)


    def Init(self):
        
        data = self.ctrl(0xC0, 162, 128, 0, 0x08)
        # print('data init:', data)
        
    def SetVDiv(self):
        
        data = self.ctrl(0x40, 224,
                         bytes.fromhex("{:02x}".format(self.dictN_VDiv[self.ChVDiv[0]])),
                         0, 0x00)
        # print('data V / Div 1:', data)

        data = self.ctrl(0x40, 225,
                         bytes.fromhex("{:02x}".format(self.dictN_VDiv[self.ChVDiv[1]])),
                         0, 0x00)
        # print('data V / Div 2:', data)
    
    def SetSampleRate(self):
        
        data = self.ctrl(0x40, 226,
                         bytes.fromhex("{:02x}".format(self.dictN_SR[self.samplerate])),
                         0, 0x00)
        # print('data sample rate:', data)
    
    def GetData(self):
        
        data = self.ctrl(0x40, 227, b'\x01', 0, 0x00)
        # print('get data:', data)

        bread = self.bread(self.dictDatLen_N[self.samplerate])

        Chs = np.array(bread, dtype = float).reshape(len(bread) // 2, 2).T
        
        Ch1 = (Chs[0] - 128.) / 255. * 10. * self.ChVDiv[0]
        Ch2 = (Chs[1] - 128.) / 255. * 10. * self.ChVDiv[1]
        
        return [Ch1, Ch2]

    def set_samplerate(self, rate):

        if (rate in self.dictN_SR.keys()):

            self.samplerate = rate
            self.data_len = self.dictDatLen_N[self.samplerate] #
            self.buf_len = self.data_len // 2

            # Время отсчетов
            self.time = np.linspace(0., self.buf_len - 1,
                                    self.buf_len) / self.samplerate
            
            print('Samplerate of each channel is set to:', 
                  pprint.pformat(self.samplerate, underscore_numbers = True))

            print('Data length of each channel is set to:', 
                  pprint.pformat(self.buf_len, underscore_numbers = True))
            
            self.SetSampleRate()
        
        else:
            
            print('Available sample rates:',
                  pprint.pformat(self.get_rates(), underscore_numbers = True))
            
            print('Current samplerate:',
                  pprint.pformat(self.samplerate, underscore_numbers = True))

    def set_chvdiv(self, chvdiv):
        
        for i in range(len(chvdiv)):
        
            if (chvdiv[i] in self.dictN_VDiv.keys()):        
        
                self.ChVDiv[i] = chvdiv[i]
                
            else:
            
                print('Wrong value of V / DIV for Ch%d' % (i + 1))
                
                print('Available V / DIV:', list(self.dictN_VDiv.keys()))
                
                print('Current V / DIV:')
                
                break
        
        self.SetVDiv()
            
        print('Channel 1:', self.ChVDiv[0], ' V / DIV')
        print('Channel 2:', self.ChVDiv[1], ' V / DIV')

    def get_rate(self):

        return self.samplerate

    def get_time(self):
        
        return self.time

    def get_rates(self):
        
        values = [ 50_000, 250_000, 500_000, 2_000_000, 4_000_000,
                   8_000_000, 24_000_000]
        
        return values

    def LoadFirmware(self):
        
        wValue = [32658, 58880, 32658, 58880, 872, 888, 894, 437, 453, 469,
                  485, 501, 517, 533, 549, 565, 581, 597, 613, 629, 645, 661,
                  677, 693, 709, 725, 733, 128, 144, 160, 176, 192, 208, 224,
                  240, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416,
                  432, 436, 734, 750, 766, 782, 798, 814, 3, 822, 838, 854,
                  870, 67, 1024, 0, 895, 32658, 58880, 32658, 58880, 2398,
                  3256, 3272, 3288, 3304, 3320, 3336, 3352, 3368, 3384, 3400,
                  2939, 2955, 2971, 2987, 3003, 3019, 3035, 3036, 40, 64, 70,
                  4172, 4188, 4204, 4220, 4829, 4845, 4865, 4847, 4863, 72, 78,
                  80, 86, 102, 118, 134, 150, 166, 182, 198, 214, 230, 246,
                  262, 278, 294, 310, 326, 342, 358, 374, 390, 406, 422, 438,
                  454, 470, 486, 502, 518, 534, 550, 566, 582, 598, 614, 630,
                  646, 662, 678, 694, 710, 726, 742, 758, 774, 790, 806, 822,
                  838, 854, 870, 886, 902, 918, 934, 950, 966, 982, 998, 1014,
                  1030, 1046, 1062, 1078, 1094, 1110, 1126, 1142, 1158, 1174,
                  1190, 1206, 1222, 1238, 1240, 4737, 4753, 4785, 4801, 4807,
                  4823, 4233, 4249, 4265, 4281, 4761, 4777, 4288, 4304, 4320,
                  4336, 42, 50, 66, 74, 82, 3065, 3066, 3067, 3068, 3069, 3070,
                  3071, 3578, 3579, 3580, 3581, 3582, 3583, 4881, 4882, 4883,
                  4884, 4885, 4886, 4887, 4888, 4889, 4890, 4891, 4892, 4893,
                  4894, 4895, 4896, 4897, 4898, 3955, 3961, 3977, 3993, 4009,
                  4025, 4028, 4397, 4407, 4423, 4439, 4449, 4029, 4039, 4055,
                  4071, 4087, 4101, 2400, 2416, 2432, 2448, 2464, 2480, 2496,
                  2512, 2528, 2544, 2560, 2576, 2592, 2608, 2624, 2640, 2656,
                  2672, 3864, 3880, 3896, 3912, 3928, 3944, 3954, 54, 1907,
                  1923, 1939, 1955, 1971, 1987, 2003, 2019, 2035, 2051, 2067,
                  2083, 2099, 2115, 2131, 2147, 2163, 2179, 2195, 2211, 2227,
                  2243, 2259, 2275, 2291, 2307, 2323, 2339, 2355, 2371, 2387,
                  2397, 1241, 1257, 1273, 1289, 1305, 1321, 1337, 1353, 1369,
                  1385, 1401, 1417, 1433, 1449, 1465, 1481, 1497, 1513, 1529,
                  1545, 1561, 1577, 1593, 1609, 1625, 1641, 1657, 1673, 1689,
                  1705, 1721, 1737, 1753, 1769, 1785, 1801, 1817, 1833, 1849,
                  1865, 1881, 1897, 1906, 51, 46, 43, 4502, 4518, 4534, 4550,
                  3584, 3600, 3616, 3632, 3648, 3664, 3680, 3696, 3712, 3728,
                  4649, 4665, 4681, 3, 19, 4602, 4618, 4634, 4873, 4343, 4359,
                  4375, 4391, 4552, 4568, 4584, 4600, 4450, 4466, 4482, 4498,
                  75, 2675, 2691, 2707, 2723, 2739, 2755, 2771, 2787, 2803,
                  2819, 2835, 2851, 2867, 2883, 2899, 2915, 2931, 4693, 4695,
                  4711, 4727, 4736, 3037, 3053, 3550, 3566, 4102, 4118, 4134,
                  4150, 4166, 23, 39, 67, 83, 3072, 3088, 3104, 3120, 3136,
                  3152, 3168, 3184, 3200, 3216, 3232, 3248, 0, 3410, 3730,
                  3746, 3762, 3775, 3791, 3807, 3809, 3825, 3826, 3842, 3858,
                  3422, 3438, 3454, 3470, 3486, 3502, 3518, 3534, 2674, 32658,
                  58880, 32658, 58880]
        
        data = ['01', '01', '01', '01', '90e668e0ff74fff0e0b40b04eff0d322',
                '90e668eff0c3', '22', '907fe9e064a360030202c5a3e0750800',
                'f509a3e0fee4ee4208907feee0750a00', 'f50ba3e0fee4ee420a907fe8e0644070',
                '64e50b450a70030202d6e4907fc5f090', '7fb4e020e3f9907fc5e0750c00f50de4',
                'fcfdc3ed950dec950c501f74c02df582', 'e4347ef583e0ffe5092df582e5083cf5',
                '83eff00dbd00010c80d8e50d2509f509', 'e50c3508f508c3e50b950df50be50a95',
                '0cf50a809c907fe8e064c060030202d6', 'e50b450a607bc3e50b9440e50a940050',
                '08850a0c850b0d8006750c00750d40e4', 'fcfdc3ed950dec950c501fe5092df582',
                'e5083cf583e0ff74002df582e4347ff5', '83eff00dbd00010c80d8907fb5e50df0',
                '2509f509e50c3508f508c3e50b950df5', '0be50a950cf50a907fb4e030e29280f7',
                '907fe9e0b4ac0ae4907f00f0907fb504', 'f0907fb4e04402f0', '22',
                '90e6b9e064a36003020198a3e0750800', 'f509a3e0fee4ee420890e6bee0750a00',
                'f50ba3e0fee4ee420a90e6b8e0644070', '66e50b450a70030201ade490e68af0a3',
                'f090e6a0e020e1f990e68be0750c00f5', '0de4fcfdc3ed950dec950c501f74402d',
                'f582e434e7f583e0ffe5092df582e508', '3cf583eff00dbd00010c80d8e50d2509',
                'f509e50c3508f508c3e50b950df50be5', '0a950cf50a809a90e6b8e064c0600302',
                '01ade50b450a70030201adc3e50b9440', 'e50a94005008850a0c850b0d8006750c',
                '00750d40e4fcfdc3ed950dec950c501f', 'e5092df582e5083cf583e0ff74402df5',
                '82e434e7f583eff00dbd00010c80d8e4', '90e68af0a3e50df02509f509e50c3508',
                'f508c3e50b950df50be50a950cf50a90', 'e6a0e030e18c80f790e6b9e0b4ac0e90',
                'e7407401f0e490e68af0a304f090e6a0', 'e04480f0', '22',
                'c2011203689200907f95e044c0f0d2e8', '30000890e65d74fff08006907fab74ff',
                'f030000890e6687408f08007907fafe0', '4401f030000890e65c7401f08006907f',
                'ae7401f0d2af3001fd30000512008080', '031201b5c20180ee', '020336',
                'c0e0c083c082c085c084c086758600d2', '015391ef30000890e65d7401f0800690',
                '7fab7401f0d086d084d085d082d083d0', 'e032', '020400', '02033600',
                '02037f', '787fe4f6d8fd7581200202de', '00', '00', '01', '01', 'c105',
                '90e6007410f0120f1800000090e61274', 'a0f0000000e490e613f000000090e614',
                '74e0f0000000e490e615f000000090e6', '047480f00000007402f00000007406f0',
                '000000e4f000000090e61804f0000000', '7411f000000090e61a7409f000000090',
                'e6d27402f000000090e6e214f0000000', 'e490e671f075b4ff90e670f075b280c2',
                'a4c2a3c2a2c2a7c2a6c2a5f51df51a12', '130990e67ae04401f022',
                'e51d64017031751d0290e6f574fff090', 'e6047480f00000007402f00000007406',
                'f0000000e4f0000000fffe000fbf0001', '0ebe03f7bfe8f4e5bb30e72590e6f4e0',
                '30e01ee5ac20e019e5bb30e7fb90e6d0', '7428f0000000e490e6d1f000000075bb',
                '06', '22', 'd322', 'd322', 'd322', '90e680e030e71800000090e6247402f0',
                '000000e490e625f0000000d205801600', '0000e490e624f000000090e6257440f0',
                '000000c20590e6bae0f51bd322', '90e740e51bf0e490e68af090e68b04f0', 'd322',
                '90e6bae0f518d322', '90e740e518f0e490e68af090e68b04f0', 'd322', 'd322',
                'd322', 'd322', '90e678e05410ffc4540f4450f51913e4',
                '33f51cd20290e6b9e0245e605024f060', '3024d2b4080040030204d590008f75f0',
                '03a4c58325f0c5837302024b02029602', '02dc0204460204d50204d50204d50204',
                '65a205e43390e740f0e490e68af090e6', '8b04f090e6a0e04480f00204d790e6ba',
                'e0752d00f52ea3e0fee4ee422d90e6be', 'e0752f00f530a3e0fee4ee422f90e6b8',
                'e064c060030201b3e530452f70030204', 'd790e6a0e020e1f9c3e5309440e52f94',
                '005008852f3185303280067531007532', '4090e6b9e0b4a335e4f533f534c3e534',
                '9532e53395315060e52e2534f582e52d', '3533f583e0ff74402534f582e434e7f5',
                '83eff00534e5347002053380d0e4f533', 'f534c3e5349532e53395315018744025',
                '34f582e434e7f58374cdf00534e53470', '02053380ddad327ae779407ee77f40ab',
                '07af2eae2d120fbde490e68af090e68b', 'e532f0252ef52ee531352df52dc3e530',
                '9532f530e52f9531f52f0200ee90e6b8', 'e0644060030204d7e530452f70030204',
                'd7e490e68af090e68bf090e6a0e020e1', 'f990e68be0753100f53290e6b9e0b4a3',
                '35e4f533f534c3e5349532e533953150', '3874402534f582e434e7f583e0ffe52e',
                '2534f582e52d3533f583eff00534e534', '7002053380d0ad327ae779407ee77f40',
                'ab07af2eae2d12112de532252ef52ee5', '31352df52dc3e5309532f530e52f9531',
                'f52f0201bee490e68af090e68bf090e6', 'a0e020e1f990e740e0f5351460291460',
                '1d24fd601024fb60030204d7c2a4d2a3', 'd2a20204d7c2a4c2a3c2a20204d7c2a4',
                'c2a3d2a20204d7c2a4d2a3c2a20204d7', 'e490e68af090e68bf090e6a0e020e1f9',
                '90e740e0f53524fe601a24fd600d24fb', '701bc2a7d2a6d2a50204d7c2a7c2a6c2',
                'a50204d7c2a7c2a6d2a50204d7c2a7d2', 'a6c2a50204d7e490e68af090e68bf090',
                'e6a0e020e1f990e740e0f535120ef203', '880103740403600803c20a034d1003af',
                '14033b1803291e031730039c32000003', 'd390e60174eaf090e05074fff0751a01',
                '0203d390e60174aaf090e05074fff075', '1a010203d390e60174caf090e05074fb',
                'f0751a010203d390e60174caf090e040', '7401f0a3f0e4f51a807390e60174caf0',
                '90e0407402f0a304f0e4f51a805f90e6', '0174caf090e0407405f0a304f0e4f51a',
                '804b90e60174caf090e0407417f0a304', 'f0e4f51a803790e60174caf090e04074',
                '30f0a3f0e4f51a802490e60174caf090', 'e0407478f0a3f0e4f51a801190e60174',
                'caf090e04074f0f0a3f0e4f51a90e6f5', '74fff090e080e090e6f3f090e081e090',
                'e6c3f090e082e090e6c1f090e083e090', 'e6c2f090e085e090e6c0f090e086e090',
                'e6f4f075af07e51ab4010a74e0f59a74', '87f59b800874e0f59a7400f59b759de4',
                'e4f59ef533f53490e67be090e67cf005', '34e534700205336480453370ea0204d7',
                'e490e68af090e68bf090e6a0e020e1f9', '90e740e0f53564017077751d01807290',
                'e6bae0752d00f52ea3e0fee4ee422d90', 'e6bee0752f00f530a3e0fee4ee422fe5',
                '30452f604c90e6a0e020e1f9c3e53094', '40e52f94005008852f31853032800675',
                '310075324090e7407401f0e490e68af0', '90e68be532f0252ef52ee531352df52d',
                'c3e5309532f530e52f9531f52f80b0d3', '22c3', '22',
                'c0e0c083c082d2015391ef90e65d7401', 'f0d082d083d0e032',
                'c0e0c083c0825391ef90e65d7404f0d0', '82d083d0e032',
                'c0e0c083c0825391ef90e65d7402f0d0', '82d083d0e032',
                'c0e0c083c08290e680e030e70e850a0e', '850b0f851210851311800c85120e8513',
                '0f850a10850b115391ef90e65d7410f0', 'd082d083d0e032',
                'c0e0c083c082d2045391ef90e65d7408', 'f0d082d083d0e032',
                'c0e0c083c08290e680e030e70e850a0e', '850b0f851210851311800c85120e8513',
                '0f850a10850b115391ef90e65d7420f0', 'd082d083d0e032', '32', '32', '32',
                '32', '32', '32', '32', '32', '32', '32', '32', '32', '32', '32', '32',
                '32', '32', '32', '32', '32', '32', '32', '32', '32', '32', '32', '32',
                '32', '32', '32', '32', '32', '32', '32', '32', '32', 'ab07aa06ac05',
                'e4fde51c6010ea7e000dee2407f582e4', '34e1f583eaf0ebae050d74072ef582e4',
                '34e1f583ebf0af050d74072ff582e434', 'e1f583ecf07ae17b07af19120ddeaf19',
                '1210f7', '22', '8e368f378d388a398b3a', 'e4f53be53bc3953850200537e537ae36',
                '7002053614ffe53a253bf582e43539f5', '83e0fd120f73053b80d9', '22',
                '8e368f378d388a398b3a', 'e4fde51c6012e536ff7e000dee2407f5',
                '82e434e1f583eff0e537ae050d74072e', 'f582e434e1f583e537f07ae17b07af19',
                '120ddeab3aaa39ad38af19120bdd', '22', '6080e0000e0301110101300701000201',
                '00001100fffefffefffeffff00091212', '002d123f080301010101010701020401',
                '00000000fffcfffefffeffff09091212', '002d363f171801010101010700020100',
                '00001000fffbfffbfbfbfbfb00091212', '002d123f0803013f0101010701020001',
                '00000000fffdffffffffffff09091212', '002d363f6080e087010201013f010107',
                '00000200010000000702020707070707', '000000003f00003f03013f0101010107',
                '02020500000000000507070707070707', '00003f000000003f010180010101bf07',
                '0202030202021100ffffffffffffffff', '00091212002d123f0101010101010107',
                '00000000000000000707070707070707', '000000000000003f47e080c000000fca',
                '1e00', '90e60174caf090e6f574fff090e080e0', '90e6f3f090e081e090e6c3f090e082e0',
                '90e6c1f090e083e090e6c2f090e085e0', '90e6c0f090e086e090e6f4f075af0774',
                'e0f59a7400f59b759de4e4f59eff90e6', '7be090e67cf00fbf80f4', '22',
                '00010202030304040505', 'c204c200c203c201c202750808750907',
                '120cb8c2c975cdf875cc40d2cad2adc2', '87c2a0d2a17e0e7f008e0c8f0d75140e',
                '751512750a0e750b1c75120e75133c75', '160e75175c90e680e030e70e850a0e85',
                '0b0f851210851311800c85120e85130f', '850a10850b11ee54e070030208f77529',
                '00752a807e0e7f008e2b8f2cc374909f', 'ff740e9ecf2402cf3400fee48f288e27',
                'f526f525f524f523f522f521af28ae27', 'ad26ac25ab24aa23a922a821c3120ee1',
                '502ae52a2524f582e5293523f58374cd', 'f0e4faf9f8e5242401f524ea3523f523',
                'e93522f522e83521f52180c0e4f524f5', '23f522f521af28ae27ad26ac25ab24aa',
                '23a922a821c3120ee15037e52c2524f5', '82e52b3523f583e0ffe52a2524f582e5',
                '293523f583eff0e4faf9f8e5242401f5', '24ea3523f523e93522f522e83521f521',
                '80b385290c852a0d74002480ff740e34', 'fffec3e5159ff515e5149ef514c3e50f',
                '9ff50fe50e9ef50ec3e5119ff511e510', '9ef510c3e50b9ff50be50a9ef50ac3e5',
                '139ff513e5129ef512c3e5179ff517e5', '169ef516d2e843d82090e668e04409f0',
                '90e65ce0443df0d2af90e680e020e105', 'd2061211fa90e680e054f7f0538ef8c2',
                '043001051204d9c20130042912002850', '24c20412000320001690e682e030e704',
                'e020e1ef90e682e030e604e020e0e412', '1229120040120b7b80c7', '22',
                '90e6b9e070030205b514700302065e24', 'fe70030206f324fb70030205af147003',
                '0205a914700302059d1470030205a324', '05600302075f120046400302076b90e6',
                'bbe024fe602c14604724fd6016146031', '24067066e50c90e6b3f0e50d90e6b4f0',
                '02076be51490e6b3f0e51590e6b4f002', '076be50e90e6b3f0e50f90e6b4f00207',
                '6be51090e6b3f0e51190e6b4f002076b', '90e6bae0ff121255aa06a9077b01ea49',
                '4b600dee90e6b3f0ef90e6b4f002076b', '90e6a0e04401f002076b90e6a0e04401',
                'f002076b1212ef02076b12130102076b', '12104c02076b1212dd02076b12004840',
                '0302076b90e6b8e0247f602b14603c24', '026003020654a200e433ff25e0ffa203',
                'e4334f90e740f0e4a3f090e68af090e6', '8b7402f002076be490e740f0a3f090e6',
                '8af090e68b7402f002076b90e6bce054', '7eff7e00e0d3948040067c007d018004',
                '7c007d00ec4efeed4f2436f58274003e', 'f583e493ff3395e0feef24a1ffee34e6',
                '8f82f583e0540190e740f0e4a3f090e6', '8af090e68b7402f002076b90e6a0e044',
                '01f002076b12004e400302076b90e6b8', 'e024fe601d2402600302076b90e6bae0',
                'b40105c20002076b90e6a0e04401f002', '076b90e6bae0705990e6bce0547eff7e',
                '00e0d3948040067c007d0180047c007d', '00ec4efeed4f2436f58274003ef583e4',
                '93ff3395e0feef24a1ffee34e68f82f5', '83e054fef090e6bce05480ff13131354',
                '1fffe0540f2f90e683f0e04420f00207', '6b90e6a0e04401f08078120050507390',
                'e6b8e024fe60202402706790e6bae0b4', '0104d200805c90e6bae06402605490e6',
                'a0e04401f0804b90e6bce0547eff7e00', 'e0d3948040067c007d0180047c007d00',
                'ec4efeed4f2436f58274003ef583e493', 'ff3395e0feef24a1ffee34e68f82f583',
                'e04401f0800c120056500790e6a0e044', '01f090e6a0e04480f0', '22',
                '02002e', '53d8ef32', '021196', 'c0e0b287e509150970021508e5094508',
                '701575080475091f300206b2a1d2a080', '04b2a0d2a1c20275cdf875cc40c2cfd0',
                'e032', '1201000200000040b504226000000102', '00010a06000200000040010009022000',
                '01010080320904000002ff0000000705', '02020002000705860200020009022000',
                '01010080320904000004ff0000000705', '02024000000705860240000004030904',
                '0e034f0044004d002000200020002203', '480061006e00740065006b0044005300',
                '4f003600300032003200420045002000', '0000', '90e682e030e004e020e60b90e682e030',
                'e119e030e71590e680e04401f07f147e', '0012100690e680e054fef022',
                '90e682e044c0f090e681f04387010000', '00000022',
                '30060990e680e0440af0800790e680e0', '4408f07fdc7e0512100690e65d74fff0',
                '90e65ff05391ef90e680e054f7f022', 'e4f541d2e9d2af22',
                '90e678e020e6f9c2e990e678e04480f0', 'ef25e090e679f090e678e030e0f990e6',
                '78e04440f090e678e020e6f990e678e0', '30e1d6d2e922',
                'a90790e678e020e6f9e541702390e678', 'e04480f0e925e090e679f08d3caf03a9',
                '07753d018a3e893fe4f540754101d322', 'c322', 'a90790e678e020e6f9e541702590e678',
                'e04480f0e925e0440190e679f08d3caf', '03a907753d018a3e893fe4f540754103',
                'd322c322', '020a73', 'c0e0c083c082c085c084c086758600c0',
                'd075d000c000c001c002c003c006c007', '90e678e030e206754106020b5d90e678',
                'e020e10ce54164026006754107020b5d', 'e54124fe605f14603624fe7003020b4e',
                '24fc7003020b5a24086003020b5dab3d', 'aa3ea93faf4005408f82758300120e92',
                '90e679f0e540653c7070754105806b90', 'e679e0ab3daa3ea93fae408e82758300',
                '120ebf754102e53c6401704e90e678e0', '4420f08045e53c24feb5400790e678e0',
                '4420f0e53c14b5400a90e678e04440f0', '75410090e679e0ab3daa3ea93fae408e',
                '82758300120ebf0540800f90e678e044', '40f075410080037541005391dfd007d0',
                '06d003d002d001d000d0d0d086d084d0', '85d082d083d0e032', 'a907',
                'ae16af178f828e83a3e064037017ad01', '19ed7001228f828e83e07c002ffdec3e',
                'feaf0580df7e007f00', '22', '121162e54124fa600e146006240770f3',
                'd322e4f541d322e4f541d322', '1211c8e54124fa600e146006240770f3',
                'd322e4f541d322e4f541d322', '8e2d8f2e90e600e054187012e52e2401',
                'ffe4352dc313f52def13f52e801590e6', '00e05418ffbf100be52e25e0f52ee52d',
                '33f52de52e152eae2d7002152d4e6005', '12001780ee22',
                '7400f58690fda57c05a3e582458370f9', '22', '020c00', '020c00',
                '021281000212c7000212b10002129900', '021089000210c00002002a0002003200',
                '0200420002004a0002005200020bf900', '020bfa00020bfb00020bfc00020bfd00',
                '020bfe0002003200020bff00020dfa00', '020dfb00020dfc00020dfd00020dfe00',
                '020dff00020032000200320002003200', '02131100021312000213130002131400',
                '02131500021316000213170002131800', '0213190002131a0002131b0002131c00',
                '02131d0002131e0002131f0002132000', '0213210002132200', '020d52',
                '787fe4f6d8fd758141020d99', 'bb010ce58229f582e5833af583e02250',
                '06e92582f8e622bbfe06e92582f8e222', 'e58229f582e5833af583e49322',
                'f8bb010de58229f582e5833af583e8f0', '225006e92582c8f622bbfe05e92582c8',
                'f222', 'eb9ff5f0ea9e42f0e99d42f0e89c45f0', '22',
                'd083d082f8e4937012740193700da3a3', '93f8740193f5828883e4737402936860',
                'efa3a3a380df', '020773e493a3f8e493a34003f68001f2',
                '08dff48029e493a3f85407240cc8c333', 'c4540f4420c8834004f456800146f6df',
                'e4800b010204081020408090095ee47e', '019360bca3ff543f30e509541ffee493',
                'a360010ecf54c025e060a840b8e493a3', 'fae493a3f8e493a3c8c582c8cac583ca',
                'f0a3c8c582c8cac583cadfe9dee780be', '00', '01', '01', '00', '00']
        
        bmRequestType = 0x40
        
        bRequest = 160
        
        # wIndex = 0
        
        for i in range(len(wValue)):
            
            datai = bytes.fromhex(data[i])
            
            self.ctrl(bmRequestType, bRequest, datai, 0, wValue[i])
            
        return 0

    def close(self):
        
        try:

            self.dev.reset()

        except usb.core.USBError as e:
    
            print(e)
        
        usb.util.dispose_resources(self.dev)
        
        print("Connection is closed")

#%% Main

if __name__ == "__main__":

    pass

#%% End