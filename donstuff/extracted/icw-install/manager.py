#!/QOpenSys/pkgs/bin/python

import sys
import types
import tarfile
import datetime
sys.path.append('./tools')
from server_model import ServerModel
from agent_model import AgentModel
from tools.profile import CSVProfile

class OutputWin:
    def __init__(self, logfile):
        self.fn = open(logfile, 'a+')

    def addstr(self, str):
        print(str, file = self.fn, end='')

    def refresh(self):
        self.fn.flush()

    def scrollok(self, num):
        pass

def RestartServer(param, del80 = False):
    print('RestartServer()')
    serverM = ServerModel()

    try:
        serverM._envProfile = CSVProfile()
        serverM._envProfile.read_properties('/opt/iCluster-web/.env')
        serverM.servicePath = '/opt/iCluster-web'
        serverM.del80 = del80
        serverM.runAllJar(param)
    except Exception as e:
        param.outputWin.addstr(f"*** Caught exception: {e.__class__}: {e}")
        param.outputWin.refresh()


def RestartAgent(param):
    ag = AgentModel()
    ag.restartAgent(param)


def main():
    param = types.SimpleNamespace()
    param.outputWin = OutputWin('/opt/iCluster-web/ctl.log')

    param.outputWin.addstr('\n' + str(datetime.datetime.now()) + '\n')
    argvCpy = list()
    replace = False
    repIndex = -1

    # Replace pwd with *******
    if sys.argv[1] == 'pg':
        replace = True
        repIndex = 3
    elif sys.argv[1] == 'agent':
        replace = True
        repIndex = 4

    idx = 1
    for item in sys.argv[1:]:
        if replace is True and idx == repIndex:
            item = '******'
        argvCpy.append(item)
        idx += 1

    param.outputWin.addstr('ctl.py ' + ' '.join(argvCpy))
    param.outputWin.refresh()

    import argparse
    parser = argparse.ArgumentParser(prog='ctl.py', description='Start the iCluster-web services tool')
    subparsers = parser.add_subparsers(help='sub-command help', dest='CMD')

    # servers
    parser_srv = subparsers.add_parser('servers', help='Start servers')
    parser_srv.add_argument('--del80', help='Disable port 80, which is enabled by default in nginx', action="store_true")

    # agent
    parser_ag = subparsers.add_parser('agent', help='Start remote agent')
    parser_ag.add_argument('ip', type=str, help='agent IP address')
    parser_ag.add_argument('profile', type=str, help='agent ssh profile')
    parser_ag.add_argument('password', type=str, help='agent ssh password')
    parser_ag.add_argument('port', nargs='?', default = 22, type=int, help='agent ssh port')

    args = parser.parse_args()

    if args.CMD == 'servers':
        print('Begin restart servers')
        RestartServer(param, args.del80)

    elif args.CMD == 'agent':
        param.agentIp = args.ip
        param.agentPort = args.port
        param.pUser = args.profile
        param.pPwd = args.password
        print('Begin restart agent')
        RestartAgent(param)

    else :
        parser.print_help()

    return

if __name__ == '__main__':
    main()
