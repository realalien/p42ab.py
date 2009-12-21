#!/usr/bin/env python

import os

class NotImplementedException(Exception):
    pass

class AB:
    
    # 'long  => short' command name mapping, used in checking or validation
    AB_CMDS = { }
    
    VALID_ARGS = ("get")
    
    def __init__(self, executable):
        self.executable =  executable
        # TODO: check version info
        self.args = []
        self.output = """"""
    
    def getworkingpath(self):
        self.args = []
        self.args.extend("getworkingpath")
        self.call()
        return self.output
    
    def call(self):
        self.output = os.popen(self.executable + " " + " ".join(self.args) ).read()
        return self.output
        
        
    # ESP.TODO: use meta programming to generate commands from syntax knowledge,
    # e.g. getworkingpath call should be validated and sent to msg receiver.
    
    
if __name__ == '__main__':
    ab = AB("C:\Program Files (x86)\alienbrain\Client\Application\Tools\ab.exe")
    print(ab.getworkingpath())

# ESP. COMMMANDS

## log on
#ab logon -u Administrator -p "mes0Spicy" -d p4mirror -s Spicyfile


## setup ab local workspace, ready to import changeSet
#ab -


## add file
#ab 



#Usage Examples:
#---------------
#ab help checkout
#ab h gl
#ab enumprojects -s NXNSERVER
#ab logon -u John -p "" -d Demo_Project -s NXNSERVER
#ab setworkingpath "c:\myworkingpath\Demo_Project"
#ab enumobjects
#ab isuptodate picture1.bmp
#ab find -checkedoutby "John"
#ab checkout picture1.bmp -comment "Modifying background" -response:CheckOut.Writ
#able y
#ab logoff