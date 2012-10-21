#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sysmonitor import checkset, RES_OS, RES_IP, RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_HSPA, RES_TRAFFIC, RES_HOSTS

from client import Client
from deliverer import Deliverer
from datetime import datetime
from isp import Isp
from measure import Measure

from os import path, walk, listdir, remove
from profile import Profile
from server import Server
from sys import platform
from task import Task
from tester import Tester
from threading import Thread, Event, enumerate
from time import sleep
from timeNtp import timestampNtp
from urlparse import urlparse
from xmlutils import getvalues, getstarttime, getxml, xml2task
# from usbkey import check_usb, move_on_key
from logger import logging
from collections import deque

import sysmonitor
import httputils

import shutil
import paths
import ping
import time
import wx
import re

##NEW##
from checkSoftware import checkSoftware
from nemesysParser import parse

__version__ = '1.0.4'

TASK_FILE = '40000'

# Tempo di attesa tra una misura e la successiva in caso di misura fallita
TIME_LAG = 5
PING = 'ping'
DOWN = 'down'
UP = 'up'
# Soglia per il rapporto tra traffico 'spurio' e traffico totale
TH_TRAFFIC = 0.1
TH_TRAFFIC_INV = 0.9
# Soglia per numero di pacchetti persi
TH_PACKETDROP = 0.05
MAX_TEST_ERROR = 5

UPLOAD_RETRY = 3
TOTAL_STEPS = 15

logger = logging.getLogger()


class _Profiler(Thread):

  def __init__(self, gui, type = 'check', checkable_set = set([RES_OS, RES_IP, RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_HSPA, RES_HOSTS, RES_TRAFFIC])):
    Thread.__init__(self)

    self._gui = gui
    self._type = type
    self._checkable_set = checkable_set
    self._available_check = {RES_OS:1, RES_IP:2, RES_CPU:3, RES_RAM:4, RES_ETH:5, RES_WIFI:6, RES_HSPA:7, RES_HOSTS:8, RES_TRAFFIC:9}

    self._events = {}
    self._results = {}
    self._cycle = Event()
    self._results_flag = Event()
    self._checkset_flag = Event()
    self._usbkey_ok = False
    self._device = None

  def run(self):

    self._cycle.set()

    while (self._cycle.isSet()):
      self._results_flag.clear()
      self._checkset_flag.clear()

      if (self._type != 'tester'):
        self._usbkey_ok = self._check_usbkey()
      else:
        self._usbkey_ok = True

      if (self._usbkey_ok and self._type != 'usbkey'):
        result = checkset(set([RES_IP]))
        self._results.update(result)
        self._check_device()
        
      if (self._usbkey_ok or self._type == 'usbkey'):
        self._events.clear()
        self._results.clear()

        for res in sorted(self._available_check, key = lambda res: self._available_check[res]):
          if self._checkset_flag.isSet():
            self._events.clear()
            self._results.clear()
            break
          if res in self._checkable_set:
            res_flag = Event()
            self._events[res] = res_flag
            self._events[res].clear()
            self._check_resource(res)

            if self._events[res].isSet():
              del self._events[res]
              if (self._type == 'tester'):
                message_flag = False
              else:
                message_flag = True
              wx.CallAfter(self._gui.set_resource_info, res, self._results[res], message_flag)
        
        self._results_flag.set()

        if (self._type != 'tester'):
          self._cycle.clear()
        else:
          sleep(1)

    if (self._usbkey_ok and self._type == 'check'):
      self._tester = _Tester(self._gui)
      self._tester._uploadall()
      wx.CallAfter(self._gui._after_check)

  def stop(self):
    self._cycle.clear()

  def set_check(self, checkable_set = set([RES_OS, RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_HSPA, RES_HOSTS, RES_TRAFFIC])):
    self._checkable_set = checkable_set
    self._checkset_flag.set()

  def _check_resource(self, resource):
    result = checkset(set([resource]))
    self._results.update(result)
    self._events[resource].set()

  def get_results(self):
    self._results_flag.wait()
    self._results_flag.clear()
    if self._checkset_flag.isSet():
      self._results_flag.wait()
      self._results_flag.clear()
    if (self._type == 'usbkey'):
      results = self._usbkey_ok
    else:
      results = {}
      for key in self._results:
        results[key] = self._results[key]['value']
    return results

  def _check_device(self):
    try:
      ip = self._results[RES_IP]['value']
      id = sysmonitor.getDev(ip)
    except Exception as e:
      info = {'status':False, 'value':-1, 'info':''}
      wx.CallAfter(self._gui.set_resource_info, RES_ETH, info, False)
      wx.CallAfter(self._gui.set_resource_info, RES_WIFI, info, False)
      wx.CallAfter(self._gui.set_resource_info, RES_HSPA, info, False)
      wx.CallAfter(self._gui._update_messages, e, 'red')
      return
      
    if (self._device == None):
      self._device = id
      if (self._type != 'tester'):
        dev_info = sysmonitor.getDevInfo(id)
        dev_type = dev_info['type']
        if (dev_type == 14):
          dev_descr = "rete locale via cavo ethernet"
        elif (dev_type == 25):
          dev_descr = "rete locale wireless"
        elif (dev_type == 3 or dev_type == 17):
          dev_descr = "rete mobile su dispositivo hspa"
        else:
          dev_descr = dev_info['descr']
        wx.CallAfter(self._gui._update_interface, dev_descr, ip)
        
        if (dev_info['descr'] != 'none'):
          dev_descr = dev_info['descr'] 
        wx.CallAfter(self._gui._update_messages, "Interfaccia di rete in esame: %s" % dev_descr, 'green')
        wx.CallAfter(self._gui._update_messages, "Indirizzo IP dell'interfaccia di rete in esame: %s" % ip, 'green')
        
    elif (id != self._device):
      self._cycle.clear()
      self._usbkey_ok = False
      wx.CallAfter(self._gui._update_messages, "Test interrotto per variazione interfaccia di rete di riferimento.", 'red')
      wx.CallAfter(self._gui.stop)
      
         
  def _check_usbkey(self):
    check = True
    # if (not check_usb()):
      # self._cycle.clear()
      # logger.info('Verifica della presenza della chiave USB fallita')
      # wx.CallAfter(self._gui._update_messages, "Per l'utilizzo di questo software occorre disporre della opportuna chiave USB. Inserire la chiave nel computer e riavviare il programma.", 'red')
    return check


def getclient(options):

  profile = Profile(id = None, upload = options.bandwidthup,
                    download = options.bandwidthdown)
  isp = Isp('fub001')
  return Client(id = options.clientid, profile = profile, isp = isp,
                geocode = None, username = 'speedtest',
                password = options.password)


class _Tester(Thread):

  def __init__(self, gui):
    Thread.__init__(self)
    paths_check = paths.check_paths()
    for check in paths_check:
      logger.info(check)
      
    self._sent = paths.SENT_DAY_DIR
    self._outbox = paths.OUTBOX_DAY_DIR

    self._gui = gui
    self._profiler = _Profiler(self._gui, 'tester')

    (options, args, md5conf) = parse(__version__)

    self._client = getclient(options)
    self._scheduler = options.scheduler
    self._repository = options.repository
    self._tasktimeout = options.tasktimeout
    self._testtimeout = options.testtimeout
    self._httptimeout = options.httptimeout
    self._md5conf = md5conf
    
    self._deliverer = Deliverer(self._repository, self._client.isp.certificate, self._httptimeout)

    self._running = Event()

  def join(self, timeout = None):
    self._running.clear()
    logger.info("Chiusura del tester")
    #wx.CallAfter(self._gui._update_messages, "Attendere la chiusura del programma...")

  def _get_server(self, servers = set([Server('NAMEX', '193.104.137.133', 'NAP di Roma'), Server('MIX', '193.104.137.4', 'NAP di Milano')])):

    maxREP = 4
    best = {}
    best['start'] = None
    best['delay'] = 8000
    best['server'] = None
    RTT = {}

    wx.CallAfter(self._gui._update_messages, "Scelta del server di misura in corso")

    for server in servers:
      RTT[server.name] = best['delay']

    for repeat in range(maxREP):
      sleep(1)
      wx.CallAfter(self._gui._update_messages, "Test %d di %d di ping." % (repeat+1, maxREP), 'blue')
      wx.CallAfter(self._gui.update_gauge)
      for server in servers:
        try:
          start = None
          delay = 0
          start = datetime.fromtimestamp(timestampNtp())
          delay = ping.do_one("%s" % server.ip, 1) * 1000
          if (delay < RTT[server.name]):
            RTT[server.name] = delay
          if (delay < best['delay']):
            best['start'] = start
            best['delay'] = delay
            best['server'] = server
        except Exception as e:
          logger.info('Errore durante il ping dell\'host %s: %s' % (server.ip, e))
          pass

    if best['server'] != None:
      for server in servers:
        if (RTT[server.name] != 8000):
          wx.CallAfter(self._gui._update_messages, "Distanza dal %s: %.1f ms" % (server.name, RTT[server.name]), 'blue')
        else:
          wx.CallAfter(self._gui._update_messages, "Distanza dal %s: TimeOut" % (server.name), 'blue')
      wx.CallAfter(self._gui._update_messages, "Scelto il server di misura %s" % best['server'].name)
    else:
      wx.CallAfter(self._gui._update_messages, "Impossibile eseguire i test poiche' i server risultano irragiungibili da questa linea. Contattare l'helpdesk del progetto Misurainternet per avere informazioni sulla risoluzione del problema.", 'red')

    return best
  
  def _download_task(self):
    # Scarica il prossimo task dallo scheduler #
    #logger.info('Reading resource %s for client %s' % (self._scheduler, self._client))

    url = urlparse(self._scheduler)
    certificate = self._client.isp.certificate
    connection = httputils.getverifiedconnection(url = url, certificate = certificate, timeout = self._httptimeout)

    try:
      connection.request('GET', '%s?clientid=%s&version=%s&confid=%s' % (url.path, self._client.id, __version__, self._md5conf))
      data = connection.getresponse().read()
    except Exception as e:
      logger.error('Impossibile scaricare lo scheduling. Errore: %s.' % e)
      # [TODO] ##
      # dialogo con utente in caso di errore ##
      return None
    
    task = xml2task(data)
    task.ftpdownpath = '/download/'+TASK_FILE+'.rnd'
    self._client.profile.upload = int(TASK_FILE)
    logger.info("TASK: [%s]" % task)
    
    #task = Task(0, '2010-01-01 10:01:00', Server('NAMEX', '193.104.137.133', 'NAP di Roma'), '/download/%s' % TASK_FILE, 'upload/%s' % TASK_FILE, 4, 4, 10, 4, 4, 0, True)
    return task

  def _test_gating(self, test, testtype):
    '''
    Funzione per l'analisi del contabit ed eventuale gating dei risultati del test
    '''
    stats = test.counter_stats
    logger.info('Sniffer Statistics: %s' % stats)
    continue_testing = False

    logger.info('Analisi della percentuale dei pacchetti persi')
    packet_drop = stats.packet_drop
    packet_tot = stats.packet_tot_all
    if (packet_tot > 0):
      logger.info('Persi %s pacchetti di %s' % (packet_drop, packet_tot))
      packet_ratio = float(packet_drop) / float(packet_tot)
      logger.info('Percentuale di pacchetti persi: %.2f%%' % (packet_ratio * 100))
      if (packet_tot > 0 and packet_ratio > TH_PACKETDROP):
        info = 'Eccessiva presenza di traffico di rete, impossibile analizzare i dati di test'
        wx.CallAfter(self._gui.set_resource_info, RES_TRAFFIC, {'status': False, 'info': info, 'value': None})
        return continue_testing

    else:
      info = 'Errore durante la misura, impossibile analizzare i dati di test'
      wx.CallAfter(self._gui.set_resource_info, RES_TRAFFIC, {'status': False, 'info': info, 'value': None})
      return continue_testing

    if (testtype == DOWN):
      byte_nem = stats.payload_down_nem_net
      byte_all = byte_nem + stats.byte_down_oth_net
      packet_nem = stats.packet_up_nem_net
      packet_all = packet_nem + stats.packet_up_oth_net
    else:
      byte_nem = stats.payload_up_nem_net
      byte_all = byte_nem + stats.byte_up_oth_net
      packet_nem = stats.packet_down_nem_net
      packet_all = packet_nem + stats.packet_down_oth_net

    logger.info('Analisi dei rapporti di traffico')
    if byte_all > 0 and packet_all > 0:
      traffic_ratio = float(byte_all - byte_nem) / float(byte_all)
      packet_ratio_inv = float(packet_all - packet_nem) / float(packet_all)
      value1 = "%.2f%%" % (traffic_ratio * 100)
      value2 = "%.2f%%" % (packet_ratio_inv * 100)
      logger.info('Traffico NeMeSys: [ %d pacchetti di %d totali e %.1f Kbyte di %.1f totali ]' % (packet_nem,  packet_all, byte_nem / 1024.0, byte_all / 1024.0))
      logger.info('Percentuale di traffico spurio: %.2f%% traffico e %.2f%% pacchetti' % (traffic_ratio * 100, packet_ratio_inv * 100))
      if traffic_ratio < 0:
        wx.CallAfter(self._gui._update_messages, 'Errore durante la verifica del traffico di misura: impossibile salvare i dati.', 'red')
        return continue_testing
      elif traffic_ratio < TH_TRAFFIC and packet_ratio_inv < TH_TRAFFIC_INV:
        # Dato da salvare sulla misura
        # test.bytes = byte_all
        info = 'Traffico internet non legato alla misura: percentuali %s/%s' % (value1, value2)
        wx.CallAfter(self._gui.set_resource_info, RES_TRAFFIC, {'status': True, 'info': info, 'value': value1}, False)
        return True
      else:
        info = 'Eccessiva presenza di traffico internet non legato alla misura: percentuali %s/%s' % (value1, value2)
        wx.CallAfter(self._gui.set_resource_info, RES_TRAFFIC, {'status': False, 'info': info, 'value': value1})
        return continue_testing
    else:
      info = 'Errore durante la misura, impossibile analizzare i dati di test'
      wx.CallAfter(self._gui.set_resource_info, RES_TRAFFIC, {'status': False, 'info': info, 'value': 'error'})
      return continue_testing

    return True

  def _get_bandwith(self, test):

    if test.time > 0:
      return int(round(test.bytes * 8 / test.time))
    else:
      raise Exception("Errore durante la valutazione del test")

  def _do_test(self, tester, type, task):
    test_done = 0
    test_good = 0
    test_todo = 0

    best_value = 0
    best_test = None
    
    if type == PING:
      stringtype = "ping"
      test_todo = task.ping
    elif type == DOWN:
      stringtype = "ftp download"
      test_todo = task.download
    elif type == UP:
      stringtype = "ftp upload"
      test_todo = task.upload

    self._profiler.set_check(set([RES_HOSTS, RES_TRAFFIC]))
    pre_profiler = self._profiler.get_results()

    while (test_good < test_todo and self._running.isSet()):

      # Esecuzione del test
      test = None
      error = 0
      while (error < MAX_TEST_ERROR and test == None):
        self._profiler.set_check(set([RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_HSPA]))
        profiler = self._profiler.get_results()
        sleep(1)
        
        wx.CallAfter(self._gui._update_messages, "Test %d di %d di %s" % (test_good+1, test_todo, stringtype.upper()), 'blue')
        
        try:
          test_done += 1
          message =  "Tentativo numero %s con %s riusciti su %s da collezionare" % (test_done,test_good,test_todo)
          if type == PING:
            logger.info("[PING] "+message+" [PING]")
            test = tester.testping()
          elif type == DOWN:
            logger.info("[DOWNLOAD] "+message+" [DOWNLOAD]")
            test = tester.testftpdown(self._client.profile.download * task.multiplier * 1000 / 8, task.ftpdownpath)
          elif type == UP:
            logger.info("[UPLOAD] "+message+" [UPLOAD]")
            test = tester.testftpup(self._client.profile.upload * task.multiplier * 1000 / 8, task.ftpuppath)
          else:
            logger.warn("Tipo di test da effettuare non definito!")
        except Exception as e:
          if (self._running.isSet()):
            error += 1
          else:
            error = MAX_TEST_ERROR
          test = None
          wx.CallAfter(self._gui._update_messages, "Errore durante l'esecuzione di un test: %s" % e, 'red')
          wx.CallAfter(self._gui._update_messages, "Ripresa del test tra %d secondi" % TIME_LAG)
          sleep(TIME_LAG)

      if test != None:      
        test.update(pre_profiler)
        test.update(profiler)
        
        if type == PING:
          test_good += 1
          logger.info("[ Ping: %s ] [ Actual Best: %s ]" % (test.time, best_value))
          if best_value == 0:
            best_value = 4444
          if test.time < best_value:
            best_value = test.time
            best_test = test
          wx.CallAfter(self._gui.update_gauge)
        else:
          bandwidth = self._get_bandwith(test)
          
          if type == DOWN:
            self._client.profile.download = min(bandwidth, 40000)
            task.update_ftpdownpath(bandwidth)
          elif type == UP:
            self._client.profile.upload = min(bandwidth, 40000)
          else:
            logger.warn("Tipo di test effettuato non definito!")
            
          if test_good > 0:
            # Analisi da contabit
            if (self._test_gating(test, type)):
              logger.info("[ Bandwidth in %s : %s ] [ Actual Best: %s ]" % (type, bandwidth, best_value))
              if bandwidth > best_value:
                best_value = bandwidth
                best_test = test
              wx.CallAfter(self._gui.update_gauge)
              test_good += 1
          else:
            wx.CallAfter(self._gui.update_gauge)
            test_good += 1
      
      else:
        raise Exception("Errore: [Test = None] La misurazione non puo' essere completata")

    best_test.done = test_done
    return best_test

  def run(self):

    self._running.set()
    
    wx.CallAfter(self._gui._update_messages, "Inizio dei test di misura.")
    wx.CallAfter(self._gui.update_gauge)

    # Profilazione
    self._profiler.set_check(set([RES_OS, RES_IP]))
    self._profiler.start()
    profiler = self._profiler.get_results()
    sleep(1)
    
    #ping_test = self._get_server()
    #server = ping_test['server']
    
    # TODO task tra Try Except per gestire il fatto che potrebbe non esserci banda.... vedi executer 
    task = self._download_task()
    if task != None:
      try:
        wx.CallAfter(self._gui._update_messages, "Server di misura %s" % task.server.name)
        wx.CallAfter(self._gui.update_gauge)
        
        start_time = datetime.fromtimestamp(timestampNtp())

        (ip, os) = (profiler[RES_IP], profiler[RES_OS])
        tester = Tester(if_ip = ip, host = task.server, timeout = self._testtimeout,
                   username = self._client.username, password = self._client.password)

        measure = Measure(self._client, start_time, task.server, ip, os, __version__)
        #logger.debug("\n\n%s\n\n",str(measure))
        
        test_types = [PING,DOWN,UP]
        
        # Testa i ping
        for type in test_types:
          test = self._do_test(tester, type, task)
          measure.savetest(test)
          wx.CallAfter(self._gui._update_messages, "Elaborazione dei dati")
          # if (move_on_key()):
          if (type == PING):
            wx.CallAfter(self._gui._update_messages, "Tempo di risposta del server: %.1f ms" % test.time, 'green')
            wx.CallAfter(self._gui._update_ping, test.time)
          elif (type == DOWN):
            wx.CallAfter(self._gui._update_messages, "Download bandwith %s kbps" % self._get_bandwith(test), 'green')
            wx.CallAfter(self._gui._update_down, self._get_bandwith(test))
          elif (type == UP):
            wx.CallAfter(self._gui._update_messages, "Upload bandwith %s kbps" % self._get_bandwith(test), 'green')
            wx.CallAfter(self._gui._update_up, self._get_bandwith(test))
          # else:
            # raise Exception("chiave USB mancante")
          #logger.debug("\n\n%s\n\n",str(measure))
        
        stop_time = datetime.fromtimestamp(timestampNtp())
        measure.savetime(start_time,stop_time)
        
        ## Salvataggio della misura ##
        measure_file = self._save_measure(measure)
        #report = self._upload(measure_file)
        self._uploadall()
        ## Fine Salvataggio ##
        
        
      except Exception as e:
        logger.warning('Misura sospesa per eccezione: %s.' % e)
        wx.CallAfter(self._gui._update_messages, 'Misura sospesa per errore: %s.' % e, 'red')
    else:
      wx.CallAfter(self._gui._update_messages, "Impossibile eseguire ora i test di misura. Riprovare tra qualche minuto.", 'red')
        
    self._profiler.stop()
    wx.CallAfter(self._gui.stop)
    
    
  def _save_measure(self, measure):
    # Salva il file con le misure
    f = open('%s/measure_%s.xml' % (self._outbox, measure.id), 'w')
    f.write(str(measure))
    # Aggiungi la data di fine in fondo al file
    f.write('\n<!-- [finished] %s -->' % datetime.fromtimestamp(timestampNtp()).isoformat())
    f.close()
    return f.name
    
    
  def _uploadall(self):
    '''
    Cerca di spedire tutti i file di misura che trova nella cartella d'uscita
    '''
    
    for retry in range(UPLOAD_RETRY):
      allOK = True
      
      filenames = []
      for root, dirs, files in walk(paths.OUTBOX_DIR):
        for file in files:
          if (re.search('measure_[0-9]{14}.xml',file) != None):
            filenames.append(path.join(root, file))
      
      len_filenames = len(filenames)
      
      if (len_filenames > 0):
        logger.info('Trovati %s file di misura ancora da spedire.' % len_filenames)
        if retry == 0:
          wx.CallAfter(self._gui._update_messages, "Salvataggio delle misure in corso....")
        
        for filename in filenames:
          uploadOK = self._upload(filename)
          if uploadOK:
            logger.info('File %s spedito con successo.' % filename)
          else:
            logger.info('Errore nella spedizione del file %s.' % filename)
            sleep_time = 5*(retry+1)
            allOK = False
            
        if allOK:
          wx.CallAfter(self._gui._update_messages, "Salvataggio completato con successo.",'green')
          break
        else:
          wx.CallAfter(self._gui._update_messages, "Tentativo di salvataggio numero %s di %s fallito." % (retry+1, UPLOAD_RETRY),'red')
          if (retry+1)<UPLOAD_RETRY:
            wx.CallAfter(self._gui._update_messages, "Nuovo tentativo fra %s secondi." % sleep_time,'red')
            sleep(sleep_time)
          else:
            wx.CallAfter(self._gui._update_messages, "Impossibile salvare le misure.",'red')
            title = "Salvataggio Misure"
            message = \
            '''
            Non � stato possibile salvare le misure per %s volte.
            
            Un nuovo tentativo verr� effettuato:
            1) a seguito della prossima profilazione
            2) a seguito della prossima misura
            3) al prossimo riavvio di NeMeSys Speedtest
            ''' % UPLOAD_RETRY
            msgBox = wx.MessageDialog(None, message, title, wx.OK|wx.ICON_INFORMATION)
            msgBox.ShowModal()
            msgBox.Destroy()

          
      else:
        logger.info('Nessun file di misura ancora da spedire.') 
        break
      
      
  def _upload(self, filename):
    '''
    Spedisce il filename di misura al repository entro il tempo messo a
    disposizione secondo il parametro httptimeout
    '''
    
    #return False
    result = False

    try:
      # Crea il Deliverer che si occuper� della spedizione
      zipname = self._deliverer.pack(filename)
      response = self._deliverer.upload(zipname)

      if (response != None):
        (code, message) = self._parserepositorydata(response)
        code = int(code)
        logger.info('Risposta dal server di upload: [%d] %s' % (code, message))

        # Se tutto � andato bene sposto il file zip nella cartella "sent" e rimuovo l'xml
        if (code == 0):
          time = getstarttime(filename)
          remove(filename)
          self._movefiles(zipname)

          result = True

    except Exception as e:
      logger.error('Errore durante la spedizione del file delle misure %s: %s' % (filename, e))

    finally:
      # Elimino lo zip del file di misura temporaneo
      if path.exists(zipname):
        remove(zipname)
      # Elimino il file di misura 
      if result and path.exists(filename):
        remove(filename)

      return result
      
      
  def _parserepositorydata(self, data):
    '''
    Valuta l'XML ricevuto dal repository, restituisce il codice e il messaggio ricevuto
    '''

    xml = getxml(data)
    if (xml == None):
      logger.error('Nessuna risposta ricevuta')
      return None

    nodes = xml.getElementsByTagName('response')
    if (len(nodes) < 1):
      logger.error('Nessuna risposta ricevuta nell\'XML:\n%s' % xml.toxml())
      return None

    node = nodes[0]

    code = getvalues(node, 'code')
    message = getvalues(node, 'message')
    return (code, message)
    
    
  def _movefiles(self, filename):
    
    dir = path.dirname(filename)
    #pattern = path.basename(filename)[0:-4]
    pattern = path.basename(filename)

    try:
      for file in listdir(dir):
        # Cercare tutti i file che iniziano per pattern
        if (re.search(pattern, file) != None):
          # Spostarli tutti in self._sent
          old = path.join(dir, file)
          new = path.join(self._sent,file)
          shutil.move(old, new)

    except Exception as e:
      logger.error('Errore durante lo spostamento dei file di misura %s' % e)
    
    
    
    
class NemesysSpeedtestGUI(wx.Frame):
    def __init__(self, *args, **kwds):
        self._stream = deque([], maxlen = 800)
        self._stream_flag = Event()

        self._tester = None
        self._profiler = None
        self._button_play = False
        self._button_check = False

        # begin wxGlade: Frame.__init__
        wx.Frame.__init__(self, *args, **kwds)

        self.sizer_1_staticbox = wx.StaticBox(self, -1, "Risultati")
        self.sizer_2_staticbox = wx.StaticBox(self, -1, "Indicatori di stato del sistema")
        self.sizer_3_staticbox = wx.StaticBox(self, -1, "Messaggi")
        self.bitmap_button_play = wx.BitmapButton(self, -1, wx.Bitmap(path.join(paths.ICONS, u"play.png"), wx.BITMAP_TYPE_ANY))
        self.bitmap_button_check = wx.BitmapButton(self, -1, wx.Bitmap(path.join(paths.ICONS, u"check.png"), wx.BITMAP_TYPE_ANY))
        self.bitmap_5 = wx.StaticBitmap(self, -1, wx.Bitmap(path.join(paths.ICONS, u"logo_nemesys.png"), wx.BITMAP_TYPE_ANY))
        self.label_5 = wx.StaticText(self, -1, "Versione %s" % __version__, style = wx.ALIGN_CENTRE)
        self.label_6 = wx.StaticText(self, -1, "Ne.Me.Sys.", style = wx.ALIGN_CENTRE)
        self.bitmap_cpu = wx.StaticBitmap(self, -1, wx.Bitmap(path.join(paths.ICONS, u"%s_gray.png" % RES_CPU.lower()), wx.BITMAP_TYPE_ANY))
        self.bitmap_ram = wx.StaticBitmap(self, -1, wx.Bitmap(path.join(paths.ICONS, u"%s_gray.png" % RES_RAM.lower()), wx.BITMAP_TYPE_ANY))
        self.bitmap_eth = wx.StaticBitmap(self, -1, wx.Bitmap(path.join(paths.ICONS, u"%s_gray.png" % RES_ETH.lower()), wx.BITMAP_TYPE_ANY))
        self.bitmap_wifi = wx.StaticBitmap(self, -1, wx.Bitmap(path.join(paths.ICONS, u"%s_gray.png" % RES_WIFI.lower()), wx.BITMAP_TYPE_ANY))
        self.bitmap_hspa = wx.StaticBitmap(self, -1, wx.Bitmap(path.join(paths.ICONS, u"%s_gray.png" % RES_HSPA.lower()), wx.BITMAP_TYPE_ANY))
        self.bitmap_hosts = wx.StaticBitmap(self, -1, wx.Bitmap(path.join(paths.ICONS, u"%s_gray.png" % RES_HOSTS.lower()), wx.BITMAP_TYPE_ANY))
        self.bitmap_traffic = wx.StaticBitmap(self, -1, wx.Bitmap(path.join(paths.ICONS, u"%s_gray.png" % RES_TRAFFIC.lower()), wx.BITMAP_TYPE_ANY))
        self.label_cpu = wx.StaticText(self, -1, "%s\n- - - -" % RES_CPU, style = wx.ALIGN_CENTRE)
        self.label_ram = wx.StaticText(self, -1, "%s\n- - - -" % RES_RAM, style = wx.ALIGN_CENTRE)
        self.label_eth = wx.StaticText(self, -1, "%s\n- - - -" % RES_ETH, style = wx.ALIGN_CENTRE)
        self.label_wifi = wx.StaticText(self, -1, "%s\n- - - -" % RES_WIFI, style = wx.ALIGN_CENTRE)
        self.label_hspa = wx.StaticText(self, -1, "%s\n- - - -" % RES_HSPA, style = wx.ALIGN_CENTRE)
        self.label_hosts = wx.StaticText(self, -1, "%s\n- - - -" % RES_HOSTS, style = wx.ALIGN_CENTRE)
        self.label_traffic = wx.StaticText(self, -1, "%s\n- - - -" % RES_TRAFFIC, style = wx.ALIGN_CENTRE)
        self.gauge_1 = wx.Gauge(self, -1, TOTAL_STEPS, style = wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.label_r_1 = wx.StaticText(self, -1, "Ping", style = wx.ALIGN_CENTRE)
        self.label_r_2 = wx.StaticText(self, -1, "Download", style = wx.ALIGN_CENTRE)
        self.label_r_3 = wx.StaticText(self, -1, "Upload", style = wx.ALIGN_CENTRE)
        self.label_rr_ping = wx.StaticText(self, -1, "- - - -", style = wx.ALIGN_CENTRE)
        self.label_rr_down = wx.StaticText(self, -1, "- - - -", style = wx.ALIGN_CENTRE)
        self.label_rr_up = wx.StaticText(self, -1, "- - - -", style = wx.ALIGN_CENTRE)
        self.messages_area = wx.TextCtrl(self, -1, "Ne.Me.Sys. Speedtest v.%s" % __version__, style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_WORDWRAP)
        self.label_interface = wx.StaticText(self, -1, "", style = wx.ALIGN_CENTRE)
        self.grid_sizer_1 = wx.FlexGridSizer(2, 7, 0, 0)
        self.grid_sizer_2 = wx.FlexGridSizer(2, 3, 0, 0)

        self.sizer_1 = wx.BoxSizer(wx.VERTICAL)
        self.sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_3 = wx.BoxSizer(wx.VERTICAL)
        self.sizer_4 = wx.BoxSizer(wx.VERTICAL)
        self.sizer_5 = wx.StaticBoxSizer(self.sizer_1_staticbox, wx.VERTICAL)
        self.sizer_6 = wx.StaticBoxSizer(self.sizer_3_staticbox, wx.VERTICAL)
        self.sizer_7 = wx.StaticBoxSizer(self.sizer_2_staticbox, wx.VERTICAL)
        
        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_BUTTON, self._play, self.bitmap_button_play)
        self.Bind(wx.EVT_BUTTON, self._check, self.bitmap_button_check)
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: Frame.__set_properties
        self.SetTitle("Ne.Me.Sys Speedtest")
        self.SetSize((750, 500))
        self.bitmap_button_play.SetMinSize((120, 120))
        self.bitmap_button_check.SetMinSize((40, 120))
        self.bitmap_5.SetMinSize((95, 70))
        self.label_5.SetFont(wx.Font(10, wx.ROMAN, wx.ITALIC, wx.NORMAL, 0, ""))
        self.label_6.SetFont(wx.Font(14, wx.ROMAN, wx.ITALIC, wx.NORMAL, 0, ""))
        self.bitmap_cpu.SetMinSize((60, 60))
        self.bitmap_ram.SetMinSize((60, 60))
        self.bitmap_wifi.SetMinSize((60, 60))
        self.bitmap_hosts.SetMinSize((60, 60))
        self.bitmap_traffic.SetMinSize((60, 60))
        self.gauge_1.SetMinSize((730, 22))
        self.label_r_1.SetFont(wx.Font(12, wx.ROMAN, wx.ITALIC, wx.BOLD, 0, ""))
        self.label_r_2.SetFont(wx.Font(12, wx.ROMAN, wx.ITALIC, wx.BOLD, 0, ""))
        self.label_r_3.SetFont(wx.Font(12, wx.ROMAN, wx.ITALIC, wx.BOLD, 0, ""))
        self.label_rr_ping.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD, 0, ""))
        self.label_rr_down.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD, 0, ""))
        self.label_rr_up.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD, 0, ""))
        self.label_interface.SetFont(wx.Font(12, wx.ROMAN, wx.ITALIC, wx.NORMAL, 0, ""))
        
        self.messages_area.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL, 0, ""))
        self.messages_area.SetMinSize((710, 150))
        self.sizer_5.SetMinSize((450, 120))
        self.sizer_6.SetMinSize((730, 100))
        self.sizer_7.SetMinSize((730, 100))

        #self.SetBackgroundColour(wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
        self.SetBackgroundColour(wx.Colour(242, 242, 242))

        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: Frame.__do_layout   
        self.grid_sizer_1.Add(self.bitmap_cpu, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 20)
        self.grid_sizer_1.Add(self.bitmap_ram, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 20)
        self.grid_sizer_1.Add(self.bitmap_eth, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 20)
        self.grid_sizer_1.Add(self.bitmap_wifi, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 20)
        self.grid_sizer_1.Add(self.bitmap_hspa, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 20)
        self.grid_sizer_1.Add(self.bitmap_hosts, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 20)
        self.grid_sizer_1.Add(self.bitmap_traffic, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 20)
        
        self.grid_sizer_1.Add(self.label_cpu, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.grid_sizer_1.Add(self.label_ram, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.grid_sizer_1.Add(self.label_eth, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.grid_sizer_1.Add(self.label_wifi, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.grid_sizer_1.Add(self.label_hspa, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.grid_sizer_1.Add(self.label_hosts, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.grid_sizer_1.Add(self.label_traffic, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        
        self.grid_sizer_2.Add(self.label_r_1, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 40)
        self.grid_sizer_2.Add(self.label_r_2, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 40)
        self.grid_sizer_2.Add(self.label_r_3, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 40)
        
        self.grid_sizer_2.Add(self.label_rr_ping, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.grid_sizer_2.Add(self.label_rr_down, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        self.grid_sizer_2.Add(self.label_rr_up, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 2)
        
        self.sizer_3.Add(self.grid_sizer_2, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_3.Add(self.label_interface, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 4)
        #self.sizer_3.Add(self.label_alert_area, 0, wx.TOP | wx.DOWN | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 4)
        #self.sizer_3.Add(self.grid_sizer_1, 0, wx.DOWN | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 8)
        #self.sizer_3.Add(wx.StaticLine(self, -1), 0, wx.ALL | wx.EXPAND, 0)
        #self.sizer_5.Add(wx.StaticLine(self, -1, style = wx.LI_VERTICAL), 0, wx.RIGHT | wx.EXPAND, 4)
        
        self.sizer_5.Add(self.sizer_3, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 4)
        
        self.sizer_4.Add(self.bitmap_5, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 4)
        self.sizer_4.Add(self.label_6, 0, wx.TOP | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 4)
        self.sizer_4.Add(self.label_5, 0, wx.LEFT | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, 8)
        
        self.sizer_2.Add(self.bitmap_button_play, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 4)
        self.sizer_2.Add(self.bitmap_button_check, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_2.Add(self.sizer_5, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 4)
        self.sizer_2.Add(self.sizer_4, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 4)
        
        self.sizer_6.Add(self.messages_area, 0, wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
        
        self.sizer_7.Add(self.grid_sizer_1, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 8)

        self.sizer_1.Add(self.sizer_2, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 4)
        self.sizer_1.Add(self.gauge_1, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 0)
        self.sizer_1.Add(self.sizer_6, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 4)
        self.sizer_1.Add(self.sizer_7, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 4)

        self.SetSizer(self.sizer_1)
        self.Layout()
        # end wxGlade

        self._check(None)

    def _on_close(self, event):
      logger.info("Richiesta di close")
      dlg = wx.MessageDialog(self,"\nVuoi davvero chiudere Ne.Me.Sys. Speedtest?","Ne.Me.Sys. Speedtest", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
      res = dlg.ShowModal()
      dlg.Destroy()
      if res == wx.ID_OK:
        self._killTester()    
        self.Destroy()
        
    def _play(self, event):
      self._button_play = True
      self._check(None)
      #self.bitmap_button_play.SetBitmapLabel(wx.Bitmap(path.join(paths.ICONS, u"stop.png")))

    def stop(self):
      #self.bitmap_button_play.SetBitmapLabel(wx.Bitmap(path.join(paths.ICONS, u"play.png")))

      self._killTester()
      self._profiler = _Profiler(self, 'usbkey', set())
      self._profiler.start()
      self._check_usbkey = self._profiler.get_results()
      if (self._check_usbkey):
        self._enable_button()
        self._update_messages("Sistema pronto per una nuova misura")
      self.update_gauge(TOTAL_STEPS)

    def _killTester(self):
      if (self._tester and self._tester != None):
        self._tester.join()
        for thread in enumerate():
          if thread.isAlive():
            try:
              thread._Thread__stop()
            except:
              logger.error("%s could not be terminated" % str(thread.getName()))
      
    def _check(self, event):
      self._button_check = True
      self.bitmap_button_play.Disable()
      self.bitmap_button_check.Disable()
      self._reset_info()
      self._update_messages("Profilazione dello stato del sistema di misura.")
      self._profiler = _Profiler(self)
      self._profiler.start()

    def _after_check(self):
      if (self._button_play):
        self._button_play = False
        self._button_check = False
        self._tester = _Tester(self)
        self._tester.start()
      else:
        # move_on_key()
        self._button_check = False
        self._update_messages("Profilazione terminata")
        self._enable_button()

    def _enable_button(self):
      self.bitmap_button_play.Enable()
      self.bitmap_button_check.Enable()

    def _update_down(self, downwidth):
      self.label_rr_down.SetLabel("%d kbps" % downwidth)
      self.Layout()

    def _update_up(self, upwidth):
      self.label_rr_up.SetLabel("%d kbps" % upwidth)
      self.Layout()

    def _update_ping(self, rtt):
      self.label_rr_ping.SetLabel("%.1f ms" % rtt)
      self.Layout()

    def _update_interface(self, interface, ip):
      self.label_interface.SetLabel("Interfaccia di test: %s\nIndirizzo IP di rete: %s" % (interface,ip))
      self.Layout()
    
    def _reset_info(self):
      checkable_set = set([RES_CPU, RES_RAM, RES_ETH, RES_WIFI, RES_HSPA, RES_HOSTS, RES_TRAFFIC])

      for resource in checkable_set:
        self.set_resource_info(resource, {'status': None, 'info': None, 'value': None})

      self.label_rr_down.SetLabel("- - - -")
      self.label_rr_up.SetLabel("- - - -")
      self.label_rr_ping.SetLabel("- - - -")
      self.label_interface.SetLabel("")

      self.messages_area.Clear()
      self.update_gauge(0)
      self.Layout()

    def update_gauge(self, value=None):
      if (value == None):
        value=self.gauge_1.GetValue()+1
      self.gauge_1.SetValue(value)

    def set_resource_info(self, resource, info, message_flag = True):
      res_bitmap = None
      res_label = None

      if info['status'] == None:
        color = 'gray'
      elif info['status'] == True:
        color = 'green'
      else:
        color = 'red'

      if resource == RES_CPU:
        res_bitmap = self.bitmap_cpu
        res_label = self.label_cpu
      elif resource == RES_RAM:
        res_bitmap = self.bitmap_ram
        res_label = self.label_ram
      elif resource == RES_ETH:
        res_bitmap = self.bitmap_eth
        res_label = self.label_eth
      elif resource == RES_WIFI:
        res_bitmap = self.bitmap_wifi
        res_label = self.label_wifi
      elif resource == RES_HSPA:
        res_bitmap = self.bitmap_hspa
        res_label = self.label_hspa
      elif resource == RES_HOSTS:
        res_bitmap = self.bitmap_hosts
        res_label = self.label_hosts
      elif resource == RES_TRAFFIC:
        res_bitmap = self.bitmap_traffic
        res_label = self.label_traffic

      if (res_bitmap != None):
        res_bitmap.SetBitmap(wx.Bitmap(path.join(paths.ICONS, u"%s_%s.png" % (resource.lower(), color))))

      if (res_label != None):
        if (info['value'] != None):
          if resource == RES_ETH or resource == RES_WIFI or resource == RES_HSPA:
            status = {-1:"Not Present", 0:"Off Line", 1:"On Line"}
            res_label.SetLabel("%s\n%s" % (resource, status[info['value']]))
          elif resource == RES_CPU or resource == RES_RAM:
            res_label.SetLabel("%s\n%.1f%%" % (resource, float(info['value'])))
          else:
            res_label.SetLabel("%s\n%s" % (resource, info['value']))
        else:
          res_label.SetLabel("%s\n- - - -" % resource)

      if (message_flag) and (info['info'] != None):
        self._update_messages("%s: %s" % (resource, info['info']), color)

      self.Layout()

    def _update_messages(self, message, color = 'black'):
      logger.info('Messagio all\'utente: "%s"' % message)
      self._stream.append((message, color))
      if (not self._stream_flag.isSet()):
        if (platform.startswith('win')):
          writer = Thread(target = self._writer)
          writer.start()
        else:
          self._writer()

    def _writer(self):
      self._stream_flag.set()
      while (len(self._stream) > 0):
        (message, color) = self._stream.popleft()
        date = datetime.fromtimestamp(time.time()).strftime('%c')
        start = self.messages_area.GetLastPosition()
        end = start + len(date) + 1
        if (start != 0):
          txt = ("\n%s %s" % (date, message))
        else:
          txt = ("%s %s" % (date, message))
        self.messages_area.AppendText(txt)
        self.messages_area.ScrollLines(-1)
        self.messages_area.SetStyle(start, end, wx.TextAttr(color))
      self._stream_flag.clear()






    
def sleeper():
    sleep(.001)
    return 1 # don't forget this otherwise the timeout will be removed
    
    
if __name__ == "__main__":

  logger.info('Starting Ne.Me.Sys. Speedtest v.%s' % __version__)
  
  app = wx.PySimpleApp(0)
  
  checker = checkSoftware(__version__)
  check = checker.checkIT()

  if check:
    sysmonitor.interfaces()
    if (platform.startswith('win')):
      wx.CallLater(200, sleeper)
    wx.InitAllImageHandlers()
    GUI = NemesysSpeedtestGUI(None, -1, "", style = wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.RESIZE_BOX))
    app.SetTopWindow(GUI)
    GUI.Show()
    app.MainLoop()
