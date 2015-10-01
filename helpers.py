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

import os

def file_get_contents(filename):
    """ retrieves the contents of a file. """
    with open(filename) as f:
        return f.read()

def group(lst, n):
    """group([0,3,4,10,2,3], 2) => [(0,3), (4,10), (2,3)]
    
    Group a list into consecutive n-tuples. Incomplete tuples are
    discarded e.g.
    
    >>> group(range(10), 3)
    [(0, 1, 2), (3, 4, 5), (6, 7, 8)]

    SOURCE: http://code.activestate.com/recipes/303060-group-a-list-into-sequential-n-tuples/

    """
    return zip(*[lst[i::n] for i in range(n)])
 
