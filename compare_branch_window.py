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

class CompareBranchWindow:
    """ 
    Class for handling the 'compare with branch' functionality.
    """
    
    def __init__(self, gitpath, filepath):
        """ 
        Will collect branches information and build the branches-window.
        """

        self._src_filepath = filepath
        self._gitpath = gitpath
        self.window = Gtk.Window()
        self.set_diff_viewer("meld %s %s")

        try:
            # list branches
            sp = subprocess.Popen(['git', '--git-dir='+gitpath+'/.git', '--work-tree='+gitpath, 'branch'], 
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)
            sp.wait()

            output, err = sp.communicate()
            output = output.decode()
            lines = output.split("\n")

            listStore = Gtk.ListStore(str)

            for line in lines:
                isCurrent = line[0:1] == '*'
                branch    = line[2:]

                if not isCurrent and branch.strip() != "":
                    listStore.append([branch])
                  
            treeview = Gtk.TreeView(model=listStore)
            treeview.get_selection().connect("changed", self._on_table_changed)

            grid = Gtk.Grid()
            grid.attach(treeview, 0, 0, 1, 1)
            
            cell   = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn("branch", cell, text=0)
            treeview.append_column(column)

            compareButton = Gtk.Button()
            compareButton.set_label("Compare")
            compareButton.connect("clicked", self._on_compare_button_clicked)
            grid.attach(compareButton, 0, 1, 1, 1)

            self.window.add(grid)
            self.window.show_all()
        except OSError as error:
            print(error)

    def set_diff_viewer(self, diffviewer):
        self._diffviewer = diffviewer

    def get_diff_viewer(self):
        return self._diffviewer
        
    def _on_table_changed(self, selection):
        """
        Will be called when the selected entry (branch) of the displayed table changes.
        """

        (model, iter) = selection.get_selected()
        self._branch = model[iter][0]

    def _on_compare_button_clicked(self, button, data=None):
        """
        Triggered when the 'compare' button is clicked.
        Will fetch and store the file from selected branch into temp-file.
        Calls the diff-viewer to show a diff between the current file and the temp-file.
        """

        branch   = self._branch
        gitpath  = self._gitpath
        filepath = self._src_filepath

        gitpathLen = len(gitpath) +1
        filerelpath = filepath[gitpathLen:]

        tmpFilepath = "/tmp/addiks-compare" + filepath.replace("/", ".")

        try:
            # fetch file-content from different branch.
            sp = subprocess.Popen(['git', '--git-dir='+gitpath+'/.git', '--work-tree='+gitpath, 'show', branch+':'+filerelpath], 
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
            
            # call the diff-viewer (by default meld)
            sp = subprocess.Popen(diffviewer)
            time.sleep(3)
            os.remove(tmpFilepath)
            
        except OSError as error:
            print(error)
