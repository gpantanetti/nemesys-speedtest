#!/usr/bin/env python
# -*- coding: utf-8 -*-

# from sysMonitor import SysMonitor, RES_OS, RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_HSPA, RES_DEV, RES_MAC, RES_IP, RES_MASK, RES_HOSTS, RES_TRAFFIC
from sysMonitor import SysMonitor, RES_OS, RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_DEV, RES_MAC, RES_IP, RES_MASK, RES_HOSTS, RES_TRAFFIC
from collections import OrderedDict
import threading
from logger import logging
import gui_event

import time

logger = logging.getLogger()

ALL_RES = [RES_OS, RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_DEV, RES_MAC, RES_IP, RES_MASK, RES_HOSTS, RES_TRAFFIC]
MESSAGE = [RES_OS, RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_IP, RES_HOSTS, RES_TRAFFIC]

class sysProfiler(object):

    def __init__(self, event_dispatcher, mode = 'check', checkable_set = set(ALL_RES)):
#         Thread.__init__(self)
        
        self._event_dispatcher = event_dispatcher
        self._mode = mode
        self._stop = False
        if (self._mode == 'check'):
            self._message_flag = True
            self._post_end_event = True
            self._report_device = True 
        elif (self._mode == 'tester'):
            self._message_flag = False
            self._post_end_event = False
            self._report_device = False 
            
        
        self._checkable_set = checkable_set
        self._available_check = OrderedDict \
        ([ \
        (RES_DEV, None),\
        (RES_MAC, None),\
        (RES_IP, None),\
        (RES_MASK, None),\
        (RES_OS, None),\
        (RES_CPU, None),\
        (RES_RAM, None),\
        (RES_ETH, None),\
        (RES_WIFI, None),\
#         (RES_HSPA, None),\
        (RES_HOSTS, None),\
        (RES_TRAFFIC, None) \
        ])
        
        self._device = None
        
        self._sys_monitor = SysMonitor()
        self._lock = threading.Lock()
#         self._profiler_idle = Event()
#         self._profiler_idle.set()


    def profile_once_and_call_back(self, callback, resources = set(ALL_RES), report_progress = False):
        profiling_thread = threading.Thread(target = self._do_profile, args = (resources, callback, False, report_progress))
        profiling_thread.daemon = True
        profiling_thread.start()


    def profile_once(self, resources = set(ALL_RES)):
        return self._do_profile(resources = resources)


    def profile_in_background(self, resources = set(ALL_RES), callback = None):
        self._stop = False
        profiling_thread = threading.Thread(target = self._do_background_profile, args = (resources, callback))
        profiling_thread.daemon = True
        profiling_thread.start()


    def stop_background_profiling(self):
        self._stop = True
        

    def _do_background_profile(self, resources = set(ALL_RES), callback = None):
        while not self._stop:
            self._do_profile(resources, callback, is_background=True)
            time.sleep(1)
    
    def _do_profile(self, resources = set(ALL_RES), callback = None, is_background = False, report_progress = False):
#         self._profiler_idle.wait(10.0)
#         if not self._profiler_idle.is_set():
#             if is_background:
#                 return None
#             else:
#                 raise Exception("Time out nel profiler, impossibile completare la profilazione del sistema")
#              
        with self._lock:   
#             self._profiler_idle.clear()
            if report_progress:
                i = 0
                self._event_dispatcher.postEvent(gui_event.ProgressEvent(i))
            self._check_device()
            sysmon_results = OrderedDict([])
            for res in resources:
                if res in self._available_check:
                    result = self._sys_monitor.checkres(res)
                    sysmon_results[res] = result#self._sys_monitor.checkres(res).get('value', None)
                    if report_progress:
                        i += 1
                        self._event_dispatcher.postEvent(gui_event.ProgressEvent(float(i)/len(resources)))
                    if (res in MESSAGE):
                        "TODO: call back!"
                        self._event_dispatcher.postEvent(gui_event.ResourceEvent(res, sysmon_results[res], self._message_flag))
            
            results = {}
            for key in sysmon_results:
                results[key] = sysmon_results[key].get('value', None)
            if callback != None:
                callback(results)
            else:
                return results

    
    def _check_device(self):
        try:
            ip = self._sys_monitor.checkres(RES_IP)['value']
            dev = self._sys_monitor.checkres(RES_DEV, ip)['value']
        except Exception as e:
            info = {'status':False, 'value':-1, 'info':e}
            self._event_dispatcher.postEvent(gui_event.ResourceEvent(RES_ETH, info, False))
            self._event_dispatcher.postEvent(gui_event.ResourceEvent(RES_WIFI, info, False))
            self._event_dispatcher.postEvent(gui_event.ErrorEvent(e))
            return
            
        if (self._device == None):
            self._device = dev
            if self._report_device:
                self._event_dispatcher.postEvent(gui_event.UpdateEvent("Interfaccia di test: %s" % dev))
                self._event_dispatcher.postEvent(gui_event.UpdateEvent("Indirizzo IP di rete: %s" % ip))
                self._event_dispatcher.postEvent(gui_event.UpdateEvent("Interfaccia di rete in esame: %s" % dev))
                
        elif (dev != self._device):
            "TODO: handle at higher level"
            self._event_dispatcher.postEvent(gui_event.ErrorEvent("Test interrotto per variazione interfaccia di rete di riferimento."))         
            self._event_dispatcher.postEvent(gui_event.StopEvent()) 
    
    