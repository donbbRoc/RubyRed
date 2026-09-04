import collections
import curses
import re
from curses import textpad

from curses import panel


Item = collections.namedtuple('Item', field_names=('label', 'value'))


class Menu(object):

    def __init__(self, nlines, ncols, title, items, parentScr, border):

        self.window = parentScr.subwin(nlines, ncols, 1, 1)
        self.window.timeout(5000)
        self.window.keypad(1)
        self.panel = panel.new_panel(self.window)
        self.panel.hide()
        panel.update_panels()

        self.title = title
        self.border = border
        self.position = 0

        if type(items) is list :
            if type(items[0]) is Item:
                self.items = items
            else:
                self.items = [Item(label=name, value=name) for name in items]
        else :
            raise TypeError

        self.offset_x = 0
        self.offset_y = 0


    def _draw_border(self):
        if self.border is True:
            self.window.border()
            if self.offset_x == 0:
                self.offset_x = 2
            if self.offset_y == 0:
                self.offset_y = 2

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


    def navigate(self, n):
        self.position += n
        if self.position < 0:
            self.position = len(self.items) - 1
        elif self.position >= len(self.items):
            self.position = 0


    def hide(self):
        self.panel.hide()
        self.window.clear()
        self.window.refresh()


    def display(self):

        self.panel.top()
        self.panel.show()
        self.window.clear()

        curses.doupdate()

        self._draw_border()
        offset_top = self.offset_y
        offset_bottom =  self.offset_y

        self.max_y, self.max_x = self.window.getmaxyx()

        # Display the menu title.
        if self.title:
            self.addline(offset_top, self.title, curses.A_REVERSE)
            self.addline(offset_top + 1, '-' * len(self.title), curses.A_NORMAL)
            offset_top += 2

        window_height = max(self.max_y - offset_top - offset_bottom, 0)

        if self.position < window_height:
            window = (0, window_height - 1)
        else:
            window = (self.position - (window_height - 1), self.position)

        row = 0

        for index, item in enumerate(self.items):

            if index < window[0] or index > window[1]:
                continue

            # Highlight the selected item.
            if index == self.position:
                mode = curses.A_REVERSE
            else:
                mode = curses.A_NORMAL

            # Display the item.
            self.addline(
                offset_top + row,
                item.label,
                mode,
            )

            row += 1

        # Blank bottom lines if screen was resized
        for y in range(offset_bottom - 1):
            self.addline(
                self.max_y - ( y + 1) - 1,
                ' ',
                curses.A_NORMAL,
            )

        self.window.refresh()

    def select(self, index = None):

        self.panel.top()
        self.panel.show()

        while True:
            self.display()

            # Because window.timeout was called,
            # this returns -1 if nothing was pressed.

            if index is None:
                key = self.window.getch()

                if key in [curses.KEY_ENTER, ord('\n')]:
                    return self.items[self.position].value
                elif key == curses.KEY_UP:
                    self.navigate(-1)
                elif key == curses.KEY_DOWN:
                    self.navigate(1)
                elif key in (ord('q'), ord('Q')):
                    raise KeyboardInterrupt
                elif key == curses.ascii.ESC:
                    return key

            else :
                self.position = index
                index = None


        # self.window.clear()
        # self.panel.hide()
        # panel.update_panels()
        # curses.doupdate()

