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
# Previous copyright below
# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved.

"""
This is the actual client code. Actual GUI classes are in the separate modules
"""

import time
import slskproto
import slskmessages
from slskmessages import newId
import transfers
import Queue
import threading
from config import *
import string
import types
import locale
import utils
from utils import _
import os

class PeerConnection:
	"""
	Holds information about a peer connection. Not every field may be set
	to something. addr is (ip, port) address, conn is a socket object, msgs is
	a list of outgoing pending messages, token is a reverse-handshake 
	number (protocol feature), init is a PeerInit protocol message. (read
	slskmessages docstrings for explanation of these)
	"""
	def __init__(self, addr = None, username = None, conn = None, msgs = None, token = None, init = None, conntimer = None, tryaddr = None):
		self.addr = addr
		self.username = username
		self.conn = conn
		self.msgs = msgs
		self.token = token
		self.init = init
		self.conntimer = conntimer
		self.tryaddr = tryaddr

class ConnectToPeerTimeout:
	def __init__(self, conn, callback):
		self.conn = conn
		self.callback = callback
	
	def timeout(self):
		self.callback([self])

class NetworkEventProcessor:
	""" This class contains handlers for various messages from the networking
	thread"""
	def __init__(self, frame, callback, writelog, setstatus, configfile):

		self.frame = frame
		self.callback = callback
		self.logMessage = writelog
		self.setStatus = setstatus
	
		self.config = Config(configfile)
		self.config.frame = frame
		self.config.readConfig()
	
		self.queue = Queue.Queue(0)
		try:
			import GeoIP
			self.geoip = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)
		except ImportError:
			try:
				import _GeoIP
				self.geoip = _GeoIP.new(_GeoIP.GEOIP_MEMORY_CACHE)
			except ImportError:
				self.geoip = None
		self.protothread = slskproto.SlskProtoThread(self.frame.networkcallback, self.queue, self.config, self)
		uselimit = self.config.sections["transfers"]["uselimit"]
		uploadlimit = self.config.sections["transfers"]["uploadlimit"]
		limitby = self.config.sections["transfers"]["limitby"]
		self.queue.put(slskmessages.SetUploadLimit(uselimit, uploadlimit, limitby))
		if self.config.sections["transfers"]["geoblock"]:
			panic = self.config.sections["transfers"]["geopanic"]
			cc = self.config.sections["transfers"]["geoblockcc"]
			self.queue.put(slskmessages.SetGeoBlock([panic, cc]))
		else:
			self.queue.put(slskmessages.SetGeoBlock(None))

		self.serverconn = None
		self.waitport = None
		self.peerconns = []
		self.watchedusers = []
		self.ip_requested = {}
		self.users = {}
		self.chatrooms = None
		self.privatechat = None
		self.globallist = None
		self.userinfo = None
		self.userbrowse = None
		self.search = None
		self.transfers = None
		self.userlist = None
		self.logintime = None
		self.ipaddress = None
		self.privileges_left = None
		self.servertimer = None
		self.servertimeout = -1
		
		self.CompressedSharesBuddy = self.CompressedSharesNormal = None
		self.CompressShares("normal")
		self.CompressShares("buddy")
		self.newbuddyshares = self.newnormalshares = False
		self.distribcache = {}
		self.requestedShares = {}
		self.requestedInfo = {}
		self.requestedFolders = {}
		self.speed = 0
		self.translatepunctuation = string.maketrans(string.punctuation, string.join([' ' for i in string.punctuation],''))
		self.searchResultsConnections = []
		self.searchResultsTimer = threading.Timer(10, self.closeSearchResults)
		self.searchResultsTimer.start()
		self.respondDistributed = True
		self.respondDistributedTimer = threading.Timer(60, self.ToggleRespondDistributed)
		self.respondDistributedTimer.start()
		
				


		# Callback handlers for messages
		self.events = {slskmessages.ConnectToServer:self.ConnectToServer,
			slskmessages.ConnectError:self.ConnectError,
			slskmessages.IncPort:self.IncPort,
			slskmessages.ServerConn:self.ServerConn,
			slskmessages.ConnClose:self.ConnClose,
			slskmessages.Login:self.Login,
			slskmessages.MessageUser:self.MessageUser,
			slskmessages.PMessageUser:self.PMessageUser,
			slskmessages.ExactFileSearch:self.ExactFileSearch,
			slskmessages.UserJoinedRoom:self.UserJoinedRoom,
			slskmessages.SayChatroom:self.SayChatRoom,
			slskmessages.JoinRoom:self.JoinRoom,
			slskmessages.UserLeftRoom:self.UserLeftRoom,
			slskmessages.QueuedDownloads:self.QueuedDownloads,
			slskmessages.GetPeerAddress:self.GetPeerAddress,
			slskmessages.OutConn:self.OutConn,
			slskmessages.UserInfoReply:self.UserInfoReply,
			slskmessages.UserInfoRequest:self.UserInfoRequest,
			slskmessages.PierceFireWall:self.PierceFireWall,
			slskmessages.CantConnectToPeer:self.CantConnectToPeer,
			slskmessages.PeerTransfer:self.PeerTransfer,
			slskmessages.SharedFileList:self.SharedFileList,
			slskmessages.GetSharedFileList:self.GetSharedFileList,
			slskmessages.FileSearchRequest:self.FileSearchRequest,
			slskmessages.FileSearchResult:self.FileSearchResult,
			slskmessages.ConnectToPeer:self.ConnectToPeer,
			slskmessages.GetUserStatus:self.GetUserStatus,
			slskmessages.GetUserStats:self.GetUserStats,
			slskmessages.Relogged:self.Relogged,
			slskmessages.PeerInit:self.PeerInit,
			slskmessages.DownloadFile:self.FileDownload,
			slskmessages.UploadFile:self.FileUpload,
			slskmessages.FileRequest:self.FileRequest,
			slskmessages.TransferRequest:self.TransferRequest,
			slskmessages.TransferResponse:self.TransferResponse,
			slskmessages.QueueUpload:self.QueueUpload,
			slskmessages.QueueFailed:self.QueueFailed,
			slskmessages.UploadFailed:self.UploadFailed,
			slskmessages.PlaceInQueue:self.PlaceInQueue,
		        slskmessages.FileError:self.FileError,
			slskmessages.FolderContentsResponse:self.FolderContentsResponse,
			slskmessages.FolderContentsRequest:self.FolderContentsRequest,
			slskmessages.RoomList:self.RoomList,
			slskmessages.LeaveRoom:self.LeaveRoom,
			slskmessages.GlobalUserList:self.GlobalUserList,
			slskmessages.AddUser:self.AddUser,
			slskmessages.PrivilegedUsers:self.PrivilegedUsers,
			slskmessages.AddToPrivileged:self.AddToPrivileged,
			slskmessages.CheckPrivileges:self.CheckPrivileges,
			slskmessages.ServerPing:self.DummyMessage,
			slskmessages.ParentMinSpeed:self.DummyMessage,
			slskmessages.ParentSpeedRatio:self.DummyMessage,
			slskmessages.Msg85:self.DummyMessage,
			slskmessages.Msg12547:self.Msg12547,
			slskmessages.ParentInactivityTimeout:self.ParentInactivityTimeout,
			slskmessages.SearchInactivityTimeout:self.SearchInactivityTimeout,
			slskmessages.MinParentsInCache:self.MinParentsInCache,
			slskmessages.Msg89:self.DummyMessage,
			slskmessages.WishlistInterval:self.WishlistInterval,
			slskmessages.DistribAliveInterval:self.DummyMessage,
			slskmessages.AdminMessage:self.AdminMessage,
			slskmessages.TunneledMessage:self.TunneledMessage,
			slskmessages.IncConn:self.IncConn,
			slskmessages.PlaceholdUpload:self.PlaceholdUpload,
			slskmessages.PlaceInQueueRequest:self.PlaceInQueueRequest,
			slskmessages.UploadQueueNotification:self.UploadQueueNotification,
			slskmessages.SearchRequest:self.SearchRequest,
			slskmessages.FileSearch:self.SearchRequest,
			slskmessages.RoomSearch:self.SearchRequest,
			slskmessages.UserSearch:self.SearchRequest,
			slskmessages.NetInfo:self.NetInfo,
			slskmessages.DistribAlive:self.DistribAlive,
			slskmessages.DistribSearch:self.DistribSearch,
			ConnectToPeerTimeout:self.ConnectToPeerTimeout,
			transfers.TransferTimeout:self.TransferTimeout,
			slskmessages.RescanShares:self.RescanShares,
			slskmessages.RescanBuddyShares:self.RescanBuddyShares,
			str:self.Notify,
			slskmessages.InternalData:self.DisplaySockets,
			slskmessages.GlobalRecommendations:self.GlobalRecommendations,
			slskmessages.Recommendations:self.Recommendations,
			slskmessages.ItemRecommendations:self.ItemRecommendations,
			slskmessages.SimilarUsers:self.SimilarUsers,
			slskmessages.ItemSimilarUsers:self.ItemSimilarUsers,
			slskmessages.UserInterests:self.UserInterests,
			slskmessages.RoomTickerState:self.RoomTickerState,
			slskmessages.RoomTickerAdd:self.RoomTickerAdd,
			slskmessages.RoomTickerRemove:self.RoomTickerRemove,
			slskmessages.AckNotifyPrivileges:self.AckNotifyPrivileges,
			slskmessages.NotifyPrivileges:self.NotifyPrivileges,
			slskmessages.Unknown126:self.Unknown126,
			slskmessages.Unknown127:self.Unknown127,
			slskmessages.PrivateRoomUsers:self.PrivateRoomUsers,
			slskmessages.PrivateRoomOwned:self.PrivateRoomOwned,
			slskmessages.PrivateRoomAddUser:self.PrivateRoomAddUser,
			slskmessages.PrivateRoomRemoveUser:self.PrivateRoomRemoveUser,
			slskmessages.PrivateRoomAdded:self.PrivateRoomAdded,
			slskmessages.PrivateRoomRemoved:self.PrivateRoomRemoved,
			slskmessages.PrivateRoomDisown:self.PrivateRoomDisown,
			slskmessages.PrivateRoomToggle:self.PrivateRoomToggle,
			slskmessages.PrivateRoomSomething:self.PrivateRoomSomething,
			slskmessages.PrivateRoomOperatorAdded:self.PrivateRoomOperatorAdded,
			slskmessages.PrivateRoomOperatorRemoved:self.PrivateRoomOperatorRemoved,
			slskmessages.PrivateRoomAddOperator:self.PrivateRoomAddOperator,
			slskmessages.PrivateRoomRemoveOperator:self.PrivateRoomRemoveOperator,
			}


	def ProcessRequestToPeer(self, user, message, window = None, address = None):
		""" 
		Sends message to a peer and possibly sets up a window to display 
		the result.
		"""
	
		conn = None
		for i in self.peerconns:
			if i.username == user and i.init.type == 'P' and message.__class__ is not slskmessages.FileRequest and message.__class__ is not slskmessages.FileSearchResult:
				conn = i
				break
		if conn is not None:
			if conn.conn is not None:
				message.conn = conn.conn
				self.queue.put(message)
				if window is not None:
					window.InitWindow(conn.username, conn.conn)
				if message.__class__ is slskmessages.TransferRequest and self.transfers is not None:
					self.transfers.gotConnect(message.req, conn.conn)
				return
			else:
				conn.msgs.append(message)
		else:
			if message.__class__ is slskmessages.FileRequest:
				type = 'F'
			elif message.__class__ is slskmessages.DistribConn:
				type = 'D'
			else:
				type = 'P'
			init = slskmessages.PeerInit(None, self.config.sections["server"]["login"], type, 0)
			firewalled = self.config.sections["server"]["firewalled"]
			addr = None
			behindfw = None
			token = None
			if user in self.users:
				addr = self.users[user].addr
				behindfw = self.users[user].behindfw
			elif address is not None:
				addr = address
			if firewalled:
				if addr is None:
					self.queue.put(slskmessages.GetPeerAddress(user))
				elif behindfw is None:
					self.queue.put(slskmessages.OutConn(None, addr))
				else:
					firewalled = 0
			if not firewalled:
				token = newId()
				self.queue.put(slskmessages.ConnectToPeer(token, user, type))
			conn = PeerConnection(addr = addr, username = user, msgs = [message], token = token, init = init)
			self.peerconns.append(conn)
			if token is not None:
				timeout = 300.0
				conntimeout = ConnectToPeerTimeout(self.peerconns[-1], self.callback)
				timer = threading.Timer(timeout, conntimeout.timeout)
				self.peerconns[-1].conntimer = timer
				timer.start()
			if message.__class__ is slskmessages.FileSearchResult:
				self.searchResultsConnections.append(conn)
		if message.__class__ is slskmessages.TransferRequest and self.transfers is not None:
			if conn.addr is None:
				self.transfers.gettingAddress(message.req)
			elif conn.token is None:
				self.transfers.gotAddress(message.req)
			else:
				self.transfers.gotConnectError(message.req)

	def closeSearchResults(self):
		if self.searchResultsTimer is not None:
			self.searchResultsTimer.cancel()
		for conn in self.searchResultsConnections[:]:
			self.searchResultsConnections.remove(conn)
			self.ClosePeerConnection(conn)
		self.searchResultsTimer = threading.Timer(10, self.closeSearchResults)
		self.searchResultsTimer.start()
		
	def setServerTimer(self):
		if self.servertimeout == -1:
			self.servertimeout = 15
		elif 0 < self.servertimeout < 600:
			self.servertimeout = self.servertimeout * 2
		self.servertimer = threading.Timer(self.servertimeout, self.ServerTimeout)
		self.servertimer.start()
		self.logMessage(_("The server seems to be down or not responding, retrying in %i seconds") %(self.servertimeout))
	
	def ServerTimeout(self):
		if self.config.needConfig() <= 1:
			self.callback([slskmessages.ConnectToServer()])
	
	def StopTimers(self):
		for i in self.peerconns:
			if i.conntimer is not None:
				i.conntimer.cancel()
		if self.servertimer is not None:
			self.servertimer.cancel()
		if self.searchResultsTimer is not None:
			self.searchResultsTimer.cancel()
		if self.respondDistributedTimer is not None:
			self.respondDistributedTimer.cancel()
		if self.transfers is not None:
			self.transfers.AbortTransfers()
			if self.transfers.uploadQueueTimer is not None:
				self.transfers.uploadQueueTimer.cancel()
			if self.transfers.downloadQueueTimer is not None:
				self.transfers.downloadQueueTimer.cancel()
	def ConnectToServer(self, msg):
		self.frame.OnConnect(None)

	def encodeuser(self, string, user = None):
		coding = None
		config = self.config.sections
		if user and user in config["server"]["userencoding"]:
			coding = config["server"]["userencoding"][user]
		string = self.decode(string, coding)
		try:
			
			return string.encode(locale.nl_langinfo(locale.CODESET))
		except:
			return string
		
	def encode(self, str, networkenc = None):
		if networkenc is None:
			networkenc = self.config.sections["server"]["enc"]
		if type(str) is types.UnicodeType:
			return str.encode(networkenc,'replace')
		else:
			return str.decode("utf-8",'replace').encode(networkenc,'replace')

	def decode(self, string, networkenc = None):
		if networkenc is None:
			networkenc = self.config.sections["server"]["enc"]
		return str(string).decode(networkenc,'replace').encode("utf-8", "replace")

	def getencodings(self):
		# Encodings and descriptions for ComboBoxes
		return [["Latin", 'ascii'], ["US-Canada", 'cp037'],  ['Hebrew', 'cp424'], ['US English', 'cp437'], ['International', 'cp500'], ['Greek', 'cp737'], ['Estonian', 'cp775'], ['Western European', 'cp850'], ['Central European', 'cp852'], ['Cyrillic', 'cp855'], ['Cyrillic', 'cp856'], ['Turkish', 'cp857'], ['Portuguese', 'cp860'], ['Icelandic', 'cp861'], ['Hebrew', 'cp862'], ['French Canadian', 'cp863'], ['Arabic', 'cp864'], ['Nordic', 'cp865'], ['Cyrillic', 'cp866'], ['Latin-9', 'cp869'], ['Thai', 'cp874'], ['Greek', 'cp875'], ['Japanese', 'cp932'], ['Chinese Simple', 'cp936'], ['Korean', 'cp949'], ['Chinese Traditional', 'cp950'], ['Urdu',  'cp1006'], ['Turkish',  'cp1026'], ['Latin', 'cp1140'], ['Central European', 'cp1250'], ['Cyrillic', 'cp1251'], ['Latin', 'cp1252'], ['Greek', 'cp1253'], ['Turkish', 'cp1254'], ['Hebrew', 'cp1255'], ['Arabic', 'cp1256'], ['Baltic', 'cp1257'], ['Vietnamese', 'cp1258'],  ['Latin', 'iso8859-1'], ['Latin 2', 'iso8859-2'], ['South European', 'iso8859-3'], ['North European', 'iso8859-4'], ['Cyrillic', 'iso8859-5'], ['Arabic', 'iso8859-6'], ['Greek', 'iso8859-7'], ['Hebrew', 'iso8859-8'], ['Turkish', 'iso8859-9'], ['Nordic', 'iso8859-10'], ['Thai', 'iso8859-11'], ['Baltic', 'iso8859-13'], ['Celtic', 'iso8859-14'], ['Western European', 'iso8859-15'], ['South-Eastern European', 'iso8859-16'], ['Cyrillic', 'koi8-r'], ['Latin', 'latin-1'], ['Cyrillic', 'mac-cyrillic'], ['Greek', 'mac-greek'], ['Icelandic', 'mac-iceland'], ['Latin 2', 'mac-latin2'], ['Latin', 'mac-roman'], ['Turkish', 'mac-turkish'], ['International', 'utf-16'], ['International', 'utf-7'], ['International', 'utf-8']]

	def sendNumSharedFoldersFiles(self):
		"""
		Send number of files in buddy shares if only buddies can
		download, and buddy-shares are enabled.
		"""
		conf = self.config.sections

		if conf["transfers"]["enablebuddyshares"] and conf["transfers"]["friendsonly"]:
			shared_db = "bsharedfiles"
		else:
			shared_db = "sharedfiles"
		sharedfolders = len(conf["transfers"][shared_db])
		sharedfiles = 0
		for i in conf["transfers"][shared_db].keys():
			sharedfiles += len(conf["transfers"][shared_db][i])
		self.queue.put(slskmessages.SharedFoldersFiles(sharedfolders, sharedfiles))

	def RescanShares(self, msg, rebuild=False):
		import utils
		utils.frame = self.frame
		utils.log = self.logMessage
		files, streams, wordindex, fileindex, mtimes = utils.rescandirs(msg.shared, self.config.sections["transfers"]["sharedmtimes"], self.config.sections["transfers"]["sharedfiles"], self.config.sections["transfers"]["sharedfilesstreams"], msg.yieldfunction, self.frame.SharesProgress, name=_("Shares"), rebuild=rebuild)
		self.frame.RescanFinished([files, streams, wordindex, fileindex, mtimes], "normal")
		
	def RebuildShares(self, msg):
		self.RescanShares(msg, rebuild=True)
	
	def RebuildBuddyShares(self, msg):
		self.RescanBuddyShares(msg, rebuild=True)
	
	def RescanBuddyShares(self, msg, rebuild=False):
		import utils
		utils.frame = self.frame
		utils.log = self.logMessage
		files, streams, wordindex, fileindex, mtimes = utils.rescandirs(msg.shared, self.config.sections["transfers"]["bsharedmtimes"], self.config.sections["transfers"]["bsharedfiles"], self.config.sections["transfers"]["bsharedfilesstreams"], msg.yieldfunction, self.frame.BuddySharesProgress, name=_("Buddy Shares"), rebuild=rebuild)
		self.frame.RescanFinished([files, streams, wordindex, fileindex, mtimes], "buddy")
		
	def CompressShares(self, sharestype):
		if sharestype == "normal":
			streams = self.config.sections["transfers"]["sharedfilesstreams"]
		elif sharestype == "buddy":
			streams = self.config.sections["transfers"]["bsharedfilesstreams"]

		if streams is None:
			message = _("ERROR: No %(type)s shares database available") % {"type": sharestype}
			print message
			self.logMessage(message, None)
			return
		
		m = slskmessages.SharedFileList(None, streams)
		m.makeNetworkMessage(nozlib=0, rebuild=True)
		
		if sharestype == "normal":
			self.CompressedSharesNormal = m
		elif sharestype == "buddy":
			self.CompressedSharesBuddy = m
        
	## Notify user of error when recieving or sending a message
	# @param self NetworkEventProcessor (Class)
	# @param string a string containing an error message
	def Notify(self, string):
		self.logMessage("%s" % self.decode(string))

	def DisplaySockets(self, msg):
		self.frame.SetSocketStatus(msg.msg)
		
	def ConnectError(self, msg):
		if msg.connobj.__class__ is slskmessages.ServerConn:
			self.setStatus(_("Can't connect to server %(host)s:%(port)s: %(error)s") % {'host': msg.connobj.addr[0], 'port': msg.connobj.addr[1], 'error': self.decode(msg.err) } )
			self.setServerTimer()
			if self.serverconn is not None:
				self.serverconn = None
		
			self.frame.ConnectError(msg)
		elif msg.connobj.__class__ is slskmessages.OutConn:
			for i in self.peerconns[:]:
				if i.addr == msg.connobj.addr and i.conn is None: 
					if i.token is None:
						i.token  = newId()
						self.queue.put(slskmessages.ConnectToPeer(i.token, i.username, i.init.type))
						if i.username in self.users:
							self.users[i.username].behindfw = "yes"
						for j in i.msgs: 
							if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
								self.transfers.gotConnectError(j.req)
						conntimeout = ConnectToPeerTimeout(i, self.callback)
						timer = threading.Timer(300.0, conntimeout.timeout)
						timer.start()
						if i.conntimer is not None:
							i.conntimer.cancel()
						i.conntimer = timer
					else:
						for j in i.msgs:
							if j.__class__ in [slskmessages.TransferRequest, slskmessages.FileRequest] and self.transfers is not None:
								self.transfers.gotCantConnect(j.req)
						self.logMessage(_("Can't connect to %s, sending notification via the server") %(i.username), 1)
						self.queue.put(slskmessages.CantConnectToPeer(i.token, i.username))
						if i.conntimer is not None:
							i.conntimer.cancel()
						self.peerconns.remove(i)
					break
			else:
				self.logMessage("%s %s %s" %(msg.err, msg.__class__, vars(msg)))
		else:
			self.logMessage("%s %s %s" %(msg.err, msg.__class__, vars(msg)), 1)
			self.ClosedConnection(msg.connobj.conn, msg.connobj.addr)

	def IncPort(self, msg):
		self.waitport = msg.port
		self.setStatus(_("Listening on port %i") %(msg.port))

	def ServerConn(self, msg):
		self.setStatus(_("Connected to server %(host)s:%(port)s, logging in...") % {'host':msg.addr[0], 'port': msg.addr[1]})
		time.sleep(1)
		self.serverconn = msg.conn
		self.servertimeout = -1
		self.users = {}
		self.queue.put(slskmessages.Login(self.config.sections["server"]["login"], self.config.sections["server"]["passw"], 181)) #155, 156, 157, 180
		if self.waitport is not None:	
			self.queue.put(slskmessages.SetWaitPort(self.waitport))

	def PeerInit(self, msg):
	#	list = [i for i in self.peerconns if i.conn == msg.conn.conn]
	#	if list == []:
		self.peerconns.append(PeerConnection(addr = msg.conn.addr, username = msg.user, conn = msg.conn.conn, init = msg, msgs = []))
	#	else:
	#	    for i in list:
	#		i.init = msg
	#		i.username = msg.user

	def ConnClose(self, msg):
		self.ClosedConnection(msg.conn, msg.addr)

	def ClosedConnection(self, conn, addr):
		if conn == self.serverconn:
			self.setStatus(_("Disconnected from server %(host)s:%(port)s") %{'host':addr[0], 'port':addr[1]})
			if not self.frame.manualdisconnect:
				self.setServerTimer()
			else:
				self.frame.manualdisconnect = 0
			if self.searchResultsTimer is not None:
				self.searchResultsTimer.cancel()
			if self.respondDistributedTimer is not None:
				self.respondDistributedTimer.cancel()
			self.serverconn = None
			self.watchedusers = []
			if self.transfers is not None:
				self.transfers.AbortTransfers()
				self.transfers.SaveDownloads()
				if self.transfers.uploadQueueTimer is not None:
					self.transfers.uploadQueueTimer.cancel()
				if self.transfers.downloadQueueTimer is not None:
					self.transfers.downloadQueueTimer.cancel()
			self.privatechat = self.chatrooms = self.userinfo = self.userbrowse = self.search = self.transfers = self.userlist = None
			self.frame.ConnClose(conn, addr)
		else:
			for i in self.peerconns[:]:
				if i.conn == conn:
					self.logMessage(_("Connection closed by peer: %s") % self.decode(vars(i)), 1)
					if i.conntimer is not None:
						i.conntimer.cancel()
					if self.transfers is not None:
						self.transfers.ConnClose(conn, addr)
					if i == self.GetDistribConn():
						self.DistribConnClosed(i)
					self.peerconns.remove(i)
					break
			else:
				self.logMessage(_("Removed connection closed by peer: %(conn_obj)s %(address)s") %{'conn_obj':conn, 'address':addr}, 1)
				self.queue.put(slskmessages.ConnClose(conn))
		
	def Login(self, msg):
		self.logintime = time.time()
		conf = self.config.sections
		if msg.success:
			self.setStatus(_("Logged in, getting the list of rooms..."))
			self.transfers = transfers.Transfers(conf["transfers"]["downloads"], self.peerconns, self.queue, self, self.users)
			if msg.ip is not None:
				self.ipaddress = msg.ip
			
			self.privatechat, self.chatrooms, self.userinfo, self.userbrowse, self.search, downloads, uploads, self.userlist = self.frame.InitInterface(msg)
		
			self.transfers.setTransferPanels(downloads, uploads)
			self.sendNumSharedFoldersFiles()
			self.queue.put(slskmessages.SetStatus((not self.frame.away)+1))
			for thing in self.config.sections["interests"]["likes"]:
				self.queue.put(slskmessages.AddThingILike(self.encode(thing)))
			for thing in self.config.sections["interests"]["dislikes"]:
				self.queue.put(slskmessages.AddThingIHate(self.encode(thing)))
			if not len(self.distribcache):
   				self.queue.put(slskmessages.HaveNoParent(1))
			self.queue.put(slskmessages.NotifyPrivileges(1, self.config.sections["server"]["login"]))
			self.privatechat.Login()
			self.queue.put(slskmessages.CheckPrivileges())
			
			self.queue.put(slskmessages.PrivateRoomToggle(self.config.sections["server"]["private_chatrooms"]))
		else:
			self.frame.manualdisconnect = 1
			self.setStatus(_("Can not log in, reason: %s") %(msg.reason))
			self.logMessage(_("Can not log in, reason: %s") %(msg.reason))
			self.frame.settingswindow.SetSettings(self.config.sections)
			self.frame.settingswindow.SwitchToPage("Server")
			#self.frame.settingswindow.Hilight(self.frame.settingswindow.pages["Server"].Login)
			self.frame.settingswindow.Hilight(self.frame.settingswindow.pages["Server"].Password)
				
	def NotifyPrivileges(self, msg):
		if msg.token != None:
			pass
		
	def AckNotifyPrivileges(self, msg):
		if msg.token != None:
			pass
			# Until I know the syntax, sending this message is probably a bad idea
			#self.queue.put(slskmessages.AckNotifyPrivileges(msg.token))
			
	def PMessageUser(self, msg):
		user = ip = port = None
		# Get peer's username, ip and port
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
				user = i.username
				if i.addr is not None:
					ip, port = i.addr
				break
		if user == None:
			# No peer connection
			return
		if user != msg.user:
			text = _("(Warning: %(realuser)s is attempting to spoof %(fakeuser)s) ") % {"realuser": user, "fakeuser": msg.user} + msg.msg
			msg.user = user
		else:
			text = msg.msg
		if self.privatechat is not None:
			self.privatechat.ShowMessage(msg, text, status=0)
			
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
			
	def MessageUser(self, msg):
		status = 0
		if self.logintime:
			if time.time() <= self.logintime + 2:
				# Offline message 
				status = 1
		
		if self.privatechat is not None:
			self.privatechat.ShowMessage(msg, msg.msg, status=status)
			self.queue.put(slskmessages.MessageAcked(msg.msgid))
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def UserJoinedRoom(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.UserJoinedRoom(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))


	def JoinRoom(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.JoinRoom(msg)
			ticker = ""
			if msg.room in self.config.sections["ticker"]["rooms"]:
				ticker = self.config.sections["ticker"]["rooms"][msg.room]
			elif self.config.sections["ticker"]["default"]:
				ticker = self.config.sections["ticker"]["default"]
			if ticker:
				encoding = self.config.sections["server"]["enc"]
				if msg.room in self.config.sections["server"]["roomencoding"]:
					encoding = self.config.sections["server"]["roomencoding"][msg.room]
				self.queue.put(slskmessages.RoomTickerSet(msg.room, self.encode(ticker, encoding)))
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	def Unknown126(self, msg):
		self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	def Unknown127(self, msg):
		self.logMessage("%s %s" %(msg.__class__, vars(msg)))
		

		
	def PrivateRoomUsers(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.PrivateRoomUsers(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	def PrivateRoomOwned(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.PrivateRoomOwned(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
		
	def PrivateRoomAddUser(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.PrivateRoomAddUser(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
		
	def PrivateRoomRemoveUser(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.PrivateRoomRemoveUser(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
				
	def PrivateRoomOperatorAdded(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.PrivateRoomOperatorAdded(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
		
		
	def PrivateRoomOperatorRemoved(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.PrivateRoomOperatorRemoved(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

				
	def PrivateRoomAddOperator(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.PrivateRoomAddOperator(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
		
	def PrivateRoomRemoveOperator(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.PrivateRoomRemoveOperator(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
				
	def PrivateRoomAdded(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.PrivateRoomAdded(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
		
	def PrivateRoomRemoved(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.PrivateRoomRemoved(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
			
	def PrivateRoomDisown(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.PrivateRoomDisown(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	def PrivateRoomToggle(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.TogglePrivateRooms(msg.enabled)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	def PrivateRoomSomething(self, msg):
		#msg.debug()
		pass
	
	def LeaveRoom(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.LeaveRoom(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))


	def SayChatRoom(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.SayChatRoom(msg, msg.msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def AddUser(self, msg):
		if msg.user not in self.watchedusers:
			self.watchedusers.append(msg.user)
		if not msg.userexists:
			if msg.user not in self.users:
				self.users[msg.user] = UserAddr(status = -1)
			if self.search is not None:	
				self.search.NonExistantUser(msg.user)
		if self.transfers is not None:
			self.transfers.getAddUser(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
		if msg.status is not None:
			self.GetUserStatus(msg)
		elif msg.userexists and msg.status is None:
			self.queue.put(slskmessages.GetUserStatus(msg.user))
			
		if msg.files is not None:
			self.GetUserStats(msg)
		elif msg.userexists and msg.files is None:
			self.queue.put(slskmessages.GetUserStats(msg.user))
			
	def PrivilegedUsers(self, msg):
		if self.transfers is not None:
			self.transfers.setPrivilegedUsers(msg.users)
			self.logMessage(_("%i privileged users") %(len(msg.users)))
			self.queue.put(slskmessages.HaveNoParent(1))
			self.queue.put(slskmessages.GetUserStats(self.config.sections["server"]["login"]))
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def AddToPrivileged(self, msg):
		if self.transfers is not None:
			self.transfers.addToPrivileged(msg.user)
			#self.logMessage(_("User %s added to privileged list") %(msg.user), 1)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def CheckPrivileges(self, msg):
		mins = msg.seconds / 60
		hours = mins / 60
		days = hours / 24
		if msg.seconds == 0:
			self.logMessage(_("You have no privileges left"))
		else:
			self.logMessage(_("%(days)i days, %(hours)i hours, %(minutes)i minutes, %(seconds)i seconds of download privileges left") %{'days':days, 'hours':hours % 24, 'minutes':mins % 60, 'seconds':msg.seconds % 60})
		self.privileges_left = msg.seconds
		
	def AdminMessage(self, msg):
		self.logMessage("%s" %(msg.msg))
	
	def DummyMessage(self, msg):
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)
		
	def Msg12547(self, msg):
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)
		
	def ParentInactivityTimeout(self, msg):
		pass
		#msg.debug()
	def SearchInactivityTimeout(self, msg):
		pass
		#msg.debug()
	def MinParentsInCache(self, msg):
		pass
		#msg.debug()
	def WishlistInterval(self, msg):
		if self.search is not None:
			self.search.SetInterval(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)

	def GetUserStatus(self, msg):
		# Causes recursive requests when privileged?
		#self.queue.put(slskmessages.AddUser(msg.user))
		if msg.user in self.users:
			if msg.status == 0:
				self.users[msg.user] = UserAddr(status = msg.status)
			else:
				self.users[msg.user].status = msg.status
		else:
			self.users[msg.user] = UserAddr(status = msg.status)
		
		if msg.privileged != None:
			if msg.privileged == 1:
				if self.transfers is not None:
					self.transfers.addToPrivileged(msg.user)
					
				else:
					self.logMessage("%s %s" %(msg.__class__, vars(msg)))

		self.frame.GetUserStatus(msg)
		if self.userlist is not None:
			self.userlist.GetUserStatus(msg)
		if self.transfers is not None:
			self.transfers.GetUserStatus(msg)
		if self.privatechat is not None:
			self.privatechat.GetUserStatus(msg)
		if self.userinfo is not None:
			self.userinfo.GetUserStatus(msg)
		if self.userbrowse is not None:
			self.userbrowse.GetUserStatus(msg)
		if self.search is not None:
			self.search.GetUserStatus(msg)
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.GetUserStatus(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def UserInterests(self, msg):
		if self.userinfo is not None:
			self.userinfo.ShowInterests(msg)
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)
	
	def GetUserStats(self, msg):
		if msg.user == self.config.sections["server"]["login"]:
			self.speed = msg.avgspeed
	
		self.frame.GetUserStats(msg)
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.GetUserStats(msg)
		if self.userinfo is not None:
			self.userinfo.GetUserStats(msg)
		if self.userlist is not None:
			self.userlist.GetUserStats(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def UserLeftRoom(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.UserLeftRoom(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))


	def QueuedDownloads(self, msg):
	#	if self.chatrooms is not None:
	#	    self.chatrooms.roomsctrl.QueuedDownloads(msg) 
	#	else: 
		self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def GetPeerAddress(self, msg):
		for i in self.peerconns:
			if i.username == msg.user and i.addr is None:
				if msg.port != 0 or i.tryaddr == 10:
					if i.tryaddr == 10:
						self.logMessage(_("Server reported port 0 for the 10th time for user %(user)s, giving up") %{'user':msg.user}, 1)
					elif i.tryaddr is not None:
						self.logMessage(_("Server reported non-zero port for user %(user)s after %(tries)i retries") %{'user':msg.user, 'tries':i.tryaddr}, 1)
					i.addr = (msg.ip, msg.port)
					i.tryaddr = None
					self.queue.put(slskmessages.OutConn(None, i.addr))
					for j in i.msgs:
						if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
							self.transfers.gotAddress(j.req)
				else:
					if i.tryaddr is None:
						i.tryaddr = 1
						self.logMessage(_("Server reported port 0 for user %(user)s, retrying") %{'user':msg.user}, 1)
					else:
						i.tryaddr +=1
					self.queue.put(slskmessages.GetPeerAddress(msg.user))
				break
		else:
			if msg.user in self.users:
				self.users[msg.user].addr = (msg.ip, msg.port)
			else:
				self.users[msg.user] = UserAddr(addr = (msg.ip, msg.port) )
			if msg.user in self.ip_requested:
				if self.ip_requested[msg.user]:
					self.frame.OnUnBlockUser(msg.user)
				else:
					self.frame.OnBlockUser(msg.user)
				del self.ip_requested[msg.user]
				return
				
			import socket
			if self.geoip:
				cc = self.geoip.country_name_by_addr(msg.ip)
				cn = self.geoip.country_code_by_addr(msg.ip)
				if cn is not None:
					self.frame.HasUserFlag(msg.user, "flag_"+cn)
			else:
				cc = ""
			if cc:
				cc = " (%s)" % cc
			else:
				cc = ""
			try:
				hostname = socket.gethostbyaddr(msg.ip)[0]
				message = _("IP address of %(user)s is %(ip)s, name %(host)s, port %(port)i%(country)s") %{'user':msg.user, 'ip':msg.ip, 'host':hostname, 'port':msg.port, 'country':cc}
			except:
				message = _("IP address of %(user)s is %(ip)s, port %(port)i%(country)s") %{'user':msg.user, 'ip':msg.ip, 'port':msg.port, 'country':cc}
			self.logMessage(message)
		
			
	def Relogged(self, msg):
		self.logMessage(_("Someone else is logging in with the same nickname, server is going to disconnect us"))
		self.frame.manualdisconnect = 1

	def OutConn(self, msg):
		for i in self.peerconns:
			if i.addr == msg.addr and i.conn is None:
				if i.token is None:
					i.init.conn = msg.conn
					self.queue.put(i.init)
				else:
					self.queue.put(slskmessages.PierceFireWall(msg.conn, i.token))
				i.conn = msg.conn
				for j in i.msgs:
					if j.__class__ is slskmessages.UserInfoRequest and self.userinfo is not None:
						self.userinfo.InitWindow(i.username, msg.conn)
					if j.__class__ is slskmessages.GetSharedFileList and self.userbrowse is not None:
						self.userbrowse.InitWindow(i.username, msg.conn)
					if j.__class__ is slskmessages.FileRequest and self.transfers is not None:
						self.transfers.gotFileConnect(j.req, msg.conn)
					if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
						self.transfers.gotConnect(j.req, msg.conn)
					j.conn = msg.conn
					self.queue.put(j)
				i.msgs = []
				break
		
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)

	def IncConn(self, msg):
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)

	def ConnectToPeer(self, msg):
		init = slskmessages.PeerInit(None, msg.user, msg.type, 0)
		self.queue.put(slskmessages.OutConn(None, (msg.ip, msg.port), init))
		self.peerconns.append(PeerConnection(addr = (msg.ip, msg.port), username = msg.user, msgs = [], token = msg.token, init = init))
	
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)

	def CheckUser(self, user, addr):
		"""
		Check if this user is banned, geoip-blocked, and which shares
		it is allowed to access based on transfer and shares settings.
		"""
		if user in self.config.sections["server"]["banlist"]:
			if self.config.sections["transfers"]["usecustomban"]:
				return 0, _("Banned (%s)") % self.config.sections["transfers"]["customban"]
			else:
				return 0, _("Banned")
		if user in [i[0] for i in self.config.sections["server"]["userlist"]] and self.config.sections["transfers"]["enablebuddyshares"]:
			# For sending buddy-only shares
			return 2, ""
		if user in [i[0] for i in self.config.sections["server"]["userlist"]]:
			return 1, ""
		if self.config.sections["transfers"]["friendsonly"]:
			return 0, _("Sorry, friends only")
		if not self.geoip or not self.config.sections["transfers"]["geoblock"]:
			return 1, _("geoip")
		cc = None
		if addr is not None:
			cc = self.geoip.country_code_by_addr(addr)
		if not cc:
			if self.config.sections["transfers"]["geopanic"]:
				return 0, _("Sorry, geographical paranoia")
			else:
				return 1, ""
		if self.config.sections["transfers"]["geoblockcc"][0].find(cc) >= 0:
			return 0, _("Sorry, your country is blocked")
		return 1, ""
	
	def CheckSpoof(self, user, ip, port):
		if user not in self.users:
			return 0
		if self.users[user].addr != None:
			#if len(self.users[user].addr) != 2:
				#return 0
			if len(self.users[user].addr) == 2:
				if self.users[user].addr is not None:
					u_ip, u_port = self.users[user].addr
					if u_ip != ip:
						warning = _("IP %(ip)s:%(port)s is spoofing user %(user)s with a peer request, blocking because it does not match IP: %(real_ip)s") %{'ip':ip, 'port':port, 'user':user, 'real_ip':u_ip}
						self.logMessage(warning , None)
						print warning 
						return 1
		return 0
	
	def GetSharedFileList(self, msg):
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)
		user = ip = port = None
		# Get peer's username, ip and port
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
				
				user = i.username
				if i.addr is not None:
					if len(i.addr) != 2:
						break
					ip, port = i.addr
				break
		if user == None:
			# No peer connection
			return
		requestTime = time.time()
		if user in self.requestedShares:
			if not requestTime >  10 + self.requestedShares[user]:
				# Ignoring request, because it's 10 or less seconds since the
				# last one by this user
				return
		self.requestedShares[user] = requestTime
		# Check address is spoofed, if possible
		#if self.CheckSpoof(user, ip, port):
			# Message IS spoofed
		#	return
		if user == self.config.sections["server"]["login"]:
			if ip != None and port != None:
				self.logMessage(_("%(user)s is making a BrowseShares request, blocking possible spoofing attempt from IP %(ip)s port %(port)s") %{'user':user, 'ip':ip, 'port':port}, None)
			else:
				self.logMessage(_("%(user)s is making a BrowseShares request, blocking possible spoofing attempt from an unknown IP & port") %{'user':user}, None)
			if msg.conn.conn != None:
				self.queue.put(slskmessages.ConnClose(msg.conn.conn))
			return
		self.logMessage(_("%(user)s is making a BrowseShares request") %{'user':user}, None)
		addr = msg.conn.addr[0]
		checkuser, reason = self.CheckUser(user, addr)
	
		if checkuser == 1:
			## Send Normal Shares
			if self.newnormalshares:
				self.CompressShares("normal")
				self.newnormalshares = False
			m = self.CompressedSharesNormal

		elif checkuser == 2:
			## Send Buddy Shares
			if self.newbuddyshares:
				self.CompressShares("buddy")
				self.newbuddyshares = False
			m = self.CompressedSharesBuddy

		else:
			## Nyah, Nyah
			m = slskmessages.SharedFileList(msg.conn.conn, {})
			m.makeNetworkMessage(nozlib=0)


		m.conn = msg.conn.conn
		self.queue.put(m)
		
		
	def ClosePeerConnection(self, peerconn, force=False):
		if peerconn == None:
			return
		curtime = time.time()
		for i in self.peerconns[:]:
			if i.conn == peerconn:
				if not self.protothread.socketStillActive(i.conn) or force:
					self.queue.put(slskmessages.ConnClose(i.conn))
				break
		
	def UserInfoReply(self, msg):
		for i in self.peerconns:
			if i.conn is msg.conn.conn and self.userinfo is not None:
				# probably impossible to do this
				if i.username != self.config.sections["server"]["login"]:
					self.userinfo.ShowInfo(i.username, msg)
			
	def UserInfoRequest(self, msg):
		user = ip = port = None
		# Get peer's username, ip and port
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
				user = i.username
				if i.addr is not None:
					ip, port = i.addr
				break
		if user == None:
			# No peer connection
			return
		requestTime = time.time()
		if user in self.requestedInfo:
			if not requestTime >  10 + self.requestedInfo[user]:
				# Ignoring request, because it's 10 or less seconds since the
				# last one by this user
				return
		self.requestedInfo[user] = requestTime
		# Check address is spoofed, if possible
		#if self.CheckSpoof(user, ip, port):
			# Message IS spoofed
		#	return
		if user == self.config.sections["server"]["login"]:
			if ip is not None and port is not None:
				self.logMessage(_("Blocking %(user)s from making a UserInfo request, possible spoofing attempt from IP %(ip)s port %(port)s") %{'user':user, 'ip':ip, 'port':port}, None)
			else:
				self.logMessage(_("Blocking %s from making a UserInfo request, possible spoofing attempt from an unknown IP & port") %(user), None)
			if msg.conn.conn != None:
				self.queue.put(slskmessages.ConnClose(msg.conn.conn))
			return
		if user in self.config.sections["server"]["banlist"]:
			self.logMessage(_("%(user)s is banned, but is making a UserInfo request") %{'user':user}, 1)
			self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)
			return
		try:
			if sys.platform == "win32":
				userpic = u"%s" % self.config.sections["userinfo"]["pic"]
				if not os.path.exists(userpic):
					userpic = self.config.sections["userinfo"]["pic"]
			else:
				userpic = self.config.sections["userinfo"]["pic"]
			f=open(userpic,'rb')
			pic = f.read()
			f.close()
		except:
			pic = None
		descr = self.encode(eval(self.config.sections["userinfo"]["descr"], {})).replace("\n", "\r\n")
		
		if self.transfers is not None:
			totalupl = self.transfers.getTotalUploadsAllowed()
			queuesize = self.transfers.getUploadQueueSizes()[0]
			slotsavail = (not self.transfers.bandwidthLimitReached())
			ua = self.frame.np.config.sections["transfers"]["remotedownloads"]
			if ua:
				uploadallowed = self.frame.np.config.sections["transfers"]["uploadallowed"]
			else:
				uploadallowed = ua
			self.queue.put(slskmessages.UserInfoReply(msg.conn.conn, descr, pic, totalupl, queuesize, slotsavail, uploadallowed))
	
		self.logMessage(_("%(user)s is making a UserInfo request") %{'user':user}, None)
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)
		


	def SharedFileList(self, msg):
		for i in self.peerconns:
			if i.conn is msg.conn.conn and self.userbrowse is not None:
				if i.username != self.config.sections["server"]["login"]:
					self.userbrowse.ShowInfo(i.username, msg)

	def FileSearchResult(self, msg):
		for i in self.peerconns:
			if i.conn is msg.conn.conn and self.search is not None:
				if self.geoip:
					if i.addr:
						country = self.geoip.country_code_by_addr(i.addr[0])
					else:
						country = ""
				else:
					country = ""
				self.search.ShowResult(msg, i.username, country)
				self.ClosePeerConnection(i.conn)

	def PierceFireWall(self, msg):
		for i in self.peerconns:
			if i.token == msg.token and i.conn is None:
				if i.conntimer is not None:
					i.conntimer.cancel()
				i.init.conn = msg.conn.conn
				self.queue.put(i.init)
				i.conn = msg.conn.conn
				for j in i.msgs:
					if j.__class__ is slskmessages.UserInfoRequest and self.userinfo is not None:
						self.userinfo.InitWindow(i.username, msg.conn.conn)
					if j.__class__ is slskmessages.GetSharedFileList and self.userbrowse is not None:
						self.userbrowse.InitWindow(i.username, msg.conn.conn)
					if j.__class__ is slskmessages.FileRequest and self.transfers is not None:
						self.transfers.gotFileConnect(j.req, msg.conn.conn)
					if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
						self.transfers.gotConnect(j.req, msg.conn.conn)
					j.conn = msg.conn.conn
					self.queue.put(j)
				i.msgs = []
				break

		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)

	def CantConnectToPeer(self, msg):
		for i in self.peerconns[:]:
			if i.token == msg.token:
				if i.conntimer is not None:
					i.conntimer.cancel()
				if i == self.GetDistribConn():
					self.DistribConnClosed(i)
				self.peerconns.remove(i)
				self.logMessage(_("Can't connect to %s (either way), giving up") % (i.username), 1)
				for j in i.msgs: 
					if j.__class__ in [slskmessages.TransferRequest, slskmessages.FileRequest] and self.transfers is not None:
						self.transfers.gotCantConnect(j.req)

	def ConnectToPeerTimeout(self, msg):
		for i in self.peerconns[:]:
			if i == msg.conn:
				if i == self.GetDistribConn():
					self.DistribConnClosed(i)
				self.peerconns.remove(i)
				self.logMessage(_("User %s does not respond to connect request, giving up") % (i.username), 1)
				for j in i.msgs:
					if j.__class__ in [slskmessages.TransferRequest, slskmessages.FileRequest] and self.transfers is not None:
						self.transfers.gotCantConnect(j.req)

	def TransferTimeout(self, msg):
		if self.transfers is not None:
			self.transfers.TransferTimeout(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	
	def FileDownload(self, msg):
		if self.transfers is not None:
			self.transfers.FileDownload(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	def FileUpload(self, msg):
		if self.transfers is not None:
			self.transfers.FileUpload(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	
	def FileRequest(self, msg):
		if self.transfers is not None:
			self.transfers.FileRequest(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	def FileError(self, msg):
		if self.transfers is not None:
			self.transfers.FileError(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	def TransferRequest(self, msg):
		if self.transfers is not None:
			self.transfers.TransferRequest(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def TransferResponse(self, msg):
		if self.transfers is not None:
			self.transfers.TransferResponse(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	
	def QueueUpload(self, msg):
		if self.transfers is not None:
			self.transfers.QueueUpload(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	def QueueFailed(self, msg):
		if self.transfers is not None:
			self.transfers.QueueFailed(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	def PlaceholdUpload(self, msg):
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)
	
	def PlaceInQueueRequest(self, msg):
		if self.transfers is not None:
			self.transfers.PlaceInQueueRequest(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def UploadQueueNotification(self, msg):
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)
		self.transfers.UploadQueueNotification(msg)
			
	def UploadFailed(self, msg):
		if self.transfers is not None:
			self.transfers.UploadFailed(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	
	def PlaceInQueue(self, msg):
		if self.transfers is not None:
			self.transfers.PlaceInQueue(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def FolderContentsResponse(self, msg):
		if self.transfers is not None:
			
			for i in self.peerconns:
				if i.conn is msg.conn.conn:
					username = i.username
			# Check for a large number of files
			many=0
			folder = ""
			files = []
			for i in msg.list.keys():
				for j in msg.list[i].keys():
					if os.path.commonprefix([i, j]) == j:
						files = msg.list[i][j]
						numfiles = len(files)
						if numfiles > 100:
							many=1
							
							
							folder = j
							
							
			if many:
		
				self.frame.download_large_folder(username, folder, files, numfiles, msg)
				
			else:
				self.transfers.FolderContentsResponse(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def FolderContentsRequest(self, msg):
		username = None
		checkuser = None
		reason = ""
		for i in self.peerconns:
			if i.conn is msg.conn.conn:
				username = i.username
				checkuser, reason = self.CheckUser(username, None)
				break
		if not username:
			return
		if not checkuser:
			self.queue.put(slskmessages.MessageUser(username, "[Automatic Message] "+reason) )
			return
		else:
			self.queue.put(slskmessages.MessageUser(username, "Please try browsing me if you get 'File not shared' errors. This is an automatic message, you don't have to reply to it." ) )
			
		if checkuser == 1:
			shares = self.config.sections["transfers"]["sharedfiles"]
		elif checkuser == 2:
			shares = self.config.sections["transfers"]["bsharedfiles"]
		else:
			response = self.queue.put(slskmessages.TransferResponse(msg.conn.conn, 0, reason = reason, req=0) )
			shares = {}
		
		if checkuser:
			if msg.dir.replace("\\", os.sep)[:-1] in shares:
				self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\", os.sep)[:-1]]))
			elif msg.dir.replace("\\", os.sep) in shares:
				self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\", os.sep)]))
			else:
				if checkuser == 2:
					shares = self.config.sections["transfers"]["sharedfiles"]
					if msg.dir.replace("\\", os.sep)[:-1] in shares:
						self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\", os.sep)[:-1]]))
					elif msg.dir.replace("\\", os.sep) in shares:
						self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.replace("\\", os.sep)]))
					
				
		
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)

	def RoomList(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.SetRoomList(msg)
			self.setStatus("")
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	def GlobalUserList(self, msg):
		if self.globallist is not None:
			self.globallist.setGlobalUsersList(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	def PeerTransfer(self, msg):
		if self.userinfo is not None and msg.msg is slskmessages.UserInfoReply:
			self.userinfo.UpdateGauge(msg)
		if self.userbrowse is not None and msg.msg is slskmessages.SharedFileList:
			self.userbrowse.UpdateGauge(msg)

	def TunneledMessage(self, msg):
		if msg.code in self.protothread.peerclasses:
			peermsg = self.protothread.peerclasses[msg.code](None)
		
			peermsg.parseNetworkMessage(msg.msg)
			peermsg.tunneleduser = msg.user
			peermsg.tunneledreq = msg.req
			peermsg.tunneledaddr = msg.addr
			self.callback([peermsg])
		else:
			self.logMessage(_("Unknown tunneled message: %s") %(vars(msg)))

	def ExactFileSearch(self, msg):
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)
		
	def FileSearchRequest(self, msg):
		for i in self.peerconns:
			if i.conn == msg.conn.conn:
				user = i.username
				self.processSearchRequest(msg.searchterm, user, msg.searchid, 1)
		
	
	def SearchRequest(self, msg):
		self.processSearchRequest(msg.searchterm, msg.user, msg.searchid, 0)
		
	def ToggleRespondDistributed(self, settings=False):
		"""
		Toggle responding to distributed search each (default: 60sec)
		interval
		"""
		if self.respondDistributedTimer is not None:
			self.respondDistributedTimer.cancel()
		if self.config.sections["searches"]["distrib_timer"]:
			if not settings:
				# Don't toggle when just changing the settings
				self.respondDistributed = not self.respondDistributed
			self.respondDistributedTimer = threading.Timer(self.config.sections["searches"]["distrib_ignore"], self.ToggleRespondDistributed)
			self.respondDistributedTimer.start()
		else:
			# Always respond
			self.respondDistributed = True
			
	def DistribSearch(self, msg):
		if self.respondDistributed: # set in ToggleRespondDistributed
			self.processSearchRequest(msg.searchterm, msg.user, msg.searchid, 0)
	
	def processSearchRequest(self, searchterm, user, searchid, direct = 0):
		if searchterm is None:
			return

		checkuser, reason = self.CheckUser(user, None)
		if not checkuser:
			return
		if reason == "geoip":
			geoip = 1
		else:
			geoip = 0
		maxresults = self.config.sections["searches"]["maxresults"]
		if checkuser == 2:
			wordindex = self.config.sections["transfers"]["bwordindex"]
			fileindex = self.config.sections["transfers"]["bfileindex"]
		else:
			wordindex = self.config.sections["transfers"]["wordindex"]
			fileindex = self.config.sections["transfers"]["fileindex"]
		fifoqueue = self.config.sections["transfers"]["fifoqueue"]
		if maxresults == 0:
			return
		terms = searchterm.translate(self.translatepunctuation).lower().split()
		list = [wordindex[i][:] for i in terms if i in wordindex]
		if len(list) != len(terms) or len(list) == 0:
			#self.logMessage(_("User %(user)s is searching for %(query)s, returning no results") %{'user':user, 'query':self.decode(searchterm)}, 2)
			return
		min = list[0]
		for i in list[1:]:
			if len(i) < len(min):
				min = i
		list.remove(min)
		for i in min[:]:
			for j in list:
				if i not in j:
					min.remove(i)
					break
		results = min[:maxresults]
		if len(results) > 0 and self.transfers is not None:
			queuesizes = self.transfers.getUploadQueueSizes()
			slotsavail = int(not self.transfers.bandwidthLimitReached())
			if len(results) > 0:
				message = slskmessages.FileSearchResult(None, user, geoip, searchid, results, fileindex, slotsavail, self.speed, queuesizes, fifoqueue)
				self.ProcessRequestToPeer(user, message)
				if direct:
					self.logMessage(_("User %(user)s is directly searching for %(query)s, returning %(num)i results") %{'user':user, 'query':self.decode(searchterm), 'num':len(results)}, 1)
				else:
					self.logMessage(_("User %(user)s is searching for %(query)s, returning %(num)i results") %{'user':user, 'query':self.decode(searchterm), 'num':len(results)}, 1)
					
	def NetInfo(self, msg):
		#print msg.list
		self.distribcache.update(msg.list)
		if len(self.distribcache) > 0:
			self.queue.put(slskmessages.HaveNoParent(0))
			if not self.GetDistribConn():
				user = self.distribcache.keys()[0]
				addr = self.distribcache[user]
				#self.queue.put(slskmessages.SearchParent( addr[0]))
				self.ProcessRequestToPeer(user, slskmessages.DistribConn(), None, addr)
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)

	def DistribAlive(self, msg):
		self.logMessage("%s %s" %(msg.__class__, vars(msg)), 1)
	
	def GetDistribConn(self):
		for i in self.peerconns:
			if i.init.type == 'D':
				return i
		return None

	def DistribConnClosed(self, conn):
		del self.distribcache[conn.username]
		if len(self.distribcache) > 0:
			user = self.distribcache.keys()[0]
			addr = self.distribcache[user]
			#self.queue.put(slskmessages.SearchParent( addr[0]))
			#print user, addr
			self.ProcessRequestToPeer(user, slskmessages.DistribConn(), None, addr)
		else:
			self.queue.put(slskmessages.HaveNoParent(1))

	def GlobalRecommendations(self, msg):
		self.frame.GlobalRecommendations(msg)
	
	def Recommendations(self, msg):
		self.frame.Recommendations(msg)
	
	def ItemRecommendations(self, msg):
		self.frame.ItemRecommendations(msg)
	
	def SimilarUsers(self, msg):
		self.frame.SimilarUsers(msg)
	
	def ItemSimilarUsers(self, msg):
		self.frame.ItemSimilarUsers(msg)
	
	def RoomTickerState(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.TickerSet(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	def RoomTickerAdd(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.TickerAdd(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))
	
	def RoomTickerRemove(self, msg):
		if self.chatrooms is not None:
			self.chatrooms.roomsctrl.TickerRemove(msg)
		else:
			self.logMessage("%s %s" %(msg.__class__, vars(msg)))

	def logTransfer(self, message, toUI = 0):
		if self.config.sections["logging"]["transfers"]:
			fn = os.path.join(self.config.sections["logging"]["logsdir"], "transfers.log")
			try:
				f = open(fn, "a")
				f.write(time.strftime("%c"))
				f.write(" %s\n" % message)
				f.close()
			except IOError, error:
				self.logMessage(_("Couldn't write to transfer log: %s") % error)
		if toUI:
			self.logMessage(message)
        
class UserAddr:
	def __init__(self, addr = None, behindfw = None, status = None):
		self.addr = addr
		self.behindfw = behindfw
		self.status = status
