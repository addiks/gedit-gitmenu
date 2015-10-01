"""
 * Copyright (C) 2013  Gerrit Addiks.
 * This package (including this file) was released under the terms of the GPL-3.0.
 * You should have received a copy of the GNU General Public License along with this program.
 * If not, see <http://www.gnu.org/licenses/> or send me a mail so i can send you a copy.
 * 
 * @license GPL-3.0
 * @author Gerrit Addiks <gerrit@addiks.de>
 * @web http://addiks.net/gedit-plugin-git-menu/
 * @version 1.0
"""

from gi.repository import Gtk, GObject, Gedit, PeasGtk, Gio
from compare_revision_window import CompareRevisionWindow
from compare_branch_window import CompareBranchWindow
from helpers import group, file_get_contents
import subprocess
from subprocess import Popen, PIPE
import os
import re
import time

class AddiksGitMenuWindow(GObject.Object, Gedit.WindowActivatable):
    """ 
    This class represents the plugin's extension points to a gedit window.
    """

    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        """ Will be called by gedit, indicates that the plugin should be activated. """
        self._init_gitmenu()

    def _init_gitmenu(self):
        """ Will build the git-menu in the gedit-menu. """

        plugin_path = os.path.dirname(__file__)
        manager = self.window.get_ui_manager()
        actions = [
            ['OpenGitDirectoryAction', "Open git directory",    "", self._on_open_git_directory],
            ['AddToIndexAction',       "Stage to index",        "", self._on_add_to_index],
            ['RemoveFromIndexAction',  "Unstage from index",    "", self._on_remove_from_index],
            ['PullAction',             "Pull the checkout",     "", self._on_pull],
            ['CheckoutAction',         "Checkout this file",    "", self._on_checkout],
            ['CompareRevisionAction',  "Open file history",     "", self._on_compare_revision],
            ['CompareFileAction',      "Compare with file",     "", self._on_compare_file],
            ['CompareBranchAction',    "Compare with branch",   "", self._on_compare_branch],
            ['GitAction',              "Git",                   "_Git", None],
        ]

        self._actions = Gtk.ActionGroup("AddiksGitMenuActions")
        for action in actions:
            self._actions.add_actions([(action[0], Gtk.STOCK_INFO, action[1], None, action[2], action[3]),])
            
        self._gitAction = self._actions.get_action("GitAction")

        manager.insert_action_group(self._actions)
        self._ui_merge_id = manager.add_ui_from_string(file_get_contents(plugin_path + "/menubar.xml"))
        manager.ensure_update()

    def do_update_state(self):
        """ Called by gedit. Indicates that the state of the document changed. """

        if self._check_in_git(False):
            self._gitAction.set_visible(True)
        else:
            self._gitAction.set_visible(False)

        document = self.window.get_active_document()
        path = self._get_git_directory()
        if self._check_in_file(False) and self._check_in_git(False):
            filepath = document.get_location().get_path()
            try:
                # gets the current state of a file (untracked; modified; staged; modified & staged)
                sp = subprocess.Popen(
                    ['git', '--git-dir='+path+'/.git', '--work-tree='+path, 'status', '--porcelain', filepath], 
                    stdin=PIPE, stdout=PIPE, stderr=PIPE
                )
                sp.wait()
                output, err = sp.communicate()

                # depatch file state
                if output[:2] == b'??':
                    afterTag = " [?]" # untracked

                elif output[:2] == b'M ':
                    afterTag = " [S]" # staged

                elif output[:2] == b' M':
                    afterTag = " [M]" # modified

                elif output[:2] == b'MM':
                    afterTag = " [MS]" # modified & staged

                else:
                    afterTag = ""

                # get current window title
                newTitle = title = self.window.get_title()

                # remove old tag from current title
                tagPattern = " \[[SM\?]S?\]"
                if re.match(".*"+tagPattern, title):
                    newTitle = re.sub(tagPattern, "", title)
                newTitle = afterTag + newTitle

                # set new title if changed
                if(title != newTitle):
                    self.window.set_title(newTitle)
            except OSError as error:
                print(error)

    def _get_git_directory(self):
        """ Gets the absolute path to the work-dir. """

        document = self.window.get_active_document()
        if document != None and document.get_location() != None:
            filepath = document.get_location().get_path()
            filepath = os.path.abspath(filepath)
            while filepath != "/":
                filepath = os.path.dirname(filepath)
                if os.path.exists(filepath + "/.git"):
                    return filepath
        else:
            return None

    def _check_in_file(self, doAlert=True):
        """ 
        Checks if the current document is in a file on disk.
        If not (and doAlert is True), then an alert-dialog will be displayed. 
        """

        document = self.window.get_active_document()
        if(document == None or 
           document.get_location == None or
           document.get_location() == None):
            if doAlert:
                dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.NONE, "Not in persistent file!")
                dialog.format_secondary_text("The current open file has no location on disk!")
                dialog.run()
            return False
        else:
            return True
        
    def _check_in_git(self, doAlert=True):
        """ 
        Checks if the current document is in a git work-dir.
        If not (and doAlert is True), then an alert-dialog will be displayed. 
        """

        gitpath = self._get_git_directory()
        if gitpath == None:
            if doAlert:
                dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.NONE, "Not in git-workdir!")
                dialog.format_secondary_text("This action can only be performed when the file is inside an git-working-directory.")
                dialog.run()
            return False
        else:
            return True

    def _get_diff_viewer(self):
        diff_viewer = 'meld %s %s'

        plugin_path = os.path.dirname(__file__)
        diffrc_path = plugin_path + "/diffrc"
        if os.path.exists(diffrc_path):
            diff_viewer = file_get_contents(diffrc_path)

        return diff_viewer

    ### MENU EVENTS

    def _on_compare_file(self, action, data=None):
        """ Event called when menu-item 'Compare with file' gets triggered. """

        if self._check_in_file():
            document = self.window.get_active_document()
            gitpath = self._get_git_directory()
            filepath = document.get_location().get_path()

            chooser = Gtk.FileChooserDialog("Please choose a file", self.window,
                Gtk.FileChooserAction.OPEN,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

            if(gitpath != None):
                chooser.set_current_folder(gitpath)

            response = chooser.run()

            if response == Gtk.ResponseType.OK:
                compareFilepath = chooser.get_filename()
                try:
                    sp = subprocess.Popen(['meld', filepath, compareFilepath])
                except OSError as error:
                    print(error)

            chooser.destroy()
        
    def _on_compare_branch(self, action, data=None):
        """ Event called when menu-item 'Compare with branch' gets triggered. """

        if self._check_in_file():
            document = self.window.get_active_document()
            gitpath = self._get_git_directory()
            filepath = document.get_location().get_path()
            compare = CompareBranchWindow(gitpath, filepath)
            compare.set_diff_viewer(self._get_diff_viewer())
    
    def _on_compare_revision(self, action, data=None):
        """ Event called when menu-item 'Open file history' gets triggered. """

        if self._check_in_file():
            document = self.window.get_active_document()
            gitpath = self._get_git_directory()
            filepath = document.get_location().get_path()
            compare = CompareRevisionWindow(gitpath, filepath)
            compare.set_diff_viewer(self._get_diff_viewer())
   
    def _on_open_git_directory(self, action, data=None):
        """ Event called when menu-item 'Open git directory' gets triggered. """

        filepath = self._get_git_directory()
        try:
            subprocess.Popen(['xdg-open', filepath])
        except OSError as error:
            print(error)

    def _on_add_to_index(self, action, data=None):
        """ Event called when menu-item 'Add to index / stage' gets triggered. """

        if self._check_in_file():
            document = self.window.get_active_document()
            gitpath = self._get_git_directory()
            filepath = document.get_location().get_path()
            try:
                # adds the file to git-index ( = staging)
                sp = subprocess.Popen(['git', '--git-dir='+gitpath+'/.git', '--work-tree='+gitpath, 'add', filepath])
                sp.wait()
            except OSError as error:
                print(error)
            self.do_update_state()
            
    def _on_remove_from_index(self, action, data=None):
        """ Event called when menu-item 'Remove from index / unstage' gets triggered. """

        if self._check_in_file():
            document = self.window.get_active_document()
            gitpath = self._get_git_directory()
            filepath = document.get_location().get_path()
            try:
                # remove the file from git-index ( = unstage )
                sp = subprocess.Popen(['git', '--git-dir='+gitpath+'/.git', '--work-tree='+gitpath, 'reset', 'HEAD', filepath])
                sp.wait()
            except OSError as error:
                print(error)
            self.do_update_state()
            
    def _on_pull(self, action, data=None):
        """
        Event called when menu-item 'pull' gets triggered.
        ('git pull' will always pull the entire work-dir, not only the open file.)        
        """

        if self._check_in_git():
            gitpath = self._get_git_directory()
            try:
                # pulls the work-dir from git remote.
                sp = subprocess.Popen(['git', '--git-dir='+gitpath+'/.git', '--work-tree='+gitpath, 'pull'], 
                    stdin=PIPE, stdout=PIPE, stderr=PIPE
                )
                sp.wait()
                output, err = sp.communicate()
                output = output.decode()

                # reaload gedit document
                encoding = Gedit.Encoding.get_utf8()
                document = self.window.get_active_document()
                document.load(document.get_location(), encoding, 1, 1, False)

                messageWindow = Gtk.Window()
                textView = Gtk.TextView()
                textBuff = textView.get_buffer()
                textBuff.set_text(output)
                label = Gtk.Label()
                label.set_text(output)
                messageWindow.add(label)
                messageWindow.show_all()

            except OSError as error:
                print(error)
            self.do_update_state()
            
    def _on_checkout(self, action, data=None):
        """ 
        Event called when menu-item 'checkout' gets triggered.
        This will revert all modifications and put the file back into 'unchanged' state.
        (Does not revert staging)
        """

        if self._check_in_file():
            document = self.window.get_active_document()
            gitpath = self._get_git_directory()
            filepath = document.get_location().get_path()
            try:
                # checkout the file into it's unchanged state
                sp = subprocess.Popen(['git', '--git-dir='+gitpath+'/.git', '--work-tree='+gitpath, 'checkout', filepath])
                sp.wait()
                encoding = Gedit.Encoding.get_utf8()
                document.load(document.get_location(), encoding, 1, 1, False)
            except OSError as error:
                print(error)
            self.do_update_state()
            
