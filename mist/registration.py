#!/usr/bin/env python
# -*- coding: utf-8 -*-
# generated by wxGlade 0.6.3 on Wed Apr 11 17:48:58 2012


import hashlib
import httplib
import logging
import os
import urlparse
import wx

import iptools
import paths


SWN = 'MisuraInternet Speed Test'

logger = logging.getLogger(__name__)

configurationServer = 'https://speedtest.agcom244.fub.it/Config'
MAXretry = 5    # # numero massimo di tentativi prima di chiudere la finestra ##
provinciaList = sorted(["TO", "VC", "NO", "CN", "AT", "AL", "AO", "IM", "SV", "GE", "SP", "VA", "CO", "SO", "MI", "BG", "BS", "PV", "CR", "MN", "BZ", "TN", "VR", "VI", "BL", "TV", "VE", "PD", "RO", "UD", "GO", "TS", "PC", "PR", "RE", "MO", "BO", "FE", "RA", "FC", "PU", "AN", "MC", "AP", "MS", "LU", "PT", "FI", "LI", "PI", "AR", "SI", "GR", "PG", "TR", "VT", "RI", "RM", "LT", "FR", "CE", "BN", "NA", "AV", "SA", "AQ", "TE", "PE", "CH", "CB", "FG", "BA", "TA", "BR", "LE", "PZ", "MT", "CS", "CZ", "RC", "TP", "PA", "ME", "AG", "CL", "EN", "CT", "RG", "SR", "SS", "NU", "CA", "PN", "IS", "OR", "BI", "LC", "LO", "RN", "PO", "KR", "VV", "VB", "OT", "OG", "VS", "CI", "MB", "FM", "BT"])

RegInfo = \
{ \
"style":wx.OK | wx.ICON_INFORMATION, \
"title":"Informazioni sulla registrazione", \
"message": \
'''
Verranno ora richieste le credenziali per l'attivazione.\n
Se NON e' stata effettuata l'iscrizione verra' richiesto di
selezionare la provincia dalla quale si sta effettuando
la misura con %s.\n
Se e' stata effettuata l'iscrizione verra' richiesto di
inserire i codici di accesso (username e password)
utilizzate per accedere all'area riservata su misurainternet.it.
Al momento dell'inserimento si prega di verificare
la correttezza delle credenziali di accesso.\n
Dopo %s tentativi falliti, sara' necessario riavviare
il programma per procedere nuovamente all'inserimento.\n
Al momento dell'inserimento si prega di avere accesso alla rete.''' % (SWN, MAXretry)
}

ErrorCode = \
{ \
"style":wx.OK | wx.ICON_ERROR, \
"title":"%s Error" % SWN, \
"message": \
'''
Le credenziali di accesso inserite sono errate.\n
Controllare la loro correttezza accedendo all'area 
personale sul sito www.misurainternet.it
'''
}

ErrorSave = \
{ \
"style":wx.OK | wx.ICON_ERROR, \
"title":"%s Error" % SWN, \
"message":"\nErrore nel salvataggio del file di configurazione." \
}

ErrorDownload = \
{ \
"style":wx.OK | wx.ICON_ERROR, \
"title":"%s Error" % SWN, \
"message":"\nErrore nel download del file di configurazione\no credenziali di accesso non corrette." \
}

ErrorRetry = \
{ \
"style":wx.OK | wx.ICON_ERROR, \
"title":"%s Error" % SWN, \
"message": \
'''
Il download del file di configurazione e' fallito per %s volte.\n
Riavviare il programma dopo aver verificato la correttezza
delle credenziali di accesso e di avere accesso alla rete.
''' % MAXretry
}

ErrorRegistration = \
{ \
"style":wx.OK | wx.ICON_ERROR, \
"title":"%s Registration Error" % SWN, \
"message": "\nQuesta copia di %s non risulta correttamente registrata." % SWN \
}


class Dialog(wx.Dialog):

    def __init__(self, parent, title, default, caption, pos=(200,200)):
        # kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Dialog.__init__(self, None, -1, "", pos)
        self.label_1 = wx.StaticText(self, -1, "\nSe e' stata effettuata l'iscrizione inserire\ni codici di accesso (username e password)\nutilizzati per accedere all'area personale.\n", style=wx.ALIGN_CENTRE)
        self.label_username = wx.StaticText(self, -1, "Username:", style=wx.ALIGN_RIGHT)
        self.text_username = wx.TextCtrl(self, -1, default)
        self.label_password = wx.StaticText(self, -1, "Password:", style=wx.ALIGN_RIGHT)
        self.text_password = wx.TextCtrl(self, -1, "", style=wx.TE_PASSWORD)
        self.button_1 = wx.Button(self, caption, "Accedi")
        self.label_2 = wx.StaticText(self, -1, "\nSe NON e' stata effettuata l'iscrizione inserire\nla provincia in cui si sta effettuando\nla misura con MisuraInternet Speed Test.\n", style=wx.ALIGN_CENTRE)
        self.label_provincia = wx.StaticText(self, -1, "Provincia:", style=wx.ALIGN_RIGHT)
        self.text_provincia = wx.ComboBox(self, choices=provinciaList, style=wx.CB_READONLY)

        self.__set_properties(title)
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.button_pressed, self.button_1)
        # end wxGlade

    def __set_properties(self, title):
        # begin wxGlade: MyFrame.__set_properties
        self.SetTitle(title)
        self.SetSize((360, 294))
        self.label_username.SetMinSize((80, 26))
        self.text_username.SetMinSize((180, 26))
        self.label_password.SetMinSize((80, 26))
        self.text_password.SetMinSize((180, 26))
        self.label_provincia.SetMinSize((80, 26))
        self.text_provincia.SetMinSize((80, 26))
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MyFrame.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)

        sizer_1.Add(self.label_2, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_BOTTOM, 0)

        sizer_4.Add(self.label_provincia, 0, wx.ALIGN_CENTRE_VERTICAL, 0)
        sizer_4.Add(self.text_provincia, 0, 0, 0)
        sizer_1.Add(sizer_4, 1, wx.ALIGN_CENTER_HORIZONTAL, 8)

        sizer_1.Add(self.label_1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_BOTTOM, 0)

        sizer_2.Add(self.label_username, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_2.Add(self.text_username, 0, 0, 0)
        sizer_1.Add(sizer_2, 1, wx.ALIGN_CENTER_HORIZONTAL, 8)

        sizer_3.Add(self.label_password, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        sizer_3.Add(self.text_password, 0, 0, 0)
        sizer_1.Add(sizer_3, 1, wx.ALIGN_CENTER_HORIZONTAL, 8)

        sizer_1.Add(self.button_1, 0, wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL, 8)
        
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def GetValue(self):
        username = self.text_username.GetValue()
        password = self.text_password.GetValue()
        provincia = self.text_provincia.GetValue()
        if (len(username) > 2):
            return "%s|%s" % (username, hashlib.sha1(password).hexdigest())
        else:
            if (len(provincia) == 2):
                mac = iptools.get_mac_address()
                return "%s|%s" % (provincia, mac)
            else:
                return None


    def button_pressed(self, event):    # wxGlade: MyDialog.<event_handler>
        self.EndModal(event.GetId())



def showDialog(dialog, message=None):
    if (message == None):
        msgBox = wx.MessageDialog(None, dialog['message'], dialog['title'], dialog['style'], pos=(200,200))
    else:
        msgBox = wx.MessageDialog(None, message, dialog['title'], dialog['style'], pos=(200,200))
    msgBox.ShowModal()
    msgBox.Destroy()
    
def getconf(code, filepath, url):
    # # Scarica il file di configurazione dalla url (HTTPS) specificata, salvandolo nel file specificato. ##
    # # Solleva eccezioni in caso di problemi o file ricevuto non corretto. ##
    
    url = urlparse.urlparse(url)
    try:
        connection = httplib.HTTPSConnection(host=url.hostname)
        # Warning This does not do any verification of the server's certificate. #
    
        connection.request('GET', '%s?clientid=%s' % (url.path, code))
        logger.debug("Dati inviati: %s" % code)
    
        data = connection.getresponse().read()
    except:
        raise Exception("Impossibile contattare il server, verificare la connessione a Internet")
    logger.debug("Dati ricevuti:\n%s" % data)
    
    # Controllo se nel file di configurazione e' presente il codice di attivazione. #
    if (data.find(code) != -1 or data.find("username") != -1):
        data2file = open(filepath, 'w')
        data2file.write(data)
    else:
        raise Exception(data.replace(";", ""))

    return os.path.exists(filepath)
    
def registration(code):
    if len(code) < 4:
        regOK = False
        logger.error("ClientID assente o di errata lunghezza")
        retry = 0
        showDialog(RegInfo)
        for retry in range(MAXretry):
            # # Prendo un codice licenza valido sintatticamente    ##
            code = None
            logger.info('Tentativo di registrazione %s di %s' % (retry + 1, MAXretry))
            title = "Tentativo %s di %s" % (retry + 1, MAXretry)
            default = ""
            dlg = Dialog(None, title, default, wx.ID_OK, pos=(200,200))
            res = dlg.ShowModal()
            code = dlg.GetValue()
            dlg.Destroy()
            logger.info("Codici di accesso inseriti dall'utente: %s" % code)
            if (res != wx.ID_OK):
                logger.warning('Registration aborted at attempt number %d' % (retry + 1))
                break
            
            filepath = paths.CONF_MAIN 
            try:
                if(code != None and len(code) > 4):
                    # Prendo il file di configurazione. #
                    regOK = getconf(code, filepath, configurationServer)
                    if (regOK == True):
                        logger.info('Configuration file successfully downloaded and saved')
                        break
                    else:
                        logger.error('Configuration file not correctly saved')
                        showDialog(ErrorSave)
                else:
                    logger.error('Wrong username/password')
                    showDialog(ErrorCode)
            except Exception as error:
                logger.error('Configuration file not downloaded or incorrect: %s' % error)
                showDialog(ErrorDownload, str(error))
            
            if not (retry + 1 < MAXretry):
                showDialog(ErrorRetry)
                
        if not regOK:
            logger.info('Verifica della registrazione del software fallita')
            showDialog(ErrorRegistration)
        
    else:
        regOK = True
    
    return regOK

if __name__ == '__main__':
    import log_conf
    log_conf.init_log()
    app = wx.App(False)
    registration("456")
    # getconf('ab0cd1ef2gh3ij4kl5mn6op7qr8st9uv', './../config/client.conf', 'https://finaluser.agcom244.fub.it/Config')
