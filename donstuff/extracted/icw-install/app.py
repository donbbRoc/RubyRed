import os
from os import path
import logging
import json
import curses
import argparse

from frame import Frame
import icwconfig

class App(object):

    def __init__(self, mode = 'install'):
        self.path = './icw-'+ mode +'.json'
        self.config = None

    def load(self):
        print(self.path)
        if path.exists(self.path) is False:
            raise FileExistsError
        
        if path.isfile(self.path) is False:
            raise FileExistsError

        with open(self.path, encoding="utf-8") as f:
            self.config = json.load(f)


def main():
    # logging.debug('This message should go to the log file')
    # logging.info('So should this')
    # logging.warning('And this, too')
    # logging.error('And non-ASCII stuff, too, like Øresund and Malmö')

    varLog = '/QOpenSys/var/log/'
    if path.exists(varLog) is False:
        print(f'{varLog} Path Not Exists Error')
        raise FileExistsError
    logFile = os.path.join(varLog, 'iCluster-web-install.log')

    logging.basicConfig(filename=logFile,
                        filemode='a',
                        # format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        format='%(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG) # DEBUG
                        


    logging.debug(f'prodtype1111111111111111111  {icwconfig.prodtype}')

    app = App(str(icwconfig.mode.name))
    app.load()

    frame = Frame(app)
    curses.wrapper(frame.display)

    # if len(icwconfig.lastWord) > 0:
    print(icwconfig.lastWord)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('install', nargs='?', choices=['install', 'upgrade'], default='install', type=str)
    parser.add_argument('debug', nargs='?', const='prod', type=str)
    args = parser.parse_args()

    print('args.install :' + args.install)

    if args.install == 'install' :
        icwconfig.mode = icwconfig.EModetype.install
    elif args.install == 'upgrade' :
        icwconfig.mode = icwconfig.EModetype.upgrade
    else:
        raise ValueError('')

    if args.debug == 'debug':
        icwconfig.prodtype = icwconfig.EProdtype.debug
        print('debug')
    else:
        icwconfig.prodtype = icwconfig.EProdtype.prod
        print('prod')


    if os.environ["PATH"].find('/QOpenSys/pkgs/bin') < 0:
        os.environ["PATH"] = "/QOpenSys/pkgs/bin:" + os.environ["PATH"]
    main()
