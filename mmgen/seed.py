#!/usr/bin/env python3
#
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C)2013-2019 The MMGen Project <mmgen@tuta.io>
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
seed.py:  Seed-related classes and methods for the MMGen suite
"""

import os

from mmgen.common import *
from mmgen.obj import *
from mmgen.crypto import *

pnm = g.proj_name

def check_usr_seed_len(seed_len):
	if opt.seed_len != seed_len and 'seed_len' in opt.set_by_user:
		m = "ERROR: requested seed length ({}) doesn't match seed length of source ({})"
		die(1,m.format((opt.seed_len,seed_len)))

def _is_mnemonic(s,fmt):
	oq_save = opt.quiet
	opt.quiet = True
	try:
		SeedSource(in_data=s,in_fmt=fmt)
		ret = True
	except:
		ret = False
	finally:
		opt.quiet = oq_save
	return ret

def is_bip39_mnemonic(s): return _is_mnemonic(s,fmt='bip39')
def is_mmgen_mnemonic(s): return _is_mnemonic(s,fmt='words')

class SeedBase(MMGenObject):

	data    = MMGenImmutableAttr('data',bytes,typeconv=False)
	sid     = MMGenImmutableAttr('sid',SeedID,typeconv=False)

	def __init__(self,seed_bin=None):
		if not seed_bin:
			# Truncate random data for smaller seed lengths
			seed_bin = sha256(get_random(1033)).digest()[:opt.seed_len//8]
		elif len(seed_bin)*8 not in g.seed_lens:
			die(3,'{}: invalid seed length'.format(len(seed_bin)))

		self.data      = seed_bin
		self.sid       = SeedID(seed=self)

	@property
	def bitlen(self):
		return len(self.data) * 8

	@property
	def byte_len(self):
		return len(self.data)

	@property
	def hexdata(self):
		return self.data.hex()

	@property
	def fn_stem(self):
		return self.sid

class SubSeedList(MMGenObject):
	have_short = True
	nonce_start = 0

	def __init__(self,parent_seed):
		self.member_type = SubSeed
		self.parent_seed = parent_seed
		self.data = { 'long': IndexedDict(), 'short': IndexedDict() }

	def __len__(self):
		return len(self.data['long'])

	def get_subseed_by_ss_idx(self,ss_idx_in,print_msg=False):
		ss_idx = SubSeedIdx(ss_idx_in)
		if print_msg:
			msg_r('{} {} of {}...'.format(
				green('Generating subseed'),
				ss_idx.hl(),
				self.parent_seed.sid.hl(),
			))

		if ss_idx.idx > len(self):
			self._generate(ss_idx.idx)

		sid = self.data[ss_idx.type].key(ss_idx.idx-1)
		idx,nonce = self.data[ss_idx.type][sid]
		if idx != ss_idx.idx:
			m = "{} != {}: self.data[{t!r}].key(i) does not match self.data[{t!r}][i]!"
			die(3,m.format(idx,ss_idx.idx,t=ss_idx.type))

		if print_msg:
			msg('\b\b\b => {}'.format(SeedID.hlc(sid)))

		seed = self.member_type(self,idx,nonce,length=ss_idx.type)
		assert seed.sid == sid,'{} != {}: Seed ID mismatch!'.format(seed.sid,sid)
		return seed

	def get_subseed_by_seed_id(self,sid,last_idx=None,print_msg=False):

		def get_existing_subseed_by_seed_id(sid):
			for k in ('long','short') if self.have_short else ('long',):
				if sid in self.data[k]:
					idx,nonce = self.data[k][sid]
					return self.member_type(self,idx,nonce,length=k)

		def do_msg(subseed):
			if print_msg:
				qmsg('{} {} ({}:{})'.format(
					green('Found subseed'),
					subseed.sid.hl(),
					self.parent_seed.sid.hl(),
					subseed.ss_idx.hl(),
				))

		if last_idx == None:
			last_idx = g.subseeds

		subseed = get_existing_subseed_by_seed_id(sid)
		if subseed:
			do_msg(subseed)
			return subseed

		if len(self) >= last_idx:
			return None

		self._generate(last_idx,last_sid=sid)

		subseed = get_existing_subseed_by_seed_id(sid)
		if subseed:
			do_msg(subseed)
			return subseed

	def _collision_debug_msg(self,sid,idx,nonce,nonce_desc='nonce'):
		slen = 'short' if sid in self.data['short'] else 'long'
		m1 = 'add_subseed(idx={},{}):'.format(idx,slen)
		if sid == self.parent_seed.sid:
			m2 = 'collision with parent Seed ID {},'.format(sid)
		else:
			m2 = 'collision with ID {} (idx={},{}),'.format(sid,self.data[slen][sid][0],slen)
		msg('{:30} {:46} incrementing {} to {}'.format(m1,m2,nonce_desc,nonce+1))

	def _generate(self,last_idx=None,last_sid=None):

		if last_idx == None:
			last_idx = g.subseeds

		first_idx = len(self) + 1

		if first_idx > last_idx:
			return None

		if last_sid != None:
			last_sid = SeedID(sid=last_sid)

		def add_subseed(idx,length):
			for nonce in range(self.nonce_start,self.member_type.max_nonce+1): # handle SeedID collisions
				sid = make_chksum_8(self.member_type.make_subseed_bin(self,idx,nonce,length))
				if not (sid in self.data['long'] or sid in self.data['short'] or sid == self.parent_seed.sid):
					self.data[length][sid] = (idx,nonce)
					return last_sid == sid
				elif g.debug_subseed: # should get ≈450 collisions for first 1,000,000 subseeds
					self._collision_debug_msg(sid,idx,nonce)
			else: # must exit here, as this could leave self.data in inconsistent state
				raise SubSeedNonceRangeExceeded('add_subseed(): nonce range exceeded')

		for idx in SubSeedIdxRange(first_idx,last_idx).iterate():
			match1 = add_subseed(idx,'long')
			match2 = add_subseed(idx,'short') if self.have_short else False
			if match1 or match2: break

	def format(self,first_idx,last_idx):

		r = SubSeedIdxRange(first_idx,last_idx)

		if len(self) < last_idx:
			self._generate(last_idx)

		fs1 = '{:>18} {:>18}\n'
		fs2 = '{i:>7}L: {:8} {i:>7}S: {:8}\n'

		hdr = '{:>16} {} ({} bits)\n\n'.format('Parent Seed:',self.parent_seed.sid.hl(),self.parent_seed.bitlen)
		hdr += fs1.format('Long Subseeds','Short Subseeds')
		hdr += fs1.format('-------------','--------------')

		sl = self.data['long'].keys
		ss = self.data['short'].keys
		body = (fs2.format(sl[n-1],ss[n-1],i=n) for n in r.iterate())

		return hdr + ''.join(body)

class Seed(SeedBase):

	def __init__(self,seed_bin=None):
		self.subseeds = SubSeedList(self)
		SeedBase.__init__(self,seed_bin=seed_bin)

	def subseed(self,ss_idx_in,print_msg=False):
		return self.subseeds.get_subseed_by_ss_idx(ss_idx_in,print_msg=print_msg)

	def subseed_by_seed_id(self,sid,last_idx=None,print_msg=False):
		return self.subseeds.get_subseed_by_seed_id(sid,last_idx=last_idx,print_msg=print_msg)

	def split(self,count,id_str=None,master_idx=None):
		return SeedShareList(self,count,id_str,master_idx)

	@staticmethod
	def join_shares(seed_list,master_idx=None,id_str=None):
		if not hasattr(seed_list,'__next__'): # seed_list can be iterator or iterable
			seed_list = iter(seed_list)

		class d(object):
			byte_len,ret,count = None,0,0

		def add_share(ss):
			if d.byte_len:
				assert ss.byte_len == d.byte_len,'Seed length mismatch! {} != {}'.format(ss.byte_len,d.byte_len)
			else:
				d.byte_len = ss.byte_len
			d.ret ^= int(ss.data.hex(),16)
			d.count += 1

		if master_idx:
			master_share = next(seed_list)

		for ss in seed_list:
			add_share(ss)

		if master_idx:
			add_share(SeedShareMasterJoining(master_idx,master_share,id_str,d.count+1).derived_seed)

		SeedShareCount(d.count)
		return Seed(seed_bin=d.ret.to_bytes(d.byte_len,'big'))

class SubSeed(SeedBase):

	idx    = MMGenImmutableAttr('idx',int,typeconv=False)
	nonce  = MMGenImmutableAttr('nonce',int,typeconv=False)
	ss_idx = MMGenImmutableAttr('ss_idx',SubSeedIdx)
	max_nonce = 1000

	def __init__(self,parent_list,idx,nonce,length):
		self.idx = idx
		self.nonce = nonce
		self.ss_idx = str(idx) + { 'long': 'L', 'short': 'S' }[length]
		self.parent_list = parent_list
		SeedBase.__init__(self,seed_bin=type(self).make_subseed_bin(parent_list,idx,nonce,length))

	@staticmethod
	def make_subseed_bin(parent_list,idx:int,nonce:int,length:str):
		seed = parent_list.parent_seed
		short = { 'short': True, 'long': False }[length]
		# field maximums: idx: 4294967295 (1000000), nonce: 65535 (1000), short: 255 (1)
		scramble_key  = idx.to_bytes(4,'big') + nonce.to_bytes(2,'big') + short.to_bytes(1,'big')
		return scramble_seed(seed.data,scramble_key)[:16 if short else seed.byte_len]

class SeedShareList(SubSeedList):
	have_short = False
	split_type = 'N-of-N'

	count = MMGenImmutableAttr('count',SeedShareCount)
	id_str = MMGenImmutableAttr('id_str',SeedShareIDString)

	def __init__(self,parent_seed,count,id_str=None,master_idx=None):
		self.member_type = SeedShare
		self.parent_seed = parent_seed
		self.id_str = id_str or 'default'
		self.count = count

		def make_master_share():
			for nonce in range(SeedShare.max_nonce+1):
				ms = SeedShareMaster(self,master_idx,nonce)
				if ms.sid == parent_seed.sid:
					if g.debug_subseed:
						m = 'master_share seed ID collision with parent seed, incrementing nonce to {}'
						msg(m.format(nonce+1))
				else:
					return ms
			raise SubSeedNonceRangeExceeded('nonce range exceeded')

		self.master_share = make_master_share() if master_idx else None

		for nonce in range(SeedShare.max_nonce+1):
			self.nonce_start = nonce
			self.data = { 'long': IndexedDict(), 'short': IndexedDict() } # 'short' is required as a placeholder
			if self.master_share:
				self.data['long'][self.master_share.sid] = (1,self.master_share.nonce)
			self._generate(count-1)
			self.last_share = ls = SeedShareLast(self)
			if ls.sid in self.data['long'].keys + [parent_seed.sid]:
				# collision: throw out entire split list and redo with new start nonce
				if g.debug_subseed:
					self._collision_debug_msg(ls.sid,count,nonce,nonce_desc='nonce_start')
			else:
				self.data['long'][ls.sid] = (self.count,nonce)
				break
		else:
			raise SubSeedNonceRangeExceeded('nonce range exceeded')

		if g.debug_subseed:
			A = parent_seed.data
			B = self.join().data
			assert A == B,'Data mismatch!\noriginal seed: {!r}\nrejoined seed: {!r}'.format(A,B)

	def get_share_by_idx(self,idx,base_seed=False):
		if idx == self.count:
			return self.last_share
		elif self.master_share and idx == 1:
			return self.master_share if base_seed else self.master_share.derived_seed
		else:
			ss_idx = SubSeedIdx(str(idx) + 'L')
			return self.get_subseed_by_ss_idx(ss_idx)

	def get_share_by_seed_id(self,sid,base_seed=False):
		if sid == self.data['long'].key(self.count-1):
			return self.last_share
		elif self.master_share and sid == self.data['long'].key(0):
			return self.master_share if base_seed else self.master_share.derived_seed
		else:
			return self.get_subseed_by_seed_id(sid)

	def join(self):
		return Seed.join_shares(self.get_share_by_idx(i+1) for i in range(len(self)))

	def format(self):
		assert self.split_type == 'N-of-N'
		fs1 = '    {}\n'
		fs2 = '{i:>5}: {}\n'
		mfs1,mfs2,midx,msid = ('','','','')
		if self.master_share:
			mfs1,mfs2 = (' with master share #{} ({})',' master share #{}')
			midx,msid = (self.master_share.idx,self.master_share.sid)

		hdr  = '    {} {} ({} bits)\n'.format('Seed:',self.parent_seed.sid.hl(),self.parent_seed.bitlen)
		hdr += '    {} {c}-of-{c} (XOR){m}\n'.format('Split Type:',c=self.count,m=mfs1.format(midx,msid))
		hdr += '    {} {}\n\n'.format('ID String:',self.id_str.hl())
		hdr += fs1.format('Shares')
		hdr += fs1.format('------')

		sl = self.data['long'].keys
		body1 = fs2.format(sl[0]+mfs2.format(midx),i=1)
		body = (fs2.format(sl[n],i=n+1) for n in range(1,len(self)))

		return hdr + body1 + ''.join(body)

class SeedShare(SubSeed):

	@staticmethod
	def make_subseed_bin(parent_list,idx:int,nonce:int,length:str):
		seed = parent_list.parent_seed
		assert parent_list.have_short == False
		assert length == 'long'
		# field maximums: id_str: none (256 chars), count: 65535 (1024), idx: 65535 (1024), nonce: 65535 (1000)
		scramble_key = '{}:{}:'.format(parent_list.split_type,parent_list.id_str).encode() + \
						parent_list.count.to_bytes(2,'big') + idx.to_bytes(2,'big') + nonce.to_bytes(2,'big')
		if parent_list.master_share:
			scramble_key += b':master:' + parent_list.master_share.idx.to_bytes(2,'big')
		return scramble_seed(seed.data,scramble_key)[:seed.byte_len]

class SeedShareLast(SeedBase):

	idx = MMGenImmutableAttr('idx',SeedShareIdx)
	nonce = 0

	def __init__(self,parent_list):
		self.idx = parent_list.count
		self.parent_list = parent_list
		SeedBase.__init__(self,seed_bin=self.make_subseed_bin(parent_list))

	@staticmethod
	def make_subseed_bin(parent_list):
		seed_list = (parent_list.get_share_by_idx(i+1) for i in range(len(parent_list)))
		seed = parent_list.parent_seed

		ret = int(seed.data.hex(),16)
		for ss in seed_list:
			ret ^= int(ss.data.hex(),16)

		return ret.to_bytes(seed.byte_len,'big')

class SeedShareMaster(SeedBase):

	idx = MMGenImmutableAttr('idx',MasterShareIdx)
	nonce = MMGenImmutableAttr('nonce',int,typeconv=False)

	def __init__(self,parent_list,idx,nonce):
		self.idx = idx
		self.nonce = nonce
		self.parent_list = parent_list
		SeedBase.__init__(self,self.make_base_seed_bin())

		self.derived_seed = SeedBase(self.make_derived_seed_bin(parent_list.id_str,parent_list.count))

	def make_base_seed_bin(self):
		seed = self.parent_list.parent_seed
		# field maximums: idx: 65535 (1024)
		scramble_key = b'master_share:' + self.idx.to_bytes(2,'big') + self.nonce.to_bytes(2,'big')
		return scramble_seed(seed.data,scramble_key)[:seed.byte_len]

	def make_derived_seed_bin(self,id_str,count):
		# field maximums: id_str: none (256 chars), count: 65535 (1024)
		scramble_key = id_str.encode() + b':' + count.to_bytes(2,'big')
		return scramble_seed(self.data,scramble_key)[:self.byte_len]

class SeedShareMasterJoining(SeedShareMaster):

	id_str = MMGenImmutableAttr('id_str',SeedShareIDString)
	count = MMGenImmutableAttr('count',SeedShareCount)

	def __init__(self,idx,base_seed,id_str,count):
		SeedBase.__init__(self,seed_bin=base_seed.data)

		self.id_str = id_str or 'default'
		self.count = count
		self.derived_seed = SeedBase(self.make_derived_seed_bin(self.id_str,self.count))

class SeedSource(MMGenObject):

	desc = g.proj_name + ' seed source'
	file_mode = 'text'
	stdin_ok = False
	ask_tty = True
	no_tty  = False
	op = None
	_msg = {}

	class SeedSourceData(MMGenObject): pass

	def __new__(cls,fn=None,ss=None,seed_bin=None,seed=None,
				passchg=False,in_data=None,ignore_in_fmt=False,in_fmt=None):

		in_fmt = in_fmt or opt.in_fmt

		def die_on_opt_mismatch(opt,sstype):
			opt_sstype = cls.fmt_code_to_type(opt)
			compare_or_die(
				opt_sstype.__name__, 'input format requested on command line',
				sstype.__name__,     'input file format'
			)

		if ss:
			sstype = ss.__class__ if passchg else cls.fmt_code_to_type(opt.out_fmt)
			me = super(cls,cls).__new__(sstype or Wallet) # default: Wallet
			me.seed = ss.seed
			me.ss_in = ss
			me.op = ('conv','pwchg_new')[bool(passchg)]
		elif fn or opt.hidden_incog_input_params:
			from mmgen.filename import Filename
			if fn:
				f = Filename(fn)
			else:
				# permit comma in filename
				fn = ','.join(opt.hidden_incog_input_params.split(',')[:-1])
				f = Filename(fn,ftype=IncogWalletHidden)
			if in_fmt and not ignore_in_fmt:
				die_on_opt_mismatch(in_fmt,f.ftype)
			me = super(cls,cls).__new__(f.ftype)
			me.infile = f
			me.op = ('old','pwchg_old')[bool(passchg)]
		elif in_fmt:  # Input format
			sstype = cls.fmt_code_to_type(in_fmt)
			me = super(cls,cls).__new__(sstype)
			me.op = ('old','pwchg_old')[bool(passchg)]
		else: # Called with no args, 'seed' or 'seed_bin' - initialize with random or supplied seed
			sstype = cls.fmt_code_to_type(opt.out_fmt)
			me = super(cls,cls).__new__(sstype or Wallet) # default: Wallet
			me.seed = seed or Seed(seed_bin=seed_bin or None)
			me.op = 'new'
#			die(1,me.seed.sid.hl()) # DEBUG

		return me

	def __init__(self,fn=None,ss=None,seed_bin=None,seed=None,
				passchg=False,in_data=None,ignore_in_fmt=False,in_fmt=None):

		self.ssdata = self.SeedSourceData()
		self.msg = {}
		self.in_data = in_data

		for c in reversed(self.__class__.__mro__):
			if hasattr(c,'_msg'):
				self.msg.update(c._msg)

		if hasattr(self,'seed'):
			self._encrypt()
			return
		elif hasattr(self,'infile') or self.in_data or not g.stdin_tty:
			self._deformat_once()
			self._decrypt_retry()
		else:
			if not self.stdin_ok:
				die(1,'Reading from standard input not supported for {} format'.format(self.desc))
			self._deformat_retry()
			self._decrypt_retry()

		m = ('',', seed length {}'.format(self.seed.bitlen))[self.seed.bitlen!=256]
		qmsg('Valid {} for Seed ID {}{}'.format(self.desc,self.seed.sid.hl(),m))

	def _get_data(self):
		if hasattr(self,'infile'):
			self.fmt_data = get_data_from_file(self.infile.name,self.desc,binary=self.file_mode=='binary')
		elif self.in_data:
			self.fmt_data = self.in_data
		else:
			self.fmt_data = self._get_data_from_user(self.desc)

	def _get_data_from_user(self,desc):
		return get_data_from_user(desc)

	def _deformat_once(self):
		self._get_data()
		if not self._deformat():
			die(2,'Invalid format for input data')

	def _deformat_retry(self):
		while True:
			self._get_data()
			if self._deformat(): break
			msg('Trying again...')

	def _decrypt_retry(self):
		while True:
			if self._decrypt(): break
			if opt.passwd_file:
				die(2,'Passphrase from password file, so exiting')
			msg('Trying again...')

	@classmethod
	def get_subclasses_str(cls): # returns name of calling class too
		return cls.__name__ + ' ' + ''.join([c.get_subclasses_str() for c in cls.__subclasses__()])

	@classmethod
	def get_subclasses_easy(cls,acc=[]):
		return [globals()[c] for c in cls.get_subclasses_str().split()]

	@classmethod
	def get_subclasses(cls): # returns calling class too
		def GetSubclassesTree(cls,acc):
			acc += [cls]
			for c in cls.__subclasses__(): GetSubclassesTree(c,acc)
		acc = []
		GetSubclassesTree(cls,acc)
		return acc

	@classmethod
	def get_extensions(cls):
		return [s.ext for s in cls.get_subclasses() if hasattr(s,'ext')]

	@classmethod
	def fmt_code_to_type(cls,fmt_code):
		if not fmt_code: return None
		for c in cls.get_subclasses():
			if hasattr(c,'fmt_codes') and fmt_code in c.fmt_codes:
				return c
		return None

	@classmethod
	def ext_to_type(cls,ext):
		if not ext: return None
		for c in cls.get_subclasses():
			if hasattr(c,'ext') and ext == c.ext:
				return c
		return None

	@classmethod
	def format_fmt_codes(cls):
		d = [(c.__name__,('.'+c.ext if c.ext else str(c.ext)),','.join(c.fmt_codes))
					for c in cls.get_subclasses()
				if hasattr(c,'fmt_codes')]
		w = max(len(i[0]) for i in d)
		ret = ['{:<{w}}  {:<9} {}'.format(a,b,c,w=w) for a,b,c in [
			('Format','FileExt','Valid codes'),
			('------','-------','-----------')
			] + sorted(d)]
		return '\n'.join(ret) + ('','-α')[g.debug_utf8] + '\n'

	def get_fmt_data(self):
		self._format()
		return self.fmt_data

	def write_to_file(self,outdir='',desc=''):
		self._format()
		kwargs = {
			'desc':     desc or self.desc,
			'ask_tty':  self.ask_tty,
			'no_tty':   self.no_tty,
			'binary':   self.file_mode == 'binary'
		}
		# write_data_to_file(): outfile with absolute path overrides opt.outdir
		if outdir:
			of = os.path.abspath(os.path.join(outdir,self._filename()))
		write_data_to_file(of if outdir else self._filename(),self.fmt_data,**kwargs)

class SeedSourceUnenc(SeedSource):

	def _decrypt_retry(self): pass
	def _encrypt(self): pass

	def _filename(self):
		s = self.seed
		return '{}[{}]{x}.{}'.format(
			s.fn_stem,
			s.bitlen,
			self.ext,
			x='-α' if g.debug_utf8 else '')

class SeedSourceEnc(SeedSource):

	_msg = {
		'choose_passphrase': """
You must choose a passphrase to encrypt your new {} with.
A key will be generated from your passphrase using a hash preset of '{}'.
Please note that no strength checking of passphrases is performed.  For
an empty passphrase, just hit ENTER twice.
	""".strip()
	}

	def _get_hash_preset_from_user(self,hp,desc_suf=''):
# 					hp=a,
		n = ('','old ')[self.op=='pwchg_old']
		m,n = (('to accept the default',n),('to reuse the old','new '))[
						int(self.op=='pwchg_new')]
		fs = "Enter {}hash preset for {}{}{},\n or hit ENTER {} value ('{}'): "
		p = fs.format(
			n,
			('','new ')[self.op=='new'],
			self.desc,
			('',' '+desc_suf)[bool(desc_suf)],
			m,
			hp
		)
		while True:
			ret = my_raw_input(p)
			if ret:
				if ret in g.hash_presets:
					self.ssdata.hash_preset = ret
					return ret
				else:
					msg('Invalid input.  Valid choices are {}'.format(', '.join(g.hash_presets)))
			else:
				self.ssdata.hash_preset = hp
				return hp

	def _get_hash_preset(self,desc_suf=''):
		if hasattr(self,'ss_in') and hasattr(self.ss_in.ssdata,'hash_preset'):
			old_hp = self.ss_in.ssdata.hash_preset
			if opt.keep_hash_preset:
				qmsg("Reusing hash preset '{}' at user request".format(old_hp))
				self.ssdata.hash_preset = old_hp
			elif 'hash_preset' in opt.set_by_user:
				hp = self.ssdata.hash_preset = opt.hash_preset
				qmsg("Using hash preset '{}' requested on command line".format(opt.hash_preset))
			else: # Prompt, using old value as default
				hp = self._get_hash_preset_from_user(old_hp,desc_suf)

			if (not opt.keep_hash_preset) and self.op == 'pwchg_new':
				m = ("changed to '{}'".format(hp),'unchanged')[hp==old_hp]
				qmsg('Hash preset {}'.format(m))
		elif 'hash_preset' in opt.set_by_user:
			self.ssdata.hash_preset = opt.hash_preset
			qmsg("Using hash preset '{}' requested on command line".format(opt.hash_preset))
		else:
			self._get_hash_preset_from_user(opt.hash_preset,desc_suf)

	def _get_new_passphrase(self):
		desc = '{}passphrase for {}{}'.format(
				('','new ')[self.op=='pwchg_new'],
				('','new ')[self.op in ('new','conv')],
				self.desc
			)
		if opt.passwd_file:
			w = pwfile_reuse_warning()
			pw = ' '.join(get_words_from_file(opt.passwd_file,desc,quiet=w))
		elif opt.echo_passphrase:
			pw = ' '.join(get_words_from_user('Enter {}: '.format(desc)))
		else:
			mswin_pw_warning()
			for i in range(g.passwd_max_tries):
				pw = ' '.join(get_words_from_user('Enter {}: '.format(desc)))
				pw2 = ' '.join(get_words_from_user('Repeat passphrase: '))
				dmsg('Passphrases: [{}] [{}]'.format(pw,pw2))
				if pw == pw2:
					vmsg('Passphrases match'); break
				else: msg('Passphrases do not match.  Try again.')
			else:
				die(2,'User failed to duplicate passphrase in {} attempts'.format(g.passwd_max_tries))

		if pw == '': qmsg('WARNING: Empty passphrase')
		self.ssdata.passwd = pw
		return pw

	def _get_passphrase(self,desc_suf=''):
		desc = '{}passphrase for {}{}'.format(
			('','old ')[self.op=='pwchg_old'],
			self.desc,
			('',' '+desc_suf)[bool(desc_suf)]
		)
		if opt.passwd_file:
			w = pwfile_reuse_warning()
			ret = ' '.join(get_words_from_file(opt.passwd_file,desc,quiet=w))
		else:
			mswin_pw_warning()
			ret = ' '.join(get_words_from_user('Enter {}: '.format(desc)))
		self.ssdata.passwd = ret

	def _get_first_pw_and_hp_and_encrypt_seed(self):
		d = self.ssdata
		self._get_hash_preset()

		if hasattr(self,'ss_in') and hasattr(self.ss_in.ssdata,'passwd'):
			old_pw = self.ss_in.ssdata.passwd
			if opt.keep_passphrase:
				d.passwd = old_pw
				qmsg('Reusing passphrase at user request')
			else:
				pw = self._get_new_passphrase()
				if self.op == 'pwchg_new':
					m = ('changed','unchanged')[pw==old_pw]
					qmsg('Passphrase {}'.format(m))
		else:
			qmsg(self.msg['choose_passphrase'].format(self.desc,d.hash_preset))
			self._get_new_passphrase()

		d.salt     = sha256(get_random(128)).digest()[:g.salt_len]
		key        = make_key(d.passwd, d.salt, d.hash_preset)
		d.key_id   = make_chksum_8(key)
		d.enc_seed = encrypt_seed(self.seed.data,key)

class MMGenMnemonic(SeedSourceUnenc):

	stdin_ok = True
	fmt_codes = 'mmwords','words','mnemonic','mnem','mn','m'
	desc = 'MMGen native mnemonic data'
	mn_name = 'MMGen native'
	ext = 'mmwords'
	mn_lens = [i // 32 * 3 for i in g.seed_lens]
	wl_id = 'mmgen'
	conv_cls = baseconv

	def __init__(self,*args,**kwargs):
		self.conv_cls.init_mn(self.wl_id)
		super().__init__(*args,**kwargs)

	def _get_data_from_user(self,desc):

		if not g.stdin_tty:
			return get_data_from_user(desc)

		from mmgen.term import get_char_raw,get_char

		def choose_mn_len():
			prompt = 'Choose a mnemonic length: 1) 12 words, 2) 18 words, 3) 24 words: '
			urange = [str(i+1) for i in range(len(self.mn_lens))]
			while True:
				r = get_char('\r'+prompt).decode()
				if r in urange: break
			msg_r(('\r','\n')[g.test_suite] + ' '*len(prompt) + '\r')
			return self.mn_lens[int(r)-1]

		msg('{} {}'.format(blue('Mnemonic type:'),yellow(self.mn_name)))

		while True:
			mn_len = choose_mn_len()
			prompt = 'Mnemonic length of {} words chosen. OK?'.format(mn_len)
			if keypress_confirm(prompt,default_yes=True,no_nl=not g.test_suite):
				break

		wl = self.conv_cls.digits[self.wl_id]
		longest_word = max(len(w) for w in wl)
		from string import ascii_lowercase

		m  = 'Enter your {ml}-word seed phrase, hitting ENTER or SPACE after each word.\n'
		m += "Optionally, you may use pad characters.  Anything you type that's not a\n"
		m += 'lowercase letter will be treated as a {lq}pad character{rq}, i.e. it will simply\n'
		m += 'be discarded.  Pad characters may be typed before, after, or in the middle\n'
		m += "of words.  For each word, once you've typed {lw} characters total (including\n"
		m += 'pad characters) any pad character will enter the word.'

		# pexpect chokes on these utf8 chars under MSYS2
		lq,rq = (('“','”'),('"','"'))[g.test_suite and g.platform=='win']
		msg(m.format(ml=mn_len,lw=longest_word,lq=lq,rq=rq))

		def get_word():
			s,pad = '',0
			while True:
				ch = get_char_raw('',num_chars=1).decode()
				if ch in '\b\x7f':
					if s: s = s[:-1]
				elif ch in '\n\r ':
					if s: break
				elif ch not in ascii_lowercase:
					pad += 1
					if s and pad + len(s) > longest_word:
						break
				else:
					s += ch
			return s

		def in_list(w):
			from bisect import bisect_left
			idx = bisect_left(wl,w)
			return(True,False)[idx == len(wl) or w != wl[idx]]

		p = ('Enter word #{}: ','Incorrect entry. Repeat word #{}: ')
		words,err = [],0
		while len(words) < mn_len:
			msg_r('{r}{s}{r}'.format(r='\r',s=' '*40))
			if err == 1: time.sleep(0.1)
			msg_r(p[err].format(len(words)+1))
			s = get_word()
			if in_list(s): words.append(s)
			err = (1,0)[in_list(s)]
		msg('')
		qmsg('Mnemonic successfully entered')
		return ' '.join(words)

	@staticmethod
	def _mn2hex_pad(mn): return len(mn) * 8 // 3

	@staticmethod
	def _hex2mn_pad(hexnum): return len(hexnum) * 3 // 8

	def _format(self):

		hexseed = self.seed.hexdata

		mn  = self.conv_cls.fromhex(hexseed,self.wl_id,self._hex2mn_pad(hexseed))
		ret = self.conv_cls.tohex(mn,self.wl_id,self._mn2hex_pad(mn))

		# Internal error, so just die on fail
		compare_or_die(ret,'recomputed seed',hexseed,'original',e='Internal error')

		self.ssdata.mnemonic = mn
		self.fmt_data = ' '.join(mn) + '\n'

	def _deformat(self):

		mn = self.fmt_data.split()

		if len(mn) not in self.mn_lens:
			m = 'Invalid mnemonic ({} words).  Valid numbers of words: {}'
			msg(m.format(len(mn),', '.join(map(str,self.mn_lens))))
			return False

		for n,w in enumerate(mn,1):
			if w not in self.conv_cls.digits[self.wl_id]:
				msg('Invalid mnemonic: word #{} is not in the {} wordlist'.format(n,self.wl_id.upper()))
				return False

		hexseed = self.conv_cls.tohex(mn,self.wl_id,self._mn2hex_pad(mn))
		ret     = self.conv_cls.fromhex(hexseed,self.wl_id,self._hex2mn_pad(hexseed))

		if len(hexseed) * 4 not in g.seed_lens:
			msg('Invalid mnemonic (produces too large a number)')
			return False

		# Internal error, so just die
		compare_or_die(' '.join(ret),'recomputed mnemonic',' '.join(mn),'original',e='Internal error')

		self.seed = Seed(bytes.fromhex(hexseed))
		self.ssdata.mnemonic = mn

		check_usr_seed_len(self.seed.bitlen)

		return True

class BIP39Mnemonic(MMGenMnemonic):

	fmt_codes = ('bip39',)
	desc = 'BIP39 mnemonic data'
	mn_name = 'BIP39'
	ext = 'bip39'
	wl_id = 'bip39'

	def __init__(self,*args,**kwargs):
		from mmgen.bip39 import bip39
		self.conv_cls = bip39
		super().__init__(*args,**kwargs)

class SeedFile (SeedSourceUnenc):

	stdin_ok = True
	fmt_codes = 'mmseed','seed','s'
	desc = 'seed data'
	ext = 'mmseed'

	def _format(self):
		b58seed = baseconv.b58encode(self.seed.data,pad=True)
		self.ssdata.chksum = make_chksum_6(b58seed)
		self.ssdata.b58seed = b58seed
		self.fmt_data = '{} {}\n'.format(self.ssdata.chksum,split_into_cols(4,b58seed))

	def _deformat(self):
		desc = self.desc
		ld = self.fmt_data.split()

		if not (7 <= len(ld) <= 12): # 6 <= padded b58 data (ld[1:]) <= 11
			msg('Invalid data length ({}) in {}'.format(len(ld),desc))
			return False

		a,b = ld[0],''.join(ld[1:])

		if not is_chksum_6(a):
			msg("'{}': invalid checksum format in {}".format(a, desc))
			return False

		if not is_b58_str(b):
			msg("'{}': not a base 58 string, in {}".format(b, desc))
			return False

		vmsg_r('Validating {} checksum...'.format(desc))

		if not compare_chksums(a,'file',make_chksum_6(b),'computed',verbose=True):
			return False

		ret = baseconv.b58decode(b,pad=True)

		if ret == False:
			msg('Invalid base-58 encoded seed: {}'.format(val))
			return False

		self.seed = Seed(ret)
		self.ssdata.chksum = a
		self.ssdata.b58seed = b

		check_usr_seed_len(self.seed.bitlen)

		return True

class HexSeedFile(SeedSourceUnenc):

	stdin_ok = True
	fmt_codes = 'seedhex','hexseed','hex','mmhex'
	desc = 'hexadecimal seed data'
	ext = 'mmhex'

	def _format(self):
		h = self.seed.hexdata
		self.ssdata.chksum = make_chksum_6(h)
		self.ssdata.hexseed = h
		self.fmt_data = '{} {}\n'.format(self.ssdata.chksum, split_into_cols(4,h))

	def _deformat(self):
		desc = self.desc
		d = self.fmt_data.split()
		try:
			d[1]
			chk,hstr = d[0],''.join(d[1:])
		except:
			msg("'{}': invalid {}".format(self.fmt_data.strip(),desc))
			return False

		if not len(hstr)*4 in g.seed_lens:
			msg('Invalid data length ({}) in {}'.format(len(hstr),desc))
			return False

		if not is_chksum_6(chk):
			msg("'{}': invalid checksum format in {}".format(chk, desc))
			return False

		if not is_hex_str(hstr):
			msg("'{}': not a hexadecimal string, in {}".format(hstr, desc))
			return False

		vmsg_r('Validating {} checksum...'.format(desc))

		if not compare_chksums(chk,'file',make_chksum_6(hstr),'computed',verbose=True):
			return False

		self.seed = Seed(bytes.fromhex(hstr))
		self.ssdata.chksum = chk
		self.ssdata.hexseed = hstr

		check_usr_seed_len(self.seed.bitlen)

		return True

class Wallet (SeedSourceEnc):

	fmt_codes = 'wallet','w'
	desc = g.proj_name + ' wallet'
	ext = 'mmdat'

	def _get_label_from_user(self,old_lbl=''):
		d = "to reuse the label '{}'".format(old_lbl.hl()) if old_lbl else 'for no label'
		p = 'Enter a wallet label, or hit ENTER {}: '.format(d)
		while True:
			msg_r(p)
			ret = my_raw_input('')
			if ret:
				self.ssdata.label = MMGenWalletLabel(ret,on_fail='return')
				if self.ssdata.label:
					break
				else:
					msg('Invalid label.  Trying again...')
			else:
				self.ssdata.label = old_lbl or MMGenWalletLabel('No Label')
				break
		return self.ssdata.label

	# nearly identical to _get_hash_preset() - factor?
	def _get_label(self):
		if hasattr(self,'ss_in') and hasattr(self.ss_in.ssdata,'label'):
			old_lbl = self.ss_in.ssdata.label
			if opt.keep_label:
				qmsg("Reusing label '{}' at user request".format(old_lbl.hl()))
				self.ssdata.label = old_lbl
			elif opt.label:
				qmsg("Using label '{}' requested on command line".format(opt.label.hl()))
				lbl = self.ssdata.label = opt.label
			else: # Prompt, using old value as default
				lbl = self._get_label_from_user(old_lbl)

			if (not opt.keep_label) and self.op == 'pwchg_new':
				m = ("changed to '{}'".format(lbl),'unchanged')[lbl==old_lbl]
				qmsg('Label {}'.format(m))
		elif opt.label:
			qmsg("Using label '{}' requested on command line".format(opt.label.hl()))
			self.ssdata.label = opt.label
		else:
			self._get_label_from_user()

	def _encrypt(self):
		self._get_first_pw_and_hp_and_encrypt_seed()
		self._get_label()
		d = self.ssdata
		d.pw_status = ('NE','E')[len(d.passwd)==0]
		d.timestamp = make_timestamp()

	def _format(self):
		d = self.ssdata
		s = self.seed
		slt_fmt  = baseconv.b58encode(d.salt,pad=True)
		es_fmt = baseconv.b58encode(d.enc_seed,pad=True)
		lines = (
			d.label,
			'{} {} {} {} {}'.format(s.sid.lower(), d.key_id.lower(),
										s.bitlen, d.pw_status, d.timestamp),
			'{}: {} {} {}'.format(d.hash_preset,*get_hash_params(d.hash_preset)),
			'{} {}'.format(make_chksum_6(slt_fmt),split_into_cols(4,slt_fmt)),
			'{} {}'.format(make_chksum_6(es_fmt), split_into_cols(4,es_fmt))
		)
		chksum = make_chksum_6(' '.join(lines).encode())
		self.fmt_data = '\n'.join((chksum,)+lines) + '\n'

	def _deformat(self):

		def check_master_chksum(lines,desc):

			if len(lines) != 6:
				msg('Invalid number of lines ({}) in {} data'.format(len(lines),desc))
				return False

			if not is_chksum_6(lines[0]):
				msg('Incorrect master checksum ({}) in {} data'.format(lines[0],desc))
				return False

			chk = make_chksum_6(' '.join(lines[1:]))
			if not compare_chksums(lines[0],'master',chk,'computed',
						hdr='For wallet master checksum',verbose=True):
				return False

			return True

		lines = self.fmt_data.splitlines()
		if not check_master_chksum(lines,self.desc): return False

		d = self.ssdata
		d.label = MMGenWalletLabel(lines[1])

		d1,d2,d3,d4,d5 = lines[2].split()
		d.seed_id = d1.upper()
		d.key_id  = d2.upper()
		check_usr_seed_len(int(d3))
		d.pw_status,d.timestamp = d4,d5

		hpdata = lines[3].split()

		d.hash_preset = hp = hpdata[0][:-1]  # a string!
		qmsg("Hash preset of wallet: '{}'".format(hp))
		if 'hash_preset' in opt.set_by_user:
			uhp = opt.hash_preset
			if uhp != hp:
				qmsg("Warning: ignoring user-requested hash preset '{}'".format(uhp))

		hash_params = list(map(int,hpdata[1:]))

		if hash_params != get_hash_params(d.hash_preset):
			msg("Hash parameters '{}' don't match hash preset '{}'".format(' '.join(hash_params),d.hash_preset))
			return False

		lmin,foo,lmax = [v for k,v in baseconv.b58pad_lens] # 22,33,44
		for i,key in (4,'salt'),(5,'enc_seed'):
			l = lines[i].split(' ')
			chk = l.pop(0)
			b58_val = ''.join(l)

			if len(b58_val) < lmin or len(b58_val) > lmax:
				msg('Invalid format for {} in {}: {}'.format(key,self.desc,l))
				return False

			if not compare_chksums(chk,key,
					make_chksum_6(b58_val),'computed checksum',verbose=True):
				return False

			val = baseconv.b58decode(b58_val,pad=True)
			if val == False:
				msg('Invalid base 58 number: {}'.format(b58_val))
				return False

			setattr(d,key,val)

		return True

	def _decrypt(self):
		d = self.ssdata
		# Needed for multiple transactions with {}-txsign
		suf = ('',os.path.basename(self.infile.name))[bool(opt.quiet)]
		self._get_passphrase(desc_suf=suf)
		key = make_key(d.passwd, d.salt, d.hash_preset)
		ret = decrypt_seed(d.enc_seed, key, d.seed_id, d.key_id)
		if ret:
			self.seed = Seed(ret)
			return True
		else:
			return False

	def _filename(self):
		s = self.seed
		d = self.ssdata
		return '{}-{}[{},{}]{x}.{}'.format(
				s.fn_stem,
				d.key_id,
				s.bitlen,
				d.hash_preset,
				self.ext,
				x='-α' if g.debug_utf8 else '')

class Brainwallet (SeedSourceEnc):

	stdin_ok = True
	fmt_codes = 'mmbrain','brainwallet','brain','bw','b'
	desc = 'brainwallet'
	ext = 'mmbrain'
	# brainwallet warning message? TODO

	def get_bw_params(self):
		# already checked
		a = opt.brain_params.split(',')
		return int(a[0]),a[1]

	def _deformat(self):
		self.brainpasswd = ' '.join(self.fmt_data.split())
		return True

	def _decrypt(self):
		d = self.ssdata
		# Don't set opt.seed_len! In txsign, BW seed len might differ from other seed srcs
		if opt.brain_params:
			seed_len,d.hash_preset = self.get_bw_params()
		else:
			if 'seed_len' not in opt.set_by_user:
				m1 = 'Using default seed length of {} bits\n'
				m2 = 'If this is not what you want, use the --seed-len option'
				qmsg((m1+m2).format(yellow(str(opt.seed_len))))
			self._get_hash_preset()
			seed_len = opt.seed_len
		qmsg_r('Hashing brainwallet data.  Please wait...')
		# Use buflen arg of scrypt.hash() to get seed of desired length
		seed = scrypt_hash_passphrase(self.brainpasswd.encode(),b'',d.hash_preset,buflen=seed_len//8)
		qmsg('Done')
		self.seed = Seed(seed)
		msg('Seed ID: {}'.format(self.seed.sid))
		qmsg('Check this value against your records')
		return True

class IncogWallet (SeedSourceEnc):

	file_mode = 'binary'
	fmt_codes = 'mmincog','incog','icg','i'
	desc = 'incognito data'
	ext = 'mmincog'
	no_tty = True

	_msg = {
		'check_incog_id': """
  Check the generated Incog ID above against your records.  If it doesn't
  match, then your incognito data is incorrect or corrupted.
	""",
		'record_incog_id': """
  Make a record of the Incog ID but keep it secret.  You will use it to
  identify your incog wallet data in the future.
	""",
		'incorrect_incog_passphrase_try_again': """
Incorrect passphrase, hash preset, or maybe old-format incog wallet.
Try again? (Y)es, (n)o, (m)ore information:
""".strip(),
		'confirm_seed_id': """
If the Seed ID above is correct but you're seeing this message, then you need
to exit and re-run the program with the '--old-incog-fmt' option.
""".strip(),
		'dec_chk': " {} hash preset"
	}

	def _make_iv_chksum(self,s): return sha256(s).hexdigest()[:8].upper()

	def _get_incog_data_len(self,seed_len):
		e = (g.hincog_chk_len,0)[bool(opt.old_incog_fmt)]
		return g.aesctr_iv_len + g.salt_len + e + seed_len//8

	def _incog_data_size_chk(self):
		# valid sizes: 56, 64, 72
		dlen = len(self.fmt_data)
		valid_dlen = self._get_incog_data_len(opt.seed_len)
		if dlen == valid_dlen:
			return True
		else:
			if opt.old_incog_fmt:
				msg('WARNING: old-style incognito format requested.  Are you sure this is correct?')
			m = 'Invalid incognito data size ({} bytes) for this seed length ({} bits)'
			msg(m.format(dlen,opt.seed_len))
			msg('Valid data size for this seed length: {} bytes'.format(valid_dlen))
			for sl in g.seed_lens:
				if dlen == self._get_incog_data_len(sl):
					die(1,'Valid seed length for this data size: {} bits'.format(sl))
			msg('This data size ({} bytes) is invalid for all available seed lengths'.format(dlen))
			return False

	def _encrypt (self):
		self._get_first_pw_and_hp_and_encrypt_seed()
		if opt.old_incog_fmt:
			die(1,'Writing old-format incog wallets is unsupported')
		d = self.ssdata
		# IV is used BOTH to initialize counter and to salt password!
		d.iv = get_random(g.aesctr_iv_len)
		d.iv_id = self._make_iv_chksum(d.iv)
		msg('New Incog Wallet ID: {}'.format(d.iv_id))
		qmsg('Make a record of this value')
		vmsg(self.msg['record_incog_id'])

		d.salt = get_random(g.salt_len)
		key = make_key(d.passwd, d.salt, d.hash_preset, 'incog wallet key')
		chk = sha256(self.seed.data).digest()[:8]
		d.enc_seed = encrypt_data(chk+self.seed.data, key, g.aesctr_dfl_iv, 'seed')

		d.wrapper_key = make_key(d.passwd, d.iv, d.hash_preset, 'incog wrapper key')
		d.key_id = make_chksum_8(d.wrapper_key)
		vmsg('Key ID: {}'.format(d.key_id))
		d.target_data_len = self._get_incog_data_len(self.seed.bitlen)

	def _format(self):
		d = self.ssdata
		self.fmt_data = d.iv + encrypt_data(d.salt+d.enc_seed, d.wrapper_key, d.iv, self.desc)

	def _filename(self):
		s = self.seed
		d = self.ssdata
		return '{}-{}-{}[{},{}]{x}.{}'.format(
				s.fn_stem,
				d.key_id,
				d.iv_id,
				s.bitlen,
				d.hash_preset,
				self.ext,
				x='-α' if g.debug_utf8 else '')

	def _deformat(self):

		if not self._incog_data_size_chk(): return False

		d = self.ssdata
		d.iv             = self.fmt_data[0:g.aesctr_iv_len]
		d.incog_id       = self._make_iv_chksum(d.iv)
		d.enc_incog_data = self.fmt_data[g.aesctr_iv_len:]
		msg('Incog Wallet ID: {}'.format(d.incog_id))
		qmsg('Check this value against your records')
		vmsg(self.msg['check_incog_id'])

		return True

	def _verify_seed_newfmt(self,data):
		chk,seed = data[:8],data[8:]
		if sha256(seed).digest()[:8] == chk:
			qmsg('Passphrase{} are correct'.format(self.msg['dec_chk'].format('and')))
			return seed
		else:
			msg('Incorrect passphrase{}'.format(self.msg['dec_chk'].format('or')))
			return False

	def _verify_seed_oldfmt(self,seed):
		m = 'Seed ID: {}.  Is the Seed ID correct?'.format(make_chksum_8(seed))
		if keypress_confirm(m, True):
			return seed
		else:
			return False

	def _decrypt(self):
		d = self.ssdata
		self._get_hash_preset(desc_suf=d.incog_id)
		self._get_passphrase(desc_suf=d.incog_id)

		# IV is used BOTH to initialize counter and to salt password!
		key = make_key(d.passwd, d.iv, d.hash_preset, 'wrapper key')
		dd = decrypt_data(d.enc_incog_data, key, d.iv, 'incog data')

		d.salt     = dd[0:g.salt_len]
		d.enc_seed = dd[g.salt_len:]

		key = make_key(d.passwd, d.salt, d.hash_preset, 'main key')
		qmsg('Key ID: {}'.format(make_chksum_8(key)))

		verify_seed = getattr(self,'_verify_seed_'+
						('newfmt','oldfmt')[bool(opt.old_incog_fmt)])

		seed = verify_seed(decrypt_seed(d.enc_seed, key, '', ''))

		if seed:
			self.seed = Seed(seed)
			msg('Seed ID: {}'.format(self.seed.sid))
			return True
		else:
			return False

class IncogWalletHex (IncogWallet):

	file_mode = 'text'
	desc = 'hex incognito data'
	fmt_codes = 'mmincox','incox','incog_hex','xincog','ix','xi'
	ext = 'mmincox'
	no_tty = False

	def _deformat(self):
		ret = decode_pretty_hexdump(self.fmt_data)
		if ret:
			self.fmt_data = ret
			return IncogWallet._deformat(self)
		else:
			return False

	def _format(self):
		IncogWallet._format(self)
		self.fmt_data = pretty_hexdump(self.fmt_data)

class IncogWalletHidden (IncogWallet):

	desc = 'hidden incognito data'
	fmt_codes = 'incog_hidden','hincog','ih','hi'
	ext = None

	_msg = {
		'choose_file_size': """
You must choose a size for your new hidden incog data.  The minimum size is
{} bytes, which puts the incog data right at the end of the file. Since you
probably want to hide your data somewhere in the middle of the file where it's
harder to find, you're advised to choose a much larger file size than this.
	""".strip(),
		'check_incog_id': """
  Check generated Incog ID above against your records.  If it doesn't
  match, then your incognito data is incorrect or corrupted, or you
  may have specified an incorrect offset.
	""",
		'record_incog_id': """
  Make a record of the Incog ID but keep it secret.  You will used it to
  identify the incog wallet data in the future and to locate the offset
  where the data is hidden in the event you forget it.
	""",
		'dec_chk': ', hash preset, offset {} seed length'
	}

	def _get_hincog_params(self,wtype):
		a = getattr(opt,'hidden_incog_'+ wtype +'_params').split(',')
		return ','.join(a[:-1]),int(a[-1]) # permit comma in filename

	def _check_valid_offset(self,fn,action):
		d = self.ssdata
		m = ('Input','Destination')[action=='write']
		if fn.size < d.hincog_offset + d.target_data_len:
			fs = "{} file '{}' has length {}, too short to {} {} bytes of data at offset {}"
			die(1,fs.format(m,fn.name,fn.size,action,d.target_data_len,d.hincog_offset))

	def _get_data(self):
		d = self.ssdata
		d.hincog_offset = self._get_hincog_params('input')[1]

		qmsg("Getting hidden incog data from file '{}'".format(self.infile.name))

		# Already sanity-checked:
		d.target_data_len = self._get_incog_data_len(opt.seed_len)
		self._check_valid_offset(self.infile,'read')

		flgs = os.O_RDONLY|os.O_BINARY if g.platform == 'win' else os.O_RDONLY
		fh = os.open(self.infile.name,flgs)
		os.lseek(fh,int(d.hincog_offset),os.SEEK_SET)
		self.fmt_data = os.read(fh,d.target_data_len)
		os.close(fh)
		qmsg("Data read from file '{}' at offset {}".format(self.infile.name,d.hincog_offset))

	# overrides method in SeedSource
	def write_to_file(self):
		d = self.ssdata
		self._format()
		compare_or_die(d.target_data_len, 'target data length',
				len(self.fmt_data),'length of formatted ' + self.desc)

		k = ('output','input')[self.op=='pwchg_new']
		fn,d.hincog_offset = self._get_hincog_params(k)

		if opt.outdir and not os.path.dirname(fn):
			fn = os.path.join(opt.outdir,fn)

		check_offset = True
		try:
			os.stat(fn)
		except:
			if keypress_confirm("Requested file '{}' does not exist.  Create?".format(fn),default_yes=True):
				min_fsize = d.target_data_len + d.hincog_offset
				msg(self.msg['choose_file_size'].format(min_fsize))
				while True:
					fsize = parse_bytespec(my_raw_input('Enter file size: '))
					if fsize >= min_fsize: break
					msg('File size must be an integer no less than {}'.format(min_fsize))

				from mmgen.tool import MMGenToolCmd
				MMGenToolCmd().rand2file(fn,str(fsize))
				check_offset = False
			else:
				die(1,'Exiting at user request')

		from mmgen.filename import Filename
		f = Filename(fn,ftype=type(self),write=True)

		dmsg('{} data len {}, offset {}'.format(capfirst(self.desc),d.target_data_len,d.hincog_offset))

		if check_offset:
			self._check_valid_offset(f,'write')
			if not opt.quiet:
				confirm_or_raise('',"alter file '{}'".format(f.name))

		flgs = os.O_RDWR|os.O_BINARY if g.platform == 'win' else os.O_RDWR
		fh = os.open(f.name,flgs)
		os.lseek(fh, int(d.hincog_offset), os.SEEK_SET)
		os.write(fh, self.fmt_data)
		os.close(fh)
		msg("{} written to file '{}' at offset {}".format(capfirst(self.desc),f.name,d.hincog_offset))
