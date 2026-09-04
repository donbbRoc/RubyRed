
import sys
import subprocess
import re
import argparse
from os import path

import logging

import postgres_tools

class Services():
    def __init__(self):
        self.pg_help = postgres_tools.pg_help

    def get_pg_status(self):
        return self.pg_help.get_status()


def main():
    services = Services()
    print(services.get_pg_status())



if __name__ == '__main__':
    main()
