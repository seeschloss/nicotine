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
import gobject
import time
import sys

from pynicotine import slskmessages
from utils import InitialiseColumns, PopupMenu, InputDialog, Humanize, HumanSpeed, PressHeader

from pynicotine.utils import _

class UserList:
	def __init__(self, frame):
		self.frame = frame
		self.userlist = []
		
		self.usersmodel = gtk.ListStore(gtk.gdk.Pixbuf, gtk.gdk.Pixbuf, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_BOOLEAN, gobject.TYPE_BOOLEAN, gobject.TYPE_BOOLEAN, gobject.TYPE_STRING, gobject.TYPE_STRING, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_STRING)
		self.cols = cols = InitialiseColumns(self.frame.UserList,
			[_("Status"), 20, "pixbuf"],
			[_("Country"), 25, "pixbuf"],
			[_("User"), 120, "text", self.CellDataFunc],
			[_("Speed"), 0, "text", self.CellDataFunc],
			[_("Files"), 0, "text", self.CellDataFunc],
			[_("Trusted"), 0, "toggle"],
			[_("Notify"), 0, "toggle"],
			[_("Privileged"), 0, "toggle"],
			[_("Last seen"), 160, "text", self.CellDataFunc],
			[_("Comments"), -1, "edit", self.CellDataFunc],
		)
		self.col_status, self.col_country, self.col_user, self.col_speed, self.col_files, self.col_trusted, self.col_notify, self.col_privileged, self.col_last, self.col_comments = cols
		self.col_status.set_sort_column_id(10)
		self.col_country.set_sort_column_id(14)
		self.col_user.set_sort_column_id(2)
		self.col_speed.set_sort_column_id(11)
		self.col_files.set_sort_column_id(12)
		self.col_trusted.set_sort_column_id(5)
		self.col_notify.set_sort_column_id(6)
		self.col_privileged.set_sort_column_id(7)
		self.col_last.set_sort_column_id(13)
		self.col_comments.set_sort_column_id(9)
		self.col_status.get_widget().hide()
		self.col_country.get_widget().hide()
		config = self.frame.np.config.sections
		for i in range (10):
			parent = cols[i].get_widget().get_ancestor(gtk.Button)
			if parent:
				parent.connect('button_press_event', PressHeader)
			# Read Show / Hide column settings from last session
			cols[i].set_visible(config["columns"]["userlist"][i])
		if config["columns"]["hideflags"]:
			cols[1].set_visible(0)
			config["columns"]["userlist"][1] = 0
		for render in self.col_trusted.get_cell_renderers():
			render.connect('toggled', self.cell_toggle_callback, self.frame.UserList, 5)
		for render in self.col_notify.get_cell_renderers():
			render.connect('toggled', self.cell_toggle_callback, self.frame.UserList, 6)
		for render in self.col_privileged.get_cell_renderers():
			render.connect('toggled', self.cell_toggle_callback, self.frame.UserList, 7)
		renderers = self.col_comments.get_cell_renderers()
		for render in renderers:
			render.connect('edited', self.cell_edited_callback, self.frame.UserList, 9)
		self.frame.UserList.set_model(self.usersmodel)
		self.frame.UserList.set_property("rules-hint", True)
		self.privileged = []
		self.notify = []
		self.trusted = []
		for user in self.frame.np.config.sections["server"]["userlist"]:
			notify = user[2]
			privileged = user[3]
			if len(user) > 4:
				trusted = user[4]
			else:
				trusted = 0;

			if len(user) > 5:
				last_seen = user[5]
				try:
					time_from_epoch = time.mktime(time.strptime(last_seen,
										    "%m/%d/%Y %H:%M:%S"))
				except:
					if last_seen == '':
						time_from_epoch = sys.maxint
					else:
						time_from_epoch = 0
			else:
				last_seen = _("Never seen")
				user += [last_seen]
				time_from_epoch = 0
			if len(user) > 6:
				flag = user[6]
			else:
				user += [None]
				flag = None
			row = [self.frame.GetStatusImage(0), self.frame.GetFlagImage(flag), user[0], "0", "0", trusted, notify, privileged, last_seen, user[1], 0, 0, 0, int(time_from_epoch), flag]
			if len(user) > 2:
				if user[2]:
					self.notify.append(user[0])
				if user[3]:
					self.privileged.append(user[0])
				if trusted:
					self.trusted.append(user[0])

			iter = self.usersmodel.append(row)
			self.userlist.append([user[0], user[1], last_seen, iter, flag])
		self.usersmodel.set_sort_column_id(2, gtk.SORT_ASCENDING)
		self.popup_menu = popup = PopupMenu(frame)
		popup.setup(
			("#" + _("Send _message"), popup.OnSendMessage, gtk.STOCK_EDIT),
			("", None),
			("#" + _("Show IP a_ddress"), popup.OnShowIPaddress, gtk.STOCK_NETWORK),
			("#" + _("Get user i_nfo"), popup.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
			("#" + _("Brow_se files"), popup.OnBrowseUser, gtk.STOCK_HARDDISK),
			("#" + _("Gi_ve privileges"), popup.OnGivePrivileges, gtk.STOCK_JUMP_TO),
			("$" + _("_Ban this user"), popup.OnBanUser),
			("$" + _("_Ignore this user"), popup.OnIgnoreUser),
			("", None),
			("$" + _("_Online notify"), self.OnNotify),
			("$" + _("_Privileged"), self.OnPrivileged),
			("$" + _("_Trusted"), self.OnTrusted),
			("", None),
			("#" + _("Edit _comments"), self.OnEditComments, gtk.STOCK_EDIT),
			("#" + _("_Remove"), self.OnRemoveUser, gtk.STOCK_CANCEL),
		)
		self.frame.UserList.connect("button_press_event", self.OnPopupMenu)
		
	def CellDataFunc(self, column, cellrenderer, model, iter):
		colour = self.frame.np.config.sections["ui"]["search"]
		if colour == "":
			colour = None
		cellrenderer.set_property("foreground", colour)
		
	def cell_toggle_callback(self, widget, index, treeview, pos):
	
		iter = self.usersmodel.get_iter(index)
		user = self.usersmodel.get_value(iter, 2)
		
		value = self.usersmodel.get_value(iter, pos)
		self.usersmodel.set(iter, pos, not value)
		toggle = not value
		if pos == 5:
			if toggle:
				if user not in self.trusted:
					self.trusted.append(user)
				
			else:
				if user in self.trusted:
					self.trusted.remove(user)
		elif pos == 6:
			if toggle:
				if user not in self.notify:
					self.notify.append(user)
			else:
				if user in self.notify:
					self.notify.remove(user)
		elif pos == 7:
			if toggle:
				if user not in self.privileged:
					self.privileged.append(user)
			else:
				if user in self.privileged:
					self.privileged.remove(user)

		self.SaveUserList()
		
	def cell_edited_callback(self, widget, index, value, treeview, pos):
		
		store = treeview.get_model()
		iter = store.get_iter(index)
		if pos == 9:
			self.SetComment(iter, store, value)
		
	def SetLastSeen(self, user, online =False):
		last_seen = ""
		time_from_epoch = sys.maxint

		if not online:
			last_seen = time.strftime("%m/%d/%Y %H:%M:%S")
			time_from_epoch = time.mktime(time.strptime(last_seen,
								    "%m/%d/%Y %H:%M:%S"))
		for i in self.userlist:
			if i[0] == user:
				i[2] = last_seen
				self.usersmodel.set(i[3], 8, last_seen)
				self.usersmodel.set(i[3], 13, int(time_from_epoch))
				break
				
		if not online:
			self.SaveUserList()
			
	def SetComment(self, iter, store, comments=None):
		user = store.get_value(iter, 2)
		if comments is not None:
			for i in self.userlist:
				if i[0] == user:
					i[1] = comments
					self.usersmodel.set(iter, 9, comments)
					break
			self.SaveUserList()
			
	def ConnClose(self):
		for user in self.userlist:
			self.usersmodel.set(user[3], 0, self.frame.GetStatusImage(0), 3, "0", 4, "0", 10, 0, 11, 0, 12, 0)

		for user in self.userlist:
			if self.usersmodel.get(user[3], 8)[0] is "":
				self.SetLastSeen(user[0])
	
	def OnPopupMenu(self, widget, event):
		items = self.popup_menu.get_children()
		d = self.frame.UserList.get_path_at_pos(int(event.x), int(event.y))

		if d:
			path, column, x, y = d
			user = self.frame.UserList.get_model().get_value(self.frame.UserList.get_model().get_iter(path), 2)
			
			if event.button != 3:
				if event.type == gtk.gdk._2BUTTON_PRESS:
					self.frame.privatechats.SendMessage(user, None, 1)
					self.frame.MainNotebook.set_current_page(1)
				return
			
			self.popup_menu.set_user(user)
			
			items = self.popup_menu.get_children()
			
			items[6].set_active(user in self.frame.np.config.sections["server"]["banlist"])
			items[7].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
			items[9].set_active(user in self.notify)
			items[10].set_active(user in self.privileged)
			items[11].set_active(user in self.trusted)
			
			self.popup_menu.popup(None, None, None, event.button, event.time)
		
	def GetIter(self, user):
		iters = [i[3] for i in self.userlist if i[0] == user]

		if iters:
			return iters[0]
		else:
			return None
			
	def GetUserStatus(self, msg):
		iter = self.GetIter(msg.user)
		if iter is None:
			return
		if msg.status == int(self.usersmodel.get_value(iter, 10)):
			return

		if msg.user in self.notify:
			status = [_("User %s is offline"), _("User %s is away"), _("User %s is online")][msg.status]
			self.frame.logMessage(status % msg.user)
			self.frame.NewNotification(status % msg.user)

		img = self.frame.GetStatusImage(msg.status)
		self.usersmodel.set(iter, 0, img, 10, msg.status)

		if msg.status: # online
			self.SetLastSeen(msg.user, online=True)
		elif self.usersmodel.get(iter, 8)[0] is "": # disconnected
			self.SetLastSeen(msg.user)

	def GetUserStats(self, msg):
		iter = self.GetIter(msg.user)
		if iter is None:
			return
		hspeed = HumanSpeed(msg.avgspeed)
		hfiles = Humanize(msg.files)
		self.usersmodel.set(iter, 3, hspeed, 4, hfiles, 11, msg.avgspeed, 12, msg.files)
		if msg.country is not None:
			flag = "flag_"+msg.country
			self.usersmodel.set(iter, 1, self.frame.GetFlagImage(flag), 14, flag)
			for i in self.userlist:
				if i[0] == msg.user:
					i[4] = flag
					break
				
	def SetUserFlag(self, user, flag):
		iter = self.GetIter(user)
		if iter is None:
			return
		if user not in [i[0] for i in self.userlist]:
			return
		self.usersmodel.set(iter, 1, self.frame.GetFlagImage(flag), 14, flag)
		for i in self.userlist:
			if i[0] == user:
				i[4] = flag
				

	def AddToList(self, user):
		if user in [i[0] for i in self.userlist]:
			return

		row = [self.frame.GetStatusImage(0), None, user, "0", "0", False, False, False, _("Never seen"), "", 0, 0, 0, 0, ""]
		iter = self.usersmodel.append(row)
		self.userlist.append([user, "", _("Never seen"), iter, self.frame.GetUserFlag(user)])
		self.SaveUserList()
		self.frame.np.queue.put(slskmessages.AddUser(user))

		for widget in self.frame.BuddiesComboEntries:
			gobject.idle_add(widget.Append, user)
		if self.frame.np.config.sections["words"]["buddies"]:
			gobject.idle_add(self.frame.chatrooms.roomsctrl.UpdateCompletions)
			gobject.idle_add(self.frame.privatechats.UpdateCompletions)
			
	def OnEditComments(self, widget):
		user = self.popup_menu.get_user()
		for i in self.userlist:
			if i[0] == user:
				comments = i[1]
				break
		else:
			comments = ""
		
		comments = InputDialog(self.frame.MainWindow, _("Edit comments")+"...", _("Comments")+":", comments)
		
		if comments is not None:
			for i in self.userlist:
				if i[0] == user:
					i[1] = comments
					self.usersmodel.set(i[3], 9, comments)
					break
			self.SaveUserList()

	def SaveUserList(self):
		l = []

		for i in self.userlist:
			user, comment, seen, iter, flag = i
			l.append([user, comment, (user in self.notify), (user in self.privileged), (user in self.trusted), seen, flag])
		self.frame.np.config.sections["server"]["userlist"] = l
		self.frame.np.config.writeConfig()
		
	def saveColumns(self):
		columns = []
		for column in self.frame.UserList.get_columns():
			columns.append(column.get_visible())
		self.frame.np.config.sections["columns"]["userlist"] = columns
		
		
	def RemoveFromList(self, user):
		if user in self.notify:
			self.notify.remove(user)
		if user in self.privileged:
			self.privileged.remove(user)
		if user in self.trusted:
			self.trusted.remove(user)
		for i in self.userlist:
			if i[0] == user:
				self.userlist.remove(i)
				self.usersmodel.remove(i[3])
				break
		self.SaveUserList()
		for widget in self.frame.BuddiesComboEntries:
			gobject.idle_add(widget.Remove, user)
		if self.frame.np.config.sections["words"]["buddies"]:
			gobject.idle_add(self.frame.chatrooms.roomsctrl.UpdateCompletions)
			gobject.idle_add(self.frame.privatechats.UpdateCompletions)
			
	def OnRemoveUser(self, widget):
		self.RemoveFromList(self.popup_menu.get_user())

	def OnNotify(self, widget):
		user = self.popup_menu.get_user()
		if not widget.get_active():
			if user in self.notify:
				self.notify.remove(user)
		else:
			if not user in self.notify:
				self.notify.append(user)
		self.SaveUserList()

	def OnPrivileged(self, widget):
		user = self.popup_menu.get_user()
		if not widget.get_active():
			if user in self.privileged:
				self.privileged.remove(user)
		else:
			if not user in self.privileged:
				self.privileged.append(user)
		self.SaveUserList()
		
	def OnTrusted(self, widget):
		user = self.popup_menu.get_user()
		if not widget.get_active():
			if user in self.trusted:
				self.trusted.remove(user)
		else:
			if not user in self.trusted:
				self.trusted.append(user)
		for i in self.userlist:
			if i[0] == user:
				self.usersmodel.set(i[3], 5, (user in self.trusted))
		self.SaveUserList()
		
