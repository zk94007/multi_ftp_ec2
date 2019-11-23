#!/usr/bin/python3  
#-*- coding: utf-8 -*-                                                                                                                           

import os
import sys
import random
from datetime import datetime

# Get ftp user name from argument
ftp_username = 'USR_YTUZRXGOAC_{}'.format(sys.argv[1])

# Generate 16-bit random password
ftp_password =  "".join(random.sample("abcdefghijklmnopqrstuvwxyz01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ", 16))

print(ftp_username)
print(ftp_password)

os.system('sudo adduser --disabled-password --force-badname --gecos "" {}'.format(ftp_username))
os.system('sudo usermod --password {} {}'.format(ftp_password, ftp_username))
