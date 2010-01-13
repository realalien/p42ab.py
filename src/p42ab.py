
import os, sys
import subprocess
import logging
import re
import time
from ConfigParser import ConfigParser


from datetime import datetime 

# ++++++++++++ VERY IMPORTANT ISSUES +++++++++++++
# * since the incremental sync may be interrupted, the process should be carefully logged
# * TODO: 2010.1.5 clean the code
# * TODO: write utilities methods to prevent any unexpected operations in the migration.
# * WHY: It looks like only in the cli that we can find script error?! Why can't eclipse?
# * POSTPONE: for office project, 'branch,integrate,purge' will not be implemented right now!
# * TODO: alienbrain command exception handle, interrupt or continue.

# ++++++++++++ BASIC SETUP  +++++++++++++
AB_USERNAME="Administrator"
AB_PASSWORD="mes0Spicy"
AB_PROJECT="p4migtest"          # the project name in the AlienBrain server
AB_SERVER="Spicyfile"

# NOTE: It would be better that create the workspace by hand for migration use before migration. 
P4PORT="localhost:1666"
P4USER="ZhuJiaCheng"  
P4PASSWORD="mes0Spicy"   
P4CLIENT="ZhuJiaCheng_test_specify_p4_env" # workspace


# ++++++++++++ logging facilities +++++++++++++
# better if use command argument
LOG_FILENAME = 'migration.log'
LOG_LEVEL = logging.DEBUG
logging.basicConfig(filename=LOG_FILENAME,level=LOG_LEVEL)

logger = logging.getLogger('MyLogger')
logger.setLevel(logging.INFO)  #DEBUG
# Add the log message handler to the logger
#handler = logging.FileHandler(LOG_FILENAME, maxBytes=1024*1024, backupCount=5)
handler = logging.FileHandler(LOG_FILENAME)
handler2 = logging.StreamHandler()

handler.setLevel(logging.INFO) #DEBUG
handler2.setLevel(logging.INFO) #DEBUG
logger.addHandler(handler)
logger.addHandler(handler2)

# ++++++++++++ function code  +++++++++++++
def debug(text):
    #logger.debug("------>>>  " + str(text))
    pass

def quoted(text):
    # avoid None param
    if text:
        str = text
        str.replace("\"", "'")
    # add quotation mark for dir/file names with blankspace    
    if not text.startswith("\""):
        return "\"" + str + "\""
    else:
        return str  
    
class NotImplementedException(Exception):
    def __init__(self,  reason):
        self.reason = reason


class OperationFailedException(Exception):
    """Thrown when one or a series of p4 or ab commands(wrapper in methods) can not be fully executed
    
    Attributes:
        op -- input expression in which the error occurred
        reason -- explanation of the error, maily from a ab's stdout or p4's exeption 
    """

    def __init__(self, op, reason):
        self.op = op
        self.reason = reason

    
    

class AlienBrainCLIWrapper:
    """AlienBrain command line tool wrapper, to get data easier with scripting,
    The API design will mimic the ones of Perforce, see: 'Perforce 2009.1 APIs 
    for Scripting' """
    # Q: is it a good way to parse stdout, stderr?
    
    # 'long  => short' command name mapping, used in checking or validation
    AB_CMDS = { }
    
    session = None  # obj must have sth. to record.
    auto_reconnect = True
    
    def __init__(self):
        # self.executable =  executable
        # TODO: check version info
        self.args = []
        self.output = ""
        self.potential_failed_file_dir = {}
        self.failed_ab_commands = []        # list of 2-item tuples, for defensive audit use
        
        if not self.connected(): self.logon(AB_USERNAME, AB_PASSWORD, AB_PROJECT, AB_SERVER)
        logger.debug("AlienBrainCLIWrapper#__init__ ... done! ")  # better if there is a post function call. Some modules?
        
#    def call(self):
#        self.output = os.popen(self.executable + " " + " ".join(self.args) ).read()
#        return self.output
        
        
    # ESP.TODO: use meta programming to generate commands from syntax knowledge,
    # e.g. getworkingpath call should be validated and sent to msg receiver.
    
#    def cmd(self, cmd_string):
#        """ simply get stdout and stderr from executing a commandline, it seems the result
#        parsing should be done by the each caller."""
#        proc = subprocess.Popen(cmd_string,
#                        shell=True,
#                        stdin=subprocess.PIPE,
#                        stdout=subprocess.PIPE,
#                        stderr=subprocess.PIPE,
#                        )
#        
#        stdout_value, stderr_value = proc.communicate()
#        print(stdout_value + " <<<= stdout")
#        print(stderr_value + " <<<= stderr")
        
    # Q: how to get output and return value simultaneously
    # INFO: it's an example of using subprocess.call()
    def call_using_subproc(self, cmd_string):
        """"""
        debug(cmd_string)
        retcode = subprocess.call(cmd_string, shell=True, stdin=PIPE)
        out = sys.stdout.readlines()
        err = sys.stderr.readlines()
        debug("return code " + str(retcode))
        debug(out) 
        debug(err)
        #debug(sys.__stderr__.readlines())
        return (retcode, sys.stdout, sys.stderr)
        
    # INFO, 
    def call(self,cmd_string):
        # ESP. get familiar with system call from python doc. the web page.
        process = subprocess.Popen(cmd_string, shell=True, stdin=subprocess.PIPE, 
                                   stdout=subprocess.PIPE )
        (child_stdout, child_stdin) = (process.stdout, process.stdin)
#        out = sys.stdout.readlines()
#        err = sys.stderr.readlines()

        # detect for error, usually the error will be output the stdout.
        stdout = child_stdout.readlines()
        
        logger.debug(cmd_string)
        logger.debug(stdout) 
        if stdout:
            # Q: shall I stop the processing(migration)?
            # SUG: it would be better to record the erorr.
            self.failed_ab_commands.append( (cmd_string, stdout ) )
            # Q: how to implement a atomic process, making sure the interrupted process can be rollbacked. 
            # CONT. looking into other project impl.
        process.stdin.close()
        val = process.wait()
        if  val != 0:
            logger.warn("There were feedback from server(not error really): %s " % stdout)
            logger.warn("   when issuing command [%s] , wait returns %s"  % ( cmd_string, val) ) 
            return False
        else:
            return True
        
    # damned, it should be generated from documentation or self-help.
    def logon(self, username, password, project, ab_server):
        cmd_str = " ".join(['ab', 'logon','-u', username, '-p',password, '-d', project, '-s', ab_server])
        self.call(cmd_str)
    
    def logoff(self): 
        cmd_str = " ".join(['ab','logoff'])
        self.call(cmd_str)
        
    def connected(self):
        cmd_str = " ".join(['ab','ic'])
        self.call(cmd_str)
    
    def setworkingpath(self,dir):
        #TODO: avoid blankspace and slash '\'
        cmd_str = " ".join(['ab','setworkingpath', quoted(dir) ])
        self.call(cmd_str)    
        
    def getworkingpath(self):
        #TODO: avoid blankspace and slash '\'
        cmd_str = " ".join(['ab','getworkingpath'])
        self.call(cmd_str)
    
    def apply_actions_on_files(self, p4_chg_detail):
        """ add, edit, delete files according to an perforce changelist spec
        @param p4_chg_detail: a dict of p4 changelist spec
        """
        # validation of p4_chg, TODO: more strict check
        
        if not p4_chg_detail.has_key('action'):
            return
        
        if len(p4_chg_detail['depotFile']) != len(p4_chg_detail['action']):
            raise OperationFailedException("apply_actions_on_files", "p4_chg corrupted, could not be migrate to Alienbrain")
        
        self.new_changeset_as_default("noname.default")  # looks lifeless,  but it exists in a session
        
        
        #Q: how to know the local directory of a file from //depot without view mapping info? 
        for i in range(0, len(p4_chg_detail['action']) ):
            file_in_depot = p4_chg_detail['depotFile'][i]  
            debug("file: %s \n" %  file_in_depot )
            action = p4_chg_detail['action'][i]
            debug("action: %s \n" % action )
            localdir = self.path_in_the_workspace("D:/p4migtest",file_in_depot, p4env) # @attention: use the dict that contain the view, not the value of the key. 
            debug ("local dir is : %s \n " % localdir )
            
            
            #######################################################
            # trial of alienbrain tool section.
            #######################################################
            # Test out all the actions offered by alienbrain and mapp
            # * submit empty directory  ... (AB's GUI ... OK! Scripting ...when 'ab import', auto generate a changeset, not like GUI. MUST create a changeset aforehand )
            # * group individual changes into ChangeSet ... ()
            #    >>> import new file  without assigning a changeset(Scripting ... )
            #    >>> new a file  
            #        .... without assigning a changeset (Scripting ... no ok, ) 
            #        .... with assigning a changeset (Scripting ... ) 
            #        .... Q: ok with 'synchronize -importall'? 
            #    >>> delete a file  
            #        .... without assigning a changeset (Scripting ...  no action at all)
            #        .... with assigning a changeset (Scripting ... script not OK, no action at all)
            #        .... ESP: also remember to delete from local workspace, not just remove from   (ab delete -deletelocal <file>  )
            #        .... ESP: avoid any kind of deletion-prompting.
            
        
            # * ESP, from manual ops, one action performed by p4.exe may be transferred to AB
            #   in more-than-one-step, e.g. add action => import, use a named/unnamed changeset,
            #   then submit to AB server.
            
            
            #######################################################
            # process for migration.
            #######################################################
            #TODO, experiment with python's lambda here if you have extra time!
            # TODO
            if action == "add":
                self.import_file_or_dir(file_in_depot)
            elif   action == "edit":
                # check out the file into the default changeset
                self.checkout(localdir)   #also see: NOTES 2010.1.5
                debug("ready to perform [%s] on file:[%s]" %  (action, localdir))
            elif action == "delete" :
                self.delete_file_or_dir(file_in_depot)
            elif action == "branch" :  # should be handled by the caller function.   
                # ESP, I doubt branch migration should not be carried out based on each file, maybe better based on change of higher level
                # Q: in AB, I can not create a branch from directory, which means I have to branch all the files/folders of the 
                # 'Root Branch'  
                
                # IMPORTANT: after some experiments, in AB, I found that after encountering a change with branching action from P4, 
                # there is no need to get that change(hopefully there is no other action), we can create branch using existing files
                # in the alienbrain server(hopefully having no previous changelists missed) , and the directory created by p4 branching
                # should be the working path of the branch.
                 
                # SUG: familiar yourself with branch/integrate functionalities in 'Alienbrain Advanced' GUI tool                
                pass
            elif action == "integrate" :  # should be handled by the caller function.
                # INFO: for alienbrain, we can either integrate from 'a branch's folder'(? why not multiple folder?) or from 'submitted changelist'
                # similarly, in p4, integrate from branch spec, 
                pass 
        #all files/dirs processed, submit the changeset
        # TODO: we should keep all the p4 data as much as possible
        who = str(p4_chg_detail['user'].strip())
        when = time.ctime(int(p4_chg_detail['time'])).strip()
        chg_id = str(p4_chg_detail['change'].strip())
        from_p4 = " ... P4 CL: " + chg_id + " | " + who + " | " + when
        comm = str(p4_chg_detail['desc'].strip().replace("\"", "'")) + from_p4  # remove the last carriage return key., replace double quote
        self.submit_changeset(comment=comm)    
        
        # apply the action in the alienbrain workdir.
    def create_branch(self, name, branch_view):
        """
        @param branch_view: a map from which the alienbrain should set branch's working path.
        Q: one problem remains, how to get all the branch info from a changelist, how can I ensure that submit only works on branching. 
        
        raw data of view from p4:
                //depot/projectA/... //depot/projectA_VS/...
        
        MAKE IT CLEAR: 
                There is a brain mapping here, in AB, the branch copies all the files under the 'Root Branch', 
                but in P4, a branch can just be part of directories/files.
                
                When migrating branches from P4 to AB, we should not overwrite the P4 branches folder at the client side
                (really no need to use directory for the client when migrating),
                we need to use different working path for each new branch so that some changelists can be appied to that branches.
        
                It's really a problem when migrating changelist for a branch, since we use different directories for p4 and ab,
                which means ab can not get any new changelist info from p4 branche directory. 
                                
                !!! Maybe we should use the same directory, make sure when doing sth. operations!!!
                It seems that this could be solved just by using two mapping, 
                from p4's view, we knew which directory contains a branched code, 
                    if a total branch from p4 depot, very good, AB can reuse the directory.
                    if part of the p4 depot(e.g. subfolder of depot), at least we know what files in which directory has changed, 
                        later can BE COPIED to AB's branch working path's sub-folder by using the first part 4 view  
        """
        #TODO: exception handle, rollback if any call fails.
        # create branch
        cmd_str = " ".join(['ab','createbranch', name, '-parent', quoted('Root Branch') ])
        self.call(cmd_str)
        # shift to branch in order to carry out branch related task
        cmd_str = " ".join(['ab','setactivebranch', name ])
        self.call(cmd_str)
        # set working path   # th
        #cmd_str = " ".join(['ab','setworkingpath', "d:\temp" ])
        #self.call(cmd_str)
        # shift back to main branch
        cmd_str = " ".join(['ab','setactivebranch', quoted('Root Branch') ])
        self.call(cmd_str)
        
        
    def delete_file_or_dir(self, a_depot_path):
        
        # ----------------------------------------
        # TODO: refactor to method
        debug("ready to delete: " + a_depot_path)
        parent_path = ""
        project_rel_path = ""            
        if "/" in a_depot_path: # may has parent dir  # TODO: must have at least 3 slashes to make sure there are an directory
            parent_path = os.path.dirname(a_depot_path)
        
        if a_depot_path:
            project_rel_path = parent_path.replace("//depot","")  # remember to replace both heading and tailing slash around depot.

        #assemble for one opt
        if project_rel_path and project_rel_path.strip() != "":
            ppath_str = "-parent " + "\"" + project_rel_path + "\""
        else:
            ppath_str  = ""
        
        #assemble Response, see: "Command Line Tool.pdf, P11, Default Response" of AlienBrain 7 documentation.
        response = "-response:Delete.Warning 0"   
           
        debug("p4 depot path: " + a_depot_path) 
        debug("parent_path: " + parent_path) 
        debug("ppath_str: " + ppath_str)
        debug("project_rel_path: [" + project_rel_path+"]")
        # ----------------------------------------
        if self.existsindb(quoted(project_rel_path)) and self.existsindb( quoted(a_depot_path.replace("//depot","")) ):
             cmd_str = " ".join(['ab','delete', quoted(self.path_in_the_workspace("d:/p4migtest", a_depot_path, p4env)) , "-deletelocal", response])
             self.call(cmd_str)
        
    
    def import_file_or_dir(self, a_depot_path):
        """delegate the 'ab import' command, 
        
        @attention: the file is a depot path from p4 server, when being imported by 'ab import', it should automatically import the parent directory if not present.  
        
        TODO: I wish to set the command options by default, maybe later allowing user to specify!
        """
#        IMPORT_PARAM = [ "-comment" , "-parent", "-dontgetlocal", "-dontfollowsymlink", "-ignoreexisting", "-norecursive", "-checkout"]
#        for arg in args:
#            if arg not in IMPORT_PARAM: raise "Invalid parameter for import command"
#        for key in kwargs.keys():
#            if key not in IMPORT_PARAM: raise "Invalid parameter for import command"
        
        debug("ready to import: " + a_depot_path)
        parent_path = ""
        project_rel_path = ""            
        if "/" in a_depot_path: # may has parent dir  # TODO: must have at least 3 slashes to make sure there are an directory
            parent_path = os.path.dirname(a_depot_path)
        
        if a_depot_path:
            project_rel_path = parent_path.replace("//depot","")  # remember to replace both heading and tailing slash around depot.

        #assemble for one opt
        if project_rel_path and project_rel_path.strip() != "":
            ppath_str = "-parent " + "\"" + project_rel_path + "\""
        else:
            ppath_str  = ""
        #assembly comment
        #comment = "-comment 'I did it'"
        
        debug("parent_path: " + parent_path) 
        debug("ppath_str: " + ppath_str)
        debug("project_rel_path: [" + project_rel_path+"]")
        
        if  project_rel_path.strip() != "":  
            if not self.existsindb(project_rel_path): 
                self.import_file_or_dir("//depot"+project_rel_path) # since the recursive call need a depot path, we have to make add it ok
#        cmd_str = " ".join(['ab','import', project_rel_path, ppath_str])
        cmd_str = " ".join(['ab','import', "\"" + self.path_in_the_workspace("d:/p4migtest", a_depot_path, p4env) + "\"", ppath_str, "-ignoreexisting"]) # add quotation around file/dir names
        debug("import file ..." + cmd_str)
        self.call(cmd_str)
    
    def existsindb(self, path):
        cmd_str = " ".join(['ab','existsindb', quoted(path) ])
        return self.call(cmd_str)
        
        
    def checkout(self, abs_path ): # to be more useful, *args should be merged into opts of the arguments and do some sanity check.
        # TODO: may discriminate file/dir
        cmd_str = " ".join(['ab','checkout', quoted(abs_path) ])
        self.call(cmd_str)
        
    
    def new_changeset_as_default(self, name="Unnamed"):
        """ since the pending change will all go to the default changeset which is explicitly specified by the users, 
        It has to be made crystal clear in case any miss handling of changeset and changes.  
        
        It looks like the name has no use in the alienbrain database, just a temperary container name! 
        
        It would be better to use ruby alike block, like 
          ab.new_changeset  do | chg|      
               chg.import()
               chg.move()
               chg.delete()          
          end
        which makes code more expressive!
        
          @attention:  UNTESTED
        """
        cmd_str = " ".join(['ab','getdefaultchangeset',name])
        if self.call(cmd_str):
            cmd_str = " ".join(['ab','setdefaultchangeset', name])
        else:
            cmd_str = " ".join(['ab','newchangeset', name])
            self.call(cmd_str)
            cmd_str = " ".join(['ab','setdefaultchangeset', name])
            self.call(cmd_str)   
        # TODO:  avoid error with existing named changeset
    
    def submit_changeset(self, name=None, comment="No comment!"):
        """
        If name is empty , adding some preemptive process for the weak command line process
        @param name: The name of the change set to submit.
        @attention: UNTESTED, the 'submitpendingchanges -changeset <name> ' failed to work under vista , ab7 edition
        """
        if not name:
            cmd_str = " ".join(['ab','submitpendingchanges', '-comment', quoted(comment)])
            self.call(cmd_str)
        else:
            cmd_str = " ".join(['ab','submitpendingchanges', '-changeset', name, '-comment', quoted(comment)])  # failed or not working
            self.call(cmd_str)
        

    def submit_file(self,file):    
        pass
    
    def submit_change():
        """submit changes on the workspace after calling an p4 sync"""
        #TODO: sanity check to prevent the interrupted one or duplicated one! 
        #TODO: ??make it atomic? rollback ab's change if not fulfilled.  
        pass


    def format_view_key_to_pattern(self, string):
        """To convert a p4workspace's //depot directory into a pattern for later search 
        """   
        return "^"+string.replace("/","\\/").replace("...",".*").replace("*.*","[^\/]*\.[^\/]*")+"$"

    # TODO: move to AlienBrainCLIWrapper or Util class!
    def get_single_best_match(self, depot_path, depot_view_keys):
        """find the most suitable depot_view_keys according to a depot path
        See also: test_single_best_match
        
        Attention,
        For now, the only supported depot path format is like "//depot/dir/a.txt" and "//depot/dir/..."
        I don't know if this format is allowed "//depot/.../directory/c.txt", but such wildcard matching is not implemented.
        """
        
        the_best_matching_key = None
        for key in depot_view_keys:
            found = re.match(self.format_view_key_to_pattern(key), depot_path)
            if found:
                if the_best_matching_key == None:
                    the_best_matching_key = key
                else:
                    # ESP. this judge is quite crucial, maybe still leaky?! 
                    if len(key) > len(the_best_matching_key): 
                        the_best_matching_key = key
                    else:
                        # TODO: the logic is not fully anticipated the potential unexpected. 
                        # Already has a matching, but length of the key is shorter.
                        # * ESP. there is a possibility that a short key may be a file key in depot_view_keys, 
                        #   its length may shorter than the wildcard key.
                        #   e.g. "a_depot_path4" should match "//depot/a", not"//depot/...". Use unit tests! 
                        # * It MUST be very strict in accepting such key!
                        if  (os.path.dirname(the_best_matching_key) == os.path.dirname(key)):
                             # since at the same directory, the "..." should be the least matching one.
                             if (os.path.basename(the_best_matching_key) == "..." 
                                    and os.path.basename(key) != "..." ):
                                 the_best_matching_key = key
            else:
                continue
        
        #print("###    depot path: [ %s ],  matching key: [ %s ]"  % (depot_path, str(the_best_matching_key) ))

        return the_best_matching_key  

    def path_in_the_workspace(self, workspace_basedir, a_depot_path, view):
        """
        depends on: get_single_best_match
         
        I think it's a good way to compile the the first part of view mapping as a regular express, 
        then matching a_deport_path to find the most suitable one!"
        
        map the //depot... to local directory from a preset view of p4 workspace,
        this method should give a absolute directory if fed one directory in the depot. 
        The absolute path of a file is got from p4's view and p4's client specification, 
        the path will be used to apply actions at the alienbrain's side.
        
        The difficulty is how to match the longest the map's values for a specific file.
    
        
        @param workspace_basedir: the location of the workspace, should be part of the value as shown in the 'view's key, if not, the value of 'view' dict, ????
        @param a_depot_path: the file/dir location in the view of p4 depot, should starts with //depot/
        @param view: a dict which should have key named 'view'
        """
        
        # template replace
        # TODO: see if neccessary!
        map_depot_to_local_dir = self.parse_p4_view_map(view)
        depot_workspace_dir = None   
        absolute_workspace_dir = None
        
        #TODO: ESP. potential mapping failure if single mapping on files, like \\depot
        # Here below are typical key-values in an expected p4 view mapping.  
        # key: //depot/dir/a.txt  value://wksp/rid/rib2/a.txt
        # key: //depot/dir/dir\...    value://sksp/rib2/...
        # key: //depot/dir/*.c    value://sksp/rib/rib2/*.c
        best_match = self.get_single_best_match( a_depot_path, map_depot_to_local_dir.keys() )
                
        if best_match:
            # value can be a file-file mapping or dir-dir mapping. 
            value = map_depot_to_local_dir[best_match]
            depot_workspace_dir = a_depot_path.replace(os.path.dirname(best_match)  , os.path.dirname(value) )
        else:
            # record the a_depot_path which has no corresponding 
            self.potential_failed_file_dir[a_depot_path] = "Not find proper mapping in p4 view"  
            logger.error("file[%s] can not find a proper mapping in the p4 view! ")                     

        # ----- Deprecated: ---- 
        # old implementation is not safe, guessing! Because //depot/dir1/... could be overwritten by a later entry //depot/dir1/1/...
        #temp = []        
        #candidate = ""
        #for key in map_depot_to_local_dir.keys():
            #temp.append(os.path.dirname(key))
            #if os.path.dirname(key) in a_depot_path:
                # prepare the longest mapping key for return value
                #if os.path.dirname(key) != None and len(os.path.dirname(key)) >= len(candidate) and os.path.dirname(key)!= candidate :
                #    candidate = os.path.dirname(key)
                #    symbolic_workspace_dir = a_depot_path.replace( os.path.dirname(key), map_depot_to_local_dir[key].replace("/...","") )
        # record the a_depot_path which has no corresponding 
        #if len(temp) != 1:
        #    self.potential_failed_file_dir[a_depot_path]= temp         
        # ----  end of deprecated ---- 
       
        # DONE: either one or none, see: get_single_best_match(). Assertion on all the file in p4 depot could only have one match.
        
        
        # get the 'client spec' or use param '' to convert  symbolic_workspace_dir to the 
        # TODO: use user_spec if better.
        if depot_workspace_dir:
            absolute_workspace_dir = depot_workspace_dir.replace("//"+ p4env['client'], workspace_basedir)
        
        #debug("the potential key is : " + candidate)
        #debug("the local symbolic path is: " + symbolic_workspace_dir)
        #debug("the local absolute path is: " + absolute_workspace_dir)
        
        return absolute_workspace_dir
        

    def parse_p4_view_map(self, wksp_spec):
        """Giving a p4 
        
        It's part of the steps which get a absolute path from a p4 view map and workspace abs path.
        See also:  

        It not suggested do many string manipulation here, as little as possible!
        
        @param wksp_spec: a dict, p4 workspace specification.
        """
        
        map_depot_to_local_dir = {}
        symbolic_workspace_dir = ""   # in a symbolic path
        if type(wksp_spec)  == type(dict()):
            # parse the multiple line of view mapping, hopefully each entry is on the just one line.
            view = wksp_spec['view']
            lines = view.split("\n")
            for line in lines:
                line = line.strip()
                
                if  line.strip().startswith("//depot") or line.strip().startswith("+//depot"):
                    if len(line.split(" ")) > 2 : 
                        logger.error(line + "<<<line has more than 1 blankspace, we won't process this entry. Does a directory name have spaces?!")
                        continue
                    (key, value ) = line.split(" ")
                    key = key.strip()       #remove heading/trailing spaces
                        
                    if key.startswith("+"): #remove multiple line view symbol "+"
                        key = key[1:]
                    if key.startswith("-"):
                        pass                #we don not add "-//depot//somewhere" entry as files in that directory  usually do not exist in depot, thus no migration.
                    if key and value:       #store in new dict after some cleaning.
                        map_depot_to_local_dir.update( {key:value} )    
        #debug(map_depot_to_local_dir)
        #debug("-------------- find the map view ------------------")
        
        return map_depot_to_local_dir
#if __name__ == '__main__':
#    ab = AB("C:\Program Files (x86)\alienbrain\Client\Application\Tools\ab.exe")
#    print(ab.getworkingpath())

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

from P4 import P4, P4Exception
import os
from operator import itemgetter
import operator


#TODO: logging

p4env = {
    'port': P4PORT,
    'user': P4USER,
    'passwd': P4PASSWORD,
    'client':'ZhuJiaCheng_test_specify_p4_env',
    'branch':'',
    'charset':'',
    #'customview':'''View:
    'view':'''
     //depot/... //ZhuJiaCheng_test_specify_p4_env/...
''',
    # depre: 'workspace' : 'Admin_spicyfile_1666_NightlySlave',  # => buildbot auto-generated by rules
    }

#    //depot/Alice2_Prog/Development/... //ZhuJiaCheng_test_specify_p4_env/Development/...
#    +//depot/Alice2_Prog/Tools/... //ZhuJiaCheng_test_specify_p4_env/Tools/...
#    +//depot/Alice2_Bin/PC_Dependencies/... //ZhuJiaCheng_test_specify_p4_env/PC_Dependencies/...
#    +//depot/Alice2_Bin/Binaries/... //ZhuJiaCheng_test_specify_p4_env/Binaries/...
#    +//depot/Alice2_Bin/Engine/... //ZhuJiaCheng_test_specify_p4_env/Engine/...
#    +//depot/Alice2_Bin/AliceGame/... //ZhuJiaCheng_test_specify_p4_env/AliceGame/...
#    +//depot/Alice2_Bin/*.* //ZhuJiaCheng_test_specify_p4_env/*.*
#    +//depot/Alice2_Branches/... //ZhuJiaCheng_test_specify_p4_env/Alice2_Branches/...

#ab = AB.AB()



class P4PYAPIWrapper:
    
    def __init__(self): # should input a p4env assigned by the API users
        self.p4 = P4()
        
        self.p4.client = p4env['client']
        self.p4.port = p4env['port']
        self.p4.user = p4env['user']
        self.p4.password = p4env['passwd']
        #p4.charset = p4env['charset']
        
        #TODO: lock format by setting API level!!!
        self.p4.exception_level = 1 # ignore "File(s) up-to-date"
        
        # logging if exception
        try:
            if not self.p4.connected(): self.p4.connect() 
        except P4Exception:
            for e in self.p4.errors:
                logger.error(e)
            raise
        
        #TODO: implement exception according to https://kb.perforce.com/HardwareOsNe..rkReference/NetworkIssues/NetworkError..ndowsServer
        logger.debug("P4PYAPIWrapper#__init__ ... done! ")

    #    finally:
    #        p4.disconnect()
            
    def change_workdir(self, dir):
        """ change to the desired the directory for migration, in case of
        any undesired default directory.
        
        @param dir: the absolute directory in which the migration is carried out.    
        """
        clientspec = self.p4.fetch_client()
        if os.path.exists(dir):
            clientspec['Root'] = dir
        self.p4.save_client(clientspec)  
    
    
    def p4_get_changes(self):
        """
        @return: a list of change
        """
        if not self.p4.connected():
            self.p4.connect()
            self.p4.run_login( P4PASSWORD )
        changes = []
        # TODO: see if need to get branch related changelist, it looks like 
        #  for a2, no way to get changelists from branch info.
        try:
            changes = self.p4.run('changes', '-t', '-l')
        except P4Exception:
            for e in self.p4.errors:
                logger.error(str(e))
            raise OperationFailedException("p4 changes", "See log, please!")
    
        deco = [( int(change['change']), change) for change in changes ]
        deco.sort()
        changes = [ change for (key, change) in deco]
        
        # better replace with unit test.
        logger.debug(" ------   peeding heading changelist  ----")
        logger.debug(changes[0].__class__)
        logger.debug(changes[0])
        logger.debug(changes[1])
        logger.debug(changes[0]['desc'])
        logger.debug(changes[0]['time'])
        logger.debug(changes[0].keys())
        logger.debug(" ------   end   ----")
        logger.debug("P4PYAPIWrapper#p4_get_changes... DONE!")
        return changes
    
    def tell_files_actions(self, change):
        """Given an changelist, it shall tell how many files fall into the categories of 'add','delete','edit','branch', 'integral'
        
        @return: a dict containing the number of each action.
        """
        if type(change) == type(dict()) and change.has_key("action"):
            actions = change['action']    
            logger.debug("in change, add: %d, edit: %d, delete: %d, branch: %d, integrate: %d" % 
                        ( actions.count("add"), actions.count("edit"),actions.count("delete"),
                          actions.count("branch"),actions.count("integrate") )  )
            return {"add":actions.count("add"), 
                "edit":actions.count("edit"),
                "delete":actions.count("delete"),
                "branch":actions.count("branch"),
                "integrate":actions.count("integrate") }
        else:
            logger.info("no change spicified or no actions found in change [%s]!" % str(change['change']))
            return {}
        
    
    def is_branch_changelist(self, change):
        if type(change) == type(dict()) and change.has_key("action") and ("branch" in change['action']):
            return True
        else:
            return False
        
    def is_integrate_changelist(self, change):
        if type(change) == type(dict()) and change.has_key("action") and ("integrate" in change['action']):
            return True
        else:
            return False
    
    def p4_get_change_details(self, change):
        change_num = change['change'];
        #debug( "ready to get detail of changelist %s \n " % str(change_num))
        #debug("p4_get_change_details: %s \n" % str(change_num) );
        try:
            detail = self.p4.run('describe', '-s', change_num);
        except P4Exception:
            for e in self.p4.errors:
                logger.error(str(e))
            raise OperationFailedException("p4 changes", "See log, please!")
        
        if int(change_num) % 50  == 0: 
            logger.debug("P4PYAPIWrapper#p4_get_change_details %s... DONE!" % str(change_num) )   
        return detail[0]   
    #    raise "stop here"
    #    error_count = p4.ErrorCount();
    #    errors = p4.Errors();
    #    p4.Disconnect();
    #    if error_count:
    #        debug("Skipping $change_num due to errors:\n$errors\n")
    #    return undef;
    #    
    #    my %result;
    #    result['author'] = change->{'user'};
    #    result{'log'}  = change->{'desc'};
    #    result{'date'} = time2str(SVN_DATE_TEMPLATE, change->{'time'});
    #    for (my i = 0; i < @{change->{'depotFile'}}; i++) {
    #    my file = change->{'depotFile'}[i];
    #    my action = change->{'action'}[i];
    #    my type = change->{'type'}[i];
    #    if (is_wanted_file(file)) {
    #        push @{result{'actions'}}, {'action' => action,
    #                                     'path' => file,
    #                                     'type' => type};  
    #    



class MigrationWorker:
    """It supposed to be a single thread program!
    
    Its tasks include,
        env. setup, prepare for all the pre-requistes.
        orchestra all the processes, e.g. migrate single change or in a range,
        work counting, e.g. how many changes going to migrate, working progress,
        work report, e.g. generate a report to assess migration outcome, 
        exception handling, and record error. 
    """    
    
    # Q:see necessity of const impl., see: http://code.activestate.com/recipes/414140/
    global LAST_MIGRATED_CHANGE_NUM_LOGFILENAME ; LAST_MIGRATED_CHANGE_NUM_LOGFILENAME = ".p4.mig.cl"
    global LAST_MIGRATED_CHANGE_NUM_PROPERTY_NAME ; LAST_MIGRATED_CHANGE_NUM_PROPERTY_NAME = "last_migrated_change_num"
    global SECTION_NAME; SECTION_NAME = "history"
    global NON_MIGRATED ; NON_MIGRATED = 0   # to signify that such workspace is clean and has not done any kind of migration.
    
    def __init__(self, ab_exec, p4_exec, abs_path_wksp):
        # It must know the absolute path of the executables to carry out the task
        # Q: p4_src the p4 info from which the changes are migrated. 
        #    Some of the alienbrain's info should get directly from p4 connection instance. Like what?
        if os.path.exists(ab_exec) and os.path.exists(p4_exec):
            self.ab = AlienBrainCLIWrapper()  # ab, p4 instance really means correspoding api agent.
            self.p4 = P4PYAPIWrapper()
            self.poll_period = 10
            self.map_id_to_detail = {}
            # create workspace if not present
            if not os.path.exists(abs_path_wksp):
                # create 
                os.mkdir(abs_path_wksp)
                self.abs_path_wksp = abs_path_wksp
            else:
                self.abs_path_wksp = abs_path_wksp
            
            mig_log = os.path.normpath(os.path.join(self.abs_path_wksp, LAST_MIGRATED_CHANGE_NUM_LOGFILENAME)) 
            if not os.path.exists(mig_log):
                fp = open(mig_log ,"w")
                fp.close() 
                logger.warn(".p4.mig.cl not exists in the workspace, creating new one.") 
                logger.warn("It indicates that you are going to do the 'one-time' migration task, otherwise, create that file with last migrated changelist number!")
                logger.warn("------------------------")
                cfg = ConfigParser()
                cfg.add_section(SECTION_NAME)
                cfg.set(SECTION_NAME, LAST_MIGRATED_CHANGE_NUM_PROPERTY_NAME, int(NON_MIGRATED))
                fp = open(mig_log,"w")
                cfg.write(fp)
                fp.close() # Q: could be any exception here? handling outside!
                
                
            # anyway, we should read the value from file
            cfg = ConfigParser()
            fp = open(mig_log,"r")
            cfg.readfp(fp)
            # print(cfg.sections())
            num = -1 
            if cfg.has_option(SECTION_NAME, LAST_MIGRATED_CHANGE_NUM_PROPERTY_NAME):
                num = cfg.get(SECTION_NAME, LAST_MIGRATED_CHANGE_NUM_PROPERTY_NAME)
            fp.close() # Q:
            self.set_last_migrated_changelist_num(num)
            logger.info("Migration start from changelist %s" % str(num) )
            time.sleep(5)     
        else:
            logger.info("Either of the AB and P4 executable ")
            logger.info("Finished at " + datetime.now().strftime("%d/%m/%y %H:%M:%S"))
            logger.info("--------------------------------------------------------------")
            sys.exit()

    def get_last_migrated_changelist_num(self):
        """Getter for instance variable 'last_migrated_changelist_num' """
        return self.last_successful_migration_cl
    
    
    def set_last_migrated_changelist_num(self, last_successful_mig_cl):
        """Setter for instance variable 'last_migrated_changelist_num' 
        @param last_migrated_changelist_num: the changelist number of the last successful migration.
        """
        self.last_successful_migration_cl = last_successful_mig_cl
        
        
    def record_last_migrated_changelist_num(self, last_successful_mig_cl):
        """
        Read and write the .p4.mig.cl file(under target 'working dir' as in AB /'workspace' as in P4, for now, they share the same directory!) 
        to record the latest changelist of a workspace.  
        It could be used to check last updated changelist or act as a secondary revision checking after p4 changelist hooking.
        
        @param abs_path_wksp: the absolute path of the target workspace for migration.
        """
        self.set_last_migrated_changelist_num(last_successful_mig_cl)
        cfg = ConfigParser()
        file_abspath = os.path.join(self.abs_path_wksp, LAST_MIGRATED_CHANGE_NUM_LOGFILENAME)
        cfg.add_section(SECTION_NAME)
        cfg.set(SECTION_NAME, LAST_MIGRATED_CHANGE_NUM_PROPERTY_NAME, int(last_successful_mig_cl))
        fp = open(file_abspath, "wb")
        cfg.write(fp)
        fp.close() # Q: could be any exception here? handling outside!
        logger.info("AlienBrainCLIWrapper#record_last_migrated_changelist_num  [ %s ]... Done!" % str(last_successful_mig_cl) )
        
    def know_workload(self):
        """get a general ideas on how many changes, how many files.
            One important task is to create a dict in which maps changeid to changedetails,
        this can be either used in migration operation or counting the any number.
        """
        map_id_to_detail = {}  # hopefully it will not explode the memory?!
        changes = self.p4.p4_get_changes()
        branched = 0
        integrated = 0
        for change in changes:
            id = change['change']
            self.map_id_to_detail[id] = self.p4.p4_get_change_details(change)
          
        # total number of changelist in p4
            if self.map_id_to_detail[id].has_key("action"):
                if "branch" in self.map_id_to_detail[id]['action']:
                    branched = branched + 1
                if "integrate" in self.map_id_to_detail[id]['action']:
                    integrated = integrated + 1
                    
        logger.info( "Total number of changelist which branches code in P4: " +  str(branched) )
        logger.info( "Total number of changelist which integrate code in P4: " +  str(integrated) )
        logger.info( "Start migration from changelist " +  str(int(self.last_successful_migration_cl) + 1 ) + " from P4 " )
        #logger.info( "Number of files among changeslist in P4: " +  str("") )
        
        
#    def doit(self, taskname=None, username="Administrator", password="mes0Spicy", project="p4migtest", ab_server="Spicyfile"):
#        # entrance of a unit of work
#        if self.ab: 
#            if not self.ab.connected():
#                self.ab.logon(username, password, project, ab_server)
    
    def anew_ab_server(self):
        """ To well mirrored a p4 server, one should has each corresponding changelist, 
        if the workspace is not clean, then AlienBrain may got tainted changes from workspace and will have more changelists than p4's server.
        """
        pass #TODO
        
    
    def migrate_one_time(self):        
        """just move acceptable changelists from p4 to ab
        since there will be more ops if migrateWorker does not know any previous change on file/dir, 
        for the momnent, only migrate changelist from no.1, better delete the depot in alienbrain first if redo."""
        
        #TODO: detect if the Alienbrain repository is absolute clean, if not , aborted.
        
        max_id = 0
        changes = self.p4.p4_get_changes()
        for change in changes:
            id = change['change']
            if int(id) > max_id: maxid = int(id)
        #self.migrate_by_changeno_range(range(1, max_id))
        self.migrate_by_changeno_range(range(1, 3))
        logger.debug("MigrationWorker#migrate_one_time...done!")
    
    
    def migrate_by_changeno(self, cl_num):
        """Attention: the migration is called by all kinds of migration tasks which based on changelist number, 
        its work plan is follow by a pre-calculated instance variable 'self.map_id_to_detail'(a dict) rather than by runtime detection,
        
        """
        
        # This step is critical to the migration! Otherwise stop! Really?! 
        # TODO: check this step OK or not!
        try:
            #TODO: level of abstraction is not correct, seemingly!
            self.p4.p4.run("sync","-f","//depot/...@%s" % cl_num )
            if self.p4.p4.warnings and len(self.p4.p4.warnings) > 0:
                logger.warn("Command [ sync -f //depot/...@%s ] has warning:"  % cl_num )
                logger.warn(self.p4.p4.warnings)
        except P4Exception:
            logger.error("Command [ sync -f //depot/...@%s ] has errors:"  % cl_num )
            for e in self.p4.p4.errors:
                logger.error(str(e))
        
        #detail = self.p4.p4_get_change_details(change)
        detail = self.map_id_to_detail.get(cl_num)
        
        # TODO: add unit test to avoid details without actions
        
        self.p4.tell_files_actions(detail)
        # TODO: Do branch or intergrate here? since there is no need to iterate through files in the change obj.
        # TODO: code change other than branches will be lost! amend!
        if self.p4.is_branch_changelist(detail):
            # get the branch details ? How do I know the name?
            # ab.create_branch(name)
            logger.warn("changelist %s branched code, we do not migrate it to AlienBrain!" % str(detail['change']) )
        if self.p4.is_integrate_changelist(detail):
            #pass #TODO
            logger.warn("changelist %s integrated code, we do not migrate it to AlienBrain!" % str(detail['change']))
        # migrate changelists which 'add','delete','edit' code
        try:
            self.ab.apply_actions_on_files(detail)
        except OperationFailedException:
            logger.error("Changelist [ %s ] failed to be migrated! " % id )
            raise opfe
        # ATTENTION, the recording of migrated changelist number is so important that I have to mingle it with migration code. 
        self.record_last_migrated_changelist_num(cl_num)
        logger.debug("MigrateWorker#migrate_by_changeno [ %s ]...done!" % str(cl_num) )
        
    def migrate_by_changeno_range(self, range):
        """
        One should add one more element to the range because the python's range excludes the element at the end of range
        @param range: a list, designate changelists to be migrated. 
        """
        #TODO: sort the range? 
        #if range[0] != 1:
        #    raise NotImplementedException("Please migrate from changelist #1, migrate from middle is not yet supported. ")
        
        #TODO: ESP, must have a record in case of any interruption.
        #    p4.run("sync","-f","//depot/...@%s" % demo_chg )
        
        #changes = self.p4.p4_get_changes()
        #debug("changes size %s"  % str(len(changes)) )

        # Attention: iteration through a map is not safe as the sequence unexpected!?
        range.sort()    # make sure migration changes are incremental from small to big number.
        
        # Undo last unsubmit change
        
        
        # migrate
        if 0 in range: range.remove(0)   # avoid user assigned range from 0
        if str(self.last_successful_migration_cl) != str(range[0] - 1):
            logger.error(str(range[0] - 1 ))
            logger.error(str(self.last_successful_migration_cl))
            raise OperationFailedException("migrate_by_changeno_range", "In AlienBrain#migrate_by_changeno_range() , it is assumed that 'last_successful_migration_cl = range[0]', please check the .p4.mig.cl file at the workspace") 
        for i in range:
            if self.map_id_to_detail.has_key(str(i) ):
                self.migrate_by_changeno( str(i) )
            else:
                logger.warning("Assigned value %s not in range! No such changelist!" % str(i) )
        #for change in changes:
            #id = change['change']
            #if int(id) in range: 
               #self.migrate_by_changeno(id)
        logger.debug("MigrateWorker#migrate_by_changeno_range from [%s] to [%s] ... done!" % ( str(range[0]), str(range[-1]) ))

    def migrate_to_latest_changeno(self):
        """ To migrate changelist to the lastest changeno spicified.         
        """
        changes = self.p4.p4_get_changes()
        # get from 
        if self.last_successful_migration_cl == NON_MIGRATED :
            start = 1
        else:
            start = int(self.last_successful_migration_cl) +1    # Attention: should not resubmit the last successful one, which may cause errors!
        
        end = int(changes[-1]['change'])
        logger.info("MigrateWorker#migrate_to_latest_changeno from [%s] to [%s] ... starting" % ( str(start ), str(end) ))
        self.migrate_by_changeno_range( range(start , end +1 ))
        logger.info("MigrateWorker#migrate_to_latest_changeno from [%s] to [%s] ... done!" % ( str(start), str(end) ))

    def ensure_workspace_unchanged(self):
        """
        NOT feasible, if last migration includes 'file delete', redo that one will not OK, thus can not ensure last one OK or not!
        see if we can apply last action without submit the change ... NOT FEASIBLE! """
        pass
        
    def sync_p4_to_ab(self):
        """Periodically pull the new changelist and apply them to the Alienbrain workspace, and then check into Alienbrain server"""
        while 1:
            self.carefully_sync_repos()
            time.sleep(self.poll_period)
    
    def poll_repo(self):
        # * To make sure that the continuing sync changelist can be applied, we can detect whether the later changelist details(e.g. changed files) exist!
        #   But this is not a good way to detect "up to which changelist has been app in this workspace."
        
        
        # * make sure that workspace is up-to the last synced one, 
        #   sometimes it may be removed, older changelist(of the p4) via manual operations, using other empty workspace, etc.
        
        
        # * if there is no error or any unexpected found, record to file for later use.
        
        
        # * since in p4 server, some changelist is not submitted, but the number is reserved, we should continue to check if those pending one are submitted
        #   according to the history recording.
        pass
        
    
    
    # copied from p4dti's src.
    def carefully_sync_repos(self):
        try:
            self.poll_repo()
            # Reset poll period when the poll was successful.
            self.poll_period = self.config.poll_period
        except AssertionError:
            # Assertions indicate severe bugs in the replicator.  It
            # might cause serious data corruption if we continue.
            # We also want these failures to be reported, and they
            # might go unreported if the replicator carried on
            # going.
            raise
        except KeyboardInterrupt:
            # Allow people to stop the replicator with Control-C.
            raise
        except:
            # TODO: send mail to notify
            logger.info("self.poll_period  is %s " % self.poll_period )  
            self.poll_period = self.poll_period * 2
        
        
if __name__ == '__main__':   
    # -----------------------  ab sandbox
    
    ab_exec = "C:/Program Files (x86)/alienbrain/Client/Application/Tools/ab.exe"
    p4_exec = "C:/Program Files (x86)/Perforce/p4.exe"
    
    mig_worker = MigrationWorker(ab_exec, p4_exec, "d:/p4migtest")
    
    mig_worker.know_workload()
    
    #mig_worker.migrate_by_changeno_range(range(1,2))
    #mig_worker.migrate_by_changeno_range(range(1,7))
    
    mig_worker.migrate_to_latest_changeno()
    
    
    #mig_worker.migrate_one_time()
    
#    ab = AB()
##    
#    ab.logon("Administrator", "mes0Spicy", "p4migtest ", "Spicyfile")
##    ab.getworkingpath()
##    ab.setworkingpath("d:/p4migtest")
##    ab.getworkingpath()
##    ab.connected()
##    ab.logoff()
##    ab.connected()
##    print "end of commands"
#
#    #TODO: make sure in the p4 workspace, there is no 
#
#    # ---------------------- p4 sandbox
#    p4_get_changes()[0]
#    
#    demo_chg = str(352)
#    
#    change_workdir("D:/p4migtest")
#    p4.run("sync","-f","//depot/...@%s" % demo_chg )
#    changes = p4_get_changes()
#    debug("changes size %s"  % str(len(changes)) )
#    for change in changes: 
#
#        
#        if int(change['change']) == int(demo_chg):
#            debug(" ..... " + str(change['change']) )
#            debug("found change 12 \n")
#            
#            
#            detail = p4_get_change_details(change)
#            
#            tell_files_actions(detail)
#            # TODO: Do branch or intergrate here? since there is no need to iterate through files in the change obj.
#            if is_branch_changelist(detail):
#                # get the branch details ? How do I know the name?
#                ab.create_branch(name)
#            if is_integrate_changelist(detail):
#                pass #TODO
#            ab.apply_actions_on_files(detail)
#            break;
#
##    ab.workspace_dir("c:/test", "//depot/Alice2_Prog/Tools/Buildbot/master/buildbot.tac", p4env)
#    
#    debug("DEBUG: the following files has more than two mapping depot dirs, please check.")
#    debug(ab.potential_failed_file_dir)
#    
    
#IMPORTANT NOTES:
# local p4 server , change 6, 8 ,  can't be migrated due to file unchanged.    