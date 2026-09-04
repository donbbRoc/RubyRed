

""" yum list installed|grep postgresql12
postgresql12.ppc64         12.2-2      @/postgresql12-12.2-2.ibmi7.2.ppc64
postgresql12-contrib.ppc64 12.2-2      @/postgresql12-contrib-12.2-2.ibmi7.2.ppc64
postgresql12-libpq.ppc64   12.2-2      @/postgresql12-libpq-12.2-2.ibmi7.2.ppc64
postgresql12-server.ppc64  12.2-2      @/postgresql12-server-12.2-2.ibmi7.2.ppc64
"""

import os
import sys
import select
import subprocess
import re
import argparse
from os import path
import time
import glob
from enum import Enum
import shutil

import logging

import socket
import paramiko
from paramiko.py3compat import u

from zipfile import ZipFile
import tarfile

from icwconfig import _
import icwconfig


PGstatus = Enum('PGstatus', {"NotInstalled": 'not installed', "NotRunning": 'not running', "Running": 'running', "Error": 'error'})

class PostgresHelp():
    def __init__(self):
        self.appName = 'postgresql12'
        self.version = '12.2-2'
        self.path = ''
        self.pathData = ''
        self.modules = ['postgresql12', \
                        'postgresql12-contrib', \
                        'postgresql12-libpq', \
                        'postgresql12-server', \
                        'libxslt']

        self.installed = dict()
        self.refreshed = False
        self.running = False
        self.last_installed = None

        self._pgdata = str()
        self._profile = str()
        self._profilePwd = str()
        self._dbUser = str()
        self._logfile = str()
        self._outputWindow = None
        self._server_status = PGstatus.Error
        self._conn = None
        self._zipPath = str()

    @property
    def pgdata(self):
        return self._pgdata

    @pgdata.setter
    def pgdata(self, value):
        self._pgdata = value

    @property
    def zipPath(self):
        return self._zipPath

    @zipPath.setter
    def zipPath(self, value):
        self._zipPath = value

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, value):
        self._profile = value

    @property
    def profilePwd(self):
        return self._profilePwd

    @profilePwd.setter
    def profilePwd(self, value):
        self._profilePwd = value

    @property
    def dbUser(self):
        return self._dbUser

    @dbUser.setter
    def dbUser(self, value):
        self._dbUser = value

    @property
    def outputWindow(self):
        return self._outputWindow

    @outputWindow.setter
    def outputWindow(self, value):
        self._outputWindow = value

    @property
    def logfile(self):
        return self._logfile

    @logfile.setter
    def logfile(self, value):
        self._logfile = value

    def refresh(self):
        self.installed = dict()
        notInstall = list()
        searchStr = '|'.join(item for item in self.modules)
        searchStr = f'rpm -qa|grep -E "{searchStr}"'
        logging.info(f'run cmd: {searchStr}')
        child = subprocess.Popen(searchStr, stdout=subprocess.PIPE, shell=True)
        output = child.communicate()[0]
        logging.info(f'output: {output}')

        # buf = ""
        # for item in output.decode("utf-8").split('\n'):
        #     if len(buf) > 0:
        #         item = f'{buf} {item}'
        #         buf = ''
        #     fields = item.split() 
        #     logging.info(f'fields: {fields}')

        #     if len(fields) == 3:
        #         key = fields[0].split('.')[0]
        #         self.installed[key] = (fields[0], fields[1])
        #     else :
        #         buf = item
        for item in output.decode("utf-8").split('\n'):
            if len(item) > 0:
                pos_cpu =item.rfind('.')
                pos_version2 = item[:pos_cpu].rfind('-')
                pos_version1 = item[:pos_version2].rfind('-')
                app = item[:pos_version1]
                appversion = item[:pos_cpu]
                version = item[pos_version1+1:pos_cpu]
                self.installed[app] = (appversion, version)

        self.refreshed = True
        return len(self.installed)

    def get_installed(self):
        if self.refreshed is False:
            logging.debug(f'refresh get_installed')
            self.refresh()
        return [f'{key}: {value[1]}' for key, value in self.installed.items()]

    def get_miss(self):
        notInstall = list()

        if self.refreshed is False:
            logging.debug(f'refresh get_installed')
            self.refresh()

        for item in self.modules:
            if item not in self.installed:
                notInstall.append(item)
                # print (item + ' not installed')

        return notInstall

    def check_version(self, version = None):

        errVersion = list()

        if version is None:
            version = self.version

        for key, value in self.installed.items():
            # value = (packageName , version)
            if version != value[1]:
                errVersion.append((key, value[1]))
                # print (f'error version {key} {value[1]} expected {version}')

        return errVersion

    def get_pgdata(self):

        # ps -ef | grep "postgres -D "
        pgdata = None
        child = subprocess.Popen('ps -ef | grep "postgres -D " |grep -v grep', stdout=subprocess.PIPE, shell=True)
        output = child.communicate()[0]
        for item in output.decode("utf-8").split('\n'):
            if len(item) > 0:
                if re.match(r".*postgres -D (.*)", item):
                    pgdata = re.match(r".*postgres -D (.*)", item).group(1)
                    self.running = True
                    break

        if pgdata is None:
            child = subprocess.Popen('cat /home/postgres/.profile |grep PGDATA', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            output = child.communicate()[0]
            for item in output.decode("utf-8").split('\n'):
                if len(item) > 0:
                    if re.match(r".*PGDATA=(.*)", item):
                        pgdata = re.match(r".*PGDATA=(.*)", item).group(1)
                        break

        if pgdata is None:
            child = subprocess.Popen('cat /home/postgres/.bashrc |grep PGDATA', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            output = child.communicate()[0]
            for item in output.decode("utf-8").split('\n'):
                if len(item) > 0:
                    if re.match(r".*PGDATA=(.*)", item):
                        pgdata = re.match(r".*PGDATA=(.*)", item).group(1)
                        break
        return ["" if pgdata is None else pgdata]

    def _checkFileExist(self, filePath):
        return True if path.exists(filePath) == True and path.isfile(filePath) == True else False

    def get_status(self):
        pg_ctl = '/QOpenSys/pkgs/bin/pg_ctl'
        pg_isready = '/QOpenSys/pkgs/bin/pg_isready'

        pid = ''
        pgdata = ''
        port = ''
        statusLst = []
        self._server_status = PGstatus.NotInstalled

        pgdata = self.get_pgdata()
        if pgdata is None or len(pgdata) == 0:
            return None
        pgdata = pgdata[0]

        pgdataTmp = '/home/postgres/data' if pgdata == '' else pgdata

        if self._checkFileExist(pg_ctl) == True and self._checkFileExist(pg_isready) == True:
            self._server_status = PGstatus.NotRunning

            # child = subprocess.Popen(f'{pg_ctl} status -D {pgdataTmp}', stdout=subprocess.PIPE, shell=True)
            # output = child.communicate()[0]
            # for item in output.decode("utf-8").split('\n'):
            #     if len(item) > 0:
            #         # pg_ctl: server is running (PID: 3935)
            #         # /QOpenSys/pkgs/lib/postgresql12/bin/postgres "-D" "/home/postgres/data"
            #         # pg_ctl: no server running
            #         match = re.match(r"pg_ctl: server is running \(PID: (\d+)\)", item)
            #         if match:
            #             self._server_status = PGstatus.Running
            #             pid = match.group(1)

            child = subprocess.Popen('ps -ef | grep "postgres -D"', stdout=subprocess.PIPE, shell=True)
            output = child.communicate()[0]
            for item in output.decode("utf-8").split('\n'):
                if len(item) > 0:
                    # pg_ctl: server is running (PID: 3935)
                    # postgres 1586    1   0 02:12:28      -  0:00 /QOpenSys/pkgs/lib/postgresql12/bin/postgres -D /home/postgres/data
                    # match = re.match(r"pg_ctl: server is running \(PID: (\d+)\)", item)
                    match = re.match(r"^postgres +(\d+) +.*bin/postgres -D .*$", item)
                    if match:
                        self._server_status = PGstatus.Running
                        pid = match.group(1)

            child = subprocess.Popen(f'{pg_isready}', stdout=subprocess.PIPE, shell=True)
            output = child.communicate()[0]
            for item in output.decode("utf-8").split('\n'):
                if len(item) > 0:
                    # /tmp:5432 - accepting connections
                    # /tmp:5432 - no response
                    match = re.match(r"/tmp:(\d+) - accepting connections", item)
                    if match:
                        port = match.group(1)

            logging.info(f'get_status() {self._server_status},  pid:{pid}, port:{port}' )
            # print(f'get_status() {self._server_status},  pid:{pid}, port:{port}')

        statusLst.append(    f'status : {self._server_status.value}')
        if len(pgdata) > 0:
            statusLst.append(    f'PGdata : {pgdata}')

        if self._server_status is PGstatus.Running :
            statusLst.append(f'pid    : {pid}')
            statusLst.append(f'port   : {port}')
            logging.info(f'get_status()11 {self._server_status},  pid:{pid}, port:{port}' )

        return statusLst


    def _logEvent(self, msg, outputWin = None, newLine = True):
        logging.info(msg)

        if outputWin:
            outputWin.addstr(msg)
            if newLine:
                outputWin.addstr('\n')
            outputWin.refresh()


    def ButtonPreCheck(self, btn, param = None):
        result = False
        outputWin = None
        if param:
            if param.outputWin:
                outputWin = param.outputWin
                logging.info(f'InstallDB outputwindow {id(outputWin)}')

        if self._server_status == PGstatus.Running:
            btn.label = btn.itemData['nextlabel']
            logging.info(f'btn.label {btn.label}')
            if icwconfig.mode == icwconfig.EModetype.install:
                self._logEvent(_('PostgreSQL is running \nPress [Finish] button and select menu [2. Install services] to continue.'), outputWin)
            else:
                self._logEvent(_('PostgreSQL is running \nPress [Finish] button and select menu [2. Upgrade services] to continue.'), outputWin)
            result = True

        elif self._server_status == PGstatus.NotRunning:
            self._logEvent(_('PostgreSQL is not running \nPress [Next] button to continue initialized database then start PostgreSQL.'), outputWin)
            result = True

        return result


    def _checkExist(self, filePath, isFile = False):
        if os.path.exists(filePath) is True :
            if isFile is True:
                if os.path.isfile(filePath) is False:
                    logging.info(f'filePath is file:  {os.path.isfile(filePath) }')
                    return False
            return True

        logging.info(f'filePath exists: {os.path.exists(filePath)} ')
        return False


    def _expandPath(self, path):
        
        if '~' in path:
            path = os.path.expanduser(path)

        if '$' in path:
            path = os.path.expandvars(path)
        
        return path


    def InstallDB(self, param = None):
        outputWin = None
        if param:
            if param.outputWin:
                outputWin = param.outputWin
                logging.info(f'InstallDB outputwindow {id(outputWin)}')

        missed = self.get_miss()
        packages = " ".join(item + '*ppc64.rpm' for item in missed)
        # logging.info(f'Extract the postgresql rpm package:')
        self._logEvent(_('Extract the postgresql rpm package:'), outputWin)

        if self._server_status == PGstatus.NotInstalled or len(missed) > 0:
            zipPath = param.zipPath
            zipPath = self._expandPath(zipPath)

            servicePath = '/opt/iCluster-web'
            bServicePathExist = self._checkExist(servicePath)

            if self._checkExist(zipPath, isFile = True) is False:
                self._logEvent(_('The "{zipPath}" file to extract does not exist').format(zipPath=zipPath), outputWin)
                return False
                
            with ZipFile(zipPath) as fzip:
                self._logEvent(_('Extract : iCluster_dep.rpm.tar.gz'), outputWin)
                fzip.extractall('/opt/iCluster-web/download', ['iCluster_dep.rpm.tar.gz'])

                with tarfile.open('/opt/iCluster-web/download/iCluster_dep.rpm.tar.gz', mode='r') as tarf:
                    installs = ['./rpm/postgresql12-server-12.2-2.ibmi7.2.ppc64.rpm', 
                    './rpm/postgresql12-libpq-12.2-2.ibmi7.2.ppc64.rpm',
                    './rpm/postgresql12-12.2-2.ibmi7.2.ppc64.rpm',
                    './rpm/postgresql12-contrib-12.2-2.ibmi7.2.ppc64.rpm',
                    './rpm/update-alternatives-1.19.7-1.ibmi7.2.ppc64.rpm',
                    './rpm/libxslt-1.1.29-4.ibmi7.2.ppc64.rpm']

                    for item in installs:
                        self._logEvent(_('Extract : {item}').format(item=item), outputWin)
                        tarf.extract(tarf.getmember(item), path='/opt/iCluster-web/download')

            begin = False
            installed = list()
            if outputWin:
                outputWin.scrollok(1)

            cmds = [
                    f'cd /opt/iCluster-web/download/rpm ',
                    f'/QOpenSys/pkgs/bin/rpm -Uvh --force {packages} ',
                    f'rm *.rpm ',
                    f'cd -',
                    f'echo "###Complete!###"'
                    ]

            child = subprocess.Popen('/QOpenSys/pkgs/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            beginHandle = False
            idx = 0
            while True:
                inList = list()
                if beginHandle is False and idx < len(cmds):
                    inList.append(child.stdin)
                rlist, wlist, elist = select.select([child.stdout], inList, [child.stderr], 3)

                if len(rlist) > 0:
                    line = child.stdout.readline().decode('utf-8')
                    if outputWin:
                        self._logEvent(line, outputWin, newLine = False)
                    
                    if re.match(r".*Complete!.*", line):
                        break
                    if begin is True and len(line) > 0:
                        for item in line.split(' '):
                            if re.match(r".*ppc64", item):
                                installed.append(item)
                    if re.match(r".*Installed:", line):
                        begin = True

                    beginHandle = False
                elif len(elist) > 0:
                    for e in elist:
                        self._logEvent(f'Error : {e}', outputWin)
                elif len(wlist) > 0:
                    if idx >= len(cmds):
                        continue

                    self._logEvent(cmds[idx], outputWin)
                    child.stdin.write(cmds[idx].encode('utf-8'))
                    child.stdin.write("\n".encode('utf-8'))
                    logging.info(cmds[idx])
                    child.stdin.flush() 
                    idx += 1
                    beginHandle = True

                else:
                    beginHandle = False
                    for e in elist:
                        self._logEvent(f'Error : {e}', outputWin)
                        break

            out = child.communicate("\n".encode('utf-8'))[0]
            # outputWin.addstr(out.decode('utf-8'))
            self._logEvent(out.decode('utf-8'), outputWin)

            pg_help.last_installed = installed

            self.refreshed = False
            if bServicePathExist is False:
                shutil.rmtree(servicePath, ignore_errors=False, onerror=None)

            # self._logEvent('End install DB', outputWin)
        else :
            self._logEvent(_('Postgres has been installed\nSkip the installation'), outputWin)

        return True


    def posix_shell(self, chan, cmd, outputWin):
        result = -1
        import select
        try:
            import termios
            import tty

            has_termios = True
        except ImportError:
            has_termios = False

        # stdin, stdout, stderr = client.exec_command('cd ~;/QOpenSys/pkgs/bin/initdb -E UTF-8 -D /home/postgres/data22 -Upostgres -W -A scram-sha-256;which initdb > test223')
        # cmds = ['initdb -E UTF-8 -D /home/postgres/data22 -Upostgres -W -A scram-sha-256; touch 123123; exit\n']
        runed = False

        import unicodedata

        oldtty = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            chan.settimeout(0.0)

            while True:
                r, w, e = select.select([chan, sys.stdin], [], [])
                if chan in r:
                    try:
                        if runed is False:
                            chan.send(cmd)
                            runed = True

                        x = u(chan.recv(1024))
                        
                        if len(x) == 0:
                            break

                        if len(x) > 0:
                            for line in x.splitlines():
                                # outputWin.addstr("".join(ch for ch in line if unicodedata.category(ch)!="Cc"))
                                # logging.info(line)
                                self._logEvent("".join(ch for ch in line if unicodedata.category(ch)!="Cc"), outputWin)

                                if ':' not in line:
                                    # check input prompt
                                    # outputWin.addstr('\n')
                                    self._logEvent('', outputWin)
                                # outputWin.refresh()
                        
                        
                    except socket.timeout:
                        outputWin.refresh()
                        pass
                if sys.stdin in r:
                    x = sys.stdin.read(1)
                    if len(x) == 0:
                        break
                    chan.send(x)

            if chan.exit_status_ready() is True:
                result = chan.recv_exit_status()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

        return result


    def execCommand(self, cmd, timeout = 10, outputWin = None, conn = None):
        chan = None
        if conn is None :
            chan = self._conn.invoke_shell()
        else:
            chan = conn.invoke_shell()

        stdin = chan.makefile('wb')
        stdout = chan.makefile('rb')
        stderr = chan.makefile_stderr('rb')

        self._logEvent(_('Running command : \n{cmd}\n').format(cmd=cmd), outputWin)
        stdin.write(f'{cmd}\nexit 0\n')
        lines = []
        result = None

        for i in range(timeout):
            if chan.exit_status_ready() is True:
                result = chan.recv_exit_status()
                x = u(stdout.read())
                lines = x.splitlines()
                break
            time.sleep(1)

        if result == None:
            if chan.recv_ready() is True:
                x = u(chan.recv(8192))
                lines = x.splitlines()
                result = 0

        chan.close()

        for line in lines:
            self._logEvent(line, outputWin)

        return result, lines


    # def Initdb(pgdata = '/home/postgres/data22', profile = 'postgres', profilePwd = 'postgres', dbUser = 'postgres'):
    def InitDB(self, param = None):
        pgdata = '/home/postgres/data22'
        profile = 'postgres'
        profilePwd = 'postgres'
        dbUser = 'postgres'
        outputWin = None
        result = -1

        logging.debug(f'param.pgdata 1: {param.pgdata}')
        logging.debug(f'param.profile 1: {param.profile}')
        logging.debug(f'param.profilePwd 1: {param.profilePwd}')
        logging.debug(f'param.dbUser 1: {param.dbUser}')
        logging.debug(f'param.outputWin 1: {param.outputWin}')
        
        if param:
            if hasattr(param, 'pgdata'):
                pgdata = param.pgdata
            if hasattr(param, 'profile'):
                profile = param.profile
            if hasattr(param, 'profilePwd'):
                profilePwd = param.profilePwd
            if hasattr(param, 'dbUser'):
                dbUser = param.dbUser
            if hasattr(param, 'outputWin'):
                outputWin = param.outputWin

        installed = list()
        if outputWin:
            outputWin.scrollok(1)

        # Check User Profil POSTGRES Exist else Create User Profil
        child = subprocess.Popen('/QOpenSys/usr/bin/system "DSPUSRPRF USRPRF(POSTGRES)"', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = child.communicate()
        output = output.decode('utf-8').split('\n')
        error = error.decode('utf-8').split('\n')

        notFound = True
        for line in output:
            if line.find('User Profile . . . . . . . . . . . . . . . :   POSTGRES') >= 0:
                notFound = False

        if notFound == True:
            cmds = [
                [f'/QOpenSys/usr/bin/system "CRTUSRPRF USRPRF(POSTGRES) PASSWORD({profilePwd}) PWDEXPITV(*NOMAX)"'],
                'mkdir -p /home/postgres ', 
                'chown POSTGRES /home/postgres ',
                'touch /home/postgres/.profile',
                'echo "exec bash" > /home/postgres/.profile',
                'touch /home/postgres/.bashrc', 
                'echo "export PATH=/QOpenSys/pkgs/bin:$PATH" > /home/postgres/.bashrc',
                f'echo "PGDATA={pgdata}" >> /home/postgres/.bashrc'
                ]
            self._logEvent(_('Create user profile : POSTGRES '), outputWin)
            for cmd in cmds:
                child = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                output, error = child.communicate()
                output = output.decode('utf-8').split('\n')

        try:
            # client = paramiko.SSHClient()
            if self._conn == None:
                self._conn = paramiko.SSHClient()
            # client.load_system_host_keys()
            # give up on verifying host key altogether
            self._conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._conn.banner_timeout = 60
            self._conn.connect('127.0.0.1', 22, profile, profilePwd)

            chan = self._conn.invoke_shell()
            outputWin.refresh()

            result = self.posix_shell(chan, f'LANG="EN_US.UTF-8"; '\
                                        f'LC_ALL="EN_US.UTF-8"; '\
                                        f'PATH=/QOpenSys/pkgs/bin:$PATH; '\
                                        f'PGDATA={pgdata}; '\
                                        f'/QOpenSys/pkgs/bin/initdb -E UTF-8 -D {pgdata} -U{dbUser} -W -A scram-sha-256;'\
                                        f' exit > /dev/null\n', 
                                    outputWin)

            if result != 0:
                if len(glob.glob(pgdata)) > 0:
                    result = 0
                    self._logEvent(_('DB data path :({pgdata}) exists but is not empty.').format(pgdata=pgdata), outputWin)
                # else :
                #     # Failed to initialize database
                #     self._logEvent(f'Failed to initialize database ({pgdata})', outputWin)

            chan.close()
            self.refreshed = False
            logging.debug(f'set refreshed = false')

        except paramiko.ssh_exception.AuthenticationException as e:
            self._logEvent(_('*** Ssh Error: User profile and password do not match \ntry again after modification\n'), outputWin)
            return False

        except Exception as e:
            # print("*** Caught exception: %s: %s" % (e.__class__, e))
            logging.debug("*** Caught exception: %s: %s" % (e.__class__, e))
            # traceback.print_exc()
            try:
                self._conn.close()
                self._conn = None
            except:
                pass
            # sys.exit(1)

        return True if result == 0 else False

    def StartDB(self, param = None):
        pgdata = '/home/postgres/data22'
        profile = 'postgres'
        profilePwd = 'postgres'
        dbUser = 'postgres'
        outputWin = None
        logfile = '/home/postgres/logfile'

        logging.debug(f'param.pgdata 1: {param.pgdata}')
        logging.debug(f'param.profile 1: {param.profile}')
        logging.debug(f'param.profilePwd 1: {param.profilePwd}')
        logging.debug(f'param.dbUser 1: {param.dbUser}')
        logging.debug(f'param.outputWin 1: {param.outputWin}')
        logging.debug(f'param.outputWin 1: {param.logfile}')
        
        if param:
            if hasattr(param, 'pgdata'):
                pgdata = param.pgdata
            if hasattr(param, 'profile'):
                profile = param.profile
            if hasattr(param, 'profilePwd'):
                profilePwd = param.profilePwd
            if hasattr(param, 'dbUser'):
                dbUser = param.dbUser
            if hasattr(param, 'outputWin'):
                outputWin = param.outputWin
            if hasattr(param, 'logfile'):
                logfile = param.logfile

        installed = list()
        if outputWin:
            outputWin.scrollok(1)

        try:
            if self._conn == None:
                self._conn = paramiko.SSHClient()
                self._conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self._conn.banner_timeout = 60
                self._conn.connect('127.0.0.1', 22, profile, profilePwd)

            outputWin.refresh()

            self.execCommand(f'LANG="EN_US.UTF-8"; '\
                                f'LC_ALL="EN_US.UTF-8"; '\
                                f'PATH=/QOpenSys/pkgs/bin:$PATH; '\
                                f'cd /home/postgres;'\
                                f'/QOpensys/pkgs/bin/pg_ctl -D {pgdata} -l {logfile} start;'\
                                f' exit > /dev/null\n', 
                            timeout = 10, outputWin = outputWin
                            )

            self.refreshed = False
            logging.debug(f'set refreshed = false')

        except Exception as e:
            print("*** Caught exception: %s: %s" % (e.__class__, e))
            # traceback.print_exc()
            try:
                self._conn.close()
                self._conn = None
            except:
                pass
            # sys.exit(1)
        return True

pg_help = PostgresHelp()

def is_running():
    return pg_help.get_status()

# def version():
#     if pg_help.refreshed is False:
#         pg_help.refresh()
#     return pg_help.check_version()

# def miss():
#     if pg_help.refreshed is False:
#         pg_help.refresh()
#     return pg_help.miss()

# def pg_data():
#     if pg_help.refreshed is False:
#         pg_help.refresh()
#     return [pg_help.get_pgdata()]

# def check_result():
#     if len(pg_help.get_pgdata()) > 0 and \
#     len(pg_help.installed.items()) > 0 and \
#     len(pg_help.miss()) == 0:
#         return True
#     else :
#         return False


def GetModel():
    return pg_help



def get_last_installed():
    return pg_help.last_installed

def main():
    # res = InstallDB()
    # print(res)
    # return 

    # print(pg_data())
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd")
    args = parser.parse_args()
    
    
    pg_help = PostgresHelp()
    pg_help.refresh()
    
    if args.cmd == "installed":
        for key, value in pg_help.installed.items():
            print(f'  {key}: {value[1]}')

    elif args.cmd == "version":
        errVersion = pg_help.check_version()
        # print("error version :")
        for item in errVersion:
            print(f'  {item[0]}: {item[1]}')

    elif args.cmd == "miss":
        for item in pg_help.miss():
            print(f'  {item}')

    elif args.cmd == "pg_data":
        pg_data = pg_help.get_pgdata()
        print(pg_data)
        
    elif args.cmd == "get_status":
        status = pg_help.get_status()
        print(status)
        

    else:
        for key, value in pg_help.installed.items():
            print(f'  {key}: {value[1]}')

        errVersion = pg_help.check_version()
        print("error version :")
        for item in errVersion:
            print(f'  {item[0]}: {item[1]}')

        print("missing install :")
        for item in pg_help.miss():
            print(f'  {item}')

        pg_data = pg_help.get_pgdata()
        print("pg_data :" + pg_data)

    # print(check_result())



if __name__ == '__main__':
    main()
    # Initdb()

    # notInstall = pg_help.check_installed()
    # print("Installed:")
    # for key, value in pg_help.installed.items():
    #     print(f'  {key}: {value[1]}')

    # print("notInstall:")
    # for item in notInstall:
    #     print(f'  {item}')

    

    # errVersion = pg_help.check_version()
    # print("error version :")
    # for item in errVersion:
    #     print(f'  {item[0]}: {item[1]}')

    # pg_data = pg_help.get_pgdata()
    # print("pg_data :" + pg_data)
