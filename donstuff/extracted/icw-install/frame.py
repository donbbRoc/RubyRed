import sys,os
import curses
from curses import textpad

import menu
import page

import icwconfig
from icwconfig import _

class Frame(object):

    def __init__(self, app):
        self.app = app

        self.steps = [menu.Item(label=step['name'], value=step) for step in self.app.config['steps']]

    def _getCenterX(self, width, label):
        return max(0, int((width // 2) - (len(label) // 2) - len(label) % 2))

    def _welcomeWin(self):
        bContinue = False
        height, width = self.stdscr.getmaxyx()

        welheight = 15
        welwidth = int(width // 2)
        start_y = int((height - welheight) // 2)
        start_x = int((width - welwidth) // 2)
        
        welcome = self.stdscr.subwin(welheight, welwidth, start_y, start_x)
        welcome.clear()
        welcome.border()

        # Declaration of strings
        title = "iCluster-web installer"[:width-1]
        subtitle = "    © Rocket Software"[:width-1]
        welcomeStr1 = "Press 'Enter' to continue"
        welcomeStr2 = "Press 'ESC' to exit"

        # # Centering calculations
        start_x_title = self._getCenterX(welwidth, title)
        start_x_subtitle = self._getCenterX(welwidth, subtitle)
        # start_y = int((height // 2) - 2)
        
        # Turning on attributes for title
        welcome.attron(curses.color_pair(2))
        welcome.attron(curses.A_BOLD)

        # Rendering title
        welcome.addstr(1, start_x_title, title)

        # Turning off attributes for title
        welcome.attroff(curses.color_pair(2))
        welcome.attroff(curses.A_BOLD)

        # # Print rest of text
        welcome.addstr(2, start_x_subtitle, subtitle)
        welcome.addstr(3, (welwidth // 2) - 2, '-' * 4)
        welcome.addstr(5, self._getCenterX(welwidth, welcomeStr1), welcomeStr1)
        welcome.addstr(6, self._getCenterX(welwidth, welcomeStr2), welcomeStr2)

        welcome.refresh()
        # curses.curs_set(0)

        while True:
            key = self.stdscr.getch()

            if key in [curses.KEY_ENTER, ord('\n')]:
                bContinue = True
                break
            elif key == ord('q'):
                bContinue = False
                break
            elif key == curses.ascii.ESC:
                bContinue = False
                break
            elif key == curses.KEY_RESIZE:
                bContinue = None
                break
        welcome.clear()
        del welcome
        # curses.curs_set(1)
        return bContinue

    def display(self, stdscr):
        self.stdscr = stdscr
        key = 0
        cursor_x = 0
        cursor_y = 0
        company = 'Rocket Software'
        showWelcome = False
        menuWin = None
        position = 0

        curses.curs_set(0)
        # Clear and refresh the screen for a blank canvas
        self.stdscr.clear()
        self.stdscr.refresh()

        # Start colors in curses
        curses.start_color()
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)

        # Loop where key is the last character pressed
        while (key != ord('q')):

            # Initialization
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()

            if height < 33 or width < 138:
                icwconfig.lastWord = _('The minimum size of terminal window is 138*33. \nCurrent terminal window size is {width}*{height}. \nPlease increase the size of the terminal window and run again.').format(width=width, height=height)
                break

            if key == curses.KEY_DOWN:
                cursor_y = cursor_y + 1
            elif key == curses.KEY_UP:
                cursor_y = cursor_y - 1
            elif key == curses.KEY_RIGHT:
                cursor_x = cursor_x + 1
            elif key == curses.KEY_LEFT:
                cursor_x = cursor_x - 1

            cursor_x = max(0, cursor_x)
            cursor_x = min(width-1, cursor_x)

            cursor_y = max(0, cursor_y)
            cursor_y = min(height-1, cursor_y)

            # Declaration of strings
            statusbarstr = 'Esc=exit, Tab=switch focus, Space=select'
            # TODO delete
            keystr = "Last key pressed: {}".format(key)[:width-1]
            if key == 0:
                keystr = "No key press detected..."[:width-1]

            # Centering calculations
            start_y = int((height // 2) - 2)

            # Rendering some text
            whstr = "Width:{} Height:{}".format(width, height)
            # self.stdscr.addstr(0, 0, whstr, curses.color_pair(1))

            self.stdscr.addstr(0, 1, company, curses.color_pair(1))

            # Render status bar
            self.stdscr.attron(curses.color_pair(3))
            self.stdscr.addstr(height-1, 0, statusbarstr)
            self.stdscr.addstr(height-1, len(statusbarstr), f' | {keystr} {" " * (width-len(statusbarstr)-len(keystr)-len(whstr)-5)}{whstr}')
            self.stdscr.attroff(curses.color_pair(3))

            # self.stdscr.move(cursor_y, cursor_x)

            # Refresh the screen
            self.stdscr.refresh()

            if showWelcome is True:
                result = self._welcomeWin()
                if result is True:
                    showWelcome = False
                elif result is False:
                    # exit install programe
                    key = ord('q')
                continue
            else :
                # Begin install guide
                
                ncols, nlines = int(width // 4) + 2, height - 2
                uly, ulx = 2, 0
                # curses.curs_set(0)
                menuWin = menu.Menu(nlines, ncols, self.app.config['label'], self.steps, self.stdscr, True)
                # menuWin.display()
                step = menuWin.select(position)

                if step == curses.ascii.ESC:
                    break
                elif step is not None:
                    pageWin = page.Page(nlines, width - ncols, step, self.stdscr, True)
                    pageWin.display()
                    pageWin.hide()
                
                    position = menuWin.position
                    continue


            # Wait for next input
            key = self.stdscr.getch()


# def main():
#     curses.wrapper(draw_app)

# if __name__ == "__main__":
#     main()


