# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk

from transferlist import TransferList
from utils import PopupMenu, PressHeader
import string, os
from pynicotine.utils import _
from pynicotine import slskmessages
from entrydialog import OptionDialog

class Uploads(TransferList):
	def __init__(self, frame):
		TransferList.__init__(self, frame, frame.UploadList)
		self.frame = frame
		self.frame.UploadList.set_property("rules-hint", True)
		self.popup_menu2 = popup2 = PopupMenu(frame)
		popup2.setup( 
		        ("#" + _("Clear finished/aborted"), self.OnClearFinishedAborted, gtk.STOCK_CLEAR),
			("#" + _("Clear finished"), self.OnClearFinished, gtk.STOCK_CLEAR),
			("#" + _("Clear aborted"), self.OnClearAborted, gtk.STOCK_CLEAR),
			("#" + _("Clear queued"), self.OnClearQueued, gtk.STOCK_CLEAR),
		)
		self.popup_menu_users = popup3 = PopupMenu(frame)
		popup3.setup( 
			("#" + _("Send _message"), popup3.OnSendMessage, gtk.STOCK_EDIT),
			("#" + _("Show IP a_ddress"), popup3.OnShowIPaddress, gtk.STOCK_NETWORK),
			("#" + _("Get user i_nfo"), popup3.OnGetUserInfo, gtk.STOCK_DIALOG_INFO),
			("#" + _("Brow_se files"), popup3.OnBrowseUser, gtk.STOCK_HARDDISK),
			("#" + _("Gi_ve privileges"), popup3.OnGivePrivileges, gtk.STOCK_JUMP_TO),
			("", None),
			("$" + _("_Add user to list"), popup3.OnAddToList),
			("$" + _("_Ban this user"), popup3.OnBanUser),
			("$" + _("_Ignore this user"), popup3.OnIgnoreUser),
			("#" + _("Select User's Transfers"), self.OnSelectUserTransfer, gtk.STOCK_INDEX),
		)
		
			
		self.popup_menu = popup = PopupMenu(frame)
		popup.setup(
			("#" + _("Copy _URL"), self.OnCopyURL, gtk.STOCK_COPY),
			("#" + _("Copy folder URL"), self.OnCopyDirURL, gtk.STOCK_COPY),
			("#" + _("Send to _player"), self.OnPlayFiles, gtk.STOCK_MEDIA_PLAY),
			(1, _("User"), self.popup_menu_users, self.OnPopupMenuUsers),
			("", None),
			("#" + _("Abor_t"), self.OnAbortTransfer, gtk.STOCK_CANCEL),
			("#" + _("_Clear"), self.OnClearTransfer, gtk.STOCK_CLEAR),
			("#" + _("_Retry"), self.OnUploadTransfer, gtk.STOCK_REDO),
			("", None),
			(1, _("Clear Groups"), self.popup_menu2, None),
		)
		frame.UploadList.connect("button_press_event", self.OnPopupMenu, "mouse")
		frame.UploadList.connect("key-press-event", self.on_key_press_event)
		cols = frame.UploadList.get_columns()
		for i in range (9):
			parent = cols[i].get_widget().get_ancestor(gtk.Button)
			if parent:
				parent.connect('button_press_event', PressHeader)
			# Read Show / Hide column settings from last session
			cols[i].set_visible(self.frame.np.config.sections["columns"]["uploads"][i])
		frame.clearUploadFinishedAbortedButton.connect("clicked", self.OnClearFinishedAborted)
		frame.clearUploadQueueButton.connect("clicked", self.OnTryClearQueued)
		frame.abortUploadButton.connect("clicked", self.OnAbortTransfer)
		frame.abortUserUploadButton.connect("clicked", self.OnAbortUser)
		frame.banUploadButton.connect("clicked", self.OnBan)
		frame.UploadList.expand_all()
		self.frame.ToggleTreeUploads.set_active(self.frame.np.config.sections["transfers"]["groupuploads"])
		frame.ToggleTreeUploads.connect("toggled", self.OnToggleTree)
		self.OnToggleTree(None)
		self.frame.ExpandUploads.set_active(True)
		frame.ExpandUploads.connect("toggled", self.OnExpandUploads)
		self.expanded = False

	def saveColumns(self):
		columns = []
		for column in self.frame.UploadList.get_columns():
			columns.append(column.get_visible())
		self.frame.np.config.sections["columns"]["uploads"] = columns
		
	def OnTryClearQueued(self, widget):
		direction="up"
		win = OptionDialog(self.frame, _("Clear All Queued Uploads?"), modal=True, status=None, option=False, third="")
		win.connect("response", self.frame.on_clear_response, direction)
		win.set_title(_("Nicotine+")+": "+_("Clear Queued Transfers"))
		win.set_icon( self.frame.images["n"])
		win.show()
		
	def OnExpandUploads(self, widget):

		if self.frame.ExpandUploads.get_active():
			self.frame.UploadList.expand_all()
		else:
			self.frame.UploadList.collapse_all()
			
	def OnToggleTree(self, widget):
		self.TreeUsers = self.frame.ToggleTreeUploads.get_active()
		self.frame.np.config.sections["transfers"]["groupuploads"] = self.TreeUsers
		self.RebuildTransfers()
		if not self.TreeUsers:
			self.frame.ExpandUploads.hide()
		else:
			self.frame.ExpandUploads.show()
			
	def RebuildTransfers(self):
		if self.frame.np.transfers is None:
			return
		self.Clear()
		for transfer in self.frame.np.transfers.uploads:
			self.update(transfer)
			
	def select_transfers(self):
		self.selected_transfers = []
		self.selected_users = []
		self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)
		
	def OnBan(self, widget):
		self.select_transfers()
		for user in self.selected_users:
			self.frame.BanUser(user)
			
	def OnAbortUser(self, widget):
		self.select_transfers()
		for user in self.selected_users:
			for i in self.list[:]:
				if i.user == user:
					if i not in self.selected_transfers:
						self.selected_transfers.append(i)
					
		TransferList.OnAbortTransfer(self, widget, False, False)
		self.frame.np.transfers.calcUploadQueueSizes()
		self.frame.np.transfers.checkUploadQueue()
		
	def OnUploadTransfer(self, widget):
		self.select_transfers()
		for transfer in self.selected_transfers:
			filename = transfer.filename
			path = transfer.path
			user = transfer.user

			self.frame.np.ProcessRequestToPeer(user, slskmessages.UploadQueueNotification(None))

			self.frame.np.transfers.pushFile(user, filename, path)
			self.frame.np.transfers.checkUploadQueue()

			
	def OnSelectUserTransfer(self, widet):
		if len(self.selected_users) != 1:
			return
		selected_user = self.selected_users[0]
		
		sel = self.frame.UploadList.get_selection()
		fmodel = self.frame.UploadList.get_model()
		sel.unselect_all()
		
		for item in self.transfers:
			user_file, iter, transfer = item
			user, filepath = user_file
			if selected_user == user:
				ix = fmodel.get_path(iter)
				sel.select_path(ix,)
					
		self.select_transfers()

	def on_key_press_event(self, widget, event):
		key = gtk.gdk.keyval_name(event.keyval)

		if key in ( "P", "p"):
			self.OnPopupMenu(widget, event, "keyboard")
		else:
			self.selected_transfers = []
			self.selected_users = []
			self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)
			
			if key in ( "T", "t"):
				self.OnAbortTransfer(widget)
			elif key == "Delete":
				self.OnAbortTransfer(widget, False, True)

	def OnPlayFiles(self, widget, prefix = ""):
		executable = self.frame.np.config.sections["players"]["default"]
		if "$" not in executable:
			return
		commandargs = executable.split(" ")
		pos = commandargs.index("$")
		for fn in self.selected_transfers:
			command = commandargs
			file = fn.filename.replace("\\", os.sep)
			if os.path.exists(file):
				command[pos] = file
				os.spawnlp(os.P_NOWAIT, command[0], *command)
			
	def OnPopupMenuUsers(self, widget):
		
		self.selected_transfers = []
		self.selected_users = []
		self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)

		items = self.popup_menu_users.get_children()
		
		act = False
		if len(self.selected_users) == 1:
			act = True
		items[0].set_sensitive(act)
		items[1].set_sensitive(act)
		items[2].set_sensitive(act)
		items[3].set_sensitive(act)

		act = False
		if len(self.selected_users) == 1:
			user = self.selected_users[0]
			self.popup_menu_users.set_user(user)
			
			act = True
			items[6].set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
			items[7].set_active(user in self.frame.np.config.sections["server"]["banlist"])
			items[8].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])
		
		for i in range(4, 9):
			items[i].set_sensitive(act)

		return True

	def OnPopupMenu(self, widget, event, kind):
		if kind == "mouse":
			if event.button != 3:
				return False
		
		self.selected_transfers = []
		self.selected_users = []
		self.widget.get_selection().selected_foreach(self.SelectedTransfersCallback)

		self.SelectCurrentRow(event, kind)
		
		items = self.popup_menu.get_children()
		if len(self.selected_users) != 1:
			items[3].set_sensitive(False) # Users Menu
			act = False
		else:
			items[3].set_sensitive(True) # Users Menu
			if len(self.selected_transfers) == 0:
				act = False
			else:
				act = True
		items[2].set_sensitive(act) # send to player
		
		for i in range(4, 8):
			items[i].set_sensitive(act)
			
		if len(self.selected_users) == 1:
			act = True
		else:
			act = False
		items[3].set_sensitive(act) #
			
		act = False
		if len(self.selected_transfers) == 1:
			act = True
		items[0].set_sensitive(act)
		items[1].set_sensitive(act)
		
				
		self.popup_menu.popup(None, None, None, 3, event.time)
		if kind == "keyboard":
			widget.emit_stop_by_name("key_press_event")
		elif kind == "mouse":
			widget.emit_stop_by_name("button_press_event")
		return True
		
	def ClearByUser(self, user):
		for i in self.list[:]:
			if i.user == user:
				if i.transfertimer is not None:
					i.transfertimer.cancel()
				self.list.remove(i)
		self.frame.np.transfers.calcUploadQueueSizes()
		self.frame.np.transfers.checkUploadQueue()
		self.update()

	def OnAbortTransfer(self, widget, remove = False, clear = False):
		self.select_transfers()
		TransferList.OnAbortTransfer(self, widget, remove, clear)
		self.frame.np.transfers.calcUploadQueueSizes()
		self.frame.np.transfers.checkUploadQueue()

	def OnClearQueued(self, widget):
		self.select_transfers()
		TransferList.OnClearQueued(self, widget)
		self.frame.np.transfers.calcUploadQueueSizes()
