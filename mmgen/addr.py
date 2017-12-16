#!/usr/bin/env python
#
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C)2013-2017 Philemon <mmgen-py@yandex.com>
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

"""
addr.py:  Address generation/display routines for the MMGen suite
"""

from hashlib import sha256,sha512
from binascii import hexlify,unhexlify
from mmgen.common import *
from mmgen.obj import *

pnm = g.proj_name

def sc_dmsg(desc,data):
	if os.getenv('MMGEN_DEBUG_ADDRLIST'):
		Msg('sc_debug_{}: {}'.format(desc,data))

class AddrGenerator(MMGenObject):
	def __new__(cls,gen_method):
		d = {
			'p2pkh':  AddrGeneratorP2PKH,
			'segwit': AddrGeneratorSegwit,
			'ethereum': AddrGeneratorEthereum,
			'zcash_z': AddrGeneratorZcashZ
		}
		assert gen_method in d
		me = super(cls,cls).__new__(d[gen_method])
		me.desc = d
		return me

class AddrGeneratorP2PKH(AddrGenerator):
	def to_addr(self,pubhex):
		from mmgen.protocol import hash160
		assert type(pubhex) == PubKey
		return CoinAddr(g.proto.pubhash2addr(hash160(pubhex),p2sh=False))

	def to_segwit_redeem_script(self,pubhex):
		raise NotImplementedError

class AddrGeneratorSegwit(AddrGenerator):
	def to_addr(self,pubhex):
		assert pubhex.compressed
		return CoinAddr(g.proto.pubhex2segwitaddr(pubhex))

	def to_segwit_redeem_script(self,pubhex):
		assert pubhex.compressed
		return HexStr(g.proto.pubhex2redeem_script(pubhex))

class AddrGeneratorEthereum(AddrGenerator):
	def to_addr(self,pubhex):
		assert type(pubhex) == PubKey
		import sha3
		return CoinAddr(sha3.keccak_256(pubhex[2:].decode('hex')).digest()[12:].encode('hex'))

	def to_segwit_redeem_script(self,pubhex):
		raise NotImplementedError

class AddrGeneratorZcashZ(AddrGenerator):

	def zhash256(self,vhex,t):
		byte0  = '{:02x}'.format(int(vhex[:2],16) | 0xc0)
		byte32 = '{:02x}'.format(t)
		vhex_fix = byte0 + vhex[2:64] + byte32 + '00' * 31
		assert len(vhex_fix) == 128
		from mmgen.sha256 import Sha256
		return Sha256(unhexlify(vhex_fix),preprocess=False).hexdigest()

	def to_addr(self,pubhex): # pubhex is really privhex
		key = pubhex
		assert len(key) == 64,'{}: incorrect privkey length'.format(len(key))
		addr1 = self.zhash256(key,0)
		addr2 = self.zhash256(key,1)
		from nacl.bindings import crypto_scalarmult_base
		addr2 = hexlify(crypto_scalarmult_base(unhexlify(addr2)))

		from mmgen.protocol import _b58chk_encode
		ret = _b58chk_encode(g.proto.addr_ver_num['zcash_z'][0] + addr1 + addr2)
		assert len(ret) == g.proto.addr_width,'Invalid zaddr length'
		return CoinAddr(ret)

	def to_segwit_redeem_script(self,pubhex):
		raise NotImplementedError

class KeyGenerator(MMGenObject):

	def __new__(cls,pubkey_type,generator=None,silent=False):
		if pubkey_type == 'std':
			if cls.test_for_secp256k1(silent=silent) and generator != 1:
				if not opt.key_generator or opt.key_generator == 2 or generator == 2:
					return super(cls,cls).__new__(KeyGeneratorSecp256k1)
			else:
				msg('Using (slow) native Python ECDSA library for address generation')
				return super(cls,cls).__new__(KeyGeneratorPython)
		elif pubkey_type == 'zcash_z':
			g.proto.addr_width = 95
			me = super(cls,cls).__new__(KeyGeneratorDummy)
			me.desc = 'mmgen-'+pubkey_type
			return me
		else:
			raise ValueError,'{}: invalid pubkey_type argument'.format(pubkey_type)

	@classmethod
	def test_for_secp256k1(self,silent=False):
		try:
			from mmgen.secp256k1 import priv2pub
			assert priv2pub(os.urandom(32),1)
			return True
		except:
			return False

import ecdsa
class KeyGeneratorPython(KeyGenerator):
	desc = 'mmgen-python-ecdsa'
	# From electrum:
	# secp256k1, http://www.oid-info.com/get/1.3.132.0.10
	_p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2FL
	_r = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141L
	_b = 0x0000000000000000000000000000000000000000000000000000000000000007L
	_a = 0x0000000000000000000000000000000000000000000000000000000000000000L
	_Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798L
	_Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8L
	_curve_secp256k1 = ecdsa.ellipticcurve.CurveFp(_p,_a,_b)
	_generator_secp256k1 = ecdsa.ellipticcurve.Point(_curve_secp256k1,_Gx,_Gy,_r)
	_oid_secp256k1 = (1,3,132,0,10)
	_secp256k1 = ecdsa.curves.Curve('secp256k1',_curve_secp256k1,_generator_secp256k1,_oid_secp256k1)

	# devdoc/guide_wallets.md:
	# Uncompressed public keys start with 0x04; compressed public keys begin with
	# 0x03 or 0x02 depending on whether they're greater or less than the midpoint
	# of the curve.
	def privnum2pubhex(self,numpriv,compressed=False):
		pko = ecdsa.SigningKey.from_secret_exponent(numpriv,self._secp256k1)
		# pubkey = 32-byte X coord + 32-byte Y coord (unsigned big-endian)
		pubkey = hexlify(pko.get_verifying_key().to_string())
		if compressed: # discard Y coord, replace with appropriate version byte
			# even Y: <0, odd Y: >0 -- https://bitcointalk.org/index.php?topic=129652.0
			p = ('03','02')[pubkey[-1] in '02468ace']
			return p+pubkey[:64]
		else:
			return '04'+pubkey

	def to_pubhex(self,privhex):
		assert type(privhex) == PrivKey
		return PubKey(self.privnum2pubhex(
			int(privhex,16),compressed=privhex.compressed),compressed=privhex.compressed)

class KeyGeneratorSecp256k1(KeyGenerator):
	desc = 'mmgen-secp256k1'
	def to_pubhex(self,privhex):
		assert type(privhex) == PrivKey
		from mmgen.secp256k1 import priv2pub
		return PubKey(hexlify(priv2pub(unhexlify(privhex),int(privhex.compressed))),compressed=privhex.compressed)

class KeyGeneratorDummy(KeyGenerator):
	desc = 'mmgen-dummy'
	def to_pubhex(self,privhex):
		assert type(privhex) == PrivKey
		return PubKey(str(privhex),compressed=privhex.compressed)

class AddrListEntry(MMGenListItem):
	addr  = MMGenListItemAttr('addr','CoinAddr')
	idx   = MMGenListItemAttr('idx','AddrIdx') # not present in flat addrlists
	label = MMGenListItemAttr('label','TwComment',reassign_ok=True)
	sec   = MMGenListItemAttr('sec',PrivKey,typeconv=False)

class PasswordListEntry(MMGenListItem):
	passwd = MMGenImmutableAttr('passwd',unicode,typeconv=False) # TODO: create Password type
	idx    = MMGenImmutableAttr('idx','AddrIdx')
	label  = MMGenListItemAttr('label','TwComment',reassign_ok=True)
	sec    = MMGenListItemAttr('sec',PrivKey,typeconv=False)

class AddrListChksum(str,Hilite):
	color = 'pink'
	trunc_ok = False

	def __new__(cls,addrlist):
		lines = [' '.join(addrlist.chksum_rec_f(e)) for e in addrlist.data]
		return str.__new__(cls,make_chksum_N(' '.join(lines), nchars=16, sep=True))

class AddrListIDStr(unicode,Hilite):
	color = 'green'
	trunc_ok = False
	def __new__(cls,addrlist,fmt_str=None):
		try: int(addrlist.data[0].idx)
		except:
			s = '(no idxs)'
		else:
			idxs = [e.idx for e in addrlist.data]
			prev = idxs[0]
			ret = prev,
			for i in idxs[1:]:
				if i == prev + 1:
					if i == idxs[-1]: ret += '-', i
				else:
					if prev != ret[-1]: ret += '-', prev
					ret += ',', i
				prev = i
			s = ''.join([unicode(i) for i in ret])

		if fmt_str:
			ret = fmt_str.format(s)
		else:
			bc = (g.proto.base_coin,g.coin)[g.proto.base_coin=='ETH']
			mt = addrlist.al_id.mmtype
			ret = '{}{}{}[{}]'.format(addrlist.al_id.sid,('-'+bc,'')[bc=='BTC'],('-'+mt,'')[mt in ('L','E')],s)
			sc_dmsg('id_str',ret[8:].split('[')[0])

		return unicode.__new__(cls,ret)

class AddrList(MMGenObject): # Address info for a single seed ID
	msgs = {
	'file_header': """
# {pnm} address file
#
# This file is editable.
# Everything following a hash symbol '#' is a comment and ignored by {pnm}.
# A text label of {n} characters or less may be added to the right of each
# address, and it will be appended to the tracking wallet label upon import.
# The label may contain any printable ASCII symbol.
""".strip().format(n=TwComment.max_len,pnm=pnm),
	'record_chksum': """
Record this checksum: it will be used to verify the address file in the future
""".strip(),
	'check_chksum': 'Check this value against your records',
	'removed_dup_keys': """
Removed %s duplicate WIF key%s from keylist (also in {pnm} key-address file
""".strip().format(pnm=pnm)
	}
	entry_type = AddrListEntry
	main_attr = 'addr'
	data_desc = 'address'
	file_desc = 'addresses'
	gen_desc  = 'address'
	gen_desc_pl = 'es'
	gen_addrs = True
	gen_passwds = False
	gen_keys = False
	has_keys = False
	ext      = 'addrs'
	scramble_hash_rounds = 10  # not too many rounds, so hand decoding can still be feasible
	chksum_rec_f = lambda foo,e: (str(e.idx), e.addr)

	def __init__(self,addrfile='',al_id='',adata=[],seed='',addr_idxs='',src='',
					addrlist='',keylist='',mmtype=None,do_chksum=True,chksum_only=False):

		self.update_msgs()
		mmtype = mmtype or g.proto.dfl_mmtype
		assert mmtype in MMGenAddrType.mmtypes,'{}: mmtype not in {}'.format(mmtype,repr(MMGenAddrType.mmtypes))

		if seed and addr_idxs:   # data from seed + idxs
			self.al_id,src = AddrListID(seed.sid,mmtype),'gen'
			adata = self.generate(seed,addr_idxs)
		elif addrfile:           # data from MMGen address file
			adata = self.parse_file(addrfile) # sets self.al_id
		elif al_id and adata:    # data from tracking wallet
			self.al_id = al_id
			do_chksum = False
		elif addrlist:           # data from flat address list
			self.al_id = None
			adata = AddrListList([AddrListEntry(addr=a) for a in set(addrlist)])
		elif keylist:            # data from flat key list
			self.al_id = None
			adata = AddrListList([AddrListEntry(sec=PrivKey(wif=k)) for k in set(keylist)])
		elif seed or addr_idxs:
			die(3,'Must specify both seed and addr indexes')
		elif al_id or adata:
			die(3,'Must specify both al_id and adata')
		else:
			die(3,'Incorrect arguments for %s' % type(self).__name__)

		# al_id,adata now set
		self.data = adata
		self.num_addrs = len(adata)
		self.fmt_data = ''
		self.chksum = None

		if self.al_id == None: return

		self.id_str = AddrListIDStr(self)
		if type(self) == KeyList: return

		if do_chksum:
			self.chksum = AddrListChksum(self)
			if chksum_only:
				Msg(self.chksum)
			else:
				qmsg('Checksum for %s data %s: %s' %
						(self.data_desc,self.id_str.hl(),self.chksum.hl()))
				qmsg(self.msgs[('check_chksum','record_chksum')[src=='gen']])

	def update_msgs(self):
		self.msgs = AddrList.msgs
		self.msgs.update(type(self).msgs)

	def generate(self,seed,addrnums):
		assert type(addrnums) is AddrIdxList

		seed = seed.get_data()
		seed = self.scramble_seed(seed)
		sc_dmsg('seed',seed[:8].encode('hex'))

		compressed = self.al_id.mmtype.compressed
		pubkey_type = self.al_id.mmtype.pubkey_type

		if self.gen_addrs:
			kg = KeyGenerator(pubkey_type)
			ag = AddrGenerator(self.al_id.mmtype.gen_method)

		t_addrs,num,pos,out = len(addrnums),0,0,AddrListList()
		le = self.entry_type

		while pos != t_addrs:
			seed = sha512(seed).digest()
			num += 1 # round

			if num != addrnums[pos]: continue

			pos += 1

			if not g.debug:
				qmsg_r('\rGenerating %s #%s (%s of %s)' % (self.gen_desc,num,pos,t_addrs))

			e = le(idx=num)

			# Secret key is double sha256 of seed hash round /num/
			e.sec = PrivKey(sha256(sha256(seed).digest()).digest(),compressed=compressed,pubkey_type=pubkey_type)

			if self.gen_addrs:
				e.addr = ag.to_addr(kg.to_pubhex(e.sec))

			if type(self) == PasswordList:
				e.passwd = unicode(self.make_passwd(e.sec)) # TODO - own type
				dmsg('Key {:>03}: {}'.format(pos,e.passwd))

			out.append(e)
			if g.debug: Msg('generate():\n', e.pformat())

		qmsg('\r%s: %s %s%s generated%s' % (
				self.al_id.hl(),t_addrs,self.gen_desc,suf(t_addrs,self.gen_desc_pl),' '*15))
		return out

	def check_format(self,addr): return True # format is checked when added to list entry object

	def scramble_seed(self,seed):
		is_btcfork = g.proto.base_coin == 'BTC'
		if is_btcfork and self.al_id.mmtype == 'L':
			sc_dmsg('str','(none)')
			return seed
		if g.proto.base_coin == 'ETH':
			scramble_key = g.coin.lower()
		else:
			scramble_key = (g.coin.lower()+':','')[is_btcfork] + self.al_id.mmtype.name
		sc_dmsg('str',scramble_key)
		from mmgen.crypto import scramble_seed
		return scramble_seed(seed,scramble_key,self.scramble_hash_rounds)

	def encrypt(self,desc='new key list'):
		from mmgen.crypto import mmgen_encrypt
		self.fmt_data = mmgen_encrypt(self.fmt_data.encode('utf8'),desc,'')
		self.ext += '.'+g.mmenc_ext

	def write_to_file(self,ask_tty=True,ask_write_default_yes=False,binary=False,desc=None):
		fn = u'{}.{}'.format(self.id_str,self.ext)
		ask_tty = self.has_keys and not opt.quiet
		write_data_to_file(fn,self.fmt_data,desc or self.file_desc,ask_tty=ask_tty,binary=binary)

	def idxs(self):
		return [e.idx for e in self.data]

	def addrs(self):
		return ['%s:%s'%(self.al_id.sid,e.idx) for e in self.data]

	def addrpairs(self):
		return [(e.idx,e.addr) for e in self.data]

	def coinaddrs(self):
		return [e.addr for e in self.data]

	def comments(self):
		return [e.label for e in self.data]

	def entry(self,idx):
		for e in self.data:
			if idx == e.idx: return e

	def coinaddr(self,idx):
		for e in self.data:
			if idx == e.idx: return e.addr

	def comment(self,idx):
		for e in self.data:
			if idx == e.idx: return e.label

	def set_comment(self,idx,comment):
		for e in self.data:
			if idx == e.idx:
				e.label = comment

	def make_reverse_dict(self,coinaddrs):
		d,b = MMGenDict(),coinaddrs
		for e in self.data:
			try:
				d[b[b.index(e.addr)]] = MMGenID('{}:{}'.format(self.al_id,e.idx)),e.label
			except: pass
		return d

	def remove_dup_keys(self,cmplist):
		assert self.has_keys
		pop_list = []
		for n,d in enumerate(self.data):
			for e in cmplist.data:
				if e.sec.wif == d.sec.wif:
					pop_list.append(n)
		for n in reversed(pop_list): self.data.pop(n)
		if pop_list:
			vmsg(self.msgs['removed_dup_keys'] % (len(pop_list),suf(removed,'s')))

	def add_wifs(self,key_list):
		if not key_list: return
		for d in self.data:
			for e in key_list.data:
				if e.addr and e.sec and e.addr == d.addr:
					d.sec = e.sec

	def list_missing(self,key):
		return [d.addr for d in self.data if not getattr(d,key)]

	def generate_addrs_from_keys(self):
		kg = KeyGenerator('std')
		ag = AddrGenerator('p2pkh')
		d = self.data
		for n,e in enumerate(d,1):
			qmsg_r('\rGenerating addresses from keylist: %s/%s' % (n,len(d)))
			e.addr = ag.to_addr(kg.to_pubhex(e.sec))
		qmsg('\rGenerated addresses from keylist: %s/%s ' % (n,len(d)))

	def format(self,enable_comments=False):

		out = [self.msgs['file_header']+'\n']
		if self.chksum:
			out.append(u'# {} data checksum for {}: {}'.format(
						capfirst(self.data_desc),self.id_str,self.chksum))
			out.append('# Record this value to a secure location.\n')

		if type(self) == PasswordList:
			lbl = u'{} {} {}:{}'.format(self.al_id.sid,self.pw_id_str,self.pw_fmt,self.pw_len)
		else:
			bc,mt = g.proto.base_coin,self.al_id.mmtype
			l_coin = [] if bc == 'BTC' else [g.coin] if bc == 'ETH' else [bc]
			l_type = [] if mt in ('L','E') else [mt.name.upper()]
			lbl_p2 = ':'.join(l_coin+l_type)
			lbl = self.al_id.sid + ('',' ')[bool(lbl_p2)] + lbl_p2

		sc_dmsg('lbl',lbl[9:])
		out.append(u'{} {{'.format(lbl))

		fs = '  {:<%s}  {:<34}{}' % len(str(self.data[-1].idx))
		for e in self.data:
			c = ' '+e.label if enable_comments and e.label else ''
			if type(self) == KeyList:
				out.append(fs.format(e.idx,'wif: {}'.format(e.sec.wif),c))
			elif type(self) == PasswordList:
				out.append(fs.format(e.idx,e.passwd,c))
			else: # First line with idx
				out.append(fs.format(e.idx,e.addr,c))
				if self.has_keys:
					if opt.b16: out.append(fs.format('', 'hex: '+e.sec,c))
					out.append(fs.format('', 'wif: '+e.sec.wif,c))

		out.append('}')
		self.fmt_data = '\n'.join([l.rstrip() for l in out]) + '\n'

	def parse_file_body(self,lines):

		if self.has_keys and len(lines) % 2:
			return 'Key-address file has odd number of lines'

		ret = AddrListList()
		le = self.entry_type

		while lines:
			l = lines.pop(0)
			d = l.split(None,2)

			if not is_mmgen_idx(d[0]):
				return "'%s': invalid address num. in line: '%s'" % (d[0],l)

			if not self.check_format(d[1]):
				return "'{}': invalid {}".format(d[1],self.data_desc)

			if len(d) != 3: d.append('')

			a = le(**{'idx':int(d[0]),self.main_attr:d[1],'label':d[2]})

			if self.has_keys:
				l = lines.pop(0)
				d = l.split(None,2)

				if d[0] != 'wif:':
					return "Invalid key line in file: '{}'".format(l)
				if not is_wif(d[1]):
					return "'{}': invalid {} key".format(d[1],g.proto.name.capitalize())

				a.sec = PrivKey(wif=d[1])

			ret.append(a)

		if self.has_keys and keypress_confirm('Check key-to-address validity?'):
			kg = KeyGenerator(self.al_id.mmtype.pubkey_type)
			ag = AddrGenerator(self.al_id.mmtype.gen_method)
			llen = len(ret)
			for n,e in enumerate(ret):
				msg_r('\rVerifying keys %s/%s' % (n+1,llen))
				if e.addr != ag.to_addr(kg.to_pubhex(e.sec)):
					return "Key doesn't match address!\n  %s\n  %s" % (e.sec.wif,e.addr)
			msg(' - done')

		return ret

	def parse_file(self,fn,buf=[],exit_on_error=True):

		def do_error(msg):
			if exit_on_error: die(3,msg)
			msg(msg)
			return False

		lines = get_lines_from_file(fn,self.data_desc+' data',trim_comments=True)

		if len(lines) < 3:
			return do_error("Too few lines in address file (%s)" % len(lines))

		ls = lines[0].split()
		if not 1 < len(ls) < 5:
			return do_error("Invalid first line for {} file: '{}'".format(self.gen_desc,lines[0]))
		if ls.pop() != '{':
			return do_error("'%s': invalid first line" % ls)
		if lines[-1] != '}':
			return do_error("'%s': invalid last line" % lines[-1])

		sid = ls.pop(0)
		if not is_mmgen_seed_id(sid):
			return do_error("'%s': invalid Seed ID" % ls[0])

		def parse_addrfile_label(lbl): # we must maintain backwards compat, so parse is tricky
			al_coin,al_mmtype = None,None
			lbl = lbl.split(':',1)
			if len(lbl) == 2:
				al_coin,al_mmtype = lbl[0],lbl[1].lower()
			else:
				if lbl[0].lower() in MMGenAddrType.get_names():
					al_mmtype = lbl[0].lower()
				else:
					al_coin = lbl[0]

			# this block fails if al_mmtype is invalid for g.coin
			if not al_mmtype:
				mmtype = MMGenAddrType('E' if al_coin in ('ETH','ETC') else 'L')
			else:
				try:
					mmtype = MMGenAddrType(al_mmtype)
				except:
					return do_error(u"'{}': invalid address type in address file. Must be one of: {}".format(
						mmtype.upper(),' '.join([i['name'].upper() for i in MMGenAddrType.mmtypes.values()])))

			from mmgen.protocol import CoinProtocol
			base_coin = CoinProtocol(al_coin or 'BTC',testnet=False).base_coin
			if not base_coin:
				die(2,"'{}': unknown base coin in address file label!".format(al_coin))
			return base_coin,mmtype

		def check_coin_mismatch(base_coin): # die if addrfile coin doesn't match g.coin
			if not base_coin == g.proto.base_coin:
				die(2,'{} address file format, but base coin is {}!'.format(base_coin,g.proto.base_coin))

		if type(self) == PasswordList and len(ls) == 2:
			ss = ls.pop().split(':')
			if len(ss) != 2:
				return do_error("'%s': invalid password length specifier (must contain colon)" % ls[2])
			self.set_pw_fmt(ss[0])
			self.set_pw_len(ss[1])
			self.pw_id_str = MMGenPWIDString(ls.pop())
			mmtype = MMGenPasswordType('P')
		elif len(ls) == 1:
			base_coin,mmtype = parse_addrfile_label(ls[0])
			check_coin_mismatch(base_coin)
		elif len(ls) == 0:
			base_coin,mmtype = 'BTC',MMGenAddrType('L')
			check_coin_mismatch(base_coin)
		else:
			return do_error(u"Invalid first line for {} file: '{}'".format(self.gen_desc,lines[0]))

		self.al_id = AddrListID(SeedID(sid=sid),mmtype)

		data = self.parse_file_body(lines[1:-1])
		if not issubclass(type(data),list):
			return do_error(data)

		return data

class KeyAddrList(AddrList):
	data_desc = 'key-address'
	file_desc = 'secret keys'
	gen_desc = 'key/address pair'
	gen_desc_pl = 's'
	gen_addrs = True
	gen_keys = True
	has_keys = True
	ext      = 'akeys'
	chksum_rec_f = lambda foo,e: (str(e.idx), e.addr, e.sec.wif)

class KeyList(AddrList):
	msgs = {
	'file_header': """
# {pnm} key file
#
# This file is editable.
# Everything following a hash symbol '#' is a comment and ignored by {pnm}.
""".strip().format(pnm=pnm)
	}
	data_desc = 'key'
	file_desc = 'secret keys'
	gen_desc = 'key'
	gen_desc_pl = 's'
	gen_addrs = False
	gen_keys = True
	has_keys = True
	ext      = 'keys'
	chksum_rec_f = lambda foo,e: (str(e.idx), e.addr, e.sec.wif)

class PasswordList(AddrList):
	msgs = {
	'file_header': """
# {pnm} password file
#
# This file is editable.
# Everything following a hash symbol '#' is a comment and ignored by {pnm}.
# A text label of {n} characters or less may be added to the right of each
# password.  The label may contain any printable ASCII symbol.
#
""".strip().format(n=TwComment.max_len,pnm=pnm),
	'record_chksum': """
Record this checksum: it will be used to verify the password file in the future
""".strip()
	}
	entry_type  = PasswordListEntry
	main_attr   = 'passwd'
	data_desc   = 'password'
	file_desc   = 'passwords'
	gen_desc    = 'password'
	gen_desc_pl = 's'
	gen_addrs   = False
	gen_keys    = False
	gen_passwds = True
	has_keys    = False
	ext         = 'pws'
	pw_len      = None
	pw_fmt      = None
	pw_info     = {
		'b58': { 'min_len': 8 , 'max_len': 36 ,'dfl_len': 20, 'desc': 'base-58 password' },
		'b32': { 'min_len': 10 ,'max_len': 42 ,'dfl_len': 24, 'desc': 'base-32 password' }
		}
	chksum_rec_f = lambda foo,e: (str(e.idx), e.passwd)

	def __init__(self,infile=None,seed=None,pw_idxs=None,pw_id_str=None,pw_len=None,pw_fmt=None,
				chksum_only=False,chk_params_only=False):

		self.update_msgs()

		if infile:
			self.data = self.parse_file(infile) # sets self.pw_id_str,self.pw_fmt,self.pw_len
		else:
			for k in seed,pw_idxs: assert chk_params_only or k
			for k in (pw_id_str,pw_fmt): assert k
			self.pw_id_str = MMGenPWIDString(pw_id_str)
			self.set_pw_fmt(pw_fmt)
			self.set_pw_len(pw_len)
			if chk_params_only: return
			self.al_id = AddrListID(seed.sid,MMGenPasswordType('P'))
			self.data = self.generate(seed,pw_idxs)

		self.num_addrs = len(self.data)
		self.fmt_data = ''
		self.chksum = AddrListChksum(self)

		if chksum_only:
			Msg(self.chksum)
		else:
			fs = u'{}-{}-{}-{}[{{}}]'.format(self.al_id.sid,self.pw_id_str,self.pw_fmt,self.pw_len)
			self.id_str = AddrListIDStr(self,fs)
			qmsg(u'Checksum for {} data {}: {}'.format(self.data_desc,self.id_str.hl(),self.chksum.hl()))
			qmsg(self.msgs[('record_chksum','check_chksum')[bool(infile)]])

	def set_pw_fmt(self,pw_fmt):
		assert pw_fmt in self.pw_info
		self.pw_fmt = pw_fmt

	def chk_pw_len(self,passwd=None):
		if passwd is None:
			assert self.pw_len
			pw_len = self.pw_len
			fs = '{l}: invalid user-requested length for {b} ({c}{m})'
		else:
			pw_len = len(passwd)
			fs = '{pw}: {b} has invalid length {l} ({c}{m} characters)'
		d = self.pw_info[self.pw_fmt]
		if pw_len > d['max_len']:
			die(2,fs.format(l=pw_len,b=d['desc'],c='>',m=d['max_len'],pw=passwd))
		elif pw_len < d['min_len']:
			die(2,fs.format(l=pw_len,b=d['desc'],c='<',m=d['min_len'],pw=passwd))

	def set_pw_len(self,pw_len):
		assert self.pw_fmt in self.pw_info
		d = self.pw_info[self.pw_fmt]

		if pw_len is None:
			self.pw_len = d['dfl_len']
			return

		if not is_int(pw_len):
			die(2,"'{}': invalid user-requested password length (not an integer)".format(pw_len,d['desc']))
		self.pw_len = int(pw_len)
		self.chk_pw_len()

	def make_passwd(self,hex_sec):
		assert self.pw_fmt in self.pw_info
		# we take least significant part
		return ''.join(baseconv.fromhex(hex_sec,self.pw_fmt,pad=self.pw_len))[-self.pw_len:]

	def check_format(self,pw):
		if not (is_b58_str,is_b32_str)[self.pw_fmt=='b32'](pw):
			msg('Password is not a valid {} string'.format(self.pw_fmt))
			return False
		if len(pw) != self.pw_len:
			msg('Password has incorrect length ({} != {})'.format(len(pw),self.pw_len))
			return False
		return True

	def scramble_seed(self,seed):
		# Changing either pw_fmt, pw_len or scramble_key will cause a different,
		# unrelated set of passwords to be generated: this is what we want.
		# NB: In original implementation, pw_id_str was 'baseN', not 'bN'
		scramble_key = '{}:{}:{}'.format(self.pw_fmt,self.pw_len,self.pw_id_str.encode('utf8'))
		from mmgen.crypto import scramble_seed
		return scramble_seed(seed,scramble_key,self.scramble_hash_rounds)

class AddrData(MMGenObject):
	msgs = {
	'too_many_acct_addresses': """
ERROR: More than one address found for account: '%s'.
Your 'wallet.dat' file appears to have been altered by a non-{pnm} program.
Please restore your tracking wallet from a backup or create a new one and
re-import your addresses.
""".strip().format(pnm=pnm)
	}

	def __init__(self,source=None):
		self.al_ids = {}
		if source == 'tw': self.add_tw_data()

	def seed_ids(self):
		return self.al_ids.keys()

	def addrlist(self,al_id):
		# TODO: Validate al_id
		if al_id in self.al_ids:
			return self.al_ids[al_id]

	def mmaddr2coinaddr(self,mmaddr):
		al_id,idx = MMGenID(mmaddr).rsplit(':',1)
		coinaddr = ''
		if al_id in self.al_ids:
			coinaddr = self.addrlist(al_id).coinaddr(int(idx))
		return coinaddr or None

	def coinaddr2mmaddr(self,coinaddr):
		d = self.make_reverse_dict([coinaddr])
		return (d.values()[0][0]) if d else None

	def add_tw_data(self):
		vmsg('Getting address data from tracking wallet')
		accts = g.rpch.listaccounts(0,True)
		data,i = {},0
		alists = g.rpch.getaddressesbyaccount([[k] for k in accts],batch=True)
		for acct,addrlist in zip(accts,alists):
			l = TwLabel(acct,on_fail='silent')
			if l and l.mmid.type == 'mmgen':
				obj = l.mmid.obj
				i += 1
				if len(addrlist) != 1:
					die(2,self.msgs['too_many_acct_addresses'] % acct)
				al_id = AddrListID(SeedID(sid=obj.sid),MMGenAddrType(obj.mmtype))
				if al_id not in data:
					data[al_id] = []
				data[al_id].append(AddrListEntry(idx=obj.idx,addr=addrlist[0],label=l.comment))
		vmsg('{n} {pnm} addresses found, {m} accounts total'.format(n=i,pnm=pnm,m=len(accts)))
		for al_id in data:
			self.add(AddrList(al_id=al_id,adata=AddrListList(sorted(data[al_id],key=lambda a: a.idx))))

	def add(self,addrlist):
		if type(addrlist) == AddrList:
			self.al_ids[addrlist.al_id] = addrlist
			return True
		else:
			raise TypeError, 'Error: object %s is not of type AddrList' % repr(addrlist)

	def make_reverse_dict(self,coinaddrs):
		d = MMGenDict()
		for al_id in self.al_ids:
			d.update(self.al_ids[al_id].make_reverse_dict(coinaddrs))
		return d
