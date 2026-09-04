import os
import sys
import subprocess
import time
import select
import re
import csv
import socket
from os import walk

import paramiko
from paramiko.py3compat import u

# from os import path
from zipfile import ZipFile
import tarfile

import logging
import shutil
import tempfile
from string import Template

from tools.profile import CSVProfile
from icwconfig import _
import icwconfig

class AgentModel():
    def __init__(self):
        self.agentFileList= []
        self._envProfile = None
        self._outputWindow = None
        self._conn = None

        self._zipPath = str()

        self._pUser = str()
        self._pPwd = str()

        self._agentIp = str()
        self._agentPort = str()
        self._workPath = tempfile.mkdtemp()

    def __del__(self):
        shutil.rmtree(self._workPath)


    @property
    def outputWindow(self):
        return self._outputWindow

    @outputWindow.setter
    def outputWindow(self, value):
        self._outputWindow = value


    @property
    def zipPath(self):
        return self._zipPath

    @zipPath.setter
    def zipPath(self, value):
        self._zipPath = value

    @property
    def pUser(self):
        return self._pUser

    @pUser.setter
    def pUser(self, value):
        self._pUser = value

    @property
    def pPwd(self):
        return self._pPwd

    @pPwd.setter
    def pPwd(self, value):
        self._pPwd = value

    @property
    def agentIp(self):
        return self._agentIp

    @agentIp.setter
    def agentIp(self, value):
        self._agentIp = value
        self._envProfile.profiles['NODE_HOSTNAME'] = value
        self._envProfile.profiles['GUIAGENT_HOSTNAME'] = value
        self._envProfile.profiles['GUIAGENT_PORT'] = '4545'

    @property
    def agentPort(self):
        return self._agentPort

    @agentPort.setter
    def agentPort(self, value):
        self._agentPort = value
    
    # --- .env File profile--------------------------------------------------------
    @property
    def REGISTRY_IP(self):
        return self._envProfile.profiles['REGISTRY_IP'] if self._envProfile else None

    @REGISTRY_IP.setter
    def REGISTRY_IP(self, value):
        if self._envProfile:
            self._envProfile.profiles['REGISTRY_IP'] = value

    @property
    def REGISTRY_PORT(self):
        return self._envProfile.profiles['REGISTRY_PORT'] if self._envProfile else None

    @REGISTRY_PORT.setter
    def REGISTRY_PORT(self, value):
        if self._envProfile:
            self._envProfile.profiles['REGISTRY_PORT'] = value

    @property
    def NODE_HOSTNAME(self):
        return self._envProfile.profiles['NODE_HOSTNAME'] if self._envProfile else None

    @NODE_HOSTNAME.setter
    def NODE_HOSTNAME(self, value):
        if self._envProfile:
            self._envProfile.profiles['NODE_HOSTNAME'] = value
            
    @property
    def NODE_USERNAME(self):
        return self._envProfile.profiles['NODE_USERNAME'] if self._envProfile else None

    @NODE_USERNAME.setter
    def NODE_USERNAME(self, value):
        if self._envProfile:
            self._envProfile.profiles['NODE_USERNAME'] = value

    @property
    def NODE_PASSWORD(self):
        return self._envProfile.profiles['NODE_PASSWORD'] if self._envProfile else None

    @NODE_PASSWORD.setter
    def NODE_PASSWORD(self, value):
        if self._envProfile:
            self._envProfile.profiles['NODE_PASSWORD'] = value

    @property
    def AGENT_PORT(self):
        return self._envProfile.profiles['AGENT_PORT'] if self._envProfile and 'AGENT_PORT' in self._envProfile.profiles else 8086

    @AGENT_PORT.setter
    def AGENT_PORT(self, value):
        if self._envProfile:
            self._envProfile.profiles['AGENT_PORT'] = value

    @property
    def GRPC_PORT(self):
        return self._envProfile.profiles['GRPC_PORT'] if self._envProfile and 'GRPC_PORT' in self._envProfile.profiles else 9090

    @GRPC_PORT.setter
    def GRPC_PORT(self, value):
        if self._envProfile:
            self._envProfile.profiles['GRPC_PORT'] = value

    @property
    def GUIAGENT_HOSTNAME(self):
        return self._envProfile.profiles['GUIAGENT_HOSTNAME'] if self._envProfile else None

    @GUIAGENT_HOSTNAME.setter
    def GUIAGENT_HOSTNAME(self, value):
        if self._envProfile:
            self._envProfile.profiles['GUIAGENT_HOSTNAME'] = value

    @property
    def GUIAGENT_PORT(self):
        return self._envProfile.profiles['GUIAGENT_PORT'] if self._envProfile else None

    @GUIAGENT_PORT.setter
    def GUIAGENT_PORT(self, value):
        if self._envProfile:
            self._envProfile.profiles['GUIAGENT_PORT'] = value


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

    def _logEvent(self, msg, outputWin = None, newLine = True):
        logging.info(msg)

        if outputWin:
            outputWin.addstr(msg)
            if newLine:
                outputWin.addstr('\n')
            outputWin.refresh()


    def execCommand(self, cmd, timeout = 10, outputWin = None, conn = None):
        chan = None
        if conn is None :
            chan = self._conn.invoke_shell()
        else:
            chan = conn.invoke_shell()

        stdin = chan.makefile('wb')
        stdout = chan.makefile('rb')
        stderr = chan.makefile_stderr('rb')

        self._logEvent(_('Running command in {agentIp}: \n{cmd}\n').format(agentIp=self.agentIp, cmd=cmd), outputWin)
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

        return result, lines


    def saveProfile(self, param):
        if not param :
            return False

        outputWin = param.outputWin

        # if icwconfig.mode == icwconfig.EModetype.install:
        self._envProfile.write_properties(os.path.join(self._workPath, 'iCluster-agent/.env'))

        #TODO Replace variables from the .env
        agentPath = os.path.join(self._workPath, 'iCluster-agent')

        # Maybe the HOST don't have gettext tool(envsubst), so do not use this func.
        # subprocess.run([". export-env.sh;\
        # mkdir -p BOOT-INF/classes/config/;\
        # envsubst '$REGISTRY_IP,$NODE_HOSTNAME,$NODE_USERNAME,$NODE_PASSWORD,$GUIAGENT_HOSTNAME,$GUIAGENT_PORT'\
        # <application-prod.yml.template\
        # >BOOT-INF/classes/config/application-prod.yml"], 
        # stdout=open(os.devnull, 'w'), cwd=agentPath, shell=True)
        # Replace variables from the .env
        fn = open(os.path.join(agentPath, 'application-prod.yml.template'))
        appDataTemp = fn.read()
        fn.close()
        template = Template(appDataTemp)
        appData = template.safe_substitute(self._envProfile.profiles)
        os.makedirs(os.path.join(agentPath, 'BOOT-INF/classes/config/'), exist_ok=True)
        fnData = open(os.path.join(agentPath, 'BOOT-INF/classes/config/application-prod.yml'), 'w')
        fnData.write(appData)
        fnData.close()

        #Jar Update yml configuration
        subprocess.run(['/QOpenSys/QIBM/ProdData/JavaVM/jdk80/64bit/bin/jar uf agent-1.0.jar BOOT-INF/classes/config/application-prod.yml'], stdout=open(os.devnull, 'w'), cwd=agentPath, shell=True)

        subprocess.run(['rm -f application-prod.yml.template'], 
        stdout=open(os.devnull, 'w'), cwd=agentPath, shell=True)

        #TODO remove passwd from the _envProfile
        del self._envProfile.profiles['NODE_PASSWORD']
        del self._envProfile.profiles['NODE_USERNAME']

        #TODO save _envProfile to .env
        if icwconfig.mode == icwconfig.EModetype.install:
            self._envProfile.write_properties(os.path.join(self._workPath, 'iCluster-agent/.env'))

        if not self._conn:
            self._logEvent(_('The connection does not exist, please reconnect '), outputWin)
            return False

        if len(self.agentFileList) == 0:
            self._logEvent(_('The unzip file was not found, please unzip it again'), outputWin)
            return False

        self._logEvent(_('Begin uploading agent files'), outputWin)
        curLib = None

        try:
            sftp = self._conn.open_sftp()
            targetPath = '/opt'

            if icwconfig.mode == icwconfig.EModetype.upgrade:
                try:
                    sftp.get(os.path.join(targetPath, 'iCluster-agent', '.env'), os.path.join(self._workPath, 'iCluster-agent/.env'))
                    envProfile = CSVProfile()
                    envProfile.read_properties(os.path.join(self._workPath, 'iCluster-agent/.env'))
                    envProfile.profiles['REGISTRY_IP'] = self._envProfile.profiles['REGISTRY_IP']
                    envProfile.profiles['REGISTRY_PORT'] = self._envProfile.profiles['REGISTRY_PORT']
                    envProfile.profiles['AGENT_PORT'] = self._envProfile.profiles['AGENT_PORT']
                    envProfile.profiles['GRPC_PORT'] = self._envProfile.profiles['GRPC_PORT']
                    envProfile.write_properties(os.path.join(self._workPath, 'iCluster-agent/.env'))
                except FileNotFoundError:
                    self._logEvent(_('The .env file does not exist on agent node'), outputWin)
                    sftp.close()
                    return False

            try:
                sftp.lstat(targetPath)
            except FileNotFoundError:
                sftp.mkdir(targetPath)  # Create remote_path

            try:
                sftp.lstat(os.path.join(targetPath, 'iCluster-agent'))
            except FileNotFoundError:
                sftp.mkdir(os.path.join(targetPath, 'iCluster-agent'))  # Create remote_path

            try:
                sftp.lstat(os.path.join(targetPath, 'iCluster-agent', 'application.yml'))
                sftp.remove(os.path.join(targetPath, 'iCluster-agent', 'application.yml'))
            except FileNotFoundError:
                pass

            try:
                sftp.remove(os.path.join(targetPath, 'iCluster-agent', 'application-prod.yml'))
            except FileNotFoundError:
                pass

            for filePath in self.agentFileList:
                fileObj = os.path.join(self._workPath, filePath)
                targetfile = os.path.join(targetPath, filePath)

                self._logEvent(_('Upload agent files {filePath} to {targetfile}').format(filePath=filePath, targetfile=targetfile), outputWin)
                sftp.put(fileObj, targetfile)

            # TODO do patch /Port changeable
            cwd = os.getcwd()
            patchPath = os.path.join(cwd, 'patch')
            # if self._checkExist(patchPath) == True:

                # # Port changeable
                # start = os.path.join(patchPath, 'start_agent.sh')
                # if self._checkExist(start) == True:
                #     targetfile = os.path.join(targetPath, 'iCluster-agent/start.sh')
                #     sftp.put(start, targetfile)

            self._logEvent('File upload completed.\n', outputWin)
            sftp.close()
            result, lines = self.execCommand('uname -a | awk \'{print "V"$4"R"$3}\'', outputWin = outputWin)
            ibmi_version = None
            for line in lines:
                match = re.search(r'V\d+R\d+', line)
                if match:
                    ibmi_version = match.group(0)
                    break

            if ibmi_version:
                self._logEvent(_('IBMI version is {version}').format(version=ibmi_version), outputWin)
                if ibmi_version.upper() == 'V7R6':
                    self._logEvent(_('Detected V7R6, running OS specific commands...'), outputWin)
                    result, lines = self.execCommand(f'/QOpenSys/usr/bin/system "DSPUSRPRF USRPRF({self.curConnUser})"', outputWin = outputWin)
                    for item in lines:
                        if re.match(r" *Current library  [\. ]+: +(.*)", item):
                            curLib = re.match(r" *Current library  [\. ]+: +(.*)", item).group(1)
                            break
                    if curLib is not None:
                        result, lines = self.execCommand(f'/QOpenSys/usr/bin/system "CHGUSRPRF USRPRF({self.curConnUser}) CURLIB(ICLUSTER)"', timeout = 10, outputWin = outputWin)
                        result, lines = self.execCommand('''/QOpenSys/usr/bin/system "DMADDUSR USER(QUSER_NC) AUTH(*ADMIN) DESC('iC Web User NC profile') PASSWORD(*)"''', timeout = 10, outputWin = outputWin)
                    else:
                        self._logEvent(_('Please manually execute the following command: '), outputWin)
                        self._logEvent("  DMADDUSR USER(QUSER_NC) AUTH(*ADMIN) DESC('iC Web User NC profile') PASSWORD(*)", outputWin)
                        
            else:
                self._logEvent(_('Could not determine IBMI version'), outputWin)
                
            
            if icwconfig.mode == icwconfig.EModetype.install:
                self.execCommand('''system "CRTUSRPRF USRPRF(ICA) PASSWORD(*NONE) PWDEXP(*NO) USRCLS(*USER) CURLIB(ICLUSTER) TEXT('iCluster User Profile')"''', outputWin = outputWin)
                self.execCommand('''system "CHGUSRPRF USRPRF(ICA) STATUS(*ENABLED)"''', outputWin = outputWin)

                result, lines = self.execCommand(f'/QOpenSys/usr/bin/system "DSPUSRPRF USRPRF({self.curConnUser})"', outputWin = outputWin)
                for item in lines:
                    if re.match(r" *Current library  [\. ]+: +(.*)", item):
                        curLib = re.match(r" *Current library  [\. ]+: +(.*)", item).group(1)
                        break

                if curLib is not None:
                    result, lines = self.execCommand(f'/QOpenSys/usr/bin/system "CHGUSRPRF USRPRF({self.curConnUser}) CURLIB(ICLUSTER)"', timeout = 10, outputWin = outputWin)
                    result, lines = self.execCommand('''/QOpenSys/usr/bin/system "DMADDUSR USER(QUSER) AUTH(*ADMIN) DESC('iC Web User') PASSWORD(*)"''', timeout = 10, outputWin = outputWin)
                    result, lines = self.execCommand('''/QOpenSys/usr/bin/system "DMADDUSR USER(ICA) AUTH(*ADMIN) DESC('iC Web User') PASSWORD(ica)"''', timeout = 10, outputWin = outputWin)

                    
                    result, lines = self.execCommand('''/QOpenSys/usr/bin/system "RUNSQL SQL('create or replace function icluster/evntsevlvl(msgid char(8), msgtext varchar(10500)) returns char(10) language c external name ''ICLUSTER/EVNTFUNCS(evntsevlvl)'' deterministic no sql no external action parameter style DB2SQL DISALLOW PARALLEL') COMMIT(*NONE)"''', timeout = 15, outputWin = outputWin)
                    result, lines = self.execCommand('''/QOpenSys/usr/bin/system "RUNSQL SQL('create or replace function icluster/evntmsgtext(msgid char(8), msgtext varchar(10500)) returns char(200) language c external name ''ICLUSTER/EVNTFUNCS(evntmsgtext)'' deterministic no sql no external action parameter style DB2SQL DISALLOW PARALLEL') COMMIT(*NONE)"''', timeout = 15, outputWin = outputWin)
                    result, lines = self.execCommand('''/QOpenSys/usr/bin/system "RUNSQL SQL('create or replace function icluster/evntseclvl(msgid char(8), msgtext varchar(10500)) returns char(20000) language c external name ''ICLUSTER/EVNTFUNCS(evntseclvl)'' deterministic no sql no external action parameter style DB2SQL DISALLOW PARALLEL') COMMIT(*NONE)"''', timeout = 15, outputWin = outputWin)
                    
                    result, lines = self.execCommand(f'/QOpenSys/usr/bin/system "CHGUSRPRF USRPRF({self.curConnUser}) CURLIB({curLib})"', timeout = 5, outputWin = outputWin)
                else :
                    self._logEvent(_('Please manually execute the following command: '), outputWin)
                    self._logEvent("  DMADDUSR USER(QUSER) AUTH(*ADMIN) DESC('iC Web User') PASSWORD(*)", outputWin)
                    self._logEvent("  DMADDUSR USER(ICA) AUTH(*ADMIN) DESC('iC Web User') PASSWORD(ICA)", outputWin)
                    

                self.execCommand('''system "CHGUSRPRF USRPRF(ICA) STATUS(*DISABLED)"''', outputWin = outputWin)

            # clean all old agent job
            self.execCommand('cd /opt/iCluster-agent/;/QOpenSys/pkgs/bin/bash stop.sh', outputWin = outputWin)
            self.execCommand('cd /opt/iCluster-agent/;/QOpenSys/pkgs/bin/bash start.sh;sleep 10', outputWin = outputWin)

        except Exception as e:
            if curLib is not None:
                result, lines = self.execCommand(f'/QOpenSys/usr/bin/system "CHGUSRPRF USRPRF({self.curConnUser}) CURLIB({curLib})"', timeout = 10, outputWin = outputWin)
            # print("*** Caught exception: %s: %s" % (e.__class__, e))
            logging.debug("*** Caught exception: %s: %s" % (e.__class__, e))
            # traceback.print_exc()
            try:
                self._conn.close()
                self._conn = None
            except:
                return False

        return True

    def restartAgent(self, param = None):
        if not param :
            return False
        outputWin = param.outputWin

        if self.connectAgent(param) is False:
            return False

        try:
            # clean all old agent job
            self.execCommand('cd /opt/iCluster-agent/;/QOpenSys/pkgs/bin/bash stop.sh', outputWin = outputWin)
            self.execCommand('cd /opt/iCluster-agent/;/QOpenSys/pkgs/bin/bash start.sh;sleep 10', outputWin = outputWin)
        except Exception as e:
            logging.debug("*** Caught exception: %s: %s" % (e.__class__, e))
            outputWin.addstr("*** Restart agent Error: %s: %s\n" % (e.__class__, e))


    def connectAgent(self, param = None):
        # self._conn
        if not param :
            return False

        outputWin = param.outputWin
        agentIp = param.agentIp
        agentPort = param.agentPort
        pUser = param.pUser
        pPwd = param.pPwd

        self._logEvent(_('\nBegin connecting to Agent host {pUser}@{agentIp}:{agentPort} ').format(pUser=pUser, agentIp=agentIp, agentPort=agentPort), outputWin)

        try:
            if self._conn:
                del self._conn

            tmpconn = paramiko.SSHClient()
            tmpconn.banner_timeout = 60
            # give up on verifying host key altogether
            tmpconn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            tmpconn.connect(agentIp, int(agentPort), pUser, pPwd, timeout=10)

            sftp = tmpconn.open_sftp()
            targetPath = '/opt'

            try:
                sftp.lstat(targetPath)
            except FileNotFoundError:
                sftp.mkdir(targetPath)  # Create remote_path

            targetPath = os.path.join(targetPath, 'tmp_rpm_agent')
            try:
                sftp.lstat(targetPath)
            except FileNotFoundError:
                sftp.mkdir(targetPath)  # Create remote_path

            cwd = os.getcwd()
            rpm_agent_path = os.path.join(cwd, 'rpm_agent')
            fileList = list()
            for (dirpath, dirnames, filenames) in walk(rpm_agent_path):
                if dirpath != rpm_agent_path:
                    # Donot search sub folders
                    continue
                for filename in filenames:
                    fileList.append(filename)

            for filePath in fileList:
                fileObj = os.path.join(rpm_agent_path, filePath)
                targetfile = os.path.join(targetPath, filePath)

                self._logEvent(_('Upload agent files {filePath} to {targetfile}').format(filePath=filePath, targetfile=targetfile), outputWin)
                sftp.put(fileObj, targetfile)
            sftp.close()

            self._logEvent(_('Connection succeeded.'), outputWin)
            self.execCommand(f'PATH=/QOpenSys/pkgs/bin:$PATH;export PATH; cd {targetPath}; /QOpenSys/pkgs/bin/rpm -Uvh --force libutil2-*.ppc64.rpm 2>&1 >>log; cd -', outputWin = outputWin, conn = tmpconn)
            self.execCommand(f'PATH=/QOpenSys/pkgs/bin:$PATH;export PATH; cd {targetPath}; /QOpenSys/pkgs/bin/rpm -Uvh --force chsh-*.ppc64.rpm 2>&1 >>log; cd -', outputWin = outputWin, conn = tmpconn)
            self.execCommand(f'PATH=/QOpenSys/pkgs/bin:$PATH;export PATH; cd {targetPath}; /QOpenSys/pkgs/bin/rpm -Uvh --force bash-*.ppc64.rpm 2>&1 >>log; cd -', outputWin = outputWin, conn = tmpconn)
            self.execCommand(f'/QOpenSys/pkgs/bin/chsh -s /QOpenSys/pkgs/bin/bash 2>&1 >>{targetPath}/log; rm -rf {targetPath}', outputWin = outputWin, conn = tmpconn)
            tmpconn.close()

            self._conn = paramiko.SSHClient()
            self._conn.banner_timeout = 60
            self._conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._conn.connect(agentIp, int(agentPort), pUser, pPwd, timeout=10)

            self.curConnUser = pUser
            # self.NODE_PASSWORD = pPwd

        except paramiko.ssh_exception.AuthenticationException as e:
            logging.debug("*** SSH Error: %s: %s" % (e.__class__, e))

            # outputWin.addstr("*** Ssh Error: %s: %s\n" % (e.__class__, e))
            self._logEvent(_('*** Ssh Error: User profile and password do not match \ntry again after modification\n'), outputWin)
            outputWin.refresh()
            self._logEvent(_('Connection failed.'), outputWin)
            return False
        except paramiko.ssh_exception.BadHostKeyException as e:
            logging.debug("*** Ssh Error: %s: %s" % (e.__class__, e))

            outputWin.addstr("*** Ssh Error: %s: %s\n" % (e.__class__, e))
            outputWin.addstr("*** Ssh Error: Error Host\n" )
            outputWin.refresh()
            self._logEvent(_('Connection failed.'), outputWin)
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
            self._logEvent(_('Connection failed.'), outputWin)
            return False

        return True



    def unpackZipFile(self, param = None):
        zipPath = param.zipPath

        hostIP = '127.0.0.1'
        hostPort = 22
        profile = 'CLIU'
        profilePwd = 'CLIU'
        
        outputWin = None
        if param:
            if param.outputWin:
                outputWin = param.outputWin
                logging.info(f'unpackZipFile outputwindow {id(outputWin)}')

        zipPath = self._expandPath(zipPath)

        # clean work path
        if os.path.exists(self._workPath):
            shutil.rmtree(self._workPath)

        upgradeList = [
            './iCluster-agent', 
            './iCluster-agent/application-prod.yml.template', 
            './iCluster-agent/agent-1.0.jar', 
            './iCluster-agent/.env', 
            './iCluster-agent/start.sh', 
            './iCluster-agent/status.sh',
            './iCluster-agent/stop.sh',
            './iCluster-agent/export-env.sh']

        with ZipFile(zipPath) as fzip:
            fzip.extractall(self._workPath, ['iCluster-agent.tar.gz'])
            with tarfile.open(os.path.join(self._workPath, 'iCluster-agent.tar.gz'), mode='r') as tarf:
                members = tarf.getmembers()
                for item in members:
                    if icwconfig.mode == icwconfig.EModetype.upgrade:
                        if item.name not in upgradeList:
                            continue

                    self._logEvent(_('unpack {name}').format(name=item.name), outputWin)
                    tarf.extract(item, path=self._workPath)

                    if item.isfile():
                        if item.name == './iCluster-agent/application-prod.yml.template':
                            continue
                        self.agentFileList.append(item.name)
        listStr = " ".join(self.agentFileList)
        self._logEvent(_('list: {listStr}').format(listStr=listStr), outputWin)

        # if icwconfig.mode == icwconfig.EModetype.upgrade:
        #     self.agentFileList.remove('./iCluster-agent/.env')

        # Do not need upload this file
        # self.agentFileList.remove('./iCluster-agent/application-prod.yml.template')

        envPath = os.path.join(self._workPath, 'iCluster-agent/.env')
        self._logEvent(_('Detect file {envPath}').format(envPath=envPath), outputWin)

        if self._envProfile == None:
            if self._checkExist(envPath, isFile = True) :
                self._envProfile = CSVProfile()
                self._envProfile.read_properties(envPath)
                self._logEvent(_('Agent profile template {envPath} read successfully').format(envPath=envPath), outputWin)

                self.REGISTRY_IP = ''
                self.NODE_USERNAME = ''
                self.NODE_PASSWORD = ''
                # self.GUIAGENT_HOSTNAME = '<x.x.x.x>'
                pass
            else:
                self._envProfile = None
                self._logEvent(_('Failed to read Agent profile template {envPath} \n Please check the path and try again').format(envPath=envPath), outputWin)
                return False


        return True


_gAgentModel = AgentModel()


def GetModel():
    return _gAgentModel


def main():

    model = GetModel()



if __name__ == '__main__':
    main()
