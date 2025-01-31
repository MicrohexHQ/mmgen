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
common.py: Shared routines and data for the MMGen test suites
"""

class TestSuiteException(Exception): pass
class TestSuiteFatalException(Exception): pass

import os
from mmgen.common import *

ascii_uc   = ''.join(map(chr,list(range(65,91))))   # 26 chars
ascii_lc   = ''.join(map(chr,list(range(97,123))))  # 26 chars
lat_accent = ''.join(map(chr,list(range(192,383)))) # 191 chars, L,S
ru_uc = ''.join(map(chr,list(range(1040,1072)))) # 32 chars
gr_uc = ''.join(map(chr,list(range(913,930)) + list(range(931,940)))) # 26 chars (930 is ctrl char)
gr_uc_w_ctrl = ''.join(map(chr,list(range(913,940)))) # 27 chars, L,C
lat_cyr_gr = lat_accent[:130:5] + ru_uc + gr_uc # 84 chars
ascii_cyr_gr = ascii_uc + ru_uc + gr_uc # 84 chars

utf8_text      = '[α-$ample UTF-8 text-ω]' * 10   # 230 chars, L,N,P,S,Z
utf8_combining = '[α-$ámple UTF-8 téxt-ω]' * 10   # L,N,P,S,Z,M
utf8_ctrl      = '[α-$ample\nUTF-8\ntext-ω]' * 10 # L,N,P,S,Z,C

text_jp = '必要なのは、信用ではなく暗号化された証明に基づく電子取引システムであり、これにより希望する二者が信用できる第三者機関を介さずに直接取引できるよう' # 72 chars ('W'ide)
text_zh = '所以，我們非常需要這樣一種電子支付系統，它基於密碼學原理而不基於信用，使得任何達成一致的雙方，能夠直接進行支付，從而不需要協力廠商仲介的參與。。' # 72 chars ('F'ull + 'W'ide)

sample_text = 'The Times 03/Jan/2009 Chancellor on brink of second bailout for banks'

ref_kafile_pass = 'kafile password'
ref_kafile_hash_preset = '1'

def getrandnum(n): return int(os.urandom(n).hex(),16)
def getrandhex(n): return os.urandom(n).hex()
def getrandnum_range(nbytes,rn_max):
	while True:
		rn = int(os.urandom(nbytes).hex(),16)
		if rn < rn_max: return rn

def getrandstr(num_chars,no_space=False):
	n,m = 95,32
	if no_space: n,m = 94,33
	return ''.join([chr(i%n+m) for i in list(os.urandom(num_chars))])

# Windows uses non-UTF8 encodings in filesystem, so use raw bytes here
def cleandir(d,do_msg=False):
	d_enc = d.encode()

	try:    files = os.listdir(d_enc)
	except: return

	from shutil import rmtree
	if do_msg: gmsg("Cleaning directory '{}'".format(d))
	for f in files:
		try:
			os.unlink(os.path.join(d_enc,f))
		except:
			rmtree(os.path.join(d_enc,f),ignore_errors=True)

def mk_tmpdir(d):
	try: os.mkdir(d,0o755)
	except OSError as e:
		if e.errno != 17: raise
	else:
		vmsg("Created directory '{}'".format(d))

# def mk_tmpdir_path(path,cfg):
# 	try:
# 		name = os.path.split(cfg['tmpdir'])[-1]
# 		src = os.path.join(path,name)
# 		try:
# 			os.unlink(cfg['tmpdir'])
# 		except OSError as e:
# 			if e.errno != 2: raise
# 		finally:
# 			os.mkdir(src)
# 			os.symlink(src,cfg['tmpdir'])
# 	except OSError as e:
# 		if e.errno != 17: raise
# 	else: msg("Created directory '{}'".format(cfg['tmpdir']))

def get_tmpfile(cfg,fn):
	return os.path.join(cfg['tmpdir'],fn)

def write_to_file(fn,data,binary=False):
	write_data_to_file( fn,
						data,
						quiet = True,
						binary = binary,
						ignore_opt_outdir = True )

def write_to_tmpfile(cfg,fn,data,binary=False):
	write_to_file(  os.path.join(cfg['tmpdir'],fn), data=data, binary=binary )

def read_from_file(fn,binary=False):
	from mmgen.util import get_data_from_file
	return get_data_from_file(fn,quiet=True,binary=binary)

def read_from_tmpfile(cfg,fn,binary=False):
	return read_from_file(os.path.join(cfg['tmpdir'],fn),binary=binary)

def joinpath(*args,**kwargs):
	return os.path.join(*args,**kwargs)

def ok():
	if opt.profile: return
	if opt.verbose or opt.exact_output:
		gmsg('OK')
	else: msg(' OK')

def cmp_or_die(s,t,desc=None):
	if s != t:
		m = 'ERROR: recoded data:\n{!r}\ndiffers from original data:\n{!r}'
		if desc: m = 'For {}:\n{}'.format(desc,m)
		raise TestSuiteFatalException(m.format(t,s))

def init_coverage():
	coverdir = os.path.join('test','trace')
	acc_file = os.path.join('test','trace.acc')
	try: os.mkdir(coverdir,0o755)
	except: pass
	return coverdir,acc_file

devnull_fh = open(('/dev/null','null.out')[g.platform == 'win'],'w')
def silence():
	if not (opt.verbose or (hasattr(opt,'exact_output') and opt.exact_output)):
		g.stdout = g.stderr = devnull_fh

def end_silence():
	if not (opt.verbose or (hasattr(opt,'exact_output') and opt.exact_output)):
		g.stdout = sys.stdout
		g.stderr = sys.stderr

def omsg(s):
	sys.stderr.write(s + '\n')
def omsg_r(s):
	sys.stderr.write(s)
	sys.stderr.flush()
def imsg(s):
	if opt.verbose or (hasattr(opt,'exact_output') and opt.exact_output):
		omsg(s)
def imsg_r(s):
	if opt.verbose or (hasattr(opt,'exact_output') and opt.exact_output):
		omsg_r(s)
def iqmsg(s):
	if not opt.quiet: omsg(s)
def iqmsg_r(s):
	if not opt.quiet: omsg_r(s)
