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

from gi.repository import Gtk
import subprocess
from subprocess import Popen, PIPE
import os
from helpers import group
import time

class CompareRevisionWindow:
    """
    Class for handling the 'open file history' functionality.
    """

    def __init__(self, gitpath, filepath):
        """
        Will fetch the file-history from git and display it in a table in it's own window.
        """

        self.window = Gtk.Window()
        self._src_filepath = filepath
        self._gitpath = gitpath
        self._commits = []
        self._commit = None
        self._prevCommit = None
        self.set_diff_viewer("meld %s %s")

        try:
            # fetch file-history from git.
            sp = subprocess.Popen(['git', '--git-dir='+gitpath+'/.git', '--work-tree='+gitpath, 'log', '--follow', '--full-history', filepath], 
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)
            sp.wait()

            output, err = sp.communicate()
            output = output.decode()
            lines = output.split("\n")

            listStore = Gtk.ListStore(str, str, str, str, str, str)

            commitBefore = None
            for data in group(lines, 6):
                commit  = data[0]
                author  = data[1]
                date    = data[2]
                message = data[4]
                message = message.strip()

                if(len(commit)  > 0 and
                   len(author)  > 0 and
                   len(date)    > 0 and
                   len(message) > 0):
                       

                    commit   = commit.split(" ")
                    commit   = commit[1]
                    commitId = commit
                    commit   = commit[-8:]

                    author = author.split(" ")
                    author = author[1] + " " + author[2]

                    if len(message)>60:
                        message = message[0:55] + " ..."

                    listStore.append([commit, author, date, message, commitId, commitBefore])
                    self._commits.append([commitId, commitBefore])
                    commitBefore = commitId

            treeview = Gtk.TreeView(model=listStore)
            treeview.get_selection().connect("changed", self._on_table_changed)

            i = 0
            for columnName in ["commit", "author", "date", "message"]:
                cell   = Gtk.CellRendererText()
                column = Gtk.TreeViewColumn(columnName, cell, text=i)
                treeview.append_column(column)
                i += 1

            grid = Gtk.Grid()
            grid.attach(treeview, 0, 0, 2, 1)

            self.compareButton = Gtk.Button()
            self.compareButton.set_label("Compare with current file")
            self.compareButton.connect("clicked", self._on_compare_button_clicked)
            grid.attach(self.compareButton, 0, 1, 1, 1)

            self.comparePreviousButton = Gtk.Button()
            self.comparePreviousButton.set_label("Compare with above")
            self.comparePreviousButton.connect("clicked", self._on_compare_next_button_clicked)
            grid.attach(self.comparePreviousButton, 1, 1, 1, 1)

            self.window.add(grid)
            self.window.show_all()
        except OSError as error:
            print(error)

    def set_diff_viewer(self, diffviewer):
        self._diffviewer = diffviewer

    def get_diff_viewer(self):
        return self._diffviewer
        
    def _on_table_changed(self, selection):
        """ Will be called when the selected row in the history-table changes. """

        (model, iter) = selection.get_selected()

        self._commit = model[iter][4]

        if model[iter][5] != None:
            self._prevCommit = model[iter][5]
            self.comparePreviousButton.sensitive = True
        else:
            self.comparePreviousButton.sensitive = False
            

    ### BUTTON EVENTS:

    def _on_compare_next_button_clicked(self, button, data=None):
        """
        Will be called when user clicks on 'compare with previous'.
        Shows a diff between the selected revision and the historically next one.
        """

        commitA  = self._commit
        commitB  = self._prevCommit
        gitpath  = self._gitpath
        filepath = self._src_filepath

        gitpathLen = len(gitpath) +1
        filerelpath = filepath[gitpathLen:]

        tmpFilepathA = "/tmp/addiks-compare" + filepath.replace("/", ".") + "-A"
        tmpFilepathB = "/tmp/addiks-compare" + filepath.replace("/", ".") + "-B"

        try:
            # fetches the contents of the file from another revision.
            sp = subprocess.Popen(['git', '--git-dir='+gitpath+'/.git', '--work-tree='+gitpath, 'show', commitA+':'+filerelpath], 
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)
            sp.wait()

            output, err = sp.communicate()
            output = output.decode()

            f = open(tmpFilepathA, 'w')
            f.write(output)
            f.close()

            # fetches the contents of the file from another revision.
            sp = subprocess.Popen(['git', '--git-dir='+gitpath+'/.git', '--work-tree='+gitpath, 'show', commitB+':'+filerelpath], 
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)
            sp.wait()

            output, err = sp.communicate()
            output = output.decode()

            f = open(tmpFilepathB, 'w')
            f.write(output)
            f.close()

            diffviewer = self.get_diff_viewer()
            diffviewer = diffviewer % (tmpFilepathA, tmpFilepathB)
            diffviewer = diffviewer.split(" ")
            
            # open diff-viewer (by default meld)
            sp = subprocess.Popen(diffviewer)
            time.sleep(3)
            os.remove(tmpFilepathA)
            os.remove(tmpFilepathB)
            
        except OSError as error:
            print(error)
        
    def _on_compare_button_clicked(self, button, data=None):
        """
        Will be called when user clicks the 'compare with current file' button.
        Shows a diff between the selected revision and the current open file.
        """

        commit   = self._commit
        gitpath  = self._gitpath
        filepath = self._src_filepath
        
        gitpathLen = len(gitpath) +1
        filerelpath = filepath[gitpathLen:]

        tmpFilepath = "/tmp/addiks-compare" + filepath.replace("/", ".")

        try:
            # fetches the contents of the file from another revision.
            sp = subprocess.Popen(['git', '--git-dir='+gitpath+'/.git', '--work-tree='+gitpath, 'show', commit+':'+filerelpath], 
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)
            sp.wait()

            output, err = sp.communicate()
            output = output.decode()

            f = open(tmpFilepath, 'w')
            f.write(output)
            f.close()

            diffviewer = self.get_diff_viewer()
            diffviewer = diffviewer % (filepath, tmpFilepath)
            diffviewer = diffviewer.split(" ")
            
            # open diff-viewer (by default meld)
            sp = subprocess.Popen(diffviewer)
            time.sleep(3)
            os.remove(tmpFilepath)
            
        except OSError as error:
            print(error)

