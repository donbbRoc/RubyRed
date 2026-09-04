import logging


# Using @property decorator
class FuncParamter:
    def __init__(self, funcName):
        self._funcName = funcName

    @property
    def name(self):
        return self._funcName

    @name.setter
    def name(self, value):
        self._funcName = value

class ParamWithOutput(FuncParamter):
    def __init__(self, modelData):
        FuncParamter.__init__(self, __class__.__name__)
        self._outputWin = None

        if modelData:
            self._outputWin = modelData.outputWindow

    @property
    def outputWin(self):
        return self._outputWin

    @outputWin.setter
    def outputWin(self, value):
        self._outputWin = value


class InitDBParam(ParamWithOutput):
    def __init__(self, modelData):
        ParamWithOutput.__init__(self, modelData)

        self._outputWin = None
        self._pgdata = None
        self._profile = None
        self._profilePwd = None
        self._dbUser = None
        self._logfile = None
        self._zipPath = None

        if modelData:
            self._pgdata = modelData.pgdata
            self._profile = modelData.profile
            self._profilePwd = modelData.profilePwd
            self._dbUser = modelData.dbUser
            self._outputWin = modelData.outputWindow
            self._logfile = modelData.logfile
            self._zipPath = modelData.zipPath

    @property
    def zipPath(self):
        return self._zipPath

    @zipPath.setter
    def zipPath(self, value):
        self._zipPath = value

    @property
    def pgdata(self):
        return self._pgdata

    @pgdata.setter
    def pgdata(self, value):
        self._pgdata = value

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
    def logfile(self):
        return self._logfile

    @logfile.setter
    def logfile(self, value):
        self._logfile = value


class InstallServerParam(ParamWithOutput):
    def __init__(self, modelData):
        ParamWithOutput.__init__(self, modelData)

        self._zipPath = None
        self._unzipPath = None
        self._installationPath = None
        self._rpmTar = None
        self._servicePkg = None
        self._jarPkg = None
        
        self._servicePath = None
        self._initSql = None
        self._dbUser = None
        self._dbPwd = None
        self._pUser = None
        self._pPwd = None

        if modelData:
            self._zipPath = modelData.zipPath
            self._unzipPath = modelData.unzipPath
            self._rpmTar = modelData.rpmTar
            self._servicePkg = modelData.servicePkg
            self._jarPkg = modelData.jarPkg
            self._servicePath = modelData.servicePath
            self._initSql = modelData.initSql   
            self._dbUser = modelData.dbUser
            self._dbPwd = modelData.dbPwd
            self._pUser = modelData.pUser
            self._pPwd = modelData.pPwd
    @property
    def unzipPath(self):
        return self._unzipPath

    @unzipPath.setter
    def unzipPath(self, value):
        self._unzipPath = value

    @property
    def zipPath(self):
        return self._zipPath

    @zipPath.setter
    def zipPath(self, value):
        self._zipPath = value

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


class InstallAgentParam(ParamWithOutput):
    def __init__(self, modelData):
        ParamWithOutput.__init__(self, modelData)

        self._zipPath = None

        self._pUser = None
        self._pPwd = None

        self._agentIp = str()
        self._agentPort = str()

        if modelData:
            self._zipPath = modelData.zipPath

            self._pUser = modelData.pUser
            self._pPwd = modelData.pPwd

            self._agentIp = modelData.agentIp
            self._agentPort = modelData.agentPort


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

    @property
    def agentPort(self):
        return self._agentPort

    @agentPort.setter
    def agentPort(self, value):
        self._agentPort = value


class UninstallParam(ParamWithOutput):
    def __init__(self, modelData):
        ParamWithOutput.__init__(self, modelData)

        self._zipPath = None
        # self._deploymentPath = None

        self._pUser = None
        self._pPwd = None
        self._agentIp = str()
        self._agentPort = str()

        self._bStopAgent = True
        self._bRemoveAgent = False

        self._bStopJava = True
        # self._bStopRedis = True
        self._bStopNginx = True
        self._servicePath = None
        self._dbIp = str()
        self._bRemoveICW = True
        self._bRemoveDBDATA = True
        
        self._bDelRpm = True
        # self._bDelRedis = True
        self._bDelNginx = True
        self._bDelConf = True


        if modelData:
            # self._deploymentPath = modelData.deploymentPath
            self._pUser = modelData.pUser
            self._pPwd = modelData.pPwd
            self._agentIp = modelData.agentIp
            self._agentPort = modelData.agentPort

            self._bStopAgent = modelData.bStopAgent
            self._bRemoveAgent = modelData.bRemoveAgent

            self._bStopJava = modelData.bStopJava
            # self._bStopRedis = modelData.bStopRedis
            self._bStopNginx = modelData.bStopNginx

            self._bRemoveICW = modelData.bRemoveICW
            self._bRemoveDBDATA = modelData.bRemoveDBDATA

            self._servicePath = modelData.servicePath
            self._dbIp = modelData.dbIp
        
            self._bDelRpm = modelData.bDelRpm
            # self._bDelRedis = modelData.bDelRedis
            self._bDelNginx = modelData.bDelNginx
            self._bDelConf = modelData.bDelConf


    # @property
    # def deploymentPath(self):
    #     return self._deploymentPath

    # @deploymentPath.setter
    # def deploymentPath(self, value):
    #     self._deploymentPath = value

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

def main():
    # create an object
    funcParam = FuncParamter('FuncParamter')

    print(funcParam.name)

    funcParam.name = 'testFunc2'

    print(funcParam.name)

    installfunc = ParamWithOutput("test3")

    print(installfunc.name)
    print(installfunc.outputWin)

    installfunc.outputWin = 'testFunc4'

    print(installfunc.name)
    print(installfunc.outputWin)


if __name__ == '__main__':
    main()