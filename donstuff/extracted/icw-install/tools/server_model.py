import os
import sys
import subprocess
import time
import select
import re
import csv
import socket
import glob
import shutil
import datetime
import psycopg2
import ibm_db
import unicodedata
import concurrent.futures
from os import walk

import paramiko
from paramiko.py3compat import u
# from os import path
from zipfile import ZipFile
import tarfile

import logging
from tools.profile import CSVProfile
import tools.nginx_parse as nginx_parse
from icwconfig import _
import icwconfig
import tempfile
from string import Template
import tools.web_sql_queries


class ServerModel():
    def __init__(self):
        self._host = None
        self._envProfile = None
        self._outputWindow = None

        self._zipPath = str()
        self._unzipPath = str()
        self._installationPath = str()
        self._rpmTar = str()
        self._servicePkg = str()
        self._jarPkg = str()
        
        self._servicePath = str()
        self._initSql = str()
        self._dbIp = str()
        self._dbUser = str()
        self._dbPwd = str()
        self._pUser = str()
        self._pPwd = str()
        self._lFaileds = []

        self._del80 = False

        self.rpmList = [
        'rpm/bash-5.1-2.ibmi7.2.ppc64.rpm',
        'rpm/ca-certificates-2_git20170807.10b2785-3.ibmi7.2.noarch.rpm',
        'rpm/chsh-1.0.1-1.ibmi7.2.ppc64.rpm',
        'rpm/gettext-runtime-0.19.8-1.ibmi7.2.ppc64.rpm',
        'rpm/gettext-tools-0.19.8-1.ibmi7.2.ppc64.rpm',
        'rpm/libfreetype6-2.10.4-1.ibmi7.2.ppc64.rpm',
        'rpm/libgif7-5.1.4-0.ibmi7.2.ppc64.rpm',
        'rpm/libjpeg8-1.5.1-2.ibmi7.2.ppc64.rpm',
        'rpm/libopenssl1_1-1.1.1n-1.ibmi7.2.ppc64.rpm',
        'rpm/libp11-kit0-0.23.14-2.ibmi7.2.ppc64.rpm',
        'rpm/libpng16-1.6.37-0.ibmi7.2.ppc64.rpm',
        'rpm/libtasn1-6-4.10-4.ibmi7.2.ppc64.rpm',
        'rpm/nginx-1.16.1-4.ibmi7.2.ppc64.rpm',
        # './rpm/openjdk-11-ea-11.0.11.9-1.ibmi7.2.ppc64.rpm',
        'rpm/p11-kit-trust-0.23.14-2.ibmi7.2.ppc64.rpm',
        # './rpm/redis-6.0.10-1.ibmi7.2.ppc64.rpm',
        'rpm/tar-gnu-1.29-5.ibmi7.2.ppc64.rpm',
        'rpm/python3-psycopg2-2.8.5-1.ibmi7.2.ppc64.rpm'
        ]
        
        self.keycloak_tables_to_extract = [
            "public.user_entity",
            "public.keycloak_role",
            "public.keycloak_group",
            "public.user_group_membership",
            "public.group_role_mapping",
            "public.user_role_mapping",
        ]
        self.server_tables_to_extract = [
            "public.icw_clusters",
            "public.icw_nodes",
            "public.icw_user_preference",
            "public.icw_event_log_download",
            "public.icw_common_download",
            "public.icw_report_record",
            # ACL tables will be handled separately
            "public.acl_class",
            "public.acl_sid",
            "public.acl_object_identity",
            "public.acl_entry"
        ]
        
        self.db_configs = {
            "ricw_keycloak": {
                "dbname": "ricw_keycloak",
                "user": "your_username",
                "password": "your_password",
                "host": "127.0.0.1",
                "port": "5432",
            },
            "ricw_server": {
                "dbname": "ricw_server",
                "user": "your_username",
                "password": "your_password",
                "host": "127.0.0.1",
                "port": "5432",
            },
        }
        
        self.default_password = '$2a$10$xWdh7eYXV2fB/a7EICIAgeh7EH0PUQlpMwGJGH5ysxy4ADN0vYxre'
        
        self.table_mappings = {
            "user_entity": {
                "new_name": "USERS",
                "columns": {
                    "username": "USERNAME",
                    "email": "EMAIL",
                    "first_name": "FIRSTNAME",
                    "last_name": "LASTNAME",
                    "created_timestamp": "CREATEDAT",
                    "enabled": "ENABLED"
                },
                "filter": lambda row: (
                    row.get("realm_id") == "jhipster"
                    and (row.get("username") != "service-account-internal")
                ),
                "add_columns": {"PASSWORD": self.default_password.replace("$", "\\$"), "FAILURES": 0},
                "exclude_columns": ["id", "realm_id", "federation_link", "service_account_client_link", "email_constraint", "email_verified", "not_before"]
            },
            "keycloak_role": {
                "new_name": "ROLES",
                "columns": {
                    "name": "ROLE_NAME",
                    "description": "DESCRIPTION"
                },
                "filter": lambda row: (
                    row.get("client_realm_constraint") == "jhipster"
                    and (row.get("description") is None or not row["description"].startswith("$"))
                ),
                "exclude_columns": ["id", "client_realm_constraint", "client_role", "realm_id", "client", "realm"]
            },
            "keycloak_group": {"new_name": "GROUPS", "columns": {"name": "NAME"}, "exclude_columns": ["id", "parent_group", "realm_id"]},
            "user_group_membership": {"new_name": "USER_GROUP", "columns": {"user_id": "USER_ID", "group_id": "GROUP_ID"}},
            "group_role_mapping": {"new_name": "GROUP_ROLE", "columns": {"group_id": "GROUP_ID", "role_id": "ROLE_ID"}},
            "user_role_mapping": {"new_name": "USER_ROLE", "columns": {"user_id": "USER_ID", "role_id": "ROLE_ID"}},
            "icw_clusters": {"new_name": "ICW_CLUSTERS", "columns": {
                    "cluster_id": "CLUSTER_ID",
                    "alias": "ALIAS",
                    "description": "DESCRIPTION"
                    }
                },
            "icw_nodes": {"new_name": "ICW_NODES", "exclude_columns": ["id"]},
            "icw_user_preference": {"new_name": "ICW_USER_PREFERENCE",
                                    "columns": {
                                        "key": "KEY",
                                        "user_id": "USER_ID",
                                        "value": "VALUE"    
                                    },
                                    "exclude_columns": ["id"]
                                    },
            "acl_class": {"new_name": "ACL_CLASS", 
                        "exclude_columns": ["id"]
                        },
            "acl_sid": {"new_name": "ACL_SID",
                        "columns": {
                            "principal": "PRINCIPAL",
                            "sid": "SID"    
                        }, 
                        "exclude_columns": ["id"]
                        },
            "acl_object_identity": {"new_name": "ACL_OBJECT_IDENTITY",
                                    "exclude_columns": ["id"]
                                    },
            "acl_entry": {"new_name": "ACL_ENTRY", 
                        "exclude_columns": ["id"]
                        },
            "icw_event_log_download": {"new_name": "ICW_EVENT_LOG_DOWNLOAD",
                                    "columns": {
                                            "cluster_id": "CLUSTER_ID",
                                            "end_time": "END_TIME",
                                            "file_name": "FILE_NAME",
                                            "file_path": "FILE_PATH",
                                            "file_size": "FILE_SIZE",
                                            "message": "MESSAGE",
                                            "percent_complete": "PERCENT_COMPLETE",
                                            "start_time": "START_TIME",
                                            "status": "STATUS",
                                            "user_id": "USER_ID"
                                    },
                                    "exclude_columns": ["id"]
                                    },
            "icw_common_download": {"new_name": "ICW_COMMON_DOWNLOAD",
                                    "columns": {
                                        "cluster_id": "CLUSTER_ID",
                                        "end_time": "END_TIME",
                                        "file_name": "FILE_NAME",
                                        "file_path": "FILE_PATH",
                                        "file_size": "FILE_SIZE",
                                        "message": "MESSAGE",
                                        "percent_complete": "PERCENT_COMPLETE",
                                        "start_time": "START_TIME",
                                        "status": "STATUS",
                                        "type": "TYPE",
                                        "user_id": "USER_ID"
                                        },
                                    "exclude_columns": ["id"]
                                    },
            "icw_report_record": {"new_name": "ICW_REPORT_RECORD",
                                "columns": {
                                        "api_job_name": "API_JOB_NAME",
                                        "api_message": "API_MESSAGE",
                                        "api_node_name": "API_NODE_NAME",
                                        "api_response_code": "API_RESPONSE_CODE",
                                        "api_status_code": "API_STATUS_CODE",
                                        "api_user_name": "API_USER_NAME",
                                        "cluster_id": "CLUSTER_ID",
                                        "created_date": "CREATED_DATE",
                                        "download_status": "DOWNLOAD_STATUS",
                                        "last_modified_date": "LAST_MODIFIED_DATE",
                                        "message": "MESSAGE",
                                        "pdf_path": "PDF_PATH",
                                        "percent_complete": "PERCENT_COMPLETE",
                                        "type": "TYPE",
                                        "user_id": "USER_ID"
                                            
                                    }, 
                                "exclude_columns": ["id"]
                                }
        }
        
        self.pg_id_to_db2_id = {"USERS": {}, "ROLES": {}, "GROUPS": {}}
        self.acl_sid_id_mapping = {}
        
        self.output_dir = "/tmp/extracted_data/"
        self.transformed_dir = "/tmp/transformed_data/"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.transformed_dir, exist_ok=True)
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
    def unzipPath(self):
        return self._unzipPath

    @unzipPath.setter
    def unzipPath(self, value):
        self._unzipPath = value

    @property
    def rpmTar(self):
        return self._rpmTar

    @rpmTar.setter
    def rpmTar(self, value):
        self._rpmTar = value

    @property
    def servicePkg(self):
        return self._servicePkg

    @servicePkg.setter
    def servicePkg(self, value):
        self._servicePkg = value

    @property
    def jarPkg(self):
        return self._jarPkg

    @jarPkg.setter
    def jarPkg(self, value):
        self._jarPkg = value

    @property
    def servicePath(self):
        return self._servicePath

    @servicePath.setter
    def servicePath(self, value):
        self._servicePath = value

    @property
    def initSql(self):
        return self._initSql

    @initSql.setter
    def initSql(self, value):
        self._initSql = value

    @property
    def dbIp(self):
        return self._dbIp

    @dbIp.setter
    def dbIp(self, value):
        self._dbIp = value

    @property
    def dbUser(self):
        return self._dbUser

    @dbUser.setter
    def dbUser(self, value):
        self._dbUser = value
        
    @property
    def dbPwd(self):
        return self._dbPwd

    @dbPwd.setter
    def dbPwd(self, value):
        self._dbPwd = value
    
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
    
    # --- .env File profile--------------------------------------------------------
    
    @property
    def DATABASE_IP(self):
        return self._envProfile.profiles['DATABASE_IP'] if self._envProfile else ''

    @DATABASE_IP.setter
    def DATABASE_IP(self, value):
        if self._envProfile:
            self._envProfile.profiles['DATABASE_IP'] = value
            self._update_env_file(value)
    
    @property
    def REGISTRY_IP(self):
        return self._envProfile.profiles['REGISTRY_IP'] if self._envProfile else ''

    @REGISTRY_IP.setter
    def REGISTRY_IP(self, value):
        if self._envProfile:
            self._envProfile.profiles['REGISTRY_IP'] = value

    @property
    def REGISTRY_PORT(self):
        return self._envProfile.profiles['REGISTRY_PORT'] if self._envProfile else 0

    @REGISTRY_PORT.setter
    def REGISTRY_PORT(self, value):
        if self._envProfile:
            self._envProfile.profiles['REGISTRY_PORT'] = value
            
    @property
    def GATEWAY_IP(self):
        return self._envProfile.profiles['GATEWAY_IP'] if self._envProfile else ''

    @GATEWAY_IP.setter
    def GATEWAY_IP(self, value):
        if self._envProfile:
            self._envProfile.profiles['GATEWAY_IP'] = value

    @property
    def GATEWAY_PORT(self):
        return self._envProfile.profiles['GATEWAY_PORT'] if self._envProfile else 0

    @GATEWAY_PORT.setter
    def GATEWAY_PORT(self, value):
        if self._envProfile:
            self._envProfile.profiles['GATEWAY_PORT'] = value
            
    @property
    def SERVER_IP(self):
        return self._envProfile.profiles['SERVER_IP'] if self._envProfile and 'SERVER_IP' in self._envProfile.profiles else ''

    @SERVER_IP.setter
    def SERVER_IP(self, value):
        if self._envProfile:
            self._envProfile.profiles['SERVER_IP'] = value
            self._envProfile.profiles['REGISTRY_IP'] = value
            self._envProfile.profiles['PORTAL_IP'] = value
            
            # Always use 127.0.0.1, so don't need change
            # self._envProfile.profiles['GATEWAY_IP'] = value
            # self._envProfile.profiles['KEYCLOAK_IP'] = value

    @property
    def SERVER_PORT(self):
        return self._envProfile.profiles['SERVER_PORT'] if self._envProfile and 'SERVER_PORT' in self._envProfile.profiles else 0

    @SERVER_PORT.setter
    def SERVER_PORT(self, value):
        if self._envProfile:
            self._envProfile.profiles['SERVER_PORT'] = value
            
    @property
    def PORTAL_IP(self):
        return self._envProfile.profiles['PORTAL_IP'] if self._envProfile else ''

    @PORTAL_IP.setter
    def PORTAL_IP(self, value):
        if self._envProfile:
            self._envProfile.profiles['PORTAL_IP'] = value

    @property
    def PORTAL_PORT(self):
        return self._envProfile.profiles['PORTAL_PORT'] if self._envProfile else 0

    @PORTAL_PORT.setter
    def PORTAL_PORT(self, value):
        if self._envProfile:
            self._envProfile.profiles['PORTAL_PORT'] = value

    @property
    def del80(self):
        return self._del80

    @del80.setter
    def del80(self, value):
        self._del80 = value


    def _update_env_file(self, new_value):
        """Updates DATABASE_IP in the .env file or adds it if missing."""
        env_file_path = os.path.join(self.servicePath, '.env')
        if not os.path.isfile(env_file_path):
            print(f"File not found: {env_file_path}")
            return

        updated_lines = []
        database_ip_found = False

        with open(env_file_path, "r") as file:
            for line in file:
                if line.strip().startswith("DATABASE_IP="):
                    updated_lines.append(f"DATABASE_IP={new_value}\n")
                    database_ip_found = True
                    print(f"Updated DATABASE_IP to: {new_value}")
                else:
                    updated_lines.append(line)

        if not database_ip_found:
            print(f"DATABASE_IP not found in .env file, adding DATABASE_IP={new_value}")
            updated_lines.append(f"\nDATABASE_IP={new_value}\n")

        with open(env_file_path, "w") as file:
            file.writelines(updated_lines)

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

    def unpackZipFile(self, param):

        zipPath = param.zipPath
        # unzipPath = param.unzipPath
        servicePath = param.servicePath
        outputWin = param.outputWin
        if outputWin:
            outputWin.scrollok(1)

        self._logEvent(_('Begin unpacking zip file:'), outputWin)

        zipPath = self._expandPath(zipPath)
        servicePath = self._expandPath(servicePath)

        unzipPath = ''
        if icwconfig.mode == icwconfig.EModetype.install:
            unzipPath = os.path.join(servicePath, 'download')

            if os.path.exists(servicePath) and not os.path.isfile(servicePath):
                if os.listdir(servicePath):
                    self._logEvent(
                        _('{servicePath} is a non-empty directory, please delete this directory manually or use the upgrade mode')
                        .format(servicePath=servicePath), outputWin)
                    return False
        else:
            unzipPath = os.path.join(servicePath, 'upgrade')
        
        self._logEvent(_('Unzip:{zipPath} to {unzipPath}').format(zipPath=zipPath, unzipPath=unzipPath), outputWin)

        if self._checkExist(zipPath, isFile = True) is False:
            self._logEvent(_('The "{zipPath}" file to extract does not exist').format(zipPath=zipPath), outputWin)
            return False

        if os.path.exists(unzipPath) is True:
            shutil.rmtree(unzipPath, ignore_errors=False, onerror=None)

        self._logEvent(_('Make dir:{unzipPath}').format(unzipPath=unzipPath), outputWin)
        os.makedirs(unzipPath, exist_ok=True)

        with ZipFile(zipPath) as fzip:
            fzip.extractall(unzipPath)
            self._logEvent(_('Successfully extract file {zipPath}\n').format(zipPath=zipPath), outputWin)
        
            # self._installICWDB('/opt/iCluster-web', outputWin)

        if len(glob.glob(os.path.join(unzipPath, 'iCluster_dep.rpm.tar.gz'))) == 0:
            self._logEvent(_('iCluster_dep.rpm.tar.gz file not found\n'), outputWin)
            return False

        if len(glob.glob(os.path.join(unzipPath, 'iCluster-web-jar-v*.tar.gz'))) == 0:
            self._logEvent(_('iCluster-web-jar-v*.tar.gz file not found\n'), outputWin)
            return False

        if len(glob.glob(os.path.join(unzipPath, 'iCluster-web_IBMi.tar.gz'))) == 0:
            self._logEvent(_('iCluster-web_IBMi.tar.gz file not found\n'), outputWin)
            return False

        result = self.installJar(param)
        if result == False:
            return result

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
                self._logEvent(line, outputWin)
                
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
                    self._logEvent('Select Error:', outputWin)
                    self._logEvent(e, outputWin)
                    break

        out = child.communicate("\n".encode('utf-8'))[0]
        self._logEvent(out.decode('utf-8'), outputWin)

        return installed

    def installRPM(self, param):
        # unzipPath = param.unzipPath
        # rpmTar = param.rpmTar
        rpmTar = 'iCluster_dep.rpm.tar.gz'
        outputWin = param.outputWin
        if outputWin:
            outputWin.scrollok(1)

        child = subprocess.Popen('/QOpenSys/pkgs/bin/rpm -qa', stdout=subprocess.PIPE, shell=True)
        output = child.communicate()[0]
        itemDict = dict((x, ()) for x in output.decode("utf-8").split('\n'))

        # ./rpm/(package)(version)(IBMi-version)(arch).rpm  (handles both rpm/... and ./rpm/...)
        installedRpms = list()
        pattern = re.compile(r"(?:\./)?rpm/(\S+)(-\d\S+-\d)(\.ibmi\d.\d)(\.\S+)\.rpm")
        for item in self.rpmList:
            match = pattern.match(item)
            pkgVer = match.group(1) + match.group(2) + match.group(4)
            if pkgVer in itemDict:
                installedRpms.append(item)

        if len(installedRpms) > 0:
            self._logEvent(_('\nThese RPMS are already installed: '), outputWin)
            for pkg in installedRpms:
                self._logEvent(_(pkg), outputWin)

        # Skip the installed packages
        self.rpmList = list(set(self.rpmList) - set(installedRpms))

        if len(self.rpmList) > 0:
            self._logEvent(_('Begin installing RPM packages:'), outputWin)
            unzipPath = os.path.join(self.servicePath, 'download')

            depRPMgz = os.path.join(unzipPath, rpmTar)
            self._logEvent(_('Extract tar {depRPMgz}:').format(depRPMgz=depRPMgz), outputWin)
            if self._checkExist(depRPMgz, isFile = True) is False:
                self._logEvent(_('The rpm  tar.gz file  "{depRPMgz}" does not exist').format(depRPMgz=depRPMgz), outputWin)
                return False

            self._logEvent(_('Begin unpacking {depRPMgz}').format(depRPMgz=depRPMgz), outputWin)
            with tarfile.open(depRPMgz, mode='r') as tarf:
                # self.rpmList
                # tarf.extractall(unzipPath)
                for item in self.rpmList:
                    if 'nginx' in item:
                        self.del80 = True
                    self._logEvent(_('Extract : {item}').format(item=item), outputWin)
                    try:
                        tarf.extract(tarf.getmember(item), path=unzipPath)
                    except KeyError:
                        # Try alternate path prefix (with or without './')
                        alt_item = item[2:] if item.startswith('./') else './' + item
                        tarf.extract(tarf.getmember(alt_item), path=unzipPath)

                # TODO : To check need RPM upgrade
                rpmPath = os.path.join(unzipPath, 'rpm')
                # rpms = os.listdir(rpmPath)
                # self._logEvent(_('Unpacked rpm: {rpms}\n').format(rpms=" ".join(rpms)), outputWin)

                self._logEvent(_('Begin installing RPM packages \n'), outputWin)
            
                cmds = [
                        f'cd {rpmPath} ',
                        f'/QOpenSys/pkgs/bin/rpm -Uvh --force *.rpm ',
                        f'cd - ',
                        f'sleep 3 ',
                        f'rm -rf {rpmPath} ',
                        f'echo "###Complete!###"'
                        ]

                self._runShell(cmds, outputWin)
            self._logEvent(_('Successfully install rpms'), outputWin)
        else :
            self._logEvent(_('There is no RPMS needed to be installed.'), outputWin)

        return True

    def installJar(self, param):
        # unzipPath = param.unzipPath
        # servicePkg = param.servicePkg
        # jarPkg = param.jarPkg
        servicePkg = 'iCluster-web_IBMi.tar.gz'
        # jarPkg = 'iCluster-web-jar-v9.1.0.tar.gz'
        outputWin = param.outputWin
        if outputWin:
            outputWin.scrollok(1)

        unzipPath = ''
        if icwconfig.mode == icwconfig.EModetype.install:
            unzipPath = os.path.join(self.servicePath, 'download')
        else:
            unzipPath = os.path.join(self.servicePath, 'upgrade')

        webgz = os.path.join(unzipPath, servicePkg)

        if icwconfig.mode == icwconfig.EModetype.install:
            # *** Begin extract Service Folder
            if self._checkExist(webgz, isFile = True) is False:
                self._logEvent(_('The iCluster-web IBMi tar.gz file  "{webgz}" does not exist').format(webgz=webgz), outputWin)
                return False

            self._logEvent(_('Begin unpacking {webgz} to {servicePath}').format(webgz=webgz, servicePath=self.servicePath), outputWin)
            with tarfile.open(webgz, mode='r') as tarf:
                tarf.extractall(self.servicePath)
            
            # Copy icluster folder to /opt/icluster if it exists in the package
            icluster_src = os.path.join(self.servicePath, 'icluster')
            icluster_dest = '/opt/icluster'
            if os.path.exists(icluster_src):
                self._logEvent(_('Copying icluster folder to {dest}').format(dest=icluster_dest), outputWin)
                if os.path.exists(icluster_dest):
                    self._logEvent(_('Removing existing {dest}').format(dest=icluster_dest), outputWin)
                    shutil.rmtree(icluster_dest, ignore_errors=False, onerror=None)
                shutil.copytree(icluster_src, icluster_dest)
                self._logEvent(_('Successfully copied icluster folder to {dest}').format(dest=icluster_dest), outputWin)

        elif icwconfig.mode == icwconfig.EModetype.upgrade :
            subprocess.Popen(['stop.sh', 'all'], cwd=self.servicePath, stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
            time.sleep(10)

        envPath = os.path.join(self.servicePath, '.env')
        if self._envProfile == None and self._checkExist(envPath, isFile = False) is True:
            if self._checkExist(envPath, isFile = True) :
                self._envProfile = CSVProfile()
                self._envProfile.read_properties(envPath)
            else:
                self._envProfile = None

            # TODO do patch /Port changeable
            cwd = os.getcwd()
            patchPath = os.path.join(cwd, 'patch')
            # if self._checkExist(patchPath) == True:

                # # for: disable keycloak binding htttps port
                # standalone = os.path.join(patchPath, 'keycloak_standalone.xml')
                # if self._checkExist(standalone) == True:
                #     shutil.copyfile(standalone, os.path.join(self.servicePath, 'keycloak/standalone/configuration/standalone.xml'))
                # # Port changeable
                # start = os.path.join(patchPath, 'start.sh')
                # if self._checkExist(start) == True:
                #     shutil.copyfile(start, os.path.join(self.servicePath, 'start.sh'))
                # # Port changeable
                # start_keycloak = os.path.join(patchPath, 'start_keycloak.sh')
                # if self._checkExist(start_keycloak) == True:
                #     shutil.copyfile(start_keycloak, os.path.join(self.servicePath, 'start_keycloak.sh'))

        # Upgrade Keycloak to 24.0.5 begin
        if icwconfig.mode == icwconfig.EModetype.upgrade :
            
            if self._checkExist(os.path.join(self.servicePath, 'status.sh'), isFile = True) is True:
                os.remove(os.path.join(self.servicePath, 'status.sh'))

            if self._checkExist(os.path.join(self.servicePath, 'stop.sh'), isFile = True) is True:
                os.remove(os.path.join(self.servicePath, 'stop.sh'))

            if self._checkExist(os.path.join(self.servicePath, 'ctl.py'), isFile = True) is True:
                os.remove(os.path.join(self.servicePath, 'ctl.py'))

            if self._checkExist(os.path.join(self.servicePath, 'edit_env.sh'), isFile = True) is True:
                os.remove(os.path.join(self.servicePath, 'edit_env.sh'))

            if self._checkExist(os.path.join(self.servicePath, 'gateway/application-prod.yml'), isFile = True) is True:
                os.remove(os.path.join(self.servicePath, 'gateway/application-prod.yml'))

            if self._checkExist(os.path.join(self.servicePath, 'gateway/application.yml'), isFile = True) is True:
                os.remove(os.path.join(self.servicePath, 'gateway/application.yml'))

            if self._checkExist(os.path.join(self.servicePath, 'server/application-prod.yml'), isFile = True) is True:
                os.remove(os.path.join(self.servicePath, 'server/application-prod.yml'))

            if self._checkExist(os.path.join(self.servicePath, 'server/application.yml'), isFile = True) is True:
                os.remove(os.path.join(self.servicePath, 'server/application.yml'))

            if self._checkExist(os.path.join(self.servicePath, 'jhipster-registry/jhipster-registry-7.1.0.jar'), isFile = True) is True:
                os.remove(os.path.join(self.servicePath, 'jhipster-registry/jhipster-registry-7.1.0.jar'))

        if icwconfig.mode == icwconfig.EModetype.upgrade :
            profileBackup = self._envProfile.profiles
            upgradeList = [
                './status.sh',
                './stop.sh',
                './jhipster-registry/central-server-config/application.yml.template',
                './jhipster-registry/jhipster-registry-7.3.0.jar',
                './start.sh',
                './init/init_nginx.sh',
                './portal/icluster.conf.template',
                './.env',
                './ctl.py',
                './edit_env.sh'
                ]
            with tarfile.open(webgz, mode='r') as tarf:
                for item in upgradeList:
                    self._logEvent(_('Extract : {item}').format(item=item), outputWin)
                    tarf.extract(tarf.getmember(item), path=self.servicePath)
                
                # Extract icluster folder if it exists in the package (for upgrade scenario)
                try:
                    icluster_members = [m for m in tarf.getmembers() if m.name.lstrip('./').startswith('icluster/') or m.name.lstrip('./') == 'icluster']
                    if icluster_members:
                        self._logEvent(_('Extracting icluster folder for upgrade'), outputWin)
                        for member in icluster_members:
                            tarf.extract(member, path=self.servicePath)
                except Exception as e:
                    self._logEvent(_('Note: icluster folder not found in package (this is normal for older versions)'), outputWin)

            # Copy icluster folder to /opt/icluster if it exists (upgrade scenario)
            icluster_src = os.path.join(self.servicePath, 'icluster')
            icluster_dest = '/opt/icluster'
            if os.path.exists(icluster_src):
                self._logEvent(_('Copying icluster folder to {dest}').format(dest=icluster_dest), outputWin)
                if os.path.exists(icluster_dest):
                    self._logEvent(_('Removing existing {dest}').format(dest=icluster_dest), outputWin)
                    shutil.rmtree(icluster_dest, ignore_errors=False, onerror=None)
                shutil.copytree(icluster_src, icluster_dest)
                self._logEvent(_('Successfully copied icluster folder to {dest}').format(dest=icluster_dest), outputWin)

            envPath = os.path.join(self.servicePath, '.env')
            self._envProfile.read_properties(envPath)

            if 'REDIS_URL' in profileBackup:
                del profileBackup['REDIS_URL']
            for key in profileBackup:
                self._envProfile.profiles[key] = profileBackup[key]

            self.saveProfile(None)
        # Upgrade Keycloak to 19.0.3 end

        # *** Begin extract JAR
        jarPkg = ''
        for (dirpath, dirnames, filenames) in walk(unzipPath):
            if dirpath != unzipPath:
                # Donot search sub folders
                continue
            for filename in filenames:
                aa=re.match('iCluster-web-jar-v.+\.tar\.gz', filename)
                if aa is not None:
                    jarPkg = filename
                    break
            if len(jarPkg) > 0:
                break

        jargz = os.path.join(unzipPath, jarPkg)
        if self._checkExist(jargz, isFile = True) is False:
            self._logEvent(_('The {jarPkg} file  "{jargz}" does not exist').format(jarPkg=jarPkg, jargz=jargz), outputWin)
            return False

        self._logEvent(_('Begin unpacking {jargz} to {unzipPath}').format(jargz=jargz, unzipPath=unzipPath), outputWin)
        with tarfile.open(jargz, mode='r') as tarf:
            tarf.extractall(unzipPath)
            self._logEvent(_('End unpacking {jargz}').format(jargz=jargz), outputWin)

            if icwconfig.mode == icwconfig.EModetype.upgrade:
                gatewayBk = os.path.join(self.servicePath, 'gateway/gateway-1.0.jar.preVer')
                serverBk = os.path.join(self.servicePath, 'server/server-1.0.jar.preVer')
                staticBk = os.path.join(self.servicePath, 'portal/static.preVer')
                if self._checkExist(gatewayBk, isFile = True) is False:
                    shutil.move(os.path.join(self.servicePath, 'gateway/gateway-1.0.jar'), gatewayBk)
                if self._checkExist(serverBk, isFile = True) is False:
                    shutil.move(os.path.join(self.servicePath, 'server/server-1.0.jar'), serverBk)
                if self._checkExist(staticBk, isFile = False) is False:
                    shutil.move(os.path.join(self.servicePath, 'portal/static'), staticBk)

            self._logEvent(_('Replace jar gateway-1.0.jar'), outputWin)
            shutil.copyfile(os.path.join(unzipPath, 'gateway-1.0.jar'), os.path.join(self.servicePath, 'gateway/gateway-1.0.jar'))
            self._logEvent(_('Replace jar server-1.0.jar'), outputWin)
            shutil.copyfile(os.path.join(unzipPath, 'server-1.0.jar'), os.path.join(self.servicePath, 'server/server-1.0.jar'))

            staticTarPath = os.path.join(unzipPath, 'static.tar.gz')
            with tarfile.open(staticTarPath, mode='r') as staticTarf:
                self._logEvent(_('Begin unpacking static.tar.gz'), outputWin)
                staticPath = os.path.join(self.servicePath, 'portal/')
                staticTarf.extractall(staticPath)
                child = subprocess.Popen(['chmod',
                                 '-R',
                                 '755',
                                 staticPath], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                output, err = child.communicate()
            self._logEvent(_('End unpacking static.tar.gz'), outputWin)


        if len(glob.glob(os.path.join(self.servicePath, '*.sh'))) < 5:
            # export-env.sh start.sh start_redis.sh status.sh stop.sh
            self._logEvent(_('iCluster-web shell file not found\n'), outputWin)
            return False

        if len(glob.glob(os.path.join(self.servicePath, '.env'))) == 0:
            self._logEvent(_('iCluster-web .env file not found\n'), outputWin)
            return False

        if len(glob.glob(os.path.join(self.servicePath, '*/*.jar'))) < 4:
            self._logEvent(_('iCluster-web JAR files not found\n'), outputWin)
            return False

        if len(glob.glob(os.path.join(self.servicePath, 'portal/static/index.html'))) < 1:
            self._logEvent(_('iCluster-web portal static files not found\n'), outputWin)
            return False

        return True

    def posix_shell(self, chan, cmd, outputWin):
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
            # chan.settimeout(0.0)

            while True:
                r, w, e = select.select([chan.stdout, sys.stdin], [], [])
                if chan in r:
                    try:
                        if runed is False:
                            # chan.send(cmd)
                            chan.stdin.write(cmd.encode('utf-8'))
                            runed = True

                        x = u(chan.stdout.read(1024))
                        
                        if len(x) == 0:
                            break

                        if len(x) > 0:
                            for line in x.splitlines():
                                outputWin.addstr("".join(ch for ch in line if unicodedata.category(ch)!="Cc"))
                                logging.info(line)
                                if ':' not in line:
                                    # check input prompt
                                    outputWin.addstr('\n')
                                outputWin.refresh()
                        
                        
                    except socket.timeout:
                        outputWin.refresh()
                        pass
                if sys.stdin in r:
                    x = sys.stdin.read(1)
                    if len(x) == 0:
                        break
                    chan.stdin.write(x.encode('utf-8'))

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

    def installICWDB(self, param):
        # {"label":"Service path : ", "type":"editbox", "maxlen":50, "valueOffset":25, "defaultValue":"/opt/iCluster-web", "modelprop":"servicePath"},
        # {"label":"Initialized sql script : ", "type":"editbox", "maxlen":50, "valueOffset":25, "defaultValue":"init/init_postgresql.sql", "modelprop":"initSql"},
        # icwPath = param.servicePath
        # initSql = param.initSql

        # self.servicePath
        initSql = os.path.join(self.servicePath, 'init/init_postgresql.sql')
        if len(glob.glob(initSql)) == 0:
            self._logEvent(_('iCluster-web DB initialization script ({initSql}) not found\n').format(initSql=initSql), outputWin)
            return False

        pUser = param.pUser
        pPwd = param.pPwd

        outputWin = param.outputWin
        if outputWin:
            outputWin.scrollok(1)

        child = subprocess.Popen(['/QOpenSys/pkgs/bin/dropdb',
                                 f'-U{pUser}',
                                 '-h127.0.0.1',
                                 '--if-exists',
                                 'ricw_keycloak'], env={"PGPASSWORD": pPwd}, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        child.communicate()

        child = subprocess.Popen(['/QOpenSys/pkgs/bin/dropdb',
                                 f'-U{pUser}',
                                 '-h127.0.0.1',
                                 '--if-exists',
                                 'ricw_server'], env={"PGPASSWORD": pPwd}, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        child.communicate()

        child = subprocess.Popen(['/QOpenSys/pkgs/bin/dropdb',
                                 f'-U{pUser}',
                                 '-h127.0.0.1',
                                 '--if-exists',
                                 'ricw_gateway'], env={"PGPASSWORD": pPwd}, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        child.communicate()
        

        child = subprocess.Popen(['/QOpenSys/pkgs/bin/dropuser',
                                 f'-U{pUser}',
                                 '-h127.0.0.1',
                                 '--if-exists',
                                 'ricw_keycloak'], env={"PGPASSWORD": pPwd}, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        child.communicate()

        child = subprocess.Popen(['/QOpenSys/pkgs/bin/dropuser',
                                 f'-U{pUser}',
                                 '-h127.0.0.1',
                                 '--if-exists',
                                 'ricw_server'], env={"PGPASSWORD": pPwd}, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        child.communicate()

        child = subprocess.Popen(['/QOpenSys/pkgs/bin/dropuser',
                                 f'-U{pUser}',
                                 '-h127.0.0.1',
                                 '--if-exists',
                                 'ricw_gateway'], env={"PGPASSWORD": pPwd}, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        child.communicate()


        child = subprocess.Popen(['/QOpenSys/pkgs/bin/psql',
                                 f'-U{pUser}',
                                 '-h127.0.0.1',
                                 '-dpostgres',
                                 '-a',
                                 '-f',
                                 initSql], env={"PGPASSWORD": pPwd}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output, err = child.communicate()

        for item in output.decode("utf-8").split('\n'):
            self._logEvent(item, outputWin)

        return True if child.returncode == 0 else False

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

    def runBaseServices(self, param):
        outputWin = param.outputWin

        # self.runRedis(param)
        self.runNginx(param)
        # from 9.3.1 we are removing keycloak dependency from web
        # self.runKeycloak(param)

        return True

    def testPort(self, port, ip = '127.0.0.1', retryTimes = 10, delay = 1, outputWin = None):
        count = range(retryTimes)
        error = -1

        self._logEvent(_('\nConnecting to {ip}:{port}:').format(ip=ip, port=port), outputWin, newLine = False)

        for x in count:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            error = sock.connect_ex((ip, port))
            sock.close()
            if error == 0: 
                break
            time.sleep(delay)
            if outputWin:
                self._logEvent('.', outputWin, newLine = False)
        self._logEvent(' ', outputWin)

        return True if error == 0 else False

    def runNginx(self, param):
        outputWin = param.outputWin
        if outputWin:
            outputWin.scrollok(1)

        self._logEvent(_('\n\nBegin running Nginx '), outputWin)

        self._logEvent(_('Create iCW nginx config portal/icluster.conf'), outputWin)

        subprocess.Popen(['init/init_nginx.sh'], cwd=self.servicePath, stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)

        # subprocess.Popen(['/QOpenSys/pkgs/bin/nginx', '-s', 'stop'], cwd=self.servicePath, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        child = subprocess.Popen(['/QOpenSys/pkgs/bin/nginx', '-s', 'stop'],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output, err = child.communicate()
        # for item in output.decode("utf-8").split('\n'):
        #     self._logEvent(item, outputWin)
        # for item in err.decode("utf-8").split('\n'):
        #     self._logEvent('err'+item, outputWin)

        nginxConfPath = nginx_parse.nginxConfPath
        if self._checkExist(nginxConfPath, isFile = True) is False:
            self._logEvent(_('cp {servicePath}/portal/nginx.conf to {nginxConfPath}').format(servicePath=self.servicePath, nginxConfPath=nginxConfPath), outputWin)
            subprocess.call(['cp', os.path.join(self.servicePath, 'portal/nginx.conf'), nginxConfPath])
        else:
            nginxConf = nginx_parse.NginxConf(nginxConfPath)
            nginxConf.parse()

            if self.del80:
                # Remove default 80 port
                nginxConf.removeByKeys(['http', 'server'], {'listen':'80;'})

            nginxConf.addItem(*(nginx_parse.iClusterItem))
            nginxConf.save()

        # Handle nginx1.16 default logs dir is not exist.
        logsPath = '/QOpenSys/etc/nginx/logs'
        if self._checkExist(logsPath, isFile = False) is False:
            self._logEvent(_('Create dir {Path} ').format(Path=logsPath), outputWin)
            os.makedirs(logsPath, exist_ok=True)

        nginxVarPath = '/QOpenSys/var/nginx'
        if self._checkExist(nginxConfPath, isFile = True) is False:
            self._logEvent(_('Make nginx var path: {nginxVarPath}').format(nginxVarPath=nginxVarPath), outputWin)
            os.makedirs(nginxVarPath, exist_ok=True)

        self._logEvent(_('Start nginx'), outputWin)
        time.sleep(3)

        # subprocess.Popen(['/QOpenSys/pkgs/bin/nginx'], cwd=self.servicePath, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        child = subprocess.Popen(['/QOpenSys/pkgs/bin/nginx'],stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output, err = child.communicate()
        for item in output.decode("utf-8").split('\n'):
            self._logEvent(item, outputWin)
        # for item in err.decode("utf-8").split('\n'):
        #     self._logEvent('err'+item, outputWin)

        pid = self._getPid('nginx')

        if self.testPort(int(self.PORTAL_PORT), outputWin = outputWin):
            self._logEvent(_('Nginx service [PID:{pid}] is running on port {PORTAL_PORT}.').format(pid=pid, PORTAL_PORT=self.PORTAL_PORT), outputWin)
        else:
            self._lFaileds.append('Nginx')
            self._logEvent(_('Failed to start Nginx service on port {PORTAL_PORT}.').format(PORTAL_PORT=self.PORTAL_PORT), outputWin)
        
        return pid

    def runAllJar(self, param):
        outputWin = param.outputWin
        if outputWin:
            outputWin.scrollok(1)

        self._lFaileds = []

        self._logEvent(_('\nWill start following services :\n Nginx \n Registry\n Gateway\n Server'), outputWin)
        if icwconfig.mode == icwconfig.EModetype.upgrade:
            subprocess.Popen(['/QOpenSys/pkgs/bin/nginx', '-s', 'quit'], cwd=self.servicePath, stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
            # Create any missing rpt tables before restarting services
            self.outputWin = outputWin
            self.create_missing_rpt_tables()

        result = self.runBaseServices(param)
        if result is False:
            return False

        self._logEvent(_('\nBegin running iCluster-web core services '), outputWin)

        subprocess.Popen(['stop.sh', 'registry'], cwd=self.servicePath, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        subprocess.Popen(['stop.sh', 'gateway'], cwd=self.servicePath, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))
        subprocess.Popen(['stop.sh', 'server'], cwd=self.servicePath, stdout=open(os.devnull, 'w'), stderr=open(os.devnull, 'w'))

        time.sleep(10)

        subprocess.Popen(['start.sh', 'registry'], cwd=self.servicePath, stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)

        if self.testPort(int(self.REGISTRY_PORT), retryTimes = 300, outputWin = outputWin):
            pid = self._getPid('jhipster-registry-.*jar')
            self._logEvent(_('Registry [PID:{pid}] is running on port {REGISTRY_PORT}.').format(pid=pid, REGISTRY_PORT=self.REGISTRY_PORT), outputWin)
        else:
            self._lFaileds.append('Registry')
            self._logEvent(_('Failed to start Registry service on port {REGISTRY_PORT}.').format(REGISTRY_PORT=self.REGISTRY_PORT), outputWin)

        time.sleep(15)
        subprocess.Popen(['start.sh', 'gateway'], cwd=self.servicePath, stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        if self.testPort(int(self.GATEWAY_PORT), retryTimes = 420, outputWin = outputWin):
            pid = self._getPid('gateway-.*jar')
            self._logEvent(_('Gateway [PID:{pid}] is running on port {GATEWAY_PORT}.').format(pid=pid, GATEWAY_PORT=self.GATEWAY_PORT), outputWin)
        else:
            self._lFaileds.append('Gateway')
            self._logEvent(_('Failed to start Gateway service on port {GATEWAY_PORT}.').format(GATEWAY_PORT=self.GATEWAY_PORT), outputWin)

        time.sleep(10)
        subprocess.Popen(['start.sh', 'server'], cwd=self.servicePath, stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
        if self.testPort(int(self.SERVER_PORT), retryTimes = 300, outputWin = outputWin):
            pid = self._getPid('server-.*jar')
            self._logEvent(_('Server [PID:{pid}] is running on port {SERVER_PORT}.').format(pid=pid, SERVER_PORT=self.SERVER_PORT), outputWin)
        else:
            self._lFaileds.append('Server')
            self._logEvent(_('Failed to start Server service on port {SERVER_PORT}.').format(SERVER_PORT=self.SERVER_PORT), outputWin)


        self._logEvent(_('Services start complete!'), outputWin)

        if len(self._lFaileds) > 0:
            self._logEvent(_('Following {failed_count} services start failed:').format(failed_count=len(self._lFaileds)), outputWin)
            for item in self._lFaileds:
                self._logEvent(f'{  item}', outputWin)

        return True

    def saveProfile(self, param):
        outputWin = None

        if self._envProfile is None:
            self._logEvent(_('\niCluster-web .env file not found'), outputWin)
            return False

        self._envProfile.write_properties(os.path.join(self.servicePath, '.env'))
        return True
    
    def create_user_profile(self):
        try:
            self._logEvent(_('Starting user profile creation for web\n'), self.outputWin)
            result, lines = self.execCommand('''system "CRTUSRPRF USRPRF(ICWEBUSR) PASSWORD(ICWEBUSR) PWDEXP(*NO) USRCLS(*USER) TEXT('iCluster web user profile')"''', outputWin = self.outputWin, conn = self._conn, displayCommandLog = False)
            if result == 0:
                self._logEvent(_('User profile ICWEBUSR for web created successfully \n'), self.outputWin)    
            return result
        except Exception as e:
            self._logEvent(_('Exception occured while creating user profile: {e}').format(e = e), self.outputWin)

    def connect_to_db(self):
        try:
            self._logEvent(_('Starting schema creation for web \n'), self.outputWin)
            result, lines = self.execCommand('''system "CRTLIB LIB(ICWEBUSR) TEXT('ICWEBUSR')"''', outputWin = self.outputWin, conn = self._conn, displayCommandLog = False)
            if result == 0:
                self._logEvent(_('Schema for web ICWEBUSR created successfully \n'), self.outputWin)
            return result
        except Exception as e:
            self._logEvent(_('Exception occured while creating schema for web: {e}').format(e = e), self.outputWin)
        
    def grant_authority(self):
        try:
            self._logEvent(_('Granting schema permission for user \n'), self.outputWin)
            result, lines = self.execCommand('''system "GRTOBJAUT OBJ(ICWEBUSR) OBJTYPE(*LIB) USER(ICWEBUSR) AUT(*ALL)"''', outputWin = self.outputWin, conn = self._conn, displayCommandLog = False)
            if result == 0:
                self._logEvent(_('Authority granted successfully \n'), self.outputWin)
            return result
        except Exception as e:
            self._logEvent(_('Exception occured while granting authority for web: {e}').format(e = e), self.outputWin)
        
    def create_users_table(self):
        counter_gateway = 0
        counter_server = 0
        
        try:
            conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")  # Assuming self._conn is an active ibm_db connection
            self._logEvent(_('Generating tables for gateway web service \n'), self.outputWin)

            # List of SQL create statements
            gateway_tables = [
                tools.web_sql_queries.create_users_table,
                tools.web_sql_queries.create_roles_table,
                tools.web_sql_queries.create_group_table,
                tools.web_sql_queries.create_group_role_table,
                tools.web_sql_queries.create_user_group_table,
                tools.web_sql_queries.create_user_role_table,
                tools.web_sql_queries.create_refresh_token_table,
                tools.web_sql_queries.create_gateway_dbchangelog,
                tools.web_sql_queries.create_gateway_dbchangeloglock
            ]

            server_tables = [
                tools.web_sql_queries.create_acl_class,
                tools.web_sql_queries.create_acl_object_identity,
                tools.web_sql_queries.create_acl_sid,
                tools.web_sql_queries.create_acl_entry,
                tools.web_sql_queries.create_clusters,
                tools.web_sql_queries.create_common_download,
                tools.web_sql_queries.create_event_log_download,
                tools.web_sql_queries.create_nodes,
                tools.web_sql_queries.create_report_record,
                tools.web_sql_queries.create_user_preference,
                tools.web_sql_queries.create_server_dbchangelog,
                tools.web_sql_queries.create_server_dbchangeloglock,
                tools.web_sql_queries.create_rptgeneration,
                tools.web_sql_queries.create_rptgeneration_constraints,
                tools.web_sql_queries.create_rptgeneration_indexes,
                tools.web_sql_queries.create_rptjob,
                tools.web_sql_queries.create_rptjob_indexes,
                tools.web_sql_queries.create_rptdata,
                tools.web_sql_queries.create_rptdata_indexes,
                tools.web_sql_queries.create_rptanalysis,
                tools.web_sql_queries.create_rptanalysis_indexes
            ]

            # Execute each table creation in a loop
            for sql in gateway_tables:
                try:
                    stmt = ibm_db.exec_immediate(conn, sql)
                    counter_gateway += 1
                except Exception as e:
                    self._logEvent(f"Failed to create gateway table: {e}", self.outputWin)
                    return -1  # Exit early if a table fails to create

            self._logEvent(_('Generating tables for gateway web services complete \n'), self.outputWin)
            self._logEvent(_('Total tables created for gateway webservices: {created_tables} out of {total_tables} \n').format(created_tables = counter_gateway, total_tables = len(gateway_tables)), self.outputWin)

            self._logEvent(_('Generating tables for server web service \n'), self.outputWin)

            for sql in server_tables:
                try:
                    stmt = ibm_db.exec_immediate(conn, sql)
                    counter_server += 1
                except Exception as e:
                    self._logEvent(f"Failed to create server table: {e}", self.outputWin)
                    return -1

            self._logEvent(_('Generating tables for server web services complete \n'), self.outputWin)
            self._logEvent(_('Total tables created for server webservices: {created_tables} out of {total_tables} \n').format(created_tables = counter_server, total_tables = len(server_tables)), self.outputWin)

            # Commit all table creations at once
            ibm_db.commit(conn)

            return 0  # Success

        except Exception as e:
            self._logEvent(_('Exception occurred while creating tables: {}').format(e), self.outputWin)
            return -1  # Failure    
    
    def start_journaling(self):
        try:
            self._logEvent(_('Starting journalling for the new database'), self.outputWin)
            # Create a journal receiver
            result, lines = self.execCommand('''system "CRTJRNRCV JRNRCV(ICWEBUSR/WBUSRRCV)"''', outputWin = self.outputWin, conn = self._conn, displayCommandLog = False)
            if result != 0:
                return result

            # Create a journal
            result, lines = self.execCommand('''system "CRTJRN JRN(ICWEBUSR/WBUSRJRN) JRNRCV(ICWEBUSR/WBUSRRCV)"''', outputWin = self.outputWin, conn = self._conn, displayCommandLog = False)
            if result != 0:
                return result


            # Start journaling on the ICWEBUSR schema
            result, lines = self.execCommand('''system "STRJRNPF FILE(ICWEBUSR/*ALL) JRN(ICWEBUSR/WBUSRJRN)"''', outputWin = self.outputWin, conn = self._conn, displayCommandLog = False)
            if result == 0:
                self._logEvent(_('Started journalling on web tables'), self.outputWin)
            
            return result
        except Exception as e:
            self._logEvent(_('Exception occured while starting jounalling on web schema: {e}').format(e = e), self.outputWin)

    def add_default_data(self):
        try:
            self._logEvent(_('Adding default data \n'), self.outputWin)
            
            conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")  # Ensure a valid connection
            
            # List of default data insertion queries
            default_data_queries = [
                tools.web_sql_queries.add_default_user_query,
                tools.web_sql_queries.add_role_p1,
                tools.web_sql_queries.add_group_g1,
                tools.web_sql_queries.add_user_role,
                tools.web_sql_queries.add_group_role
            ]
            
            counter = 0  # Track successful inserts
            
            for sql in default_data_queries:
                try:
                    stmt = ibm_db.exec_immediate(conn, sql)
                    counter += 1
                except Exception as e:
                    self._logEvent(f"Failed to insert default data: {e}", self.outputWin)
            
            ibm_db.commit(conn)  # Commit all successful inserts at once
            
            self._logEvent(_('Added default data successfully. Total inserts: {} \n').format(counter), self.outputWin)
            
            return 0  # Success
        
        except Exception as e:
            self._logEvent(_('Exception occurred while adding default data: {}').format(e), self.outputWin)
            return -1  # Failure
            
    def check_tables_exists(self, show_log = True):
        """Check if all required DB2 tables exist using a single SQL query."""
        try:
            if show_log:
                self._logEvent(_('Checking if web tables exist on the target system'), self._outputWindow)
            tables = [
                "USERS",
                "ROLES",
                "GROUPS",
                "USER_ROLE",
                "USER_GROUP",
                "GROUP_ROLE",
                "RFSHTOKN"
            ]
            table_list = ", ".join(f"'{t}'" for t in tables)
            sql = (
                f"SELECT COUNT(*) FROM QSYS2.SYSTABLES "
                f"WHERE TABLE_SCHEMA = 'ICWEBUSR' AND TABLE_NAME IN ({table_list})"
            )
            conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
            stmt = ibm_db.exec_immediate(conn, sql)
            row = ibm_db.fetch_tuple(stmt)
            count = int(row[0]) if row else 0
            ibm_db.close(conn)
            logging.info(f"check_tables_exists: found {count}/{len(tables)} tables")
            if count < len(tables):
                self._logEvent(
                    _('Only {count}/{total} expected tables found in ICWEBUSR.')
                    .format(count=count, total=len(tables)), self._outputWindow)
                return False
            return True
        except Exception as e:
            self._logEvent(
                _('Exception occurred while checking if web tables exist: {e}').format(e=e),
                self._outputWindow
            )
            return False

    def create_missing_rpt_tables(self):
        """Create rpt_* tables if they don't already exist. Used during upgrade."""
        rpt_tables = {
            "RPTGENERATION": [
                tools.web_sql_queries.create_rptgeneration,
                tools.web_sql_queries.create_rptgeneration_constraints,
                tools.web_sql_queries.create_rptgeneration_indexes,
            ],
            "RPTJOB": [
                tools.web_sql_queries.create_rptjob,
                tools.web_sql_queries.create_rptjob_indexes,
            ],
            "RPTDATA": [
                tools.web_sql_queries.create_rptdata,
                tools.web_sql_queries.create_rptdata_indexes,
            ],
            "RPTANALYSIS": [
                tools.web_sql_queries.create_rptanalysis,
                tools.web_sql_queries.create_rptanalysis_indexes,
            ],
        }
        try:
            conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
            # Check which rpt tables already exist
            table_names = list(rpt_tables.keys())
            table_list = ", ".join(f"'{t}'" for t in table_names)
            sql = (
                f"SELECT TABLE_NAME FROM QSYS2.SYSTABLES "
                f"WHERE TABLE_SCHEMA = 'ICWEBUSR' AND TABLE_NAME IN ({table_list})"
            )
            stmt = ibm_db.exec_immediate(conn, sql)
            existing = set()
            row = ibm_db.fetch_tuple(stmt)
            while row:
                existing.add(row[0])
                row = ibm_db.fetch_tuple(stmt)

            missing = [t for t in table_names if t not in existing]
            if not missing:
                self._logEvent(_('All rpt tables already exist, nothing to create.'), self.outputWin)
                ibm_db.close(conn)
                return True

            self._logEvent(
                _('Creating missing rpt tables: {tables}').format(tables=', '.join(missing)),
                self.outputWin,
            )
            for table_name in missing:
                for sql_stmt in rpt_tables[table_name]:
                    try:
                        ibm_db.exec_immediate(conn, sql_stmt)
                    except Exception as e:
                        self._logEvent(
                            f"Failed to execute statement for {table_name}: {e}",
                            self.outputWin,
                        )
                        ibm_db.close(conn)
                        return False

            ibm_db.commit(conn)
            ibm_db.close(conn)
            self._logEvent(_('Missing rpt tables created successfully.'), self.outputWin)

            # Start journaling on newly created tables
            try:
                proc = subprocess.run(
                    ['system', 'STRJRNPF FILE(ICWEBUSR/*ALL) JRN(ICWEBUSR/WBUSRJRN)'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                if proc.returncode == 0:
                    self._logEvent(_('Journaling started on new rpt tables.'), self.outputWin)
                else:
                    self._logEvent(
                        _('Warning: journaling command returned {rc}').format(rc=proc.returncode),
                        self.outputWin,
                    )
            except Exception as e:
                self._logEvent(
                    _('Warning: could not start journaling on new tables: {e}').format(e=e),
                    self.outputWin,
                )

            return True
        except Exception as e:
            self._logEvent(
                _('Exception creating missing rpt tables: {e}').format(e=e),
                self.outputWin,
            )
            return False

    def test_db_connection(self, db_name, user, password):
        """Test database connection with given credentials"""
        try:
            # Create a temporary config dictionary with the provided credentials
            temp_config = self.db_configs[db_name].copy()
            temp_config["user"] = user
            temp_config["password"] = password
            
            # Try to connect
            with psycopg2.connect(**temp_config) as conn:
                with conn.cursor() as cur:
                    # Simple query to verify connection works
                    cur.execute("SELECT 1;")
                    result = cur.fetchone()
                    if result and result[0] == 1:
                        self._logEvent(f"Connection to {db_name} successful.", self.outputWin)
                        return 0
        except Exception as e:
            self._logEvent(f"Database connection test failed for {db_name}: {e}", self.outputWin)
            return 1
        
        return 0  # Connection successful

    def configureDatabase(self, param):
        try:
            self._host = self._envProfile.profiles['DATABASE_IP']
            hostPort = 22
            profile = param.dbUser
            profilePwd = param.dbPwd
            
            result_user_profile = None
            result_connect_db = None
            result_grant_authority = None
            result_create_table = None
            result_journal_table = None
            result_add_data = None
            
            self.outputWin = param.outputWin
            self._conn = paramiko.SSHClient()
            self._conn.banner_timeout = 60
            self._conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._conn.connect(self._host, hostPort, profile, profilePwd, timeout=10)
            if icwconfig.mode == icwconfig.EModetype.upgrade:
                self.db_configs["ricw_keycloak"]["user"] = param.pUser
                self.db_configs["ricw_keycloak"]["password"] = param.pPwd
                self.db_configs["ricw_server"]["user"] = param.pUser
                self.db_configs["ricw_server"]["password"] = param.pPwd
                db_user = param.pUser
                db_password = param.pPwd
                keycloak_test = self.test_db_connection("ricw_keycloak", db_user, db_password)
                server_test = self.test_db_connection("ricw_server", db_user, db_password)
                if keycloak_test != 0 or server_test != 0:
                    self._logEvent(_('Database connection test failed. Configuration aborted.'), self.outputWin)
                    return False
                if self.check_tables_exists():
                    self._logEvent(_('Database already exists, You can continue to next step.'), self.outputWin)
                    return True    
            result_user_profile = self.create_user_profile()
            if result_user_profile == 0:   
                result_connect_db = self.connect_to_db()
            if result_connect_db == 0:
                result_grant_authority = self.grant_authority()
            if result_grant_authority == 0:
                if self.check_tables_exists():
                    self._logEvent(_('Skipping table creation as it already exists on target system \n'), self.outputWin)
                    self._logEvent(_('Skipping table journalling \n'), self.outputWin)
                    self._logEvent(_('Skipping default data addition as tables already exists \n'), self.outputWin)
                    result_create_table = 0
                    result_journal_table = 0
                    result_add_data = 0
                    return True
                else:
                    result_create_table = self.create_users_table()
                    if result_create_table == 0:
                        result_journal_table = self.start_journaling()
                    else:
                        self._logEvent(_('Table creation failed.'), self.outputWin)    
                    if result_journal_table == 0:
                        if icwconfig.mode == icwconfig.EModetype.install:
                            result_add_data = self.add_default_data()
                        else:    
                            result_add_data = self.migrate_data()                  
                    else:
                        self._logEvent(_('Journaling operation table failed.'), self.outputWin)
                    if result_add_data == 0:
                        self._logEvent(_('DB2 database configuration is now done.'), self.outputWin)
                        return True
                    else:
                        self._logEvent(_('Default data addition failed.'), self.outputWin)
                        return False      
        except Exception as e:
            self._logEvent(_('Exception occured on main thread: {e}').format(e = e), self.outputWin)
            
        finally:
            if self._conn:
                self._logEvent(_('Closing connection.'), self.outputWin)

    def execCommand(self, cmd, timeout = 10, outputWin = None, conn = None, displayCommandLog = True):
        chan = None
        if conn is None :
            chan = self._conn.invoke_shell()
        else:
            chan = conn.invoke_shell()

        stdin = chan.makefile('wb')
        stdout = chan.makefile('rb')
        stderr = chan.makefile_stderr('rb')
        if displayCommandLog:
            self._logEvent(_('Running command in {agentIp}: \n{cmd}\n').format(agentIp=self._host, cmd=cmd), outputWin)
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
    
    def isUpgradePGToDB2(self):
        """Returns True if this is a PG-to-DB2 upgrade (DB2 tables are absent)."""
        try:
            return not self.check_tables_exists(show_log=False)
        except Exception as e:
            logging.error(f"Error in isUpgradePGToDB2: {e}")
            return True
        
    def extract_tables_from_db(self, db_name, tables):
        """Extracts tables from a given database and saves as CSV"""
        try:
            with psycopg2.connect(**self.db_configs[db_name]) as conn:
                with conn.cursor() as cur:
                    for table_name in tables:
                        try:
                            # Get column names
                            cur.execute(f"SELECT * FROM {table_name} LIMIT 0;")
                            column_names = [desc[0] for desc in cur.description]

                            # Fetch all data
                            cur.execute(f"SELECT * FROM {table_name};")
                            rows = cur.fetchall()

                            # CSV file path
                            csv_file = os.path.join(self.output_dir, f"{table_name.replace('.', '_')}.csv")

                            # Write to CSV
                            with open(csv_file, mode="w", newline="", encoding="utf-8") as file:
                                writer = csv.writer(file)
                                writer.writerow(column_names)
                                writer.writerows(rows)

                        except Exception as e:
                            self._logEvent(f"Error extracting {table_name}: {e}", self.outputWin)

        except Exception as e:
            self._logEvent(f"Database connection error for {db_name}: {e}", self.outputWin)
    
    def transform_boolean(self, value):
        """Convert BOOLEAN to SMALLINT"""
        if value in ["TRUE", "True", "true", "1"]:
            return 1
        elif value in ["FALSE", "False", "false", "0"]:
            return 0
        return value
    
    def transform_csv(self, filename):
        """Transforms a single CSV file"""
        table_name = filename.replace(".csv", "").replace("public_", "")
        mapping = self.table_mappings.get(table_name, {})

        if not mapping:
            return

        input_path = os.path.join(self.output_dir, filename)
        output_filename = f"{mapping['new_name']}.csv"
        output_path = os.path.join(self.transformed_dir, output_filename)

        with open(input_path, mode="r", encoding="utf-8") as infile, \
             open(output_path, mode="w", newline="", encoding="utf-8") as outfile:
            
            reader = csv.DictReader(infile)
            transformed_columns = mapping.get("columns", {})

            # Prepare header
            output_headers = [transformed_columns.get(col, col) for col in reader.fieldnames if col not in mapping.get("exclude_columns", [])]
            output_headers.extend(mapping.get("add_columns", {}).keys())

            if mapping["new_name"] == "ROLES":
                output_headers.append("PRIORITY")


            writer = csv.DictWriter(outfile, fieldnames=output_headers)
            writer.writeheader()

            role_priority = {
                "ROLE_ADMIN": 1,
                "ROLE_SUPERUSER": 2,
                "ROLE_USER": 3
            }
            
            for row in reader:
                if "filter" in mapping and not mapping["filter"](row):
                    continue  # Skip row if it doesn't match the filter

                new_row = {transformed_columns.get(k, k): self.transform_boolean(v) for k, v in row.items() if k not in mapping.get("exclude_columns", [])}
                new_row.update(mapping.get("add_columns", {}))
                
                if table_name == "keycloak_role":
                    role_name_key = next((key for key in new_row.keys() if key.strip().lower() == "role_name"), None)
                    if role_name_key:
                        role_name = new_row[role_name_key].strip().upper() # Normalize case
                        priority = role_priority.get(role_name, 999)
                    else:
                        priority = 999  # Ensure priority is assigned even if role_name is missing
                    
                    new_row["PRIORITY"] = priority
                writer.writerow(new_row)
                if table_name in ["user_entity", "keycloak_role", "keycloak_group"]:
                    pg_id = row["id"]
                    self.pg_id_to_db2_id.setdefault(mapping["new_name"], {})[pg_id] = None
    
    def transform_all_csv(self):
        """Transform all extracted CSV files."""   
        # First, transform main tables (so mapping dict gets populated)
        for filename in os.listdir(self.output_dir):
            table_name = filename.replace(".csv", "").replace("public_", "")
            if table_name in ["user_entity", "keycloak_role", "keycloak_group"]:
                self.transform_csv(filename)
        
        # Then, transform mapping tables (now that mapping dict should be complete)
        for filename in os.listdir(self.output_dir):
            table_name = filename.replace(".csv", "").replace("public_", "")
            if table_name in ["user_group_membership", "group_role_mapping", "user_role_mapping"]:
                self.transform_mapping_table(filename)
        
        # Finally, transform any other tables
        for filename in os.listdir(self.output_dir):
            table_name = filename.replace(".csv", "").replace("public_", "")
            acl_tables = ["acl_class", "acl_sid", "acl_object_identity", "acl_entry"]
            if (table_name not in ["user_entity", "keycloak_role", "keycloak_group",
                                  "user_group_membership", "group_role_mapping", "user_role_mapping"] and table_name not in acl_tables):
                self.transform_csv(filename)
    
    def load_main_tables_to_db2(self):
        """Load transformed main table CSVs (USERS, ROLES, GROUPS, etc.) into DB2 and capture new IDs where required."""
        db2_schema = "ICWEBUSR"
        
        # Define main tables to be uploaded (mapping tables excluded)
        main_tables = {
            "USERS", "ROLES", "GROUPS", "ICW_CLUSTERS", "ICW_NODES"
        }
        
        # Open a DB2 connection using ibm_db
        conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
        if not conn:
            raise Exception("Failed to connect to DB2 for main tables load.")
        
        for filename in os.listdir(self.transformed_dir):
            if not filename.endswith(".csv"):
                continue
            table_name = filename.replace(".csv", "")
            if table_name not in main_tables:
                continue
            
            csv_path = os.path.join(self.transformed_dir, filename)
            try:
                with open(csv_path, mode="r", encoding="utf-8") as infile:
                    reader = csv.reader(infile)
                    headers = next(reader)
                    for row in reader:
                        values = []
                        for header, val in zip(headers, row):
                            if val is None or val.strip() == "":
                                values.append("NULL")
                            elif header.upper() == "CREATEDAT":
                                try:
                                    ts_value = int(val) / 1000
                                    dt_value = datetime.datetime.fromtimestamp(ts_value).strftime('%Y-%m-%d %H:%M:%S')
                                    values.append(f"TIMESTAMP('{dt_value}')")
                                except ValueError:
                                    values.append("NULL")
                            else:
                                values.append("'" + val.replace("'", "''") + "'")

                        sql = f"INSERT INTO {db2_schema}.{table_name} ({', '.join(headers)}) VALUES ({', '.join(values)})"
                        escaped_sql = sql.replace("'", "''").replace("\n", " ")
                        # self._logEvent(_("Escaped sql for insert op is: {escaped_sql}").format(escaped_sql = escaped_sql), self.outputWin)
                        # Execute the insert using RUNSQL
                        result, lines = self.execCommand(
                            f'''/QOpenSys/usr/bin/system "RUNSQL SQL('{escaped_sql}') COMMIT(*NONE)"''',
                            outputWin=None, conn=self._conn
                        )
                        
                        # self._logEvent(_("Insert output is: {lines}").format(lines = lines), self.outputWin)
                        # **Only update ID mapping for USERS, ROLES, GROUPS**
                        if table_name in {"USERS", "ROLES", "GROUPS"}:
                            unique_column = {
                                "USERS": "USERNAME", "ROLES": "ROLE_NAME", "GROUPS": "NAME"
                            }.get(table_name, headers[0])

                            try:
                                idx = headers.index(unique_column)
                                raw_val = row[idx]

                                if raw_val.upper() == "NULL" or raw_val == "":
                                    db2_id_query = f"SELECT ID FROM {db2_schema}.{table_name} WHERE {unique_column} IS NULL FETCH FIRST 1 ROWS ONLY"
                                else:
                                    safe_val = raw_val.replace("'", "''")
                                    db2_id_query = f"SELECT ID FROM {db2_schema}.{table_name} WHERE {unique_column} = '{safe_val}' FETCH FIRST 1 ROWS ONLY"

                                # self._logEvent(_("Selected ID is : {db2_id_query}").format(db2_id_query = db2_id_query), self.outputWin)
                                stmt = ibm_db.exec_immediate(conn, db2_id_query)
                                row_data = ibm_db.fetch_assoc(stmt)
                                db2_id = str(row_data["ID"]) if row_data and "ID" in row_data else None

                                for pg_id in self.pg_id_to_db2_id.get(table_name, {}):
                                    if self.pg_id_to_db2_id[table_name][pg_id] is None:
                                        self.pg_id_to_db2_id[table_name][pg_id] = db2_id
                                        break
                            except Exception as e:
                                self._logEvent(f"Error fetching ID for {table_name}: {e}", self.outputWin)

            except Exception as e:
                self._logEvent(f"Error loading {table_name}: {e}", self.outputWin)

        ibm_db.close(conn)
        self._logEvent("Main tables load complete.", self.outputWin)

    def load_mapping_tables_to_db2(self):
        """Load transformed mapping table CSVs (USER_GROUP, GROUP_ROLE, USER_ROLE) into DB2."""
        db2_schema = "ICWEBUSR"
        mapping_tables = {"USER_GROUP", "GROUP_ROLE", "USER_ROLE", "ICW_USER_PREFERENCE", "ICW_EVENT_LOG_DOWNLOAD",
            "ICW_COMMON_DOWNLOAD", "ICW_REPORT_RECORD"}
        
        # Open DB2 connection
        conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
        if not conn:
            raise Exception("Failed to connect to DB2 for mapping tables load.")
        for filename in os.listdir(self.transformed_dir):
            if not filename.endswith(".csv"):
                continue
            table_name = filename.replace(".csv", "")
            if table_name not in mapping_tables:
                continue
            csv_path = os.path.join(self.transformed_dir, filename)
            try:
                with open(csv_path, mode="r", encoding="utf-8") as infile:
                    reader = csv.reader(infile)
                    headers = next(reader)
                    for row in reader:
                        values = []
                        for header, val in zip(headers, row):
                            if val is None or val.strip() == "":
                                values.append("NULL")
                            else:
                                values.append("'" + val.replace("'", "''") + "'")
                        sql = f"INSERT INTO {db2_schema}.{table_name} ({', '.join(headers)}) VALUES ({', '.join(values)})"
                        escaped_sql = sql.replace("'", "''").replace("\n", " ")
                        result, lines = self.execCommand(
                            f'''/QOpenSys/usr/bin/system "RUNSQL SQL('{escaped_sql}') COMMIT(*NONE)"''',
                            outputWin=None, conn=self._conn
                        )
            except Exception as e:
                self._logEvent(f"Error loading mapping table {table_name}: {e}", self.outputWin)
        ibm_db.close(conn)
        self._logEvent("Mapping tables load complete.", self.outputWin)   
    
    def transform_mapping_table(self, filename):
        """Transforms mapping table CSV by replacing PG IDs with DB2 IDs."""
        table_name = filename.replace(".csv", "").replace("public_", "")
        mapping = self.table_mappings.get(table_name, {})
        if not mapping:
            return
        
        input_path = os.path.join(self.output_dir, filename)
        output_filename = f"{mapping['new_name']}.csv"
        output_path = os.path.join(self.transformed_dir, output_filename)
        
        # Special handling for user-role and user-group mappings
        if table_name in ["user_role_mapping", "user_group_membership"]:
            # Build dictionaries to map entities by name
            pg_users = {}
            pg_roles = {}
            pg_groups = {}
            db2_users = {}
            db2_roles = {}
            db2_groups = {}
            
            # Step 1: Load all PostgreSQL users with their IDs and usernames
            pg_user_file = None
            for f in os.listdir(self.output_dir):
                if "user_entity" in f:
                    pg_user_file = os.path.join(self.output_dir, f)
                    break
            
            if pg_user_file:
                with open(pg_user_file, 'r') as f:
                    pg_user_reader = csv.DictReader(f)
                    for row in pg_user_reader:
                        if row.get('id') and row.get('username'):
                            pg_users[row['id']] = row['username']
            
            # Step 2: Load PostgreSQL roles/groups based on the table being processed
            if table_name == "user_role_mapping":
                # Load all PostgreSQL roles
                pg_role_file = None
                for f in os.listdir(self.output_dir):
                    if "keycloak_role" in f:
                        pg_role_file = os.path.join(self.output_dir, f)
                        break
                
                if pg_role_file:
                    with open(pg_role_file, 'r') as f:
                        pg_role_reader = csv.DictReader(f)
                        for row in pg_role_reader:
                            if row.get('id') and row.get('name'):
                                pg_roles[row['id']] = row['name']
            
            elif table_name == "user_group_membership":
                # Load all PostgreSQL groups
                pg_group_file = None
                for f in os.listdir(self.output_dir):
                    if "keycloak_group" in f:
                        pg_group_file = os.path.join(self.output_dir, f)
                        break
                
                if pg_group_file:
                    with open(pg_group_file, 'r') as f:
                        pg_group_reader = csv.DictReader(f)
                        for row in pg_group_reader:
                            if row.get('id') and row.get('name'):
                                pg_groups[row['id']] = row['name']
            
            # Step 3: Get DB2 entities by their names
            conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
            try:
                # Get DB2 users
                query = "SELECT ID, USERNAME FROM ICWEBUSR.USERS"
                stmt = ibm_db.exec_immediate(conn, query)
                row = ibm_db.fetch_assoc(stmt)
                while row:
                    if row.get("USERNAME"):
                        db2_users[row["USERNAME"]] = str(row["ID"])
                    row = ibm_db.fetch_assoc(stmt)
                
                # Get DB2 roles/groups based on table being processed
                if table_name == "user_role_mapping":
                    query = "SELECT ID, ROLE_NAME FROM ICWEBUSR.ROLES"
                    stmt = ibm_db.exec_immediate(conn, query)
                    row = ibm_db.fetch_assoc(stmt)
                    while row:
                        if row.get("ROLE_NAME"):
                            db2_roles[row["ROLE_NAME"]] = str(row["ID"])
                        row = ibm_db.fetch_assoc(stmt)
                
                elif table_name == "user_group_membership":
                    query = "SELECT ID, NAME FROM ICWEBUSR.GROUPS"
                    stmt = ibm_db.exec_immediate(conn, query)
                    row = ibm_db.fetch_assoc(stmt)
                    while row:
                        if row.get("NAME"):
                            db2_groups[row["NAME"]] = str(row["ID"])
                        row = ibm_db.fetch_assoc(stmt)
            finally:
                ibm_db.close(conn)
            
            # Step 4: Build direct mappings from PG IDs to DB2 IDs using the name as the bridge
            pg_to_db2_user_id = {}
            pg_to_db2_role_id = {}
            pg_to_db2_group_id = {}
            
            for pg_id, username in pg_users.items():
                if username in db2_users:
                    pg_to_db2_user_id[pg_id] = db2_users[username]
            
            for pg_id, rolename in pg_roles.items():
                if rolename in db2_roles:
                    pg_to_db2_role_id[pg_id] = db2_roles[rolename]
            
            for pg_id, groupname in pg_groups.items():
                if groupname in db2_groups:
                    pg_to_db2_group_id[pg_id] = db2_groups[groupname]
            
            # Now transform the mapping CSV using our direct mappings
            with open(input_path, mode="r", encoding="utf-8") as infile, \
                open(output_path, mode="w", newline="", encoding="utf-8") as outfile:
                
                reader = csv.DictReader(infile)
                transformed_columns = mapping.get("columns", {})
                writer = csv.DictWriter(outfile, fieldnames=transformed_columns.values())
                writer.writeheader()
                
                if table_name == "user_role_mapping":
                    for row in reader:
                        pg_user_id = row.get("user_id")
                        pg_role_id = row.get("role_id")
                        
                        if not pg_user_id or not pg_role_id:
                            continue
                        
                        db2_user_id = pg_to_db2_user_id.get(pg_user_id)
                        db2_role_id = pg_to_db2_role_id.get(pg_role_id)
                        
                        if db2_user_id and db2_role_id:
                            new_row = {
                                transformed_columns["user_id"]: db2_user_id,
                                transformed_columns["role_id"]: db2_role_id
                            }
                            writer.writerow(new_row)
                    
                    # Add admin role mapping for user_role_mapping
                    conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
                    try:
                        admin_query = "SELECT ID FROM ICWEBUSR.USERS WHERE USERNAME = 'admin'"
                        stmt = ibm_db.exec_immediate(conn, admin_query)
                        admin_db2_id = ibm_db.fetch_assoc(stmt)
                        admin_db2_id = admin_db2_id["ID"] if admin_db2_id else None

                        role_query = "SELECT ID FROM ICWEBUSR.ROLES WHERE ROLE_NAME = 'ROLE_ADMIN'"
                        stmt = ibm_db.exec_immediate(conn, role_query)
                        role_admin_db2_id = ibm_db.fetch_assoc(stmt)
                        role_admin_db2_id = role_admin_db2_id["ID"] if role_admin_db2_id else None
                        
                        if admin_db2_id and role_admin_db2_id:
                            hardcoded_row = {
                                transformed_columns["user_id"]: admin_db2_id,
                                transformed_columns["role_id"]: role_admin_db2_id
                            }
                            writer.writerow(hardcoded_row)
                    finally:
                        ibm_db.close(conn)
                
                elif table_name == "user_group_membership":
                    for row in reader:
                        pg_user_id = row.get("user_id")
                        pg_group_id = row.get("group_id")
                        
                        if not pg_user_id or not pg_group_id:
                            continue
                        
                        db2_user_id = pg_to_db2_user_id.get(pg_user_id)
                        db2_group_id = pg_to_db2_group_id.get(pg_group_id)
                        
                        if db2_user_id and db2_group_id:
                            new_row = {
                                transformed_columns["user_id"]: db2_user_id,
                                transformed_columns["group_id"]: db2_group_id
                            }
                            writer.writerow(new_row)
            
            return  # Skip the general processing below for special mapping tables
        
        with open(input_path, mode="r", encoding="utf-8") as infile, \
            open(output_path, mode="w", newline="", encoding="utf-8") as outfile:
            
            reader = csv.DictReader(infile)
            transformed_columns = mapping.get("columns", {})
            writer = csv.DictWriter(outfile, fieldnames=transformed_columns.values())
            writer.writeheader()
            
            for row in reader:
                new_row = {}
                skip_row = False
                
                for pg_col, db2_col in transformed_columns.items():
                    pg_val = row.get(pg_col)
                    table_type = None
                    
                    if pg_col.lower() == "user_id":
                        table_type = "USERS"
                    elif pg_col.lower() == "group_id":
                        table_type = "GROUPS"
                    elif pg_col.lower() == "role_id":
                        table_type = "ROLES"

                    if table_type:
                        mapped_value = self.pg_id_to_db2_id.get(table_type, {}).get(str(pg_val))
                        if mapped_value is None:
                            skip_row = True
                            break
                        new_row[db2_col] = mapped_value
                    else:
                        new_row[db2_col] = self.transform_boolean(pg_val)
                
                if not skip_row:
                    writer.writerow(new_row)
    
    def safe_str(self, text):
        """Convert any string to a safe printable version"""
        if not isinstance(text, str):
            return str(text)
        
        try:
            # Replace non-ASCII characters with '?'
            return text.encode('ascii', 'replace').decode('ascii')
        except UnicodeError:
            return '[unicode character]'

    def sanitize_transformed_csv(self):
        """Sanitize users.csv and groups.csv by removing invalid records and logging safely."""
        pattern = re.compile(r"^[a-zA-Z0-9_@.\-]+$")  # Allowed characters only

        for filename in ("USERS.csv", "GROUPS.csv"):
            input_path = os.path.join(self.transformed_dir, filename)
            if not os.path.exists(input_path):
                self._logEvent(f"Skipping sanitization: {filename} not found.", self.outputWin)
                continue

            output_path = os.path.join(self.transformed_dir, f"sanitized_{filename}")

            try:
                with open(input_path, mode="r", encoding="utf-8") as infile, \
                    open(output_path, mode="w", newline="", encoding="utf-8") as outfile:

                    reader = csv.DictReader(infile)
                    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
                    writer.writeheader()

                    for row in reader:
                        # Extract field to validate
                        value = (row.get("USERNAME") if filename == "USERS.csv" else row.get("NAME")) or ""
                        value = value.strip()

                        if not pattern.fullmatch(value):
                            # Log sanitized version of the invalid value
                            self._logEvent(
                                f"Invalid entry removed from {filename}: '{self.safe_str(value)}'",
                                self.outputWin
                            )
                            continue  # Skip invalid row

                        writer.writerow(row)

                # Replace original file with sanitized version
                os.replace(output_path, input_path)
                self._logEvent(f"Sanitized {filename} successfully.", self.outputWin)

            except Exception as e:
                self._logEvent(f"Error sanitizing {filename}: {self.safe_str(str(e))}", self.outputWin)
    
    # Transform and load ACL_CLASS
    def transform_and_load_acl_class(self):
        """Step 1: Transform ACL_CLASS from extracted data and load it into DB2."""
        table_name = "acl_class"
        input_filename = "public_acl_class.csv"
        output_filename = "ACL_CLASS.csv"
        
        input_path = os.path.join(self.output_dir, input_filename)
        output_path = os.path.join(self.transformed_dir, output_filename)
        
        if not os.path.exists(input_path):
            self._logEvent(f"Error: {input_filename} not found in extracted data.", self.outputWin)
            return
        
        # Transform ACL_CLASS
        try:
            with open(input_path, mode="r", encoding="utf-8") as infile, \
                open(output_path, mode="w", newline="", encoding="utf-8") as outfile:
                
                reader = csv.DictReader(infile)
                headers = [col for col in reader.fieldnames if col.lower() != "id"]
                writer = csv.DictWriter(outfile, fieldnames=headers)
                writer.writeheader()
                
                for row in reader:
                    new_row = {}
                    for col in headers:
                        new_row[col] = self.transform_boolean(row[col])
                    writer.writerow(new_row)
            
            self._logEvent("ACL_CLASS transformation complete.", self.outputWin)
        except Exception as e:
            self._logEvent(f"Error transforming ACL_CLASS: {e}", self.outputWin)
            return
        
        # Load ACL_CLASS into DB2
        self._logEvent("Loading ACL_CLASS into DB2...", self.outputWin)
        db2_schema = "ICWEBUSR"
        
        try:
            conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
            if not conn:
                raise Exception("Failed to connect to DB2 for ACL_CLASS load.")
            
            with open(output_path, mode="r", encoding="utf-8") as infile:
                reader = csv.reader(infile)
                headers = next(reader)
                
                for row in reader:
                    values = []
                    for val in row:
                        if val is None or val.strip() == "":
                            values.append("NULL")
                        else:
                            values.append("'" + val.replace("'", "''") + "'")
                    
                    sql = f"INSERT INTO {db2_schema}.ACL_CLASS ({', '.join(headers)}) VALUES ({', '.join(values)})"
                    escaped_sql = sql.replace("'", "''").replace("\n", " ")
                    result, lines = self.execCommand(
                        f'''/QOpenSys/usr/bin/system "RUNSQL SQL('{escaped_sql}') COMMIT(*NONE)"''',
                        outputWin=None, conn=self._conn
                    )
            
            ibm_db.close(conn)
            self._logEvent("ACL_CLASS loaded into DB2 successfully.", self.outputWin)
        except Exception as e:
            self._logEvent(f"Error loading ACL_CLASS into DB2: {e}", self.outputWin)
    
    # Transform and load ACL_SID with user ID mapping
    def transform_and_load_acl_sid(self):
        """Step 2: Transform ACL_SID by replacing PostgreSQL user IDs with DB2 user IDs."""
        input_filename = "public_acl_sid.csv"
        output_filename = "ACL_SID.csv"
        
        input_path = os.path.join(self.output_dir, input_filename)
        output_path = os.path.join(self.transformed_dir, output_filename)
        
        # Step 1: Build a mapping from PostgreSQL user ID to username
        pg_userid_to_username = {}
        pg_users_file = os.path.join(self.output_dir, "public_user_entity.csv")
        
        with open(pg_users_file, mode="r", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                if "id" in row and "username" in row:
                    pg_userid_to_username[row["id"]] = row["username"]
        
        # Step 2: Build a mapping from username to DB2 user ID
        username_to_db2_userid = {}
        
        try:
            # Connect to DB2 to get usernames and IDs
            conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
            if conn:
                query = "SELECT ID, USERNAME FROM ICWEBUSR.USERS"
                stmt = ibm_db.exec_immediate(conn, query)
                result = ibm_db.fetch_assoc(stmt)
                
                while result:
                    if "ID" in result and "USERNAME" in result:
                        username_to_db2_userid[result["USERNAME"].lower()] = str(result["ID"])
                    result = ibm_db.fetch_assoc(stmt)
                
                ibm_db.close(conn)
        except Exception as e:
            self._logEvent(f"Warning: Error retrieving DB2 user data: {str(e)}", self.outputWin)
            self._logEvent("Will continue with transformation using available mappings", self.outputWin)
        
        # Step 3: Transform the ACL_SID data
        with open(input_path, mode="r", encoding="utf-8") as infile, \
            open(output_path, mode="w", newline="", encoding="utf-8") as outfile:
            
            reader = csv.DictReader(infile)
            writer = csv.writer(outfile)
            
            # Write header (excluding ID column)
            writer.writerow(["PRINCIPAL", "SID"])
            
            # Store original PostgreSQL entries for positional mapping
            pg_acl_sid_entries = []
            
            # Process each row
            for row in reader:
                pg_acl_sid_entries.append(row)
                pg_id = row["id"]
                principal = self.transform_boolean(row["principal"])
                sid = row["sid"]
                
                # If principal is TRUE (1), replace PostgreSQL user ID with DB2 user ID
                if principal == 1:
                    # Get the username for this PostgreSQL user ID
                    username = pg_userid_to_username.get(sid, "")
                    
                    if username and username.lower() in username_to_db2_userid:
                        # Replace with DB2 user ID
                        db2_userid = username_to_db2_userid[username.lower()]
                        writer.writerow([principal, db2_userid])
                    else:
                        self._logEvent(f"Warning: Could not map PostgreSQL user ID {sid} to DB2 user ID", self.outputWin)
                        continue
                else:
                    writer.writerow([principal, sid])
        
        self._logEvent("ACL_SID transformation complete.", self.outputWin)
        
        # Step 4: Load the transformed data into DB2
        self._logEvent("Loading ACL_SID into DB2...", self.outputWin)
        
        # If ACL_SID table has existing entries, clear them first to ensure ID consistency
        try:
            conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
            if conn:
                try:
                    ibm_db.exec_immediate(conn, "DELETE FROM ICWEBUSR.ACL_SID")
                    self._logEvent("Cleared existing ACL_SID entries for clean insertion", self.outputWin)
                except:
                    pass  # Ignore errors if table is empty or can't be cleared
                ibm_db.close(conn)
        except Exception as e:
            self._logEvent(f"Warning: Could not clear ACL_SID table: {str(e)}", self.outputWin)
            self._logEvent("Continuing with insertion anyway", self.outputWin)
        
        # Insert rows from the transformed CSV into DB2
        with open(output_path, mode="r", encoding="utf-8") as infile:
            reader = csv.reader(infile)
            next(reader)  # Skip header
            
            row_counter = 0
            for row in reader:
                row_counter += 1
                
                if len(row) < 2:  # Skip invalid rows
                    continue
                    
                principal = row[0]
                sid = row[1]
                
                safe_sid = sid.replace("'", "''")
                
                sql = f"INSERT INTO ICWEBUSR.ACL_SID (PRINCIPAL, SID) VALUES ({principal}, '{safe_sid}')"
                escaped_sql = sql.replace("'", "''").replace("\n", " ")
                
                # Execute the SQL
                try:
                    self.execCommand(
                        f'''/QOpenSys/usr/bin/system "RUNSQL SQL('{escaped_sql}') COMMIT(*NONE)"''',
                        outputWin=None, conn=self._conn
                    )
                except Exception as e:
                    self._logEvent(f"Error inserting row {row_counter}: {str(e)}", self.outputWin)
        
        # Step 5: Create positional mapping for ACL_ENTRY
        self._logEvent("Creating positional mapping for ACL_ENTRY...", self.outputWin)
        
        self.pg_acl_sid_id_to_db2_acl_sid_id = {}
        
        pg_ids = [row["id"] for row in pg_acl_sid_entries]
        pg_ids.sort(key=lambda x: int(x))
        
        for i, pg_id in enumerate(pg_ids, 1):
            db2_id = str(i)
            self.pg_acl_sid_id_to_db2_acl_sid_id[pg_id] = db2_id
        
        self._logEvent(f"Created positional mapping for {len(self.pg_acl_sid_id_to_db2_acl_sid_id)} ACL_SID entries", self.outputWin)
        
        for pg_id, db2_id in sorted(self.pg_acl_sid_id_to_db2_acl_sid_id.items(), key=lambda x: int(x[0])):
            self._logEvent(f"PG ACL_SID.ID {pg_id} -> DB2 ACL_SID.ID {db2_id}", self.outputWin)
        
        self._logEvent("ACL_SID loading complete.", self.outputWin)
    
    # Transform and load ACL_OBJECT_IDENTITY with sorting
    def transform_and_load_acl_object_identity(self):
        """Step 3: Transform ACL_OBJECT_IDENTITY from extracted data and load it into DB2."""
        input_filename = "public_acl_object_identity.csv"
        output_filename = "ACL_OBJECT_IDENTITY.csv"
        
        input_path = os.path.join(self.output_dir, input_filename)
        output_path = os.path.join(self.transformed_dir, output_filename)
        
        if not os.path.exists(input_path):
            self._logEvent(f"Error: {input_filename} not found in extracted data.", self.outputWin)
            return
        
        # Transform ACL_OBJECT_IDENTITY
        try:
            with open(input_path, mode="r", encoding="utf-8") as infile:
                reader = csv.DictReader(infile)
                all_rows = list(reader)
                
                # Sort rows by object_id_identity in ascending order
                all_rows.sort(key=lambda row: int(row.get("object_id_identity", 0)) if row.get("object_id_identity", "").isdigit() else 0)
            
            with open(output_path, mode="w", newline="", encoding="utf-8") as outfile:
                # Exclude ID column
                exclude_columns = self.table_mappings["acl_object_identity"].get("exclude_columns", [])
                headers = [col for col in all_rows[0].keys() if col.lower() not in exclude_columns]
                
                writer = csv.DictWriter(outfile, fieldnames=headers)
                writer.writeheader()
                
                for row in all_rows:
                    new_row = {}
                    for col in headers:
                        # Transform boolean values
                        new_row[col] = self.transform_boolean(row[col])
                    writer.writerow(new_row)
            
            self._logEvent("ACL_OBJECT_IDENTITY transformation complete.", self.outputWin)
        except Exception as e:
            self._logEvent(f"Error transforming ACL_OBJECT_IDENTITY: {e}", self.outputWin)
            return
        
        # Load ACL_OBJECT_IDENTITY into DB2
        self._logEvent("Loading ACL_OBJECT_IDENTITY into DB2...", self.outputWin)
        db2_schema = "ICWEBUSR"
        
        try:
            conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
            if not conn:
                raise Exception("Failed to connect to DB2 for ACL_OBJECT_IDENTITY load.")
            
            with open(output_path, mode="r", encoding="utf-8") as infile:
                reader = csv.reader(infile)
                headers = next(reader)
                
                for row in reader:
                    values = []
                    for val in row:
                        if val is None or val.strip() == "":
                            values.append("NULL")
                        else:
                            values.append("'" + val.replace("'", "''") + "'")
                    
                    sql = f"INSERT INTO {db2_schema}.ACL_OBJECT_IDENTITY ({', '.join(headers)}) VALUES ({', '.join(values)})"
                    escaped_sql = sql.replace("'", "''").replace("\n", " ")
                    result, lines = self.execCommand(
                        f'''/QOpenSys/usr/bin/system "RUNSQL SQL('{escaped_sql}') COMMIT(*NONE)"''',
                        outputWin=None, conn=self._conn
                    )
            
            ibm_db.close(conn)
            self._logEvent("ACL_OBJECT_IDENTITY loaded into DB2 successfully.", self.outputWin)
        except Exception as e:
            self._logEvent(f"Error loading ACL_OBJECT_IDENTITY into DB2: {e}", self.outputWin)

    # Transform and load ACL_ENTRY with SID mapping
    def transform_and_load_acl_entry(self):
        """Step 4: Transform ACL_ENTRY from extracted data and load it into DB2 with SID mapping."""
        input_filename = "public_acl_entry.csv"
        output_filename = "ACL_ENTRY.csv"
        
        input_path = os.path.join(self.output_dir, input_filename)
        output_path = os.path.join(self.transformed_dir, output_filename)
        
        if not os.path.exists(input_path):
            self._logEvent(f"Error: {input_filename} not found in extracted data.", self.outputWin)
            return
        
        pg_aclsid_to_db2_aclsid = {}
        
        pg_acl_sid_file = os.path.join(self.output_dir, "public_acl_sid.csv")
        if os.path.exists(pg_acl_sid_file):
            with open(pg_acl_sid_file, mode="r", encoding="utf-8") as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    pg_sid_id = row.get("id")
                    pg_principal = self.transform_boolean(row.get("principal", "0"))
                    pg_sid = row.get("sid", "")
                    
                    if not pg_sid_id or not pg_sid:
                        continue
                    
                    if pg_principal == 1:
                        db2_user_id = self.pg_id_to_db2_id.get("USERS", {}).get(pg_sid)
                        
                        if db2_user_id and db2_user_id in self.acl_sid_id_mapping:
                            db2_acl_sid_id = self.acl_sid_id_mapping[db2_user_id]
                            pg_aclsid_to_db2_aclsid[pg_sid_id] = db2_acl_sid_id
                    else:
                        if pg_sid in self.acl_sid_id_mapping:
                            db2_acl_sid_id = self.acl_sid_id_mapping[pg_sid]
                            pg_aclsid_to_db2_aclsid[pg_sid_id] = db2_acl_sid_id
        
        if not pg_aclsid_to_db2_aclsid:
            self._logEvent("No ACL_SID mappings found, using direct ID mapping as fallback.", self.outputWin)
            try:
                conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
                if conn:
                    query = "SELECT ID FROM ICWEBUSR.ACL_SID ORDER BY ID"
                    stmt = ibm_db.exec_immediate(conn, query)
                    db2_ids = []
                    result = ibm_db.fetch_assoc(stmt)
                    while result:
                        db2_ids.append(str(result["ID"]))
                        result = ibm_db.fetch_assoc(stmt)
                    ibm_db.close(conn)
                    
                    for i in range(1, len(db2_ids) + 1):
                        pg_id_str = str(i)
                        if i <= len(db2_ids):
                            pg_aclsid_to_db2_aclsid[pg_id_str] = db2_ids[i-1]
            except Exception as e:
                self._logEvent(f"Error retrieving DB2 ACL_SID IDs: {str(e)}", self.outputWin)
        
        self._logEvent(f"Created mapping for {len(pg_aclsid_to_db2_aclsid)} ACL_SID entries", self.outputWin)
        
        with open(input_path, mode="r", encoding="utf-8") as infile, \
            open(output_path, mode="w", newline="", encoding="utf-8") as outfile:
            
            reader = csv.DictReader(infile)
            exclude_columns = ["id"]
            headers = [col for col in reader.fieldnames if col not in exclude_columns]
            
            writer = csv.DictWriter(outfile, fieldnames=headers)
            writer.writeheader()
            
            processed_count = 0
            skipped_count = 0
            
            for row in reader:
                new_row = {}
                skip_row = False
                
                pg_acl_sid_id = row.get("sid")
                if pg_acl_sid_id in pg_aclsid_to_db2_aclsid:
                    new_row["sid"] = pg_aclsid_to_db2_aclsid[pg_acl_sid_id]
                else:
                    self._logEvent(f"Skipping ACL_ENTRY - no mapping for ACL_SID.ID: {pg_acl_sid_id}", self.outputWin)
                    skipped_count += 1
                    continue
                
                for col in headers:
                    if col != "sid":
                        new_row[col] = self.transform_boolean(row.get(col, ""))
                
                writer.writerow(new_row)
                processed_count += 1
            
            self._logEvent(f"ACL_ENTRY transformation complete. Processed: {processed_count}, Skipped: {skipped_count}", self.outputWin)
        
        self._logEvent("Loading ACL_ENTRY into DB2...", self.outputWin)
        db2_schema = "ICWEBUSR"
        
        conn = ibm_db.connect("*LOCAL", "ICWEBUSR", "ICWEBUSR")
        if not conn:
            self._logEvent("Failed to connect to DB2 for ACL_ENTRY load.", self.outputWin)
            return
        
        with open(output_path, mode="r", encoding="utf-8") as infile:
            reader = csv.reader(infile)
            headers = next(reader)
            
            inserted_count = 0
            for row in reader:
                values = []
                for val in row:
                    if val is None or val.strip() == "":
                        values.append("NULL")
                    else:
                        values.append("'" + val.replace("'", "''") + "'")
                
                sql = "INSERT INTO " + db2_schema + ".ACL_ENTRY (" + ", ".join(headers) + ") VALUES (" + ", ".join(values) + ")"
                escaped_sql = sql.replace("'", "''").replace("\n", " ")
                
                result, lines = self.execCommand(
                    "/QOpenSys/usr/bin/system \"RUNSQL SQL('" + escaped_sql + "') COMMIT(*NONE)\"",
                    outputWin=None, conn=self._conn
                )
                inserted_count += 1
        
        ibm_db.close(conn)
        self._logEvent(f"ACL_ENTRY loaded into DB2 successfully. Inserted {inserted_count} entries.", self.outputWin)
    
    def migrate_data(self):
        self._logEvent("Starting migration to new database.", self.outputWin)
        # 1. Extraction
        self.extract_tables_from_db("ricw_keycloak", self.keycloak_tables_to_extract)
        self.extract_tables_from_db("ricw_server", self.server_tables_to_extract)
        self._logEvent("Data extraction complete.", self.outputWin)
        # 2. Transformation
        self._logEvent("Starting CSV transformation.", self.outputWin)
        self.transform_all_csv()
        self._logEvent("CSV transformation complete.", self.outputWin)
        # 3. Santize Users and groups for unicode charaters
        self._logEvent("Sanitizing data.", self.outputWin)
        self.sanitize_transformed_csv()
        # 4. Load Main Tables into DB2 (and update ID mappings)
        self._logEvent("Starting DB2 load for main tables.", self.outputWin)
        self.load_main_tables_to_db2()
        # 5. Transform Mapping Tables (with updated IDs)
        self._logEvent("Transforming mapping tables with updated IDs.", self.outputWin)
        for filename in os.listdir(self.output_dir):
            table_name = filename.replace(".csv", "").replace("public_", "")
            if table_name in [
                "user_group_membership", 
                "group_role_mapping", 
                "user_role_mapping", 
                "icw_user_preference", 
                "icw_event_log_download",
                "icw_common_download", 
                "icw_report_record"
            ]:
                self.transform_mapping_table(filename)
        # 6. Load Mapping Tables into DB2
        self._logEvent("Starting DB2 load for mapping tables.", self.outputWin)
        self.load_mapping_tables_to_db2()
        
        # 7. ACL Tables processing
        self._logEvent("Starting ACL tables processing.", self.outputWin)
    
        # Step 1: Transform and load ACL_CLASS
        self._logEvent("Step 1: Processing ACL_CLASS table.", self.outputWin)
        self.transform_and_load_acl_class()
        
        # Step 2: Transform and load ACL_SID (with user ID mapping)
        self._logEvent("Step 2: Processing ACL_SID table.", self.outputWin)
        self.transform_and_load_acl_sid()
        
        # Step 3: Transform and load ACL_OBJECT_IDENTITY
        self._logEvent("Step 3: Processing ACL_OBJECT_IDENTITY table.", self.outputWin)
        self.transform_and_load_acl_object_identity()
        
        # Step 4: Transform and load ACL_ENTRY
        self._logEvent("Step 4: Processing ACL_ENTRY table.", self.outputWin)
        self.transform_and_load_acl_entry()
    
        self._logEvent("Migration complete.", self.outputWin)
        return 0
        
_gServerModel = ServerModel()


def GetModel():
    return _gServerModel


def main():

    model = GetModel()



if __name__ == '__main__':
    main()