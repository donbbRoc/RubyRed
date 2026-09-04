import curses
from curses import textpad
from curses import ascii


import logging

class Checkbox():
    """Simply Check box for select
    """
    def __init__(self, win, label, checked = False,  lableFirst = True, round = False, valueOffset = 0):
        self.label = label
        self.lableFirst = lableFirst
        self.win = win
        self._update_max_yx()
        self.checked = checked
        self.round = round
        self.valueOffset = valueOffset
        win.keypad(1)


    def _update_max_yx(self):
        maxy, maxx = self.win.getmaxyx()
        self.maxy = maxy - 1
        self.maxx = maxx - 1


    def show(self, focus = False):
        try:
            self.win.addstr(0, 0, self.label)

            if focus is True:
                self.win.attron(curses.A_UNDERLINE)
            # self.win.attron(curses.color_pair(4))

            if self.round:
                self.win.addstr(0, self.valueOffset, '(')
            else :
                self.win.addstr(0, self.valueOffset, '[')
            
            if self.checked is True:
                self.win.addch(ord('X'), curses.color_pair(4) |curses.A_BOLD)
            else:
                self.win.addch(ord(' '))

            if self.round:
                self.win.addstr(') ')
            else:
                self.win.addstr('] ')
            
            # self.win.attroff(curses.color_pair(4))
            
            if focus is True:
                self.win.attroff(curses.A_UNDERLINE)

            self.win.move(0, self.valueOffset + 1)

            self.win.refresh()
        except curses.error:
            pass
            # Curses will error on the last line even when it works.
            # https://stackoverflow.com/questions/7063128/last-character-of-a-window-in-python-curses
            # if y == self.max_y - 1:
            #     pass
            # else:
            #     raise

    def display(self, focus = False):
        self.show(focus = False)

    def select(self, checked = None):
        "Edit in the widget window and collect the results."
        
        if checked :
            self.checked = checked

        oldCurs = curses.curs_set(2)
        self.show(focus = True)
        lastcmd = None

        key = None
        while 1:
            ch = self.win.getch()
            lastcmd = ch
            
            if ch in (curses.KEY_UP, \
                        curses.KEY_DOWN, \
                        ord('\t'), \
                        curses.KEY_BTAB, \
                        curses.ascii.ESC, \
                        curses.ascii.LF, \
                        curses.ascii.NL, \
                        curses.KEY_ENTER):
                break

            if curses.ascii.isblank(ch) :
                self.checked = not self.checked
                self.show(focus = True)

        self.show(focus = False)
        curses.curs_set(oldCurs)
        return self.checked, lastcmd


if __name__ == '__main__':
    def test_checkbox(stdscr):
        
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)

        ncols, nlines = 30, 1
        uly, ulx = 15, 20
        stdscr.addstr(uly-2, ulx, "space key for check or unckeck,  key 'q' for quit")
        checkWin1 = curses.newwin(nlines, ncols, uly, ulx)
        checkWin2 = curses.newwin(nlines, ncols, uly + 1, ulx)
        checkWin3 = curses.newwin(nlines, ncols, uly + 2, ulx)

        stdscr.refresh()
        check1 = Checkbox(checkWin1, label = 'test select Item1')
        check2 = Checkbox(checkWin2, label = 'test select Item2')
        check3 = Checkbox(checkWin3, label = 'test select Item3', round = True)
        checked1 = check1.checked = False
        checked2 = check2.checked = True
        checked3 = check3.checked = False

        check1.show()
        check2.show()
        check3.show()

        while True:

            checked1, lastcmd = check1.select(checked1)

            if lastcmd == curses.ascii.ESC:
                break

            checked2, lastcmd = check2.select(checked2)

            if lastcmd == curses.ascii.ESC:
                break

            checked3, lastcmd = check3.select(checked3)

            if lastcmd in (curses.ascii.ESC, \
                        curses.ascii.LF, \
                        curses.ascii.NL, \
                        curses.KEY_ENTER):
                break


        return 

    str = curses.wrapper(test_checkbox)
    print('Contents of text box:', repr(str))

