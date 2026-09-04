import os
import sys
import subprocess
from subprocess import TimeoutExpired
import time
import select
import re
import csv
import socket

import paramiko
from paramiko.py3compat import u

# from os import path

import logging
import shutil

import tools.nginx_parse as nginx_parse
import tools.postgres_tools
from icwconfig import _


class UninstallModel():
    def __init__(self):
        self.agentFileList= []
        self._envProfile = None
        self._outputWindow = None
        self._conn = None

        # self._deploymentPath = str()

        self._pUser = str()
        self._pPwd = str()
        self._agentIp = str()
        self._agentPort = str()

        self._bStopAgent = True
        self._bRemoveAgent = False

        
        self._bStopJava = True
        # self._bStopRedis = True
        self._bStopNginx = True

        
        self._bRemoveICW = True
        self._bRemoveDBDATA = True

        self._servicePath = str()
        self._dbIp = str()
        
        self._bDelRpm = True
        # self._bDelRedis = True
        self._bDelNginx = True
        self._bDelConf = True
    @property
    def outputWindow(self):
        return self._outputWindow

    @outputWindow.setter
    def outputWindow(self, value):
        self._outputWindow = value


    # @property
    # def deploymentPath(self):
    #     return self._deploymentPath

    # @deploymentPath.setter
    # def deploymentPath(self, value):
    #     self._deploymentPath = value

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

    @property
    def agentPort(self):
        return self._agentPort

    @agentPort.setter
    def agentPort(self, value):
        self._agentPort = value

    @property
    def bStopAgent(self):
        return self._bStopAgent

    @bStopAgent.setter
    def bStopAgent(self, value):
        self._bStopAgent = value

    @property
    def bRemoveAgent(self):
        return self._bRemoveAgent

    @bRemoveAgent.setter
    def bRemoveAgent(self, value):
        self._bRemoveAgent = value

        

    @property
    def bStopJava(self):
        return self._bStopJava

    @bStopJava.setter
    def bStopJava(self, value):
        self._bStopJava = value

    # @property
    # def bStopRedis(self):
    #     return self._bStopRedis

    # @bStopRedis.setter
    # def bStopRedis(self, value):
    #     self._bStopRedis = value

    @property
    def bStopNginx(self):
        return self._bStopNginx

    @bStopNginx.setter
    def bStopNginx(self, value):
        self._bStopNginx = value

    @property
    def bRemoveICW(self):
        return self._bRemoveICW

    @bRemoveICW.setter
    def bRemoveICW(self, value):
        self._bRemoveICW = value

    @property
    def bRemoveDBDATA(self):
        return self._bRemoveDBDATA

    @bRemoveDBDATA.setter
    def bRemoveDBDATA(self, value):
        self._bRemoveDBDATA = value


    @property
    def servicePath(self):
        return self._servicePath

    @servicePath.setter
    def servicePath(self, value):
        self._servicePath = value

    @property
    def dbIp(self):
        return self._dbIp

    @dbIp.setter
    def dbIp(self, value):
        self._dbIp = value

    @property
    def bDelRpm(self):
        return self._bDelRpm

    @bDelRpm.setter
    def bDelRpm(self, value):
        self._bDelRpm = value

    # @property
    # def bDelRedis(self):
    #     return self._bDelRedis

    # @bDelRedis.setter
    # def bDelRedis(self, value):
    #     self._bDelRedis = value

    @property
    def bDelNginx(self):
        return self._bDelNginx

    @bDelNginx.setter
    def bDelNginx(self, value):
        self._bDelNginx = value
    
    @property
    def bDelConf(self):
        return self._bDelConf

    @bDelConf.setter
    def bDelConf(self, value):
        self._bDelConf = value

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


    def execCommand(self, cmd, timeout = 10, outputWin = None, showResult = None):
        chan = self._conn.invoke_shell()
        stdin = chan.makefile('wb')
        stdout = chan.makefile('rb')

        self._logEvent(_('Run command in remote: \n{cmd}\n').format(cmd=cmd), outputWin)
        stdin.write(f'{cmd}\nexit 0\n')
        lines = []
        result = None

        for i in range(timeout):
            if chan.exit_status_ready() is True:
                result = chan.recv_exit_status()
                # print(stdout.read())
                x = u(stdout.read())
                # for line in x.splitlines():
                #     print(line)
                lines = x.splitlines()
                break
            time.sleep(1)
        if showResult == None:
            chan.close()
            return result, lines
        else:
            if result == None:
                if chan.recv_ready() is True:
                    x = u(chan.recv(8192))
                    lines = x.splitlines()
                    result = 0
            chan.close()

            return result, lines


    def uninstallAgent(self, param = None):
        # self._conn
        if not param :
            return False

        outputWin = param.outputWin
        agentIp = param.agentIp
        agentPort = param.agentPort
        pUser = param.pUser
        pPwd = param.pPwd
        # deploymentPath = param.deploymentPath

        # bStopAgent = param.bStopAgent
        bRemoveAgent = param.bRemoveAgent

        self._logEvent(_('\nBegin connecting to Agent host {pUser}@{agentIp}:{agentPort} ').format(pUser=pUser, agentIp=agentIp, agentPort=agentPort), outputWin)

        try:
            if self._conn:
                del self._conn

            self._conn = paramiko.SSHClient()
            # give up on verifying host key altogether
            self._conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._conn.connect(agentIp, int(agentPort), pUser, pPwd)

            self._logEvent(_('Connection succeeded.'), outputWin)

            # if bStopAgent is True:
            self.execCommand('cd /opt/iCluster-agent/;/QOpenSys/pkgs/bin/bash stop.sh', outputWin = outputWin)

            if bRemoveAgent is True:
                self.execCommand('rm -rf /opt/iCluster-agent/', outputWin = outputWin)

            self._conn.close()

        except paramiko.ssh_exception.AuthenticationException as e:
            logging.debug("*** Ssh Error: %s: %s" % (e.__class__, e))

            outputWin.addstr("*** Ssh Error: %s: %s\n" % (e.__class__, e))
            outputWin.addstr("*** Ssh Error: User profile and password do not match \ntry again after modification\n" )
            outputWin.refresh()
            return False
        except paramiko.ssh_exception.BadHostKeyException as e:
            logging.debug("*** Ssh Error: %s: %s" % (e.__class__, e))

            outputWin.addstr("*** Ssh Error: %s: %s\n" % (e.__class__, e))
            outputWin.addstr("*** Ssh Error: Error Host\n" )
            outputWin.refresh()
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

        return True
    
    def removeDatabaseData(self, outputWin):
        try:
            self._logEvent(_('Starting web data removal from database.'), outputWin)
            # creating connection object
            if self._conn:
                del self._conn

            self._conn = paramiko.SSHClient()
            # give up on verifying host key altogether
            self._conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._conn.connect(self.dbIp, int(22), self.pUser, self.pPwd)

            # delete library ICWEBUSR if exists
            lib_check = '''system "CHKOBJ OBJ(ICWEBUSR) OBJTYPE(*LIB)"'''
            result, lines = self.execCommand(lib_check, showResult=True)
            output_str = ''.join(lines).upper()
            if result == 0 and "CPF9801" not in output_str:
                if self.execCommand('''system "DLTLIB LIB(ICWEBUSR)"''', showResult=True)[0] == 0:
                    if self.wait_until_deleted(lib_check, outputWin):
                        self._logEvent(_('Library ICWEBUSR deleted.'), outputWin)
                    else:
                        self._logEvent(_('Could not delete library ICWEBUSR. Delete manually.'), outputWin)
            else:
                self._logEvent(_('Library ICWEBUSR not found, skipping.'), outputWin)


            # delete profile ICWEBUSR if exists
            prof_check = '''system "CHKOBJ OBJ(ICWEBUSR) OBJTYPE(*USRPRF)"'''
            result, lines = self.execCommand(prof_check, showResult=True)
            output_str = ''.join(lines).upper()
            if result == 0 and "CPF9801" not in output_str:
                if self.execCommand('''system "DLTUSRPRF USRPRF(ICWEBUSR) OWNOBJOPT(*DLT)"''', showResult=True)[0] == 0:
                    if self.wait_until_deleted(prof_check, outputWin):
                        self._logEvent(_('User profile ICWEBUSR deleted.'), outputWin)
                    else:
                        self._logEvent(_('Could not delete user profile ICWEBUSR. Delete manually.'), outputWin)
            else:
                self._logEvent(_('User profile ICWEBUSR not found, skipping.'), outputWin)

            self._conn.close()
            return True
        except Exception as e:
            self._logEvent(_('Exception occured while performing data removal: {}').format(e), outputWin)
            return False
            
    def wait_until_deleted(self, check_command, outputWin, retries=3, delay=2):
        for retry in range(retries):
            result, lines = self.execCommand(check_command, showResult=True)
            output_str = ''.join(lines).upper()
            if result != 0 or "CPF9801" in output_str:                
                return True
            time.sleep(delay)
        return False

    def _getPid(self, checkStr):
        
        cmd = ['/QOpenSys/usr/bin/ps', '-ef']
        ps = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        cmd = ['/QOpenSys/usr/bin/grep', '-i', '-E', checkStr]
        grep = subprocess.Popen(cmd, stdin=ps.stdout, stdout=subprocess.PIPE, encoding='utf-8')
        cmd = ['awk', '{print $2}']
        awk = subprocess.Popen(cmd, stdin=grep.stdout, stdout=subprocess.PIPE, encoding='utf-8')

        ps.stdout.close()
        grep.stdout.close()
        output, err = awk.communicate()
        python_processes = output.split('\n')
        pid = 0
        if len(python_processes) > 0 and python_processes[0]:
            pid = int(python_processes[0])

        return pid

    def stopAll(self, param = None):
        # self._conn
        if not param :
            return False

        outputWin = param.outputWin

        bStopJava = param.bStopJava
        # bStopRedis = param.bStopRedis
        bStopNginx = param.bStopNginx
        
        bRemoveICW = param.bRemoveICW
        self.bRemoveDBDATA = param.bRemoveDBDATA
        self.dbIp = param.dbIp
        self.pUser = param.pUser
        self.pPwd = param.pPwd

        try:
            if bStopJava is True:
                self._logEvent(_('\nBegin stopping iCluster-web services '), outputWin)
                
                try:
                    proc = subprocess.Popen(['stop.sh', 'all'], cwd=self.servicePath, stdout=subprocess.PIPE, stderr=open(os.devnull, 'w'))
                    outs, errs = proc.communicate(timeout=15)
                    self._logEvent(f'\n{outs.decode()}', outputWin)
                except Exception as e:
                    self._logEvent(str(e), outputWin)
                self._logEvent(_('\niCluster-web services stopped'), outputWin)

            # if bStopRedis is True:
            #     self._logEvent(_('\nBegin stopping Redis '), outputWin)

            #     try:
            #         proc = subprocess.Popen("kill $(ps -ef | grep -i -E 'redis-server' | grep -v grep | awk '{print $2}')", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            #         outs, errs = proc.communicate(timeout=15)
            #         self._logEvent(f'\n{outs.decode()}', outputWin)
            #     except Exception as e:
            #         self._logEvent(str(e), outputWin)
            #     self._logEvent(_('\nRedis stopped'), outputWin)

            if bStopNginx is True:
                self._logEvent(_('\nBegin stopping Nginx '), outputWin)
                
                try:
                    proc = subprocess.Popen(['nginx', '-s', 'stop'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    outs, errs = proc.communicate(timeout=15)
                    self._logEvent(f'\n{outs.decode()}', outputWin)
                except Exception as e:
                    self._logEvent(str(e), outputWin)
                self._logEvent(_('\nNginx stopped'), outputWin)

            if bRemoveICW is True:
                stoped = False
                if bStopNginx is False:
                    pid = self._getPid('nginx')
                    if pid > 0:
                        try:
                            proc = subprocess.Popen(['nginx', '-s', 'stop'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            outs, errs = proc.communicate(timeout=15)
                            self._logEvent(f'\n{outs.decode()}', outputWin)
                            stoped = True
                        except Exception as e:
                            self._logEvent(str(e), outputWin)
                        # except Exception as e:
                        #     self._logEvent("*** Caught exception: %s: %s" % (e.__class__, e))
                        self._logEvent(_('\nNginx stopped'), outputWin)

                try:
                    # remove the include config from nginx.conf
                    nginxConf = nginx_parse.NginxConf(nginx_parse.nginxConfPath)
                    nginxConf.parse()
                    nginxConf.removeItem(*(nginx_parse.iClusterItem))
                    nginxConf.save()
                except Exception as e:
                    self._logEvent(str(e), outputWin)

                if stoped == True:
                    try:
                        child = subprocess.Popen(['/QOpenSys/pkgs/bin/nginx'],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        output, err = child.communicate()
                        for item in output.decode("utf-8").split('\n'):
                            self._logEvent(item, outputWin)
                        self._logEvent(_('\nNginx started'), outputWin)
                    except Exception as e:
                        self._logEvent(str(e), outputWin)

                self._logEvent(_('\nBegin removing iCluster-web '), outputWin)
                
                try:
                    proc = subprocess.Popen(['rm', '-rf', self.servicePath], cwd='/opt', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    outs, errs = proc.communicate(timeout=30)
                    self._logEvent(f'\n{outs.decode()}', outputWin)
                except Exception as e:
                    self._logEvent(str(e), outputWin)
                self._logEvent(_('\niCluster-web removed'), outputWin)

            if self.bRemoveDBDATA is True:
                return self.removeDatabaseData(outputWin)
        except Exception as e:
            # print("*** Caught exception: %s: %s" % (e.__class__, e))
            logging.debug("*** Caught exception: %s: %s" % (e.__class__, e))
            # traceback.print_exc()


        return True


    def _runShell(self, cmds, outputWin = None):
        idx = 0
        installed = list()
        begin = False
        beginHandle = False

        child = subprocess.Popen('/QOpenSys/pkgs/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        while True:
            inList = list()
            if beginHandle is False and idx < len(cmds):
                inList.append(child.stdin)
            rlist, wlist, elist = select.select([child.stdout], inList, [child.stderr], 1)

            if len(rlist) > 0:
                line = child.stdout.readline().decode('utf-8')
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

            elif len(wlist) > 0:
                if idx >= len(cmds):
                    continue

                child.stdin.write(cmds[idx].encode('utf-8'))
                child.stdin.write("\n".encode('utf-8'))
                child.stdin.flush() 
                idx += 1
                beginHandle = True

            else:
                beginHandle = False

                for e in elist:
                    self._logEvent(_('Select Error:'), outputWin)
                    self._logEvent(e, outputWin)
                    break

        out = child.communicate("\n".encode('utf-8'))[0]
        self._logEvent(out.decode('utf-8'), outputWin)

        return installed
        
    def delRPM(self, param = None):
        # self._conn
        if not param :
            return False

        outputWin = param.outputWin

        bDelRpm = param.bDelRpm
        # bDelRedis = param.bDelRedis
        bDelNginx = param.bDelNginx
        bDelConf = param.bDelConf


        try:
            proc = None
            if bDelRpm is True:
                if self._conn:
                    del self._conn

                self._conn = paramiko.SSHClient()
                self._conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self._conn.connect(self.dbIp, int(22), self.pUser, self.pPwd)
                self._logEvent(_('\nBegin uninstalling RPMs '), outputWin)
                
                packages = [
                    'ca-certificates-2_git20170807.10b2785-3.noarch',
                    'chsh-1.0.1-1.ppc64',
                    'curl-7.76.1-1.ppc64',
                    'gettext-runtime-0.19.8-1.ppc64',
                    'gettext-tools-0.19.8-1.ppc64',
                    'libfreetype6-2.10.4-1.ppc64',
                    'libgif7-5.1.4-0.ppc64',
                    'libjpeg8-1.5.1-2.ppc64',
                    'libp11-kit0-0.23.14-2.ppc64',
                    'libpng16-1.6.37-0.ppc64',
                    'libtasn1-6-4.10-4.ppc64',
                    'openjdk-11-ea-11.0.11.9-1.ppc64',
                    'p11-kit-trust-0.23.14-2.ppc64',
                    'tar-gnu-1.29-5.ppc64',
                ]
                
                for pkg in packages:
                    uninstall_cmd = f'/QOpenSys/pkgs/bin/rpm -e --nodeps {pkg}'
                    result, lines = self.execCommand(uninstall_cmd, outputWin=outputWin, showResult=False)
                    self._logEvent(_(f'Uninstalling package: {pkg}...'), outputWin)
                
                result, rpm_lines = self.execCommand('/QOpenSys/pkgs/bin/rpm -qa', outputWin=outputWin, showResult=True)
                installed = [l.strip() for l in rpm_lines if isinstance(l, str) and l.strip()]

                def base_name_from_full(full):
                    m = re.match(r'^(.+?)-\d', full)
                    if m:
                        return m.group(1)
                    for suff in ('.ppc64', '.noarch'):
                        if full.endswith(suff):
                            return full[:-len(suff)]
                    return full

                
                remaining_exact = {}
                remaining_related = {}
                removed = []

                installed_set = set(installed)

                for pkg in packages:
                    exact_matches = [inst for inst in installed if inst == pkg]
                    base = base_name_from_full(pkg)
                    related_matches = [inst for inst in installed if inst != pkg and (inst.startswith(base + "-") or inst.startswith(base + ".") or inst == base)]

                    if exact_matches:
                        remaining_exact[pkg] = exact_matches
                    elif related_matches:
                        remaining_related[pkg] = related_matches
                    else:
                        removed.append(pkg)

                self._logEvent(_('\nDependency uninstall summary:'), outputWin)
                for pkg, ex in remaining_exact.items():
                    for inst in ex:
                        self._logEvent(f'[REMAINING - exact]     {pkg} (installed: {inst})', outputWin)
                for pkg, rel in remaining_related.items():
                    self._logEvent(f'[REMAINING - related]   {pkg}  ->  {", ".join(rel)}', outputWin)
                for pkg in removed:
                    self._logEvent(f'[REMOVED]               {pkg}', outputWin)

                self._logEvent(_(f'\n RPM uninstallation complete. {len(removed)} removed, {len(remaining_exact)+len(remaining_related)} still present.'), outputWin)
                    
                    
            if bDelNginx is True:
                if self._conn:
                    del self._conn

                self._conn = paramiko.SSHClient()
                self._conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self._conn.connect(self.dbIp, int(22), self.pUser, self.pPwd)
                self._logEvent(_('\nBegin uninstalling Nginx '), outputWin)
                uninstall_cmd = f'/QOpenSys/pkgs/bin/rpm -e nginx-1.16.1-4.ppc64'
                result, lines = self.execCommand(uninstall_cmd, outputWin=outputWin, showResult=False)
                self._logEvent(_('\n nginx uninstalltion is complete'), outputWin)

            if bDelConf is True:
                self._logEvent(_('\nBegin deleting iCluster-web configuration files '), outputWin)
                try:
                    proc = subprocess.Popen(['rm', '-rf', '/opt/iCluster'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    outs, errs = proc.communicate(timeout=30)
                    if proc.returncode == 0:
                        self._logEvent(f'\n{outs.decode()}', outputWin)
                        self._logEvent(_('\niCluster-web configuration files deleted'), outputWin)
                    else:
                        self._logEvent(f'\nFailed to delete configuration files: {errs.decode()}', outputWin)
                        self._logEvent(_('\nPlease check and delete configuration folder /opt/iCluster manually'), outputWin)  
                except TimeoutExpired:
                    proc.kill()
                    proc.communicate()
                    self._logEvent(_('\nTimeout while deleting configuration files'), outputWin)
                    self._logEvent(_('\nPlease check and delete configuration folder /opt/iCluster manually'), outputWin)  
                except Exception as e:
                    self._logEvent(str(e), outputWin)
            
            self._conn.close()
        except Exception as e:
            # print("*** Caught exception: %s: %s" % (e.__class__, e))
            logging.debug("*** Caught exception: %s: %s" % (e.__class__, e))
            # traceback.print_exc()


        return True

_gUninstallModel = UninstallModel()


def GetModel():
    return _gUninstallModel


def main():

    model = GetModel()



if __name__ == '__main__':
    main()