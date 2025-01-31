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
ts_ref.py: Reference file tests for the test.py test suite
"""

import os
from mmgen.globalvars import g
from mmgen.opts import opt
from test.common import *
from test.test_py_d.common import *

from test.test_py_d.ts_base import *
from test.test_py_d.ts_shared import *

wpasswd = 'reference password'

class TestSuiteRef(TestSuiteBase,TestSuiteShared):
	'saved reference files'
	tmpdir_nums = [8]
	networks = ('btc','btc_tn','ltc','ltc_tn')
	passthru_opts = ('coin','testnet')
	sources = {
		'ref_addrfile':    '98831F3A{}[1,31-33,500-501,1010-1011]{}.addrs',
		'ref_segwitaddrfile':'98831F3A{}-S[1,31-33,500-501,1010-1011]{}.addrs',
		'ref_bech32addrfile':'98831F3A{}-B[1,31-33,500-501,1010-1011]{}.addrs',
		'ref_keyaddrfile': '98831F3A{}[1,31-33,500-501,1010-1011]{}.akeys.mmenc',
		'ref_passwdfile':  '98831F3A-фубар@crypto.org-b58-20[1,4,9-11,1100].pws',
		'ref_tx_file': { # data shared with ref_altcoin, autosign
			'btc': ('0B8D5A[15.31789,14,tl=1320969600].rawtx',
					'0C7115[15.86255,14,tl=1320969600].testnet.rawtx'),
			'ltc': ('AF3CDF-LTC[620.76194,1453,tl=1320969600].rawtx',
					'A5A1E0-LTC[1454.64322,1453,tl=1320969600].testnet.rawtx'),
			'bch': ('460D4D-BCH[10.19764,tl=1320969600].rawtx',
					'359FD5-BCH[6.68868,tl=1320969600].testnet.rawtx'),
			'eth': ('88FEFD-ETH[23.45495,40000].rawtx',
					'B472BD-ETH[23.45495,40000].testnet.rawtx'),
			'mm1': ('5881D2-MM1[1.23456,50000].rawtx',
					'6BDB25-MM1[1.23456,50000].testnet.rawtx'),
			'etc': ('ED3848-ETC[1.2345,40000].rawtx','')
		},
	}
	chk_data = {
		'ref_subwallet_sid': {
			'98831F3A:32L':'D66B4885',
			'98831F3A:1S':'20D95B09',
		},
		'ref_addrfile_chksum': {
			'btc': ('6FEF 6FB9 7B13 5D91','424E 4326 CFFE 5F51'),
			'ltc': ('AD52 C3FE 8924 AAF0','4EBE 2E85 E969 1B30'),
		},
		'ref_segwitaddrfile_chksum': {
			'btc': ('06C1 9C87 F25C 4EE6','072C 8B07 2730 CB7A'),
			'ltc': ('63DF E42A 0827 21C3','5DD1 D186 DBE1 59F2'),
		},
		'ref_bech32addrfile_chksum': {
			'btc': ('9D2A D4B6 5117 F02E','0527 9C39 6C1B E39A'),
			'ltc': ('FF1C 7939 5967 AB82','ED3D 8AA4 BED4 0B40'),
		},
		'ref_keyaddrfile_chksum': {
			'btc': ('9F2D D781 1812 8BAD','88CC 5120 9A91 22C2'),
			'ltc': ('B804 978A 8796 3ED4','98B5 AC35 F334 0398'),
		},
		'ref_passwdfile_chksum':   'A983 DAB9 5514 27FB',
	}
	cmd_group = ( # TODO: move to tooltest2
		('ref_words_to_subwallet_chk1','subwallet generation from reference words file (long subseed)'),
		('ref_words_to_subwallet_chk2','subwallet generation from reference words file (short subseed)'),
		('ref_subwallet_addrgen1','subwallet address file generation (long subseed)'),
		('ref_subwallet_addrgen2','subwallet address file generation (short subseed)'),
		('ref_subwallet_keygen1','subwallet key-address file generation (long subseed)'),
		('ref_subwallet_keygen2','subwallet key-address file generation (short subseed)'),
		('ref_addrfile_chk',   'saved reference address file'),
		('ref_segwitaddrfile_chk','saved reference address file (segwit)'),
		('ref_bech32addrfile_chk','saved reference address file (bech32)'),
		('ref_keyaddrfile_chk','saved reference key-address file'),
		('ref_passwdfile_chk', 'saved reference password file'),
#	Create the fake inputs:
#	('txcreate8',          'transaction creation (8)'),
		('ref_tx_chk',         'signing saved reference tx file'),
		('ref_brain_chk_spc3', 'saved brainwallet (non-standard spacing)'),
		('ref_tool_decrypt',   'decryption of saved MMGen-encrypted file'),
	)

	def _get_ref_subdir_by_coin(self,coin):
		return {'btc': '',
				'bch': '',
				'ltc': 'litecoin',
				'eth': 'ethereum',
				'etc': 'ethereum_classic',
				'xmr': 'monero',
				'zec': 'zcash',
				'dash': 'dash' }[coin.lower()]

	@property
	def ref_subdir(self):
		return self._get_ref_subdir_by_coin(g.coin)

	def ref_words_to_subwallet_chk1(self):
		return self.ref_words_to_subwallet_chk('32L')

	def ref_words_to_subwallet_chk2(self):
		return self.ref_words_to_subwallet_chk('1S')

	def ref_words_to_subwallet_chk(self,ss_idx):
		wf = dfl_words_file
		args = ['-d',self.tr.trash_dir,'-o','words',wf,ss_idx]

		t = self.spawn('mmgen-subwalletgen',args,extra_desc='(generate subwallet)')
		t.expect('Generating subseed {}'.format(ss_idx))
		chk_sid = self.chk_data['ref_subwallet_sid']['98831F3A:{}'.format(ss_idx)]
		fn = t.written_to_file('MMGen native mnemonic data')
		assert chk_sid in fn,'incorrect filename: {} (does not contain {})'.format(fn,chk_sid)
		ok()

		t = self.spawn('mmgen-walletchk',[fn],extra_desc='(check subwallet)')
		t.expect(r'Valid MMGen native mnemonic data for Seed ID ([0-9A-F]*)\b',regex=True)
		sid = t.p.match.group(1)
		assert sid == chk_sid,'subseed ID {} does not match expected value {}'.format(sid,chk_sid)
		t.read()
		return t

	def ref_subwallet_addrgen(self,ss_idx,target='addr'):
		wf = dfl_words_file
		args = ['-d',self.tr.trash_dir,'--subwallet='+ss_idx,wf,'1-10']
		t = self.spawn('mmgen-{}gen'.format(target),args)
		t.expect('Generating subseed {}'.format(ss_idx))
		chk_sid = self.chk_data['ref_subwallet_sid']['98831F3A:{}'.format(ss_idx)]
		assert chk_sid == t.expect_getend('Checksum for .* data ',regex=True)[:8]
		if target == 'key':
			t.expect('Encrypt key list? (y/N): ','n')
		fn = t.written_to_file(('Addresses','Secret keys')[target=='key'])
		assert chk_sid in fn,'incorrect filename: {} (does not contain {})'.format(fn,chk_sid)
		return t

	def ref_subwallet_addrgen1(self):
		return self.ref_subwallet_addrgen('32L')

	def ref_subwallet_addrgen2(self):
		return self.ref_subwallet_addrgen('1S')

	def ref_subwallet_keygen1(self):
		return self.ref_subwallet_addrgen('32L',target='key')

	def ref_subwallet_keygen2(self):
		return self.ref_subwallet_addrgen('1S',target='key')

	def ref_addrfile_chk(self,ftype='addr',coin=None,subdir=None,pfx=None,mmtype=None,add_args=[]):
		af_key = 'ref_{}file'.format(ftype)
		af_fn = TestSuiteRef.sources[af_key].format(pfx or self.altcoin_pfx,'' if coin else self.tn_ext)
		af = joinpath(ref_dir,(subdir or self.ref_subdir,'')[ftype=='passwd'],af_fn)
		coin_arg = [] if coin == None else ['--coin='+coin]
		tool_cmd = ftype.replace('segwit','').replace('bech32','')+'file_chksum'
		t = self.spawn('mmgen-tool',coin_arg+['-p1',tool_cmd,af]+add_args)
		if ftype == 'keyaddr':
			t.do_decrypt_ka_data(hp=ref_kafile_hash_preset,pw=ref_kafile_pass,have_yes_opt=True)
		rc = self.chk_data[   'ref_' + ftype + 'file_chksum' +
					('_'+coin.lower() if coin else '') +
					('_'+mmtype if mmtype else '')]
		ref_chksum = rc if (ftype == 'passwd' or coin) else rc[g.proto.base_coin.lower()][g.testnet]
		t.expect(chksum_pat,regex=True)
		m = t.p.match.group(0)
		t.read()
		cmp_or_die(ref_chksum,m)
		return t

	def ref_segwitaddrfile_chk(self):
		if not 'S' in g.proto.mmtypes:
			return skip('not supported')
		else:
			return self.ref_addrfile_chk(ftype='segwitaddr')

	def ref_bech32addrfile_chk(self):
		if not 'B' in g.proto.mmtypes:
			return skip('not supported')
		else:
			return self.ref_addrfile_chk(ftype='bech32addr')

	def ref_keyaddrfile_chk(self):
		return self.ref_addrfile_chk(ftype='keyaddr')

	def ref_passwdfile_chk(self):
		return self.ref_addrfile_chk(ftype='passwd')

	def ref_tx_chk(self):
		fn = self.sources['ref_tx_file'][g.coin.lower()][bool(self.tn_ext)]
		if not fn: return
		tf = joinpath(ref_dir,self.ref_subdir,fn)
		wf = dfl_words_file
		self.write_to_tmpfile(pwfile,wpasswd)
		pf = joinpath(self.tmpdir,pwfile)
		return self.txsign(tf,wf,pf,save=False,has_label=True,do_passwd=False,view='y')

	def ref_brain_chk_spc3(self):
		return self.ref_brain_chk(bw_file=ref_bw_file_spc)

	def ref_tool_decrypt(self):
		f = joinpath(ref_dir,ref_enc_fn)
		disable_debug()
		dec_file = joinpath(self.tmpdir,'famous.txt')
		t = self.spawn('mmgen-tool', ['-q','decrypt',f,'outfile='+dec_file,'hash_preset=1'])
		restore_debug()
		t.passphrase('user data',tool_enc_passwd)
		t.written_to_file('Decrypted data')
		dec_txt = read_from_file(dec_file)
		imsg_r(dec_txt)
		cmp_or_die(sample_text+'\n',dec_txt) # file adds a newline to sample_text
		return t
