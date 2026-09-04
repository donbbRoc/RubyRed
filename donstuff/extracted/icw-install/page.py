import collections
import re
import imp
import logging

import curses
from curses import textpad
from curses import panel

import item

import icwconfig

Item = collections.namedtuple('Item', field_names=('label', 'value'))


class Page(object):

    def __init__(self, nlines, ncols, step, stdscreen, border):
        
        self.window = stdscreen.subwin(nlines, ncols - 3, 1, int(ncols // 3) + 5)
        self.stdscreen = stdscreen

        self.window.timeout(5000)
        self.window.keypad(1)
        # self.panel = panel.new_panel(self.window)
        # self.panel.hide()
        # panel.update_panels()

        self.step = step
        self.title = step['name']
        self.border = border
        self.position = 0
        self.pgNo = 0
        if 'model' in self.step:
            self.model = imp.load_source(' ', self.step['model'])
        else :
            self.model = None

        self.offset_x = 0
        self.offset_y = 0
        
        self.winsDict = dict()
        self.winsDict[0] = list()
        self.itemWins = self.winsDict[0]

        self.pageBtn = True


    def _draw_border(self):
        if self.border is True:
            self.window.border()
            if self.offset_x == 0:
                self.offset_x = 2
            if self.offset_y == 0:
                self.offset_y = 2


    def navigate(self, n):

        if n != 0:
            for itemWin in self.itemWins:
                itemWin.hide()
        #         del itemWin
        #     self.itemWins = list()

        self.pgNo += n
        if self.pgNo < 0:
            self.pgNo = 0
        elif self.pgNo == len(self.step["pages"]):
            self.pgNo = len(self.step["pages"]) - 1

        while self.pgNo > 0 or self.pgNo < len(self.step["pages"]):
            if 'visiblefunc' in self.step["pages"][self.pgNo]:
                ModelData = getattr(self.model, 'GetModel')()
                visiblefunc = getattr(ModelData, self.step["pages"][self.pgNo]['visiblefunc'])
                if visiblefunc() == False:
                    self.pgNo += n
                else:
                    break
            else:
                break

        # # skip not focus control
        # while itemIdx + 1 < len(self.itemWins):
        #     itemIdx += 1
        #     if self.itemWins[itemIdx].itemData['type'] in ('label', 'dummy'):
        #         continue
        #     elif self.itemWins[itemIdx].itemData['type'] == 'editbox' and \
        #         'editable' in self.itemWins[itemIdx].itemData and self.itemWins[itemIdx].itemData['editable'] == False:
        #             continue
        #     else:
        #         break
        # continue


        logging.debug(f'navigate count: {len(self.winsDict)} {self.winsDict.keys()}')
        
        if self.pgNo in self.winsDict:
            self.itemWins = self.winsDict[self.pgNo]
            logging.debug(f'navigate load self.itemWins of {self.pgNo}, count: {len(self.winsDict)} self.itemWins len = {len(self.itemWins)}')
        else :
            self.winsDict[self.pgNo] = list()
            self.itemWins = self.winsDict[self.pgNo] 
            logging.debug(f'navigate new self.itemWins of {self.pgNo}, count: {len(self.winsDict)} ')


    def hide(self):
        # self.panel.hide()
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


    def addline(self, y, string, attr):
        """
        Displays a string on the screen. Handles truncation and borders.
        """

        if y >= self.max_y:
            return

        # Display the left blank border.
        if self.offset_x > 1:
            self.addstr(
                y = y,
                x = self.offset_x,
                string = ' ' * (self.offset_x - 1),
                attr = curses.A_NORMAL,
            )

        # Remove trailing spaces so the truncate logic works correctly.
        string = string.rstrip()

        # Truncate the string if it is too long.
        if self.offset_x + len(string) + self.offset_x > self.max_x:
            string = string[:self.max_x - self.offset_x - self.offset_x - 2] + '..'

        # Add whitespace between the end of the string and the edge of the
        # screen. This is required when scrolling, to blank out characters
        # from other lines that had been displayed here previously.
        string += ' ' * (self.max_x - self.offset_x - len(string) - self.offset_x)

        # Display the string.
        self.addstr(
            y=y,
            x=self.offset_x,
            string=string,
            attr=attr,
        )


    def pageHeader(self, offset_top):
        if len(self.step["pages"]) > 0 and self.step["pages"][self.pgNo]:
            pageNoStr = f'({self.pgNo + 1}/{len(self.step["pages"])})'
            emptylen = (self.max_x - self.offset_x - len(pageNoStr) - len(self.step["pages"][self.pgNo]["name"]) - self.offset_x)
            
            self.addline(offset_top, f'{self.step["pages"][self.pgNo]["name"]}{" "*emptylen}{pageNoStr}', curses.A_REVERSE)
            self.addline(offset_top + 1, '-' * len(self.title), curses.A_NORMAL)

            return offset_top + 2

    def _addPageBtn(self, beginY, beginX):
        # if self.pgNo < len(self.step["pages"]) - 1:
            # pgDown = item.Item(3, \
            #                     self.max_y - 1, \
            #                     beginX + self.offset_x, \
            #                     {"label":"  Next  ", "type":"button", "maxlen":15}, \
            #                     self.window, \
            #                     model = self.model,
            #                     appScr = self.stdscreen)
            # self.itemWins.append(pgDown)
            # pgDown.display()
            # pgDown.hide()
            # logging.debug(f'pgDown Hide')
        # else:
        #     finish = item.Item(3, \
        #                         self.max_y - 1, \
        #                         beginX + self.offset_x, \
        #                         {"label":" Finish ", "type":"button", "maxlen":15}, \
        #                         self.window, \
        #                         model = self.model,
        #                         appScr = self.stdscreen)
        #     self.itemWins.append(finish)
        #     finish.display()

        if self.pgNo > 0:
            pgUp = item.Item(3, \
                                self.max_y - 1, \
                                beginX + self.offset_x + 25, \
                                {"label":"Previous", "type":"button", "maxlen":15}, \
                                self.window, \
                                model = self.model,
                                appScr = self.stdscreen)
            self.itemWins.append(pgUp)
            pgUp.display()

    def refresh(self):

        # for itemWin in self.itemWins:
        #     itemWin.hide()
        #     del itemWin

        self.max_y, self.max_x = self.window.getmaxyx()

        offset_top = self.offset_y
        offset_bottom =  self.offset_y

        # Display the page header
        offset_top = self.pageHeader(offset_top)
        self.window.refresh()

        
        logging.debug(f'len(self.itemWins):{len(self.itemWins)}')

        if len(self.itemWins) is 0:
            beginY, beginX = self.window.getbegyx()
            if "items" in self.step["pages"][self.pgNo]:
                # self.itemWins = list()
                itemIdx = 0
                for itemData in self.step["pages"][self.pgNo]["items"]:
                    win = item.Item(self.max_x - self.offset_x * 2, \
                                    beginY + offset_top, \
                                    beginX + self.offset_x, \
                                    itemData, \
                                    self.window, \
                                    model = self.model,
                                    appScr = self.stdscreen)
                    self.itemWins.append(win)
                    win.display(init = True)
                    offset_top += win.getHeigh()
                    itemIdx += 1


                if self.pageBtn:
                    self._addPageBtn(beginY, beginX)
        else :
            for itemWin in self.itemWins:
                itemWin.display()


    def display(self):

        # self.panel.top()
        # self.panel.show()
        self.window.clear()

        curses.doupdate()

        self._draw_border()

        self.refresh()


        # self.max_y, self.max_x = self.window.getmaxyx()

        while True:

            key = None
            itemIdx = 0
            while True:
                # logging.debug('page refresh 1')
                # self.refresh()

                if len(self.itemWins) == 0:
                    logging.debug('page refresh 1')
                    self.refresh()

                itemWin = self.itemWins[itemIdx]
                key = itemWin.edit(key)
                # logging.debug('key: ' + str(key))

                if key == 'cmdContinue':
                    logging.debug('page refresh 2')
                    # self.refresh()
                    continue

                if key == 'cmdFinish':
                    logging.debug('key == cmdFinish')
                    for itemWin in self.itemWins:
                        if itemWin.btn != None and itemWin.itemData["label"].find('Previous') >= 0:
                            logging.debug('hide button')
                            itemWin.hide()

                elif key == ord('\t'):
                    if itemIdx + 1 < len(self.itemWins):
                        # itemIdx += 1

                        # skip not focus control
                        while itemIdx + 1 < len(self.itemWins):
                            itemIdx += 1
                            if self.itemWins[itemIdx].itemData['type'] in ('label', 'dummy'):
                                continue
                            elif self.itemWins[itemIdx].itemData['type'] == 'editbox' and \
                                'editable' in self.itemWins[itemIdx].itemData and self.itemWins[itemIdx].itemData['editable'] == False:
                                    continue
                            else:
                                break
                        continue
                    elif itemIdx + 1 == len(self.itemWins):
                        itemIdx = 0
                        continue
                    else :
                        # itemIdx = 0
                        key = self.window.getch()
                        if key in(curses.KEY_ENTER, \
                                    curses.ascii.NL, \
                                    curses.ascii.ESC):
                            break

                        if key in(curses.KEY_PPAGE, \
                                    curses.KEY_NPAGE) and icwconfig.prodtype == icwconfig.EProdtype.debug:
                            break

                elif key == curses.KEY_BTAB:
                    if itemIdx > 0:
                        # itemIdx -= 1

                        # skip not focus control
                        while itemIdx > 0:
                            itemIdx -= 1
                            if self.itemWins[itemIdx].itemData['type'] in ('label', 'dummy'):
                                continue
                            elif self.itemWins[itemIdx].itemData['type'] == 'editbox' and \
                                'editable' in self.itemWins[itemIdx].itemData and self.itemWins[itemIdx].itemData['editable'] == False:
                                    logging.debug('### break')
                                    continue
                            else:
                                break
                        continue
                    elif itemIdx == 0:
                        itemIdx = len(self.itemWins) - 1
                        continue

                elif key == curses.KEY_PPAGE or key ==  curses.KEY_NPAGE or key == curses.ascii.ESC :
                    break

                elif key in(curses.KEY_ENTER, curses.ascii.NL):
                    if itemIdx + 1 <= len(self.itemWins) - 1:
                        itemIdx += 1
                        continue
                    else:
                        break

            if key in (curses.KEY_PPAGE ,\
                       curses.KEY_NPAGE, \
                       curses.KEY_ENTER, \
                       curses.ascii.NL) :
                if key == curses.KEY_PPAGE:
                    self.navigate(-1)
                elif key in (curses.KEY_NPAGE, curses.KEY_ENTER, curses.ascii.NL):
                    self.navigate(1)
                self.refresh()
                continue

            if key == curses.ascii.ESC:
                # TODO: add confirm dialog
                break

            # key = self.window.getch()
            self.window.refresh()

            # if key == curses.KEY_PPAGE:
            #     self.navigate(-1)
            # elif key == curses.KEY_NPAGE:
            #     self.navigate(1)
            # elif key == ord('q'):
            #     break





        # self.window.clear()
        # self.panel.hide()
        # panel.update_panels()
        # curses.doupdate()

