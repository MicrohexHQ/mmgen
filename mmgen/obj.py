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
obj.py: MMGen native classes
"""

import sys,os,unicodedata
from decimal import *
from string import hexdigits,ascii_letters,digits

if os.getenv('MMGEN_DEBUG') or os.getenv('MMGEN_TEST_SUITE') or os.getenv('MMGEN_TRACEBACK'):
	from mmgen.devtools import *
else:
	class MMGenObject(object): pass
from mmgen.color import *
from mmgen.exception import *

def is_mmgen_seed_id(s): return SeedID(sid=s,on_fail='silent')
def is_mmgen_idx(s):     return AddrIdx(s,on_fail='silent')
def is_mmgen_id(s):      return MMGenID(s,on_fail='silent')
def is_coin_addr(s):     return CoinAddr(s,on_fail='silent')
def is_addrlist_id(s):   return AddrListID(s,on_fail='silent')
def is_tw_label(s):      return TwLabel(s,on_fail='silent')
def is_wif(s):           return WifKey(s,on_fail='silent')
def is_viewkey(s):       return ViewKey(s,on_fail='silent')

def truncate_str(s,width): # width = screen width
	wide_count = 0
	for i in range(len(s)):
		wide_count += unicodedata.east_asian_width(s[i]) in ('F','W')
		if wide_count + i >= width:
			return s[:i] + ('',' ')[
				unicodedata.east_asian_width(s[i]) in ('F','W')
				and wide_count + i == width]
	else: # pad the string to width if necessary
		return s + ' '*(width-len(s)-wide_count)

# dict that keeps a list of keys for efficient lookup by index
class IndexedDict(dict):

	def __init__(self,*args,**kwargs):
		if args or kwargs:
			self.die('initializing values via constructor')
		self.__keylist = []
		return dict.__init__(self,*args,**kwargs)

	def __setitem__(self,key,value):
		if key in self:
			self.die('reassignment to existing key')
		self.__keylist.append(key)
		return dict.__setitem__(self,key,value)

	@property
	def keys(self):
		return self.__keylist

	def key(self,idx):
		return self.__keylist[idx]

	def __delitem__(self,*args): self.die('item deletion')
	def move_to_end(self,*args): self.die('item moving')
	def clear(self,*args):       self.die('clearing')
	def update(self,*args):      self.die('updating')

	def die(self,desc):
		raise NotImplementedError('{} not implemented for type {}'.format(desc,type(self).__name__))

class MMGenList(list,MMGenObject): pass
class MMGenDict(dict,MMGenObject): pass
class AddrListList(list,MMGenObject): pass

class InitErrors(object):

	on_fail='die'

	@classmethod
	def arg_chk(cls,on_fail):
		cls.on_fail = on_fail
		assert on_fail in ('die','return','silent','raise'),(
			"'{}': invalid value for 'on_fail' in class {}".format(on_fail,cls.__name__) )

	@classmethod
	def init_fail(cls,e,m,e2=None,m2=None,objname=None,preformat=False):

		if preformat:
			errmsg = m
		else:
			fs = "{!r}: value cannot be converted to {} {}({})"
			e2_fmt = '({}) '.format(e2.args[0]) if e2 else ''
			errmsg = fs.format(m,objname or cls.__name__,e2_fmt,e.args[0])

		if m2: errmsg = '{!r}\n{}'.format(m2,errmsg)

		from mmgen.globalvars import g
		from mmgen.util import die,msg
		if cls.on_fail == 'silent':
			return None # TODO: return False instead?
		elif cls.on_fail == 'return':
			if errmsg: msg(errmsg)
			return None # TODO: return False instead?
		elif g.traceback or cls.on_fail == 'raise':
			if hasattr(cls,'exc'):
				raise cls.exc(errmsg)
			else:
				raise
		elif cls.on_fail == 'die':
			die(1,errmsg)

class Hilite(object):

	color = 'red'
	color_always = False
	width = 0
	trunc_ok = True
	dtype = str

	@classmethod
	# 'width' is screen width (greater than len(s) for CJK strings)
	# 'append_chars' and 'encl' must consist of single-width chars only
	def fmtc(cls,s,width=None,color=False,encl='',trunc_ok=None,
				center=False,nullrepl='',append_chars='',append_color=False):
		if cls.dtype == bytes: s = s.decode()
		s_wide_count = len([1 for ch in s if unicodedata.east_asian_width(ch) in ('F','W')])
		assert isinstance(encl,str) and len(encl) in (0,2),"'encl' must be 2-character str"
		a,b = list(encl) if encl else ('','')
		add_len = len(a) + len(b) + len(append_chars)
		if width == None: width = cls.width
		if trunc_ok == None: trunc_ok = cls.trunc_ok
		assert width >= 2 + add_len,( # 2 because CJK
			"'{!r}': invalid width ({}) (width must be at least 2)".format(s,width))
		if len(s) + s_wide_count + add_len > width:
			assert trunc_ok, "If 'trunc_ok' is false, 'width' must be >= screen width of string"
			s = truncate_str(s,width-add_len)
		if s == '' and nullrepl:
			s = nullrepl.center(width)
		else:
			s = a+s+b
			if center: s = s.center(width)
		if append_chars:
			return cls.colorize(s,color=color) + \
					cls.colorize(append_chars.ljust(width-len(s)-s_wide_count),color=append_color)
		else:
			return cls.colorize(s.ljust(width-s_wide_count),color=color)

	@classmethod
	def colorize(cls,s,color=True):
		if cls.dtype == bytes: s = s.decode()
		k = color if type(color) is str else cls.color # hack: override color with str value
		return globals()[k](s) if (color or cls.color_always) else s

	def fmt(self,*args,**kwargs):
		assert args == () # forbid invocation w/o keywords
		return self.fmtc(self,*args,**kwargs)

	@classmethod
	def hlc(cls,s,color=True):
		return cls.colorize(s,color=color)

	def hl(self,color=True):
		return self.colorize(self,color=color)

	def __str__(self):
		return self.colorize(self,color=False)

class Str(str,Hilite): pass
class Int(int,Hilite): pass

# For attrs that are always present in the data instance
# Reassignment and deletion forbidden
class MMGenImmutableAttr(object): # Descriptor

	def __init__(self,name,dtype,typeconv=True,no_type_check=False):
		self.typeconv = typeconv
		self.no_type_check = no_type_check
		assert isinstance(dtype,(str,type,type(None))),'{!r}: invalid dtype arg'.format(dtype)
		self.name = name
		self.dtype = dtype

	def __get__(self,instance,owner):
		return instance.__dict__[self.name]

	# forbid all reassignment
	def set_attr_ok(self,instance):
		return not self.name in instance.__dict__
#		return not hasattr(instance,self.name)

	def __set__(self,instance,value):
		if not self.set_attr_ok(instance):
			m = "Attribute '{}' of {} instance cannot be reassigned"
			raise AttributeError(m.format(self.name,type(instance)))
		if self.typeconv:   # convert type
			instance.__dict__[self.name] = \
				globals()[self.dtype](value,on_fail='raise') if type(self.dtype) == str else self.dtype(value)
		else:               # check type
			if type(value) == self.dtype or self.no_type_check:
				instance.__dict__[self.name] = value
			else:
				m = "Attribute '{}' of {} instance must of type {}"
				raise TypeError(m.format(self.name,type(instance),self.dtype))

	def __delete__(self,instance):
		m = "Atribute '{}' of {} instance cannot be deleted"
		raise AttributeError(m.format(self.name,type(instance)))

# For attrs that might not be present in the data instance
# Reassignment or deletion allowed if specified
class MMGenListItemAttr(MMGenImmutableAttr): # Descriptor

	def __init__(self,name,dtype,typeconv=True,reassign_ok=False,delete_ok=False):
		self.reassign_ok = reassign_ok
		self.delete_ok = delete_ok
		MMGenImmutableAttr.__init__(self,name,dtype,typeconv=typeconv)

	# return None if attribute doesn't exist
	def __get__(self,instance,owner):
		try: return instance.__dict__[self.name]
		except: return None

	def set_attr_ok(self,instance):
		return getattr(instance,self.name) == None or self.reassign_ok

	def __delete__(self,instance):
		if self.delete_ok:
			if self.name in instance.__dict__:
				del instance.__dict__[self.name]
		else:
			MMGenImmutableAttr.__delete__(self,instance)

class MMGenListItem(MMGenObject):

	valid_attrs = None
	valid_attrs_extra = set()

	def __init__(self,*args,**kwargs):
		if self.valid_attrs == None:
			type(self).valid_attrs = (
				( {e for e in dir(self) if e[:2] != '__'} | self.valid_attrs_extra ) -
				{'pformat','pmsg','pdie','valid_attrs','valid_attrs_extra'} )
		if args:
			raise ValueError('Non-keyword args not allowed')
		for k in kwargs:
			if kwargs[k] != None:
				setattr(self,k,kwargs[k])

	# allow only valid attributes to be set
	def __setattr__(self,name,value):
		if name not in self.valid_attrs:
			m = "'{}': no such attribute in class {}"
			raise AttributeError(m.format(name,type(self)))
		return object.__setattr__(self,name,value)

class MMGenIdx(int,InitErrors):
	min_val = 1
	max_val = None
	max_digits = None
	def __new__(cls,num,on_fail='die'):
		cls.arg_chk(on_fail)
		try:
			assert type(num) is not float,'is float'
			me = int.__new__(cls,num)
			if cls.max_digits:
				assert len(str(me)) <= cls.max_digits,'has more than {} digits'.format(cls.max_digits)
			if cls.max_val:
				assert me <= cls.max_val,'is greater than {}'.format(cls.max_val)
			assert me >= cls.min_val,'is less than {}'.format(cls.min_val)
			return me
		except Exception as e:
			return cls.init_fail(e,num)

class SeedShareIdx(MMGenIdx): max_val = 1024
class SeedShareCount(SeedShareIdx): min_val = 2
class MasterShareIdx(MMGenIdx): max_val = 1024
class AddrIdx(MMGenIdx): max_digits = 7

class AddrIdxList(list,InitErrors,MMGenObject):
	max_len = 1000000
	def __init__(self,fmt_str=None,idx_list=None,on_fail='die',sep=','):
		type(self).arg_chk(on_fail)
		try:
			if idx_list:
				return list.__init__(self,sorted({AddrIdx(i,on_fail='raise') for i in idx_list}))
			elif fmt_str:
				ret = []
				for i in (fmt_str.split(sep)):
					j = i.split('-')
					if len(j) == 1:
						idx = AddrIdx(i,on_fail='raise')
						if not idx: break
						ret.append(idx)
					elif len(j) == 2:
						beg = AddrIdx(j[0],on_fail='raise')
						if not beg: break
						end = AddrIdx(j[1],on_fail='raise')
						if not beg: break
						if end < beg: break
						ret.extend([AddrIdx(x,on_fail='raise') for x in range(beg,end+1)])
					else: break
				else:
					return list.__init__(self,sorted(set(ret))) # fell off end of loop - success
				raise ValueError("{!r}: invalid range".format(i))
		except Exception as e:
			return type(self).init_fail(e,idx_list or fmt_str)

class MMGenRange(tuple,InitErrors,MMGenObject):

	min_idx = None
	max_idx = None

	def __new__(cls,*args,on_fail='die'):
		cls.arg_chk(on_fail)
		try:
			if len(args) == 1:
				s = args[0]
				if type(s) == cls: return s
				assert isinstance(s,str),'not a string or string subclass'
				ss = s.split('-',1)
				first = int(ss[0])
				last = int(ss.pop())
			else:
				s = repr(args) # needed if exception occurs
				assert len(args) == 2,'one format string arg or two start,stop args required'
				first,last = args
			assert first <= last, 'start of range greater than end of range'
			if cls.min_idx is not None:
				assert first >= cls.min_idx, 'start of range < {:,}'.format(cls.min_idx)
			if cls.max_idx is not None:
				assert last <= cls.max_idx, 'end of range > {:,}'.format(cls.max_idx)
			return tuple.__new__(cls,(first,last))
		except Exception as e:
			return cls.init_fail(e,s)

	@property
	def first(self):
		return self[0]

	@property
	def last(self):
		return self[1]

	def iterate(self):
		return range(self[0],self[1]+1)

	@property
	def items(self):
		return list(self.iterate())

class SubSeedIdxRange(MMGenRange):
	min_idx = 1
	max_idx = 1000000

class UnknownCoinAmt(Decimal): pass

class BTCAmt(Decimal,Hilite,InitErrors):
	color = 'yellow'
	max_prec = 8
	max_amt = 21000000
	satoshi = Decimal('0.00000001')
	min_coin_unit = satoshi
	amt_fs = '4.8'
	units = ('satoshi',)
	forbidden_types = (float,int)

	# NB: 'from_decimal' rounds down to precision of 'min_coin_unit'
	def __new__(cls,num,from_unit=None,from_decimal=False,on_fail='die'):
		if type(num) == cls: return num
		cls.arg_chk(on_fail)
		try:
			if from_unit:
				assert from_unit in cls.units,(
					"'{}': unrecognized denomination for {}".format(from_unit,cls.__name__))
				assert type(num) == int,'value is not an integer'
				me = Decimal.__new__(cls,num * getattr(cls,from_unit))
			elif from_decimal:
				assert type(num) == Decimal,(
					"number is not of type Decimal (type is {!r})".format(type(num).__name__))
				me = Decimal.__new__(cls,num).quantize(cls.min_coin_unit)
			else:
				for t in cls.forbidden_types:
					assert type(num) is not t,"number is of forbidden type '{}'".format(t.__name__)
				me = Decimal.__new__(cls,str(num))
			assert me.normalize().as_tuple()[-1] >= -cls.max_prec,'too many decimal places in coin amount'
			if cls.max_amt:
				assert me <= cls.max_amt,'{}: coin amount too large (>{})'.format(me,cls.max_amt)
			assert me >= 0,'coin amount cannot be negative'
			return me
		except Exception as e:
			return cls.init_fail(e,num)

	def toSatoshi(self):
		return int(Decimal(self) // self.satoshi)

	def to_unit(self,unit,show_decimal=False):
		ret = Decimal(self) // getattr(self,unit)
		if show_decimal and ret < 1:
			return '{:.8f}'.format(ret).rstrip('0')
		return int(ret)

	@classmethod
	def fmtc(cls):
		raise NotImplementedError

	def fmt(self,fs=None,color=False,suf='',prec=1000):
		if fs == None: fs = self.amt_fs
		s = str(int(self)) if int(self) == self else self.normalize().__format__('f')
		if '.' in fs:
			p1,p2 = list(map(int,fs.split('.',1)))
			ss = s.split('.',1)
			if len(ss) == 2:
				a,b = ss
				ret = a.rjust(p1) + '.' + ((b+suf).ljust(p2+len(suf)))[:prec]
			else:
				ret = s.rjust(p1) + suf + (' ' * (p2+1))[:prec+1-len(suf)]
		else:
			ret = s.ljust(int(fs))
		return self.colorize(ret,color=color)

	def hl(self,color=True):
		return self.__str__(color=color)

	def __str__(self,color=False): # format simply, no exponential notation
		return self.colorize(
				str(int(self)) if int(self) == self else
				self.normalize().__format__('f'),
			color=color)

	def __repr__(self):
		return "{}('{}')".format(type(self).__name__,self.__str__())

	def __add__(self,other):
		return type(self)(Decimal.__add__(self,other))
	__radd__ = __add__

	def __sub__(self,other):
		return type(self)(Decimal.__sub__(self,other))

	def __mul__(self,other):
		return type(self)('{:0.8f}'.format(Decimal.__mul__(self,Decimal(other))))

	def __div__(self,other):
		return type(self)('{:0.8f}'.format(Decimal.__div__(self,Decimal(other))))

	def __neg__(self,other):
		return type(self)(Decimal.__neg__(self,other))

class BCHAmt(BTCAmt): pass
class B2XAmt(BTCAmt): pass
class LTCAmt(BTCAmt): max_amt = 84000000
class XMRAmt(BTCAmt): min_coin_unit = Decimal('0.000000000001')

from mmgen.altcoins.eth.obj import ETHAmt,ETHNonce

class CoinAddr(str,Hilite,InitErrors,MMGenObject):
	color = 'cyan'
	hex_width = 40
	width = 1
	trunc_ok = False
	def __new__(cls,s,on_fail='die'):
		if type(s) == cls: return s
		cls.arg_chk(on_fail)
		from mmgen.globalvars import g
		try:
			assert set(s) <= set(ascii_letters+digits),'contains non-alphanumeric characters'
			me = str.__new__(cls,s)
			va = g.proto.verify_addr(s,hex_width=cls.hex_width,return_dict=True)
			assert va,'failed verification'
			me.addr_fmt = va['format']
			me.hex = va['hex']
			return me
		except Exception as e:
			return cls.init_fail(e,s,objname='{} address'.format(g.proto.__name__))

	@classmethod
	def fmtc(cls,s,**kwargs):
		# True -> 'cyan': use the str value override hack
		if 'color' in kwargs and kwargs['color'] == True:
			kwargs['color'] = cls.color
		if not 'width' in kwargs: kwargs['width'] = cls.width
		if kwargs['width'] < len(s):
			s = s[:kwargs['width']-2] +  '..'
		return Hilite.fmtc(s,**kwargs)

	def is_for_chain(self,chain):

		from mmgen.globalvars import g
		if g.proto.__name__[:8] == 'Ethereum':
			return True

		def pfx_ok(pfx):
			if type(pfx) == tuple:
				if self[0] in pfx: return True
			elif self[:len(pfx)] == pfx: return True
			return False

		proto = g.proto.get_protocol_by_chain(chain)
		vn = proto.addr_ver_num

		if self.addr_fmt == 'bech32':
			return self[:len(proto.bech32_hrp)] == proto.bech32_hrp
		elif self.addr_fmt == 'p2sh' and 'p2sh2' in vn:
			return pfx_ok(vn['p2sh'][1]) or pfx_ok(vn['p2sh2'][1])
		else:
			return pfx_ok(vn[self.addr_fmt][1])

class TokenAddr(CoinAddr):
	color = 'blue'

class ViewKey(object):
	def __new__(cls,s,on_fail='die'):
		from mmgen.globalvars import g
		if g.proto.name == 'zcash':
			return ZcashViewKey.__new__(ZcashViewKey,s,on_fail)
		elif g.proto.name == 'monero':
			return MoneroViewKey.__new__(MoneroViewKey,s,on_fail)
		else:
			raise ValueError('{}: protocol does not support view keys'.format(g.proto.name.capitalize()))

class ZcashViewKey(CoinAddr): hex_width = 128

class SeedID(str,Hilite,InitErrors):
	color = 'blue'
	width = 8
	trunc_ok = False
	def __new__(cls,seed=None,sid=None,on_fail='die'):
		if type(sid) == cls: return sid
		cls.arg_chk(on_fail)
		try:
			if seed:
				from mmgen.seed import SeedBase
				assert isinstance(seed,SeedBase),'not a subclass of SeedBase'
				from mmgen.util import make_chksum_8
				return str.__new__(cls,make_chksum_8(seed.data))
			elif sid:
				assert set(sid) <= set(hexdigits.upper()),'not uppercase hex digits'
				assert len(sid) == cls.width,'not {} characters wide'.format(cls.width)
				return str.__new__(cls,sid)
			raise ValueError('no arguments provided')
		except Exception as e:
			return cls.init_fail(e,seed or sid)

class SubSeedIdx(str,Hilite,InitErrors):
	color = 'red'
	trunc_ok = False
	def __new__(cls,s,on_fail='die'):
		if type(s) == cls: return s
		cls.arg_chk(on_fail)
		try:
			assert isinstance(s,str),'not a string or string subclass'
			idx = s[:-1] if s[-1] in 'SsLl' else s
			from mmgen.util import is_int
			assert is_int(idx),"valid format: an integer, plus optional letter 'S','s','L' or 'l'"
			idx = int(idx)
			assert idx >= SubSeedIdxRange.min_idx, 'subseed index < {:,}'.format(SubSeedIdxRange.min_idx)
			assert idx <= SubSeedIdxRange.max_idx, 'subseed index > {:,}'.format(SubSeedIdxRange.max_idx)

			sstype,ltr = ('short','S') if s[-1] in 'Ss' else ('long','L')
			me = str.__new__(cls,str(idx)+ltr)
			me.idx = idx
			me.type = sstype
			return me
		except Exception as e:
			return cls.init_fail(e,s)

class MMGenID(str,Hilite,InitErrors,MMGenObject):
	color = 'orange'
	width = 0
	trunc_ok = False
	def __new__(cls,s,on_fail='die'):
		cls.arg_chk(on_fail)
		from mmgen.globalvars import g
		try:
			ss = str(s).split(':')
			assert len(ss) in (2,3),'not 2 or 3 colon-separated items'
			t = MMGenAddrType((ss[1],g.proto.dfl_mmtype)[len(ss)==2],on_fail='raise')
			me = str.__new__(cls,'{}:{}:{}'.format(ss[0],t,ss[-1]))
			me.sid = SeedID(sid=ss[0],on_fail='raise')
			me.idx = AddrIdx(ss[-1],on_fail='raise')
			me.mmtype = t
			assert t in g.proto.mmtypes,'{}: invalid address type for {}'.format(t,g.proto.__name__)
			me.al_id = str.__new__(AddrListID,me.sid+':'+me.mmtype) # checks already done
			me.sort_key = '{}:{}:{:0{w}}'.format(me.sid,me.mmtype,me.idx,w=me.idx.max_digits)
			return me
		except Exception as e:
			return cls.init_fail(e,s)

class TwMMGenID(str,Hilite,InitErrors,MMGenObject):
	color = 'orange'
	width = 0
	trunc_ok = False
	def __new__(cls,s,on_fail='die'):
		if type(s) == cls: return s
		cls.arg_chk(on_fail)
		ret = None
		try:
			ret = MMGenID(s,on_fail='raise')
			sort_key,idtype = ret.sort_key,'mmgen'
		except Exception as e:
			try:
				from mmgen.globalvars import g
				assert s.split(':',1)[0] == g.proto.base_coin.lower(),(
					"not a string beginning with the prefix '{}:'".format(g.proto.base_coin.lower()))
				assert set(s[4:]) <= set(ascii_letters+digits),'contains non-alphanumeric characters'
				assert len(s) > 4,'not more that four characters long'
				ret,sort_key,idtype = str(s),'z_'+s,'non-mmgen'
			except Exception as e2:
				return cls.init_fail(e,s,e2=e2)

		me = str.__new__(cls,ret)
		me.obj = ret
		me.sort_key = sort_key
		me.type = idtype
		return me

# non-displaying container for TwMMGenID,TwComment
class TwLabel(str,InitErrors,MMGenObject):
	def __new__(cls,s,on_fail='die'):
		if type(s) == cls: return s
		cls.arg_chk(on_fail)
		try:
			ss = s.split(None,1)
			mmid = TwMMGenID(ss[0],on_fail='raise')
			comment = TwComment(ss[1] if len(ss) == 2 else '',on_fail='raise')
			me = str.__new__(cls,'{}{}'.format(mmid,' {}'.format(comment) if comment else ''))
			me.mmid = mmid
			me.comment = comment
			return me
		except Exception as e:
			return cls.init_fail(e,s)

class HexStr(str,Hilite,InitErrors):
	color = 'red'
	width = None
	hexcase = 'lower'
	trunc_ok = False
	dtype = str
	def __new__(cls,s,on_fail='die',case=None):
		if type(s) == cls: return s
		cls.arg_chk(on_fail)
		if case == None: case = cls.hexcase
		try:
			assert isinstance(s,str),'not a string or string subclass'
			assert case in ('upper','lower'),"'{}' incorrect case specifier".format(case)
			assert set(s) <= set(getattr(hexdigits,case)()),'not {}case hexadecimal symbols'.format(case)
			assert not len(s) % 2,'odd-length string'
			if cls.width:
				assert len(s) == cls.width,'Value is not {} characters wide'.format(cls.width)
			return cls.dtype.__new__(cls,s)
		except Exception as e:
			return cls.init_fail(e,s)

class CoinTxID(HexStr):       color,width,hexcase = 'purple',64,'lower'
class WalletPassword(HexStr): color,width,hexcase = 'blue',32,'lower'
class MoneroViewKey(HexStr):  color,width,hexcase = 'cyan',64,'lower'
class MMGenTxID(HexStr):      color,width,hexcase = 'red',6,'upper'

class WifKey(str,Hilite,InitErrors):
	width = 53
	color = 'blue'
	def __new__(cls,s,on_fail='die'):
		if type(s) == cls: return s
		cls.arg_chk(on_fail)
		try:
			assert set(s) <= set(ascii_letters+digits),'not an ascii alphanumeric string'
			from mmgen.globalvars import g
			g.proto.wif2hex(s) # raises exception on error
			return str.__new__(cls,s)
		except Exception as e:
			return cls.init_fail(e,s)

class PubKey(HexStr,MMGenObject): # TODO: add some real checks
	def __new__(cls,s,compressed,on_fail='die'):
		try:
			assert type(compressed) == bool,"'compressed' must be of type bool"
		except Exception as e:
			return cls.init_fail(e,s)
		me = HexStr.__new__(cls,s,case='lower',on_fail=on_fail)
		if me:
			me.compressed = compressed
			return me

class PrivKey(str,Hilite,InitErrors,MMGenObject):

	color = 'red'
	width = 64
	trunc_ok = False

	compressed = MMGenImmutableAttr('compressed',bool,typeconv=False)
	wif        = MMGenImmutableAttr('wif',WifKey,typeconv=False)

	# initialize with (priv_bin,compressed), WIF or self
	def __new__(cls,s=None,compressed=None,wif=None,pubkey_type=None,on_fail='die'):
		from mmgen.globalvars import g

		if type(s) == cls: return s
		cls.arg_chk(on_fail)

		if wif:
			try:
				assert s == None,"'wif' and key hex args are mutually exclusive"
				assert set(wif) <= set(ascii_letters+digits),'not an ascii alphanumeric string'
				w2h = g.proto.wif2hex(wif) # raises exception on error
				me = str.__new__(cls,w2h['hex'])
				me.compressed = w2h['compressed']
				me.pubkey_type = w2h['pubkey_type']
				me.wif = str.__new__(WifKey,wif) # check has been done
				me.orig_hex = None
				return me
			except Exception as e:
				return cls.init_fail(e,s,objname='{} WIF key'.format(g.coin))
		else:
			try:
				assert s,'private key hex data missing'
				assert compressed is not None, "'compressed' arg missing"
				assert pubkey_type is not None,"'pubkey_type' arg missing"
				assert type(compressed) == bool,"{!r}: 'compressed' not of type 'bool'".format(compressed)
				assert len(s) == cls.width // 2,'key length must be {}'.format(cls.width // 2)
				if pubkey_type == 'password': # skip WIF creation and pre-processing for passwds
					me = str.__new__(cls,s.hex())
				else:
					me = str.__new__(cls,g.proto.preprocess_key(s.hex(),pubkey_type))
					me.wif = WifKey(g.proto.hex2wif(me,pubkey_type,compressed),on_fail='raise')
				me.compressed = compressed
				me.pubkey_type = pubkey_type
				me.orig_hex = s.hex() # save the non-preprocessed key
				return me
			except Exception as e:
				return cls.init_fail(e,s)

class AddrListID(str,Hilite,InitErrors,MMGenObject):
	width = 10
	trunc_ok = False
	color = 'yellow'
	def __new__(cls,sid,mmtype,on_fail='die'):
		cls.arg_chk(on_fail)
		try:
			assert type(sid) == SeedID,"{!r} not a SeedID instance".format(sid)
			if not isinstance(mmtype,(MMGenAddrType,MMGenPasswordType)):
				m = '{!r}: not an instance of MMGenAddrType or MMGenPasswordType'.format(mmtype)
				raise ValueError(m.format(mmtype))
			me = str.__new__(cls,sid+':'+mmtype)
			me.sid = sid
			me.mmtype = mmtype
			return me
		except Exception as e:
			return cls.init_fail(e,'sid={}, mmtype={}'.format(sid,mmtype))

class MMGenLabel(str,Hilite,InitErrors):
	color = 'pink'
	allowed = []
	forbidden = []
	max_len = 0
	min_len = 0
	max_screen_width = 0 # if != 0, overrides max_len
	desc = 'label'
	def __new__(cls,s,on_fail='die',msg=None):
		if type(s) == cls: return s
		cls.arg_chk(on_fail)
		for k in cls.forbidden,cls.allowed:
			assert type(k) == list
			for ch in k: assert type(ch) == str and len(ch) == 1
		try:
			s = s.strip()
			for ch in s:
				# Allow:    (L)etter,(N)umber,(P)unctuation,(S)ymbol,(Z)space
				# Disallow: (C)ontrol,(M)combining
				# Combining characters create width formatting issues, so disallow them for now
				if unicodedata.category(ch)[0] in 'CM':
					t = { 'C':'control', 'M':'combining' }[unicodedata.category(ch)[0]]
					raise ValueError('{}: {} characters not allowed'.format(ascii(ch),t))
			me = str.__new__(cls,s)
			if cls.max_screen_width:
				me.screen_width = len(s) + len([1 for ch in s if unicodedata.east_asian_width(ch) in ('F','W')])
				assert me.screen_width <= cls.max_screen_width,(
					'too wide (>{} screen width)'.format(cls.max_screen_width))
			else:
				assert len(s) <= cls.max_len, 'too long (>{} symbols)'.format(cls.max_len)
			assert len(s) >= cls.min_len, 'too short (<{} symbols)'.format(cls.min_len)
			assert not cls.allowed or set(list(s)).issubset(set(cls.allowed)),\
				'contains non-allowed symbols: {}'.format(' '.join(set(list(s)) - set(cls.allowed)))
			assert not cls.forbidden or not any(ch in s for ch in cls.forbidden),\
				"contains one of these forbidden symbols: '{}'".format("', '".join(cls.forbidden))
			return me
		except Exception as e:
			return cls.init_fail(e,s)

class MMGenWalletLabel(MMGenLabel):
	max_len = 48
	desc = 'wallet label'

class TwComment(MMGenLabel):
	max_screen_width = 80
	desc = 'tracking wallet comment'
	exc = BadTwComment

class MMGenTXLabel(MMGenLabel):
	max_len = 72
	desc = 'transaction label'

class MMGenPWIDString(MMGenLabel):
	max_len = 256
	min_len = 1
	desc = 'password ID string'
	forbidden = list(' :/\\')

class SeedShareIDString(MMGenPWIDString):
	desc = 'seed share ID string'

class MMGenAddrType(str,Hilite,InitErrors,MMGenObject):
	width = 1
	trunc_ok = False
	color = 'blue'
	mmtypes = { # 'name' is used to cook the seed, so it must never change!
		'L': {  'name':'legacy',
				'pubkey_type':'std',
				'compressed':False,
				'gen_method':'p2pkh',
				'addr_fmt':'p2pkh',
				'desc':'Legacy uncompressed address'},
		'C': {  'name':'compressed',
				'pubkey_type':'std',
				'compressed':True,
				'gen_method':'p2pkh',
				'addr_fmt':'p2pkh',
				'desc':'Compressed P2PKH address'},
		'S': {  'name':'segwit',
				'pubkey_type':'std',
				'compressed':True,
				'gen_method':'segwit',
				'addr_fmt':'p2sh',
				'desc':'Segwit P2SH-P2WPKH address' },
		'B': {  'name':'bech32',
				'pubkey_type':'std',
				'compressed':True,
				'gen_method':'bech32',
				'addr_fmt':'bech32',
				'desc':'Native Segwit (Bech32) address' },
		'E': {  'name':'ethereum',
				'pubkey_type':'std',
				'compressed':False,
				'gen_method':'ethereum',
				'addr_fmt':'ethereum',
				'wif_label':'privkey:',
				'extra_attrs': ('wallet_passwd',),
				'desc':'Ethereum address' },
		'Z': {  'name':'zcash_z',
				'pubkey_type':'zcash_z',
				'compressed':False,
				'gen_method':'zcash_z',
				'addr_fmt':'zcash_z',
				'extra_attrs': ('viewkey',),
				'desc':'Zcash z-address' },
		'M': {  'name':'monero',
				'pubkey_type':'monero',
				'compressed':False,
				'gen_method':'monero',
				'addr_fmt':'monero',
				'wif_label':'spendkey:',
				'extra_attrs': ('viewkey','wallet_passwd'),
				'desc':'Monero address'}
	}
	def __new__(cls,s,on_fail='die',errmsg=None):
		if type(s) == cls: return s
		cls.arg_chk(on_fail)
		from mmgen.globalvars import g
		try:
			for k,v in list(cls.mmtypes.items()):
				if s in (k,v['name']):
					if s == v['name']: s = k
					me = str.__new__(cls,s)
					for k in ('name','pubkey_type','compressed','gen_method','addr_fmt','desc'):
						setattr(me,k,v[k])
					assert me in g.proto.mmtypes + ('P',), (
						"'{}': invalid address type for {}".format(me.name,g.proto.__name__))
					me.extra_attrs = v['extra_attrs'] if 'extra_attrs' in v else ()
					me.wif_label   = v['wif_label'] if 'wif_label' in v else 'wif:'
					return me
			raise ValueError('not found')
		except Exception as e:
			m = '{}{!r}: invalid value for {} ({})'.format(
				('{!r}\n'.format(errmsg) if errmsg else ''),s,cls.__name__,e.args[0])
			return cls.init_fail(e,m,preformat=True)

	@classmethod
	def get_names(cls):
		return [v['name'] for v in cls.mmtypes.values()]

class MMGenPasswordType(MMGenAddrType):
	mmtypes = {
		'P': {  'name':'password',
				'pubkey_type':'password',
				'compressed':False,
				'gen_method':None,
				'addr_fmt':None,
				'desc':'Password generated from MMGen seed'}
	}
