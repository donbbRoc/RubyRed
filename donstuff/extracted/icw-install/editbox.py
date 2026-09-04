import curses
from curses import textpad
from curses import ascii


import logging

import icwconfig

class Editbox(textpad.Textbox):
    """Simply editing box for input
    """
    def __init__(self, win, insert_mode = False, passwd = None):
        self.insert_mode = True
        self.passwd = passwd
        # logging.debug(f'__init__ passwd:{self.passwd} passwd is None{self.passwd is None}')

        textpad.Textbox.__init__(self, win, insert_mode)
        self.placeholder = ''
        self.placeholderBegin = False


    def _insert_printable_char(self, ch):

        self._update_max_yx()
        (y, x) = self.win.getyx()
        backyx = None
        while y < self.maxy or x < self.maxx:
            if self.insert_mode:
                oldch = self.win.inch()
            # logging.debug(f'Key #3#:{oldch}')
            # The try-catch ignores the error we trigger from some curses
            # versions by trying to write into the lowest-rightmost spot
            # in the window.
            try:
                # logging.debug(f'_insert_printable_char *: before passwd:{self.passwd} passwd is None{self.passwd is None}')
                if self.passwd is not None and backyx is None:
                    # logging.debug(f'_insert_printable_char: y:{y} x:{x} maxy:{self.maxy} maxx:{self.maxx}')
                    # logging.debug(f'_insert_printable_char: before passwd:{self.passwd}')
                    self.passwd = self.passwd[:x] + chr(ch) + self.passwd[x:]

                    # trim by max length
                    if len(self.passwd) > self.maxx :
                        self.passwd = self.passwd[:self.maxx] 

                    # logging.debug(f'_insert_printable_char: after passwd:{self.passwd}')
                    ch = ord('*')

                self.win.addch(ch)
            except curses.error:
                pass
            # if not self.insert_mode or not curses.ascii.isprint(oldch):
            #     break
            ch = oldch
            (y, x) = self.win.getyx()
            # Remember where to put the cursor back since we are in insert_mode
            if backyx is None:
                backyx = y, x

        if backyx is not None:
            self.win.move(*backyx)

    def do_command(self, ch):
        "Process a single editing command."
        self._update_max_yx()
        (y, x) = self.win.getyx()
        self.lastcmd = ch
        # logging.debug(f'Key ##:{ch}')
        if curses.ascii.isprint(ch):
            # logging.debug(f'Key ##:1')
            
            if self.placeholderBegin == True:
                self.placeholderBegin = False
                self.win.erase()
                self.win.move(0, 0)

            if y < self.maxy or x < self.maxx:
                self._insert_printable_char(ch)
        elif ch in (curses.ascii.STX,curses.KEY_LEFT, curses.ascii.BS,curses.KEY_BACKSPACE):
            if self.placeholderBegin == True:
                return 1
            logging.debug(f'Key ##:2')
            if x > 0:
                self.win.move(y, x-1)
            elif y == 0:
                pass
            elif self.stripspaces:
                self.win.move(y-1, self._end_of_line(y-1))
            else:
                self.win.move(y-1, self.maxx)
            if ch in (curses.ascii.BS, curses.KEY_BACKSPACE):
                logging.debug(f'Key2 ##:{ch}')
                self.win.delch()
                
                if self.passwd and x > 0:
                    logging.debug(f'do_command1: y:{y} x:{x} maxy:{self.maxy} maxx:{self.maxx}')
                    logging.debug(f'do_command1: before passwd:{self.passwd}')
                    self.passwd = self.passwd[:x-1] + self.passwd[x:]
                    logging.debug(f'do_command1: before passwd:{self.passwd}')

        elif ch in(curses.ascii.EOT, curses.KEY_DC):                           # ^d DELETE
            if self.placeholderBegin == True:
                return 1
            logging.debug(f'Key ##:3')
            self.win.delch()
            # self.win.addch(y, self._end_of_line(y), 'A')

            # backyx = self.win.getyx()
            # self.win.move(y, self.maxx - 1 )
            self.win.addch(y, self.maxx - 1, curses.ascii.SP)
            # if backyx is not None:
            self.win.move(y, x)

            if self.passwd:
                self.passwd = self.passwd[:x] + self.passwd[x+1:]
        # elif ch == ord('\b'):                           # backspace
        elif ch == curses.ascii.DEL:                           # backspace
            if self.placeholderBegin == True:
                return 1
            if x > 0:
                self.win.move(y, x-1)
                self.win.delch()
                self.win.addch(y, self.maxx - 1, curses.ascii.SP)
                self.win.move(y, x-1)

                if self.passwd:
                    # self.passwd = self.passwd[:x] + self.passwd[x+1:]
                    logging.debug(f'do_command2: y:{y} x:{x} maxy:{self.maxy} maxx:{self.maxx}')
                    logging.debug(f'do_command2: before passwd:{self.passwd}')
                    self.passwd = self.passwd[:x-1] + self.passwd[x:]
                    logging.debug(f'do_command2: before passwd:{self.passwd}')

        # elif ch == curses.ascii.SOH:                           # ^a
        #     self.win.move(y, 0)
        elif ch == curses.KEY_HOME:                           # HOME
            self.win.move(y, 0)
        # elif ch == curses.ascii.ENQ:                           # ^e
        #     if self.stripspaces:
        #         self.win.move(y, self._end_of_line(y))
        #     else:
        #         self.win.move(y, self.maxx)
        elif ch == curses.KEY_END:                           # END
            if self.stripspaces:
                self.win.move(y, self._end_of_line(y))
            else:
                self.win.move(y, self.maxx)
        elif ch == curses.KEY_RIGHT:
            if self.placeholderBegin == True:
                return 1

            if x < self.maxx:
                self.win.move(y, x+1)
            elif y == self.maxy:
                pass
        elif ch in (curses.KEY_PPAGE, curses.KEY_NPAGE):
            if icwconfig.prodtype == icwconfig.EProdtype.debug:
                return 0
        elif ch in (curses.KEY_UP, \
                    curses.KEY_DOWN, \
                    ord('\t'), \
                    curses.KEY_BTAB, \
                    curses.ascii.LF, \
                    curses.ascii.NL, \
                    curses.ascii.ESC, \
                    curses.KEY_ENTER):
            return 0
        return 1

    def edit(self, validate = True):

        holderTxt = ''

        self.win.move(0, 0)
        "Edit in the widget window and collect the results."
        oldAttr = self.win.getbkgd()
        
        # if self.placeholder == True:
        #     holderTxt = self.gather()
        #     self.win.erase()

        if self.placeholderBegin == True or validate == False:
            self.win.chgat(curses.color_pair(2) |curses.A_BOLD|curses.A_UNDERLINE)
        else:
            self.win.chgat(curses.A_UNDERLINE)

        self.win.attron(curses.A_UNDERLINE)
        key = None
        while 1:
            ch = self.win.getch()
            # ch = self.win.getkey()
            # logging.debug(f'Key2 ##:{ch[0]}:{ord(ch[0])} {ch[1]}:{ord(ch[1])} {ch[2]}:{ord(ch[2])} {ch[3]}:{ord(ch[3])} {ch[4]}:{ord(ch[4])} {ch[5]}:{ord(ch[5])}')
            # break
            ch = self._validate(ch)

            if not ch:
                continue
            if not self.do_command(ch):
                break

            (y, x) = self.win.getyx()
            if len(self.gather()) == 0 or \
               self.placeholderBegin == True:
                self.show('', self.placeholder, focus = True)
                logging.debug(f'show placeholder {self.placeholder}')
            self.win.move(y, x)

            self.win.refresh()

        self.win.attroff(curses.A_UNDERLINE)
        self.win.move(0, 0)
        self.win.chgat(oldAttr)

        if len(self.gather()) == 0 or \
           self.placeholderBegin == True:
            self.show('', self.placeholder)

        self.win.refresh()
        logging.debug(f'out edit1: oldAttr:{oldAttr}')

        return self.gather(), self.lastcmd

    def show(self, prop, placeholder = '', focus = False, maxlen = 0):
        self.placeholder = placeholder
        showVar = prop
        attr = curses.A_NORMAL

        if len(showVar) == 0 and len(self.placeholder) > 0:
            attr = curses.color_pair(2) |curses.A_BOLD
            if focus == True:
                attr |=curses.A_UNDERLINE
            showVar = self.placeholder
            self.placeholderBegin = True
        else:
            str(showVar).ljust(maxlen - 1, chr(curses.ascii.SP))

        self.win.move(0, 0)
        for idx in range(0, len(showVar)):
            # print(prop[idx])
            # logging.debug(f'show ch:{showVar[idx]}')
            # ch = ord('*')
            self.win.addch(ord(showVar[idx]), attr)
        # if len(self.placeholder) > 0:
        #     attr = curses.color_pair(2) |curses.A_BOLD
        #     if focus == True:
        #         attr |=curses.A_UNDERLINE
        #     self.win.addstr(0, 0, self.placeholder, attr)
        #     self.placeholderBegin = True
        # else :
        #     self.win.addstr(0, 0, prop, curses.A_NORMAL)

        self.win.move(0, 0)
        self.win.refresh()


    def _end_of_line(self, y):
        """Go to the location of the first blank on the given line,
        returning the index of the last non-blank character."""
        self._update_max_yx()
        last = self.maxx
        strbuf = ''
        while True:
            if curses.ascii.ascii(self.win.inch(y, last)) != curses.ascii.SP:
                last = min(self.maxx, last+1)
                break
            elif last == 0:
                break
            strbuf += chr(curses.ascii.ascii(self.win.inch(y, last)))
            last = last - 1

        # logging.debug(f'_end_of_line: strbuf:{strbuf}, len:{len(strbuf)}')
        return last

    def gather(self):
        if self.passwd:
            return self.passwd
        if self.placeholderBegin == True:
            return ""
        "Collect and return the contents of the window."
        result = ""
        self._update_max_yx()
        for y in range(self.maxy+1):
            self.win.move(y, 0)
            stop = self._end_of_line(y)
            # logging.debug(f'gather: stop:{stop}')
            if stop == 0 and self.stripspaces:
                continue
            for x in range(self.maxx+1):
                if self.stripspaces and x > stop - 1:
                    break
                result = result + chr(curses.ascii.ascii(self.win.inch(y, x)))
            # if self.maxy > 0:
            #     result = result + "\n"
        return result

    def _validate(self, ch):
        # if self.insert_mode:
        #     self._update_max_yx()
        #     end = chr(curses.ascii.ascii(self.win.inch(0, self.maxx)))

        #     if ascii.isblank(end) is False:
        #         ch = None

        return ch

if __name__ == '__main__':
    def test_editbox(stdscr):
        ncols, nlines = 9, 4
        uly, ulx = 15, 20
        stdscr.addstr(uly-2, ulx, "Use Ctrl-G to end editing.")
        win = curses.newwin(nlines, ncols, uly, ulx)
        textpad.rectangle(stdscr, uly-1, ulx-1, uly + nlines, ulx + ncols)
        stdscr.refresh()
        return textpad.Textbox(win).edit()

    str = curses.wrapper(test_editbox)
    print('Contents of text box:', repr(str))
