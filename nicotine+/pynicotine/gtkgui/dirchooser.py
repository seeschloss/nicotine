# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import gobject
import os
import locale
import sys

from utils import recode, InputDialog

from pynicotine.utils import _

def ChooseDir(parent = None, initialdir = "~"):
	dialog = gtk.FileChooserDialog(parent=None, action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT, gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
	dialog.set_select_multiple(True)
	response = dialog.run()
	
	if response == gtk.RESPONSE_ACCEPT:
		res = dialog.get_filenames()
	else:
		res = None
	dialog.destroy()
	return res

if __name__ == "__main__":
	print ChooseDir()
	