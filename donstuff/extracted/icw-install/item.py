import sys
import collections
import re

import logging

import curses
from curses import textpad
from curses import panel

from editbox import Editbox
from button import Button
from checkbox import Checkbox

# from tools.func_param import *

class Item(object):

    def __init__(self, ncols, y, x, itemData, stdscreen, border = False, model = None, appScr = None):

        self.model = model
        self.itemData = itemData
        # self.title = step['name']
        self.border = border
        self.position = 0
        if  'valueOffset' in self.itemData:
            self.valueOffset = self.itemData['valueOffset']
        else :
            self.valueOffset = 10
        self.nlines = 3 if border is True else 1

        self.checkBox = None
        self.editBox = None
        self.placeholder = ''
        self.btn = None
        self.items = None
        self.func = None
        # self.funcParam = None
        self.outputWinLines = 0
        self.ModelData = None
        max_y, max_x = stdscreen.getmaxyx()


        window_y = y
        window_x = x
        if self.model and hasattr(self.model, 'GetModel'):
            self.ModelData = getattr(self.model, 'GetModel')()

        if self.model and self.itemData['type'] == 'list':
            addline = self.itemData['minlines']
            if 'modelfunc' in self.itemData:
                if self.ModelData:
                    self.func = getattr(self.ModelData, self.itemData['modelfunc'])
                    self.items = self.func()
                    if self.items:
                        if len(self.items) > addline:
                            addline = len(self.items)
            logging.debug(f'{self.nlines}  += {addline} = {self.nlines + addline}')
            self.nlines += addline
            logging.debug(f'self.nlines {self.nlines}')

        elif self.model and self.itemData['type'] == 'button':
            self.nlines = 3
            # if self.ModelData:
            #     self.func = getattr(self.ModelData, self.itemData['modelfunc'])
            ncols = len(self.itemData['label']) + 2
            window_y = max_y - 3
            if 'output' in self.itemData:
                self.outputWinLines = self.itemData['output']


        self.appScr = appScr
        self.window = stdscreen.subwin(self.nlines, ncols, window_y, window_x)

        self.outputWindow = None
        self.outputWindowBorder = None
        if self.outputWinLines > 0:
            self.outputWindowBorder = stdscreen.subwin(max_y - y - 3 , max_x - 4, y + self.nlines - 3, x)
            self.outputWindowBorder.border()
            self.outputWindowBorder.refresh()
            self.outputWindow = self.outputWindowBorder.subwin(max_y - y - 5, max_x - 5 - 2, y + self.nlines + 1 - 3, x + 1)
            self.outputWindow.scrollok(1)
            # self.outputWindow = None

            if self.ModelData:
                self.ModelData.outputWindow = self.outputWindow

        self.beginY, self.beginX = self.window.getbegyx()
        self.window.timeout(5000)
        self.window.keypad(1)
        self.panel = panel.new_panel(self.window)
        self.panel.hide()
        panel.update_panels()


        self.offset_x = 0
        self.offset_y = 0


    def _draw_border(self):
        if self.border is True:
            self.window.border()
            if self.offset_x == 0:
                self.offset_x = 2
            if self.offset_y == 0:
                self.offset_y = 2

    def getHeigh(self):
        logging.debug(f'{self.itemData["label"]}  getHeigh: {self.nlines} + {self.outputWinLines}')
        return self.nlines + self.outputWinLines

    def navigate(self, n):
        pass


    def hide(self):
        if self.outputWindow:
            self.outputWindow.clear()
            self.outputWindow.refresh()
        
        if self.outputWindowBorder:
            self.outputWindowBorder.clear()
            self.outputWindowBorder.refresh()

        self.panel.hide()
        self.window.clear()
        self.window.refresh()

    def addstr(self, y, x, string, attr):
        try:
            self.window.addstr(y, x, string, attr)
        except curses.error:
            # Curses will error on the last line even when it works.
            # https://stackoverflow.com/questions/7063128/last-character-of-a-window-in-python-curses
            if y == self.max_y - 1:
                pass
            else:
                raise


    def edit(self, key):

        # key = None
        lastcmd = None

        if key is None:
            key = ord('\t')

        if self.itemData['type'] == 'list':
            return ord('\t')
        elif self.itemData['type'] == 'dummy':
            return key
        elif self.itemData['type'] == 'label':
            return key
        elif self.itemData['type'] == 'button':
            if self.btn:
                result, lastcmd = self.btn.select()
                logging.debug(f'item edit return lastcmd:{lastcmd}')

        elif self.itemData['type'] == 'editbox' or self.itemData['type'] == 'password':

            if 'editable' in self.itemData and self.itemData['editable'] == False:
                return key
            # textbox = self.window.subwin(1, self.itemData['maxlen'] + 1, self.beginY, self.beginX + self.valueOffset)
            curses.curs_set(2)
            # textbox.refresh()
            validate = True
            while True:
                logging.debug(f'editbox in loop')
                text, lastcmd = self.editBox.edit(validate)

                if lastcmd == curses.ascii.ESC:
                    break
                if not self.itemData['type'] == 'password':
                    logging.debug(f'editbox {self.itemData["modelprop"]} value: "{text}", len: {len(text)}')
                if self.validate(text) is True:
                    self.itemData['value'] = text
                    self.updateModel(text)
                    if not self.itemData['type'] == 'password':
                        logging.debug(f'editbox2 {self.itemData["modelprop"]} value: {text}, len: {len(text)}')
                    break
                else:
                    validate = False
                    continue

            curses.curs_set(0)
            logging.debug(f'editbox end loop')
        # elif self.itemData['type'] == 'password':
        #     textbox = self.window.subwin(1, self.itemData['maxlen'] + 1, self.beginY, self.beginX + self.valueOffset)
        #     curses.curs_set(2)
        #     textbox.refresh()
        #     text, lastcmd = Editbox(textbox, insert_mode = True, passwd = self.refreshFromModel()).edit()
        #     curses.curs_set(0)
        #     textbox.refresh()

        #     logging.debug(f'passwd {self.itemData["modelprop"]} value: "{text}", len: {len(text)}')
        #     if self.validate(text) is True:
        #         self.itemData['value'] = text
        #         self.updateModel(text)
        #         logging.debug(f'passwd2 {self.itemData["modelprop"]} value: {text}, len: {len(text)}')

        elif self.itemData['type'] == 'checkbox':
            prop = self.refreshFromModel()
            prop, lastcmd = self.checkBox.select(prop)
            self.updateModel(prop)

        return lastcmd


    def validate(self, text):
        itType = self.itemData['type']

        if 'regex' in self.itemData:
            reg = self.itemData['regex']
            aa=re.match(reg, text)
            return False if aa is None else True

        if itType == 'editbox':
            return len(text) <= self.itemData['maxlen']

        if itType == 'password':
            return len(text) <= self.itemData['maxlen']

        return False

    def refreshFromModel(self):
        if self.ModelData \
           and 'modelprop' in self.itemData \
           and hasattr(self.ModelData, self.itemData['modelprop']):
            prop = getattr(self.ModelData, self.itemData['modelprop'])
            if prop is not None:
                return prop
            else:
                return None

    def updateModel(self, value):

        if self.ModelData \
           and 'modelprop' in self.itemData \
           and hasattr(self.ModelData, self.itemData['modelprop']):
            if not self.itemData['type'] == 'password':
                logging.debug(f'set {self.itemData["modelprop"]} value: "{value}"')
            setattr(self.ModelData, self.itemData['modelprop'], value)
            prop = getattr(self.ModelData, self.itemData['modelprop'])
            if prop:
                if not self.itemData['type'] == 'password':
                    logging.debug(f'after set  value: "{prop}"')

    def display(self, init = False):

        if self.itemData['type'] == 'dummy':
            return ord('\t')

        self.panel.top()
        self.panel.show()
        self.window.clear()

        curses.doupdate()

        self._draw_border()
        
        offset_top = self.offset_y
        self.max_y, self.max_x = self.window.getmaxyx()

        if self.model and self.itemData['type'] == 'list':
            if self.func:
                self.items = self.func()
                if self.items and self.nlines < len(self.items) + 1:
                    self.nlines = len(self.items) + 1

        if self.itemData['type'] == 'list' or \
           self.itemData['type'] == 'editbox' or \
           self.itemData['type'] == 'password' or \
           self.itemData['type'] == 'label':
            # display label
            self.addstr(
                y = offset_top,
                x = self.offset_x,
                string = f'{self.itemData["label"]}',
                attr = curses.A_NORMAL,
            )

            if self.items:
                for item in self.items:
                    logging.debug('item :'+item)
                    offset_top += 1
                    logging.info(f'item: {item}')
                    self.addstr(
                        y = offset_top,
                        x = self.valueOffset,
                        string = item.ljust(self.itemData["maxlen"] - 1),
                        attr = curses.A_NORMAL,
                    )
            # elif  self.itemData['type'] == 'editbox':
            #     # display value
            #     prop = None
            #     attr = curses.A_NORMAL

            #     if 'defaultValue' in self.itemData:
            #         prop = self.itemData["defaultValue"]
            #     # elif 'placeholder' in self.itemData:
            #     #     # self.window.attron(curses.color_pair(2) |curses.A_BOLD)
            #     #     attr = curses.color_pair(2) |curses.A_BOLD
            #     #     prop = self.itemData["placeholder"]
            #     else :
            #         prop = self.refreshFromModel()

            #     self.addstr(
            #         y = offset_top,
            #         x = self.valueOffset,
            #         string = str(prop).ljust(self.itemData["maxlen"] - 1, chr(curses.ascii.SP)),
            #         attr = attr,
            #     )

            #     self.updateModel(prop)
            
            # elif  self.itemData['type'] == 'password':
            #     # display value
            #     prop = None
            #     if 'defaultValue' in self.itemData:
            #         prop = self.itemData["defaultValue"]
            #     else :
            #         prop = self.refreshFromModel()

            #     self.addstr(
            #         y = offset_top,
            #         x = self.valueOffset,
            #         string = str(len(prop) * '*').ljust(self.itemData["maxlen"] - 1, chr(curses.ascii.SP)),
            #         attr = curses.A_NORMAL,
            #     )

            #     self.updateModel(prop)

        if self.itemData['type'] == 'editbox' or \
           self.itemData['type'] == 'password':
            # display value
            prop = None

            prop = self.refreshFromModel()
            if (prop is None or \
                (isinstance(prop, str) and len(prop) == 0) or \
                (isinstance(prop, int) and prop == 0)) \
            and 'defaultValue' in self.itemData:
                prop = self.itemData["defaultValue"]
                self.updateModel(prop)

            if 'placeholder' in self.itemData and len(self.placeholder) == 0:
                self.placeholder = self.itemData["placeholder"]
                self.placeholder = str(self.placeholder).ljust(self.itemData["maxlen"] - 1, chr(curses.ascii.SP))

            if init == False:
                prop = self.refreshFromModel()
                logging.debug(f'refreshFromModel editBox {prop}')
                
            editWin = self.window.subwin(1, self.itemData['maxlen'] + 1, self.beginY, self.beginX + self.valueOffset)

            if self.itemData['type'] == 'password':
                self.editBox = Editbox(editWin, insert_mode = True, passwd = self.refreshFromModel())
                self.editBox.show(str(len(prop) * '*'), self.placeholder, maxlen = self.itemData["maxlen"])
                logging.debug(f'item Passwd with placeholder:{self.placeholder}')
            else:
                self.editBox = Editbox(editWin, insert_mode = True)
                self.editBox.show(str(prop), self.placeholder, maxlen = self.itemData["maxlen"])
            # self.editBox.show(str(prop).ljust(self.itemData["maxlen"] - 1, chr(curses.ascii.SP)), self.placeholder)

            self.updateModel(prop)
        
        if self.itemData['type'] == 'checkbox':
            # display value
            prop = None
            if 'defaultValue' in self.itemData:
                prop = self.itemData["defaultValue"]
            else :
                prop = self.refreshFromModel()

            if init == False:
                prop = self.refreshFromModel()

            checkWin = self.window.subwin(1, self.itemData['maxlen'] + 1, self.beginY, self.beginX)
            self.checkBox = Checkbox(checkWin, label = self.itemData["label"], valueOffset = self.valueOffset)
            self.checkBox.checked = prop
            self.checkBox.show()

            self.updateModel(prop)


        if self.itemData['type'] == 'button':
            if init == False and self.outputWindow:
                logging.debug(f'display Button show output')
                self.outputWindowBorder.border()
                self.outputWindowBorder.refresh()

                self.outputWindow.scrollok(1)
                self.outputWindow.refresh()
                if self.ModelData:
                    logging.debug(f'Reset display Button show output')
                    self.ModelData.outputWindow = self.outputWindow

            self.btn = Button(self.window, label = self.itemData["label"], func = self.func, appScr = self.appScr, itemData = self.itemData, ModelData=self.ModelData )
            self.btn.prefunction()
            self.btn.display()


        self.window.refresh()
