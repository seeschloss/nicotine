# -*- coding: utf-8 -*-
# coding=utf-8
# Copyright (C) 2007 daelstorm. All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Original copyright below
# Copyright (c) 2003-2004 Hyriand. All rights reserved.

import gtk
import os, sys
dir_location = os.path.dirname(os.path.realpath(__file__))

class FastConfigureAssistant:
	def __init__(self, frame):
		builder = gtk.Builder()
		builder.add_from_file(os.path.join(dir_location, "fastconfigure.glade"))
		self.FastConfigureWindow = builder.get_object("FastConfigureAssistant")
		builder.connect_signals(self)
	def OnFastConfigureClose(self, widget):
		self.FastConfigureWindow.hide()
	def OnFastConfigureApply(self, widget):
		self.FastConfigureWindow.hide()
	def OnFastConfigureCancel(self, widget):
		self.FastConfigureWindow.hide()

