import os
import sys
import subprocess
import time
import select
import re
import csv
import socket
import glob

import logging
from enum import Enum

EType = Enum('EType', ['Root', 'Blank', 'Comment', 'Element'])

EState = Enum('EState', ['Brace', 'Item', 'End', 'Error'])

nginxConfPath = '/QOpenSys/etc/nginx/nginx.conf'
iClusterItem = ('http', '    include /opt/iCluster-web/portal/icluster.conf;\n')

# brace
class Element:
    def __init__(self, origin, etype, idx):
        self.type = etype
        # begin line
        self.begin = idx
        self.count = 0
        # origin String in conf
        self.origin = origin

        # Statement is End?
        self.stat = EState.Error
        self.elements = []
        self.name = ''
        self.value = ''

        if self.type == EType.Element:
            self.stat = self.parse()
        elif self.type == EType.Root:
            self.stat = EState.Brace
        else :
            self.stat = EState.Item


    def parse(self):
        rStr = self.origin.rstrip()
        if rStr[-1] == ';':
            lstr = self.origin.lstrip()
            idx = lstr.find(' ')
            self.name = lstr[:idx]
            self.value = lstr[idx:]
            return EState.Item

        elif '}' in rStr:
            return EState.End

        elif '{' in rStr:
            idx = self.origin.find('{')
            self.name = self.origin[:idx].strip()
            return EState.Brace

        else:
            raise Exception('EState.Error')
            return EState.Error


    # def __repr__(self):
    #     if self.count == 0:
    #         return f'{self.begin + 1}: {self.type.name}: {self.name} {self.value}\n'
    #     else: 
    #         return f'{self.begin + 1}: {self.type.name}: {self.name} {self.value}\n' + str(self.elements) + '\n'


    def add(self, element):
        self.elements.append(element)
        self.count += 1


    def compare(self, element):
        if self.type == element.type and \
           self.name == element.name and \
           self.value == element.value:
           
           return 0

        return -1



def origin(element, showNum = False):
    lineNum = ''

    if showNum == True:
        lineNum = f'{element.begin + 1}  '

    if element.type == EType.Blank:
        return f'{lineNum}\n'

    else:
        if element.count > 0:
            originStr = f'{lineNum}{element.origin}'
            for  item in element.elements:
                originStr += f'{origin(item)}'
            return originStr
        else:
            return f'{lineNum}{element.origin}'


class NginxConf():
    def __init__(self, filename):
        self.filename = filename
        self.elements = None
        self.exist = set()

    
    def parseLine(self, origin, idx):
        lStr = origin.lstrip()
        if len(lStr) == 0: 
            # blank line
            return Element(origin, EType.Blank, idx)
        elif lStr[0] == '#':
            # comment
            return Element(origin, EType.Comment, idx)
        else :
            # element
            return Element(origin, EType.Element, idx)

    def parse(self):

        stack = list() 
        self.elements = Element('', EType.Root, 0)

        # stack Push Root element
        stack.append(self.elements)

        with open(self.filename, "r") as conf:
            idx = 0
            for line in conf:
                element = self.parseLine(line, idx)
                idx += 1

                if element.type in (EType.Blank, EType.Comment):
                    stack[-1].add(element)
                elif element.type == EType.Element:
                    if element.stat == EState.Brace:
                        # PUSH
                        stack[-1].add(element)
                        stack.append(element)
                    elif element.stat == EState.Item:
                        stack[-1].add(element)
                    elif element.stat == EState.End:
                        # POP
                        stack[-1].add(element)
                        stack[-1].stat = EState.End
                        stack.pop()
                    else:
                        raise Exception('EState.Error')
                else:
                    # Error
                    raise Exception('EType.Error')

            if len(stack) > 0:
                stack[-1].stat = EState.End
                stack.pop()
            
            if len(stack) > 0:
                raise Exception('stack Error')

        # level1 = self.elements.elements
        # print(''.join(map(origin, level1)))

        # # Add item in HTTP Section
        # httpInclude = Element("    include /opt/iCluster-web/portal/icluster.conf;\n", EType.Element, 0)
        # for item in level1:
        #     if item.name == 'http':
        #         item.elements.insert(-2, httpInclude)
        

        # print(''.join(map(origin, level1)))

        return  True


    def addItem(self, section, itemStr):
        # "    include /opt/iCluster-web/portal/icluster.conf;\n"
        confItem = Element(itemStr, EType.Element, 0)

        level1 = self.elements.elements
        for item in level1:
            if item.name == section:
                founded = False
                for subElement in item.elements:
                    if subElement.compare(confItem) == 0:
                        founded = True

                if founded == False:
                    item.elements.insert(-2, confItem)
                else :
                    break


    def removeItem(self, section, itemStr):
        # "    include /opt/iCluster-web/portal/icluster.conf;\n"
        confItem = Element(itemStr, EType.Element, 0)

        level1 = self.elements.elements
        for item in level1:
            if item.name == section:
                founded = False
                foundItem = None
                for subElement in item.elements:
                    if subElement.compare(confItem) == 0:
                        founded = True
                        foundItem = subElement

                if founded == True and foundItem:
                    item.elements.remove(foundItem)
                else :
                    break


    # use example removeByKeys(['http', 'server'], {'listen':'80;', .....})
    def removeByKeys(self, keys, condition, elements = None):
        if elements is None:
            keyCnt = len(keys)
            if keyCnt is 0:
                # Key Error
                return False

            elements = self.elements.elements

        for item in elements:
            if item.name == keys[0]:
                if len(keys) > 1:
                    return self.removeByKeys(keys[1:], condition, item.elements)
                else :
                    # condition check
                    matched = True
                    for key,value in condition.items():
                        result = list(filter(lambda x: x.name.strip() == key and x.value.strip() == value, item.elements))
                        matched &= True if len(result) > 0 else False

                    if matched:
                        elements.remove(item)
                    return True
        # Not found key
        return False


    def encode(self):
        level1 = self.elements.elements
        return ''.join(map(origin, level1))

    def save(self):
        strAll = self.encode()
        if len(strAll) > 0:
            with open(self.filename, "w") as conf:
                conf.write(strAll)
        return True


def main():

    nginxConf = NginxConf('/QOpenSys/etc/nginx/nginx.conf.default')
    nginxConf.parse()
    nginxConf.addItem('http', '    include /opt/iCluster-web/portal/icluster.conf;\n')

    # Remove default 80 port
    nginxConf.removeByKeys(['http', 'server'], {'listen':'80;'})
    strAll = nginxConf.encode()
    print(strAll)

    # nginxConf.save()

if __name__ == '__main__':
    main()
