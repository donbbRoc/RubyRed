import imp
import curses
from curses import textpad
from curses import ascii
import time

import logging

from tools.func_param import *
import icwconfig

class Button():
    """Button Control
    """
    def __init__(self, win, label, func = None, appScr = None, itemData = None, ModelData=None ):
        self.label = label
        self.win = win
        self.appScr = appScr
        self._update_max_yx()
        self.itemData = itemData
        # self.func = func
        self.ModelData = ModelData

        self.paramModule = imp.load_source(' ', './tools/func_param.py')

        self.func = None
        if 'modelfunc' in self.itemData and self.ModelData  and hasattr(self.ModelData, self.itemData['modelfunc']):
            self.func = getattr(self.ModelData, self.itemData['modelfunc'])

            
        self.prefunc = None
        if 'modelPrefunc' in self.itemData and self.ModelData  and hasattr(self.ModelData, self.itemData['modelPrefunc']):
            self.prefunc = getattr(self.ModelData, self.itemData['modelPrefunc'])

        self.funcParam = None

        win.keypad(1)
        self.lastTimestamp = None


    def _update_max_yx(self):
        maxy, maxx = self.win.getmaxyx()
        self.maxy = maxy - 1
        self.maxx = maxx - 1


    def blink(self):
        self.display(focus = False)
        time.sleep(0.2)
        self.display(focus = True)


    def press(self):
        result = None
        lastcmd = 'cmdContinue'
        # self.blink()

        # anti shake
        if self.lastTimestamp and \
            time.time() - self.lastTimestamp < 1:
            return True, lastcmd

        if self.label.find('Next') >= 0:
            return None, curses.KEY_NPAGE

        if self.label.find('Skip') >= 0:
            return None, curses.KEY_NPAGE
        
        if self.label.find('Previous') >= 0:
            return None, curses.KEY_PPAGE
        
        if self.label.find('Finish') >= 0:
            return None, curses.ascii.ESC

        if self.func:
            if 'paramClass' in self.itemData:
                self.funcParam = getattr(self.paramModule, self.itemData['paramClass'])(self.ModelData)

            oldCurs = curses.curs_set(2)
            result = self.func(self.funcParam)
            curses.curs_set(oldCurs)

            if result is True:
                logging.debug(f'Button press show nextlabel')
                self.label = self.itemData['nextlabel']

                if self.label.find('Finish') >= 0:
                    lastcmd = 'cmdFinish'

        self.lastTimestamp = time.time()

        return result, lastcmd

    def prefunction(self):
        if self.prefunc:
            logging.debug(f'Do Btn prefunc')
            if 'paramClass' in self.itemData:
                self.funcParam = getattr(self.paramModule, self.itemData['paramClass'])(self.ModelData)

            result = self.prefunc(self, self.funcParam)
            logging.debug(f'Do Btn prefunc result {result} self.label{self.label}')


    def display(self, focus = False):
        self.max_y, self.max_x = self.win.getmaxyx()
        self.win.border()

        if focus is True:
            self.win.attron(curses.A_REVERSE)
            self.win.attron(curses.color_pair(1))

        self.win.addstr(1, 1, self.label + ' '*(self.max_x - 2 - len(self.label)))
        
        if focus is True:
            self.win.attroff(curses.A_REVERSE)
            self.win.attroff(curses.color_pair(1))


        self.win.refresh()


    def select(self, func = None):
        "Edit in the widget window and collect the results."
        result = None
        if func :
            self.func = func

        oldCurs = curses.curs_set(0)
        self.display(focus = True)
        lastcmd = None

        key = None
        while 1:
            ch = self.win.getch()
            lastcmd = ch
            
            # if ch in (curses.ascii.ESC, \
            #             curses.KEY_PPAGE, \
            #             curses.KEY_NPAGE):
            #     pass
            #     # self.output.clear()
                

            if ch in (curses.KEY_UP, \
                        curses.KEY_DOWN, \
                        ord('\t'), \
                        curses.KEY_BTAB, \
                        curses.ascii.ESC):
                break

            # logging.debug(f'Page Up Page Down {ch}  {icwconfig.prodtype}')
            if icwconfig.prodtype == icwconfig.EProdtype.debug:
                if ch in (curses.KEY_PPAGE, \
                            curses.KEY_NPAGE):
                    break

            if ch in (curses.ascii.LF, \
                        curses.ascii.NL, \
                        curses.KEY_ENTER) or \
               curses.ascii.isblank(ch) :
                self.display(focus = False)
                result, lastcmd = self.press()
                # self.display(focus = True)
                break

        self.display(focus = False)
        curses.curs_set(oldCurs)
        return result, lastcmd


if __name__ == '__main__':
    def test_button(stdscr):
        
        pass
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)

        ncols, nlines = len('Button 1') + 2, 3
        uly, ulx = 15, 20
        stdscr.addstr(uly-2, ulx, "space key or enter,  key 'ESC' for quit")
        btnWin1 = curses.newwin(nlines, ncols, uly, ulx)
        btnWin2 = curses.newwin(nlines, ncols, uly + 3, ulx)
        btnWin3 = curses.newwin(nlines, ncols, uly + 6, ulx)

        stdscr.refresh()
        # btnWin1.border()
        btn1 = Button(btnWin1, label = 'Button 1')
        btn2 = Button(btnWin2, label = 'Button 2')
        btn3 = Button(btnWin3, label = 'Button 3')

        btn1.display()
        btn2.display()
        btn3.display()

        while True:

            result, lastcmd = btn1.select()

            if lastcmd == curses.ascii.ESC:
                break

            result, lastcmd = btn2.select()

            if lastcmd == curses.ascii.ESC:
                break

            result, lastcmd = btn3.select()

            if lastcmd == curses.ascii.ESC:
                break

        #     checked2, lastcmd = check2.select(checked2)

        #     if lastcmd == curses.ascii.ESC:
        #         break

        #     checked3, lastcmd = check3.select(checked3)

            if lastcmd in (curses.ascii.ESC, \
                        curses.ascii.LF, \
                        curses.ascii.NL, \
                        curses.KEY_ENTER):
                break


        return 

    str = curses.wrapper(test_button)
    print('Contents of text box:', repr(str))

