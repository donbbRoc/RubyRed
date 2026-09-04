import os
import sys
import tempfile
from enum import Enum

CfgType = Enum('CfgType', ['Blank', 'Comment', 'Element'])

class CSVProfile():
    def __init__(self):
        self.profiles={ }
        self.ordered = []
        self.exist = set()


    def read_properties(self, filepath):
        """ Reads a given properties file with each line of the format key=value.  Returns a dictionary containing the pairs.

        Keyword arguments:
            filename -- the name of the file to be read
        """
        self.profiles = {}
        self.ordered = []

        with open(filepath, "r") as configFile:
            for line in configFile:
                trimed = line.strip()

                if line[0] in ('#', ';'):
                    self.ordered.append((CfgType.Comment, trimed.rstrip('\r\n')))
                elif len(trimed) == 0:
                    self.ordered.append((CfgType.Blank, ''))
                else :
                    fields = trimed.split(sep='=', maxsplit=1)
                    if len(fields) == 2:
                        self.profiles[fields[0]] = fields[1]
                        self.ordered.append((CfgType.Element, fields[0], fields[1]))
                    else:
                        raise Exception('CfgType.Error')

        self.exist = set(self.profiles.keys())
        return self.profiles

    def append_blank(self):
        self.ordered.append((CfgType.Blank, ''))


    def write_properties(self, filepath, dictionary=None):
        """ Writes the provided dictionary in key-sorted order to a properties file with each line of the format key=value

        Keyword arguments:
            filename -- the name of the file to be written
            dictionary -- a dictionary containing the key/value pairs.
        """

        if dictionary == None:
            dictionary=self.profiles
        with open(filepath, "w+") as proFile:

            for line in self.ordered:
                if line[0] == CfgType.Blank:
                    # writer.writerow([])
                    proFile.write('\n')
                elif line[0] == CfgType.Comment:
                    # writer.writerow([line[1]])
                    proFile.write(f'{line[1]}\n')
                elif line[0] == CfgType.Element:
                    if line[1] in dictionary:
                        proFile.write(f'{line[1]}={dictionary[line[1]]}\n')
                    else :
                        # profile has been deleted
                        continue
                else :
                    raise Exception('CfgType.Error')

            for key in dictionary:
                if key not in self.exist:
                    # new profile
                    proFile.write(f'{key}={dictionary[key]}\n')

def main():
    """Unit test the profile parser and writer
    """

    configTestStr = """# comment line
REGISTRY_IP=10.112.103.133
REGISTRY_PORT=8761
REG_SERVER=$REGISTRY_IP

#
JHIPSTER_URL=${REGISTRY_IP}:${REGISTRY_PORT}/eureka/



JHIPSTER_SLEEP=20
SPRING_PROFILES_ACTIVE=prod,oauth2
SPRING_SECURITY_USER_PASSWORD=admin
JHIPSTER_REGISTRY_PASSWORD=admin
SPRING_CLOUD_CONFIG_SERVER_COMPOSITE_0_TYPE=native
SPRING_SECURITY_OAUTH2_CLIENT_PROVIDER_OIDC_ISSUER_URI=http://${KEYCLOAK_IP}:${KEYCLOAK_PORT}/realms/jhipster

# IcAgent
NODE_HOSTNAME=RICDEVB

GUIAGENT_HOSTNAME=10.117.42.36
GUIAGENT_PORT=4545

AGENT_PORT=8086
GRPC_PORT=9090

# For http
TRUSTSTORE=
TRUSTSTOREPWD=
# For https
# TRUSTSTORE=-Djavax.net.ssl.trustStore=/opt/iCluster-agent/truststore.jks
# TRUSTSTOREPWD=-Djavax.net.ssl.trustStorePassword=123456
TRUSTSTORE1=-Djavax.net.ssl.trustStore=/opt/iCluster-agent/truststore.jks
"""

    fpIn  = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    fpIn.write(configTestStr)
    fpIn.close()
    # print(f'fpIn.name{fpIn.name}')

    envProfile = CSVProfile()
    envProfile.read_properties(fpIn.name)

    fpOut = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    fpOut.close()

    # Append new property
    envProfile.profiles['AppendProperty1'] = 'TestValue'
    envProfile.profiles['AppendProperty2'] = 2002
    envProfile.profiles['AppendProperty3'] = False

    # Write profile to file
    envProfile.write_properties(fpOut.name)

    # print(f'fpOut.name{fpOut.name}')
    with open(fpOut.name, 'r') as f:
        for line in f:
            print(line.rstrip('\r\n'))

    os.unlink(fpIn.name)
    os.unlink(fpOut.name)


if __name__ == '__main__':
    main()
