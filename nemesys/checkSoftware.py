#!/usr/bin/env python
# -*- coding: utf-8 -*-

from registration import registration
from urlparse import urlparse
from nemesysParser import parse
from logger import logging
import webbrowser
import httputils
import paths
import re
import wx

logger = logging.getLogger()

#Data di scadenza
dead_date = 22221111

url_version = "https://speedtest.agcom244.fub.it/version"
area_privata = "https://www.misurainternet.it/login_form.php"



class checkSoftware():

  def __init__(self, version):
    
    (options, args, md5conf) = parse(version)
    self._httptimeout = options.httptimeout
    self._clientid = options.clientid
    self._thisVersion = version
    self._lastVersion = version
    self._stillDay = "unknown"
    
    
  def _showDialog(self, dialog):
    res = None
    msgBox = wx.MessageDialog(None, dialog['message'], dialog['title'], dialog['style'])
    res = msgBox.ShowModal()
    msgBox.Destroy()
    return res
    
  def _softwareVersion(self):
    versionOK = True
    deadlineOK = True
    
    url = urlparse(url_version)
    connection = httputils.getverifiedconnection(url = url, certificate = None, timeout = self._httptimeout)
    try:
      connection.request('GET', '%s?speedtest=true&version=%s' % (url.path, self._thisVersion))
      data = connection.getresponse().read()
      
      #### FAKE REPLY ####
      data = "1.0.5:88"
      ####################
      
      data = data.split(":")
      
      #### VERSION ####
      version = re.search('(\.?\d+)+',data[0])
      '''
      una stringa di uno o pi� numeri                     \d+
      ozionalmente preceduta da un punto                  \.?
      che si ripeta pi� volte                             (\.?\d+)+
      '''
      if (version != None):
        self._lastVersion = version.string
        logger.info("L'ultima versione sul server e' la %s" % self._lastVersion)
        if (self._thisVersion != self._lastVersion):
          logger.info("Nuova versione disponbile. [ this:%s | last:%s ]" % (self._thisVersion, self._lastVersion))
          newVersion = \
          { \
          "style":wx.YES|wx.NO|wx.ICON_INFORMATION, \
          "title":"Ne.Me.Sys. Speedtest %s" % self._thisVersion, \
          "message": \
          '''
          E' disponibile la nuova versione: Ne.Me.Sys Speedtest %s

          E' possibile effetuare il download dalla relativa sezione
          nell'area privata del sito www.misurainternet.it

          Vuoi scaricare ora la nuova versione?
          ''' % self._lastVersion
          }
          res = self._showDialog(newVersion)
          if res == wx.ID_YES:
            versionOK = False
            logger.info("Si e' scelto di scaricare la nuova versione del software.")
            webbrowser.open(area_privata, new=2, autoraise=True)
            return versionOK
          else:
            logger.info("Si e' scelto di continuare ad utilizzare la vecchia versione del software.")
            versionOK = True
        else:
          versionOK = True
          logger.info("E' in esecuzione l'ultima versione del software.")
      else:
        versionOK = True
        logger.error("Errore nella verifica della presenza di una nuova versione.")
        
      #### DEADLINE ####
      deadline = re.search('(-?\d+)(?!.)',data[1])
      '''
      una stringa di uno o pi� numeri                     \d+
      ozionalmente preceduta da un segno meno             -?
      ma che non abbia alcun carattere dopo               (?!.) 
      '''
      if (deadline != None):
        self._stillDay = deadline.string
        logger.info("Giorni rimasti comunicati dal server: %s" % self._stillDay)
        if (int(self._stillDay)>=0):
          deadlineOK = True
          logger.info("L'attuale versione %s scade fra %s giorni." % (self._thisVersion, self._stillDay))
          beforeDeadline = \
          { \
          "style":wx.OK|wx.ICON_EXCLAMATION, \
          "title":"Ne.Me.Sys. Speedtest %s" % self._thisVersion, \
          "message": \
          '''
          Questa versione di Ne.Me.Sys. Speedtest
          potr� essere utilizzata ancora per %s giorni.
          ''' % self._stillDay
          }
          res = self._showDialog(beforeDeadline)
        else:
          deadlineOK = False
          self._stillDay = -(int(self._stillDay))
          logger.info("L'attuale versione %s e' scaduta da %s giorni." % (self._thisVersion, self._stillDay))
          afterDeadline = \
          { \
          "style":wx.OK|wx.ICON_EXCLAMATION, \
          "title":"Ne.Me.Sys. Speedtest %s" % self._thisVersion, \
          "message": \
          '''
          Questa versione di Ne.Me.Sys. Speedtest
          � scaduta da %s giorni e pertanto
          non potr� pi� essere utilizzata.
          ''' % self._stillDay
          }
          res = self._showDialog(afterDeadline)
      else:
        deadlineOK = True
        logger.info("Questa versione del software non ha ancora scadenza.")
        
    except Exception as e:
      logger.error("Impossibile controllare se ci sono nuove versioni. Errore: %s." % e)
      
    return (versionOK and deadlineOK)
    
    
  def _isRegistered(self):
    regOK = registration(self._clientid)
    return regOK
    
    
  def checkIT(self):
    checkOK = False
    check_list = {1:self._softwareVersion,2:self._isRegistered}
    for check in check_list:
      checkOK = check_list[check]()
      if not checkOK:
        break
    return checkOK
    
if __name__ == '__main__':
  app = wx.PySimpleApp(0)
  checker = checkSoftware("1.0.4")
  checker.checkIT()