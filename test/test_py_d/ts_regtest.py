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
ts_regtest.py: Regtest tests for the test.py test suite
"""

import os,subprocess
from decimal import Decimal
from ast import literal_eval
from mmgen.globalvars import g
from mmgen.opts import opt
from mmgen.util import die,gmsg,write_data_to_file
from mmgen.protocol import CoinProtocol
from mmgen.addr import AddrList
from test.common import *
from test.test_py_d.common import *

rt_pw = 'abc-α'
rt_data = {
	'tx_fee': {'btc':'0.0001','bch':'0.001','ltc':'0.01'},
	'rtFundAmt': {'btc':'500','bch':'500','ltc':'5500'},
	'rtFee': {
		'btc': ('20s','10s','60s','31s','10s','20s'),
		'bch': ('20s','10s','60s','0.0001','10s','20s'),
		'ltc': ('1000s','500s','1500s','0.05','400s','1000s')
	},
	'rtBals': {
		'btc': ('499.9999488','399.9998282','399.9998147','399.9996877',
				'52.99980410','946.99933647','999.99914057','52.9999',
				'946.99933647'),
		'bch': ('499.9999484','399.9999194','399.9998972','399.9997692',
				'46.78890380','953.20966920','999.99857300','46.789',
				'953.2096692'),
		'ltc': ('5499.99744','5399.994425','5399.993885','5399.987535',
				'52.98520500','10946.93753500','10999.92274000','52.99',
				'10946.937535'),
	},
	'rtBals_gb': {
		'btc': {
			'0conf0': {
				'mmgen': ('283.22339537','0','283.22339537'),
				'nonmm': ('16.77647763','0','116.77629233'),
				'total': ('299.999873','0','399.9996877'),
			},
			'0conf1': {
				'mmgen': ('283.22339537','283.22339537','0'),
				'nonmm': ('16.77647763','16.77647763','99.9998147'),
				'total': ('299.999873','299.999873','99.9998147'),
			},
			'1conf1': {
				'mmgen': ('0','0','283.22339537'),
				'nonmm': ('0','0','116.77629233'),
				'total': ('0','0','399.9996877'),
			},
			'1conf2': {
				'mmgen': ('0','283.22339537','0'),
				'nonmm': ('0','16.77647763','99.9998147'),
				'total': ('0','299.999873','99.9998147'),
			},
		},
		'bch': {
			'0conf0': {
				'mmgen': ('283.22339437','0','283.22339437'),
				'nonmm': ('16.77647763','0','116.77637483'),
				'total': ('299.999872','0','399.9997692'),
			},
			'0conf1': {
				'mmgen': ('283.22339437','283.22339437','0'),
				'nonmm': ('16.77647763','16.77647763','99.9998972'),
				'total': ('299.999872','299.999872','99.9998972'),
			},
			'1conf1': {
				'mmgen': ('0','0','283.22339437'),
				'nonmm': ('0','0','116.77637483'),
				'total': ('0','0','399.9997692'),
			},
			'1conf2': {
				'mmgen': ('0','283.22339437','0'),
				'nonmm': ('0','16.77647763','99.9998972'),
				'total': ('0','299.999872','99.9998972'),
			},
		},
		'ltc': {
			'0conf0': {
				'mmgen': ('283.21717237','0','283.21717237'),
				'nonmm': ('16.77647763','0','5116.77036263'),
				'total': ('299.99365','0','5399.987535'),
			},
			'0conf1': {
				'mmgen': ('283.21717237','283.21717237','0'),
				'nonmm': ('16.77647763','16.77647763','5099.993885'),
				'total': ('299.99365','299.99365','5099.993885'),
			},
			'1conf1': {
				'mmgen': ('0','0','283.21717237'),
				'nonmm': ('0','0','5116.77036263'),
				'total': ('0','0','5399.987535'),
			},
			'1conf2': {
				'mmgen': ('0','283.21717237','0'),
				'nonmm': ('0','16.77647763','5099.993885'),
				'total': ('0','299.99365','5099.993885'),
			},
		}
	},
	'rtBobOp3': {'btc':'S:2','bch':'L:3','ltc':'S:2'},
	'rtAmts': {
		'btc': ('500',),
		'bch': ('500',),
		'ltc': ('5500',)
	}
}

from test.test_py_d.ts_base import *
from test.test_py_d.ts_shared import *

class TestSuiteRegtest(TestSuiteBase,TestSuiteShared):
	'transacting and tracking wallet operations via regtest mode'
	networks = ('btc','ltc','bch')
	passthru_opts = ('coin',)
	tmpdir_nums = [17]
	cmd_group = (
		('setup',                    'regtest (Bob and Alice) mode setup'),
		('walletgen_bob',            'wallet generation (Bob)'),
		('walletgen_alice',          'wallet generation (Alice)'),
		('addrgen_bob',              'address generation (Bob)'),
		('addrgen_alice',            'address generation (Alice)'),
		('addrimport_bob',           "importing Bob's addresses"),
		('addrimport_alice',         "importing Alice's addresses"),
		('fund_bob',                 "funding Bob's wallet"),
		('fund_alice',               "funding Alice's wallet"),
		('bob_bal1',                 "Bob's balance"),
		('bob_add_label',            "adding an 80-screen-width label (lat+cyr+gr)"),
		('bob_twview1',              "viewing Bob's tracking wallet"),
		('bob_split1',               "splitting Bob's funds"),
		('generate',                 'mining a block'),
		('bob_bal2',                 "Bob's balance"),
		('bob_rbf_1output_create',   'creating RBF tx with one output'),
		('bob_rbf_1output_bump',     'bumping RBF tx with one output'),
		('bob_bal2a',                "Bob's balance (age_fmt=confs)"),
		('bob_bal2b',                "Bob's balance (showempty=1)"),
		('bob_bal2c',                "Bob's balance (showempty=1 minconf=2 age_fmt=days)"),
		('bob_bal2d',                "Bob's balance (minconf=2)"),
		('bob_bal2e',                "Bob's balance (showempty=1 sort=age)"),
		('bob_bal2f',                "Bob's balance (showempty=1 sort=age,reverse)"),
		('bob_rbf_send',             'sending funds to Alice (RBF)'),
		('get_mempool1',             'mempool (before RBF bump)'),
		('bob_rbf_status1',          'getting status of transaction'),
		('bob_rbf_bump',             'bumping RBF transaction'),
		('get_mempool2',             'mempool (after RBF bump)'),
		('bob_rbf_status2',          'getting status of transaction after replacement'),
		('bob_rbf_status3',          'getting status of replacement transaction (mempool)'),
		('generate',                 'mining a block'),
		('bob_rbf_status4',          'getting status of transaction after confirmed (1) replacement'),
		('bob_rbf_status5',          'getting status of replacement transaction (confirmed)'),
		('generate',                 'mining a block'),
		('bob_rbf_status6',          'getting status of transaction after confirmed (2) replacement'),
		('bob_bal3',                 "Bob's balance"),
		('bob_pre_import',           'sending to non-imported address'),
		('generate',                 'mining a block'),
		('bob_import_addr',          'importing non-MMGen address with --rescan'),
		('bob_bal4',                 "Bob's balance (after import with rescan)"),
		('bob_import_list',          'importing flat address list'),
		('bob_split2',               "splitting Bob's funds"),
		('bob_0conf0_getbalance',    "Bob's balance (unconfirmed, minconf=0)"),
		('bob_0conf1_getbalance',    "Bob's balance (unconfirmed, minconf=1)"),
		('generate',                 'mining a block'),
		('bob_1conf1_getbalance',    "Bob's balance (confirmed, minconf=1)"),
		('bob_1conf2_getbalance',    "Bob's balance (confirmed, minconf=2)"),
		('bob_bal5',                 "Bob's balance"),
		('bob_send_non_mmgen',       'sending funds to Alice (from non-MMGen addrs)'),
		('generate',                 'mining a block'),
		('alice_bal_rpcfail',        'RPC failure code'),
		('alice_send_estimatefee',   'tx creation with no fee on command line'),
		('generate',                 'mining a block'),
		('bob_bal6',                 "Bob's balance"),

		('bob_subwallet_addrgen1',     "generating Bob's addrs from subwallet 29L"),
		('bob_subwallet_addrgen2',     "generating Bob's addrs from subwallet 127S"),
		('bob_subwallet_addrimport1',  "importing Bob's addrs from subwallet 29L"),
		('bob_subwallet_addrimport2',  "importing Bob's addrs from subwallet 127S"),
		('bob_subwallet_fund',         "funding Bob's subwallet addrs"),
		('generate',                   'mining a block'),
		('bob_twview2',                "viewing Bob's tracking wallet"),
		('bob_twview3',                "viewing Bob's tracking wallet"),
		('bob_subwallet_txcreate',     'creating a transaction with subwallet inputs'),
		('bob_subwallet_txsign',       'signing a transaction with subwallet inputs'),
		('bob_subwallet_txdo',         "sending from Bob's subwallet addrs"),
		('generate',                   'mining a block'),
		('bob_twview4',                "viewing Bob's tracking wallet"),

		('bob_alice_bal',            "Bob and Alice's balances"),
		('alice_bal2',               "Alice's balance"),

		('alice_add_label1',         'adding a label'),
		('alice_chk_label1',         'the label'),
		('alice_add_label2',         'adding a label'),
		('alice_chk_label2',         'the label'),
		('alice_edit_label1',        'editing a label (zh)'),
		('alice_edit_label2',        'editing a label (lat+cyr+gr)'),
		('alice_chk_label3',         'the label'),
		('alice_remove_label1',      'removing a label'),
		('alice_chk_label4',         'the label'),
		('alice_add_label_coinaddr', 'adding a label using the coin address'),
		('alice_chk_label_coinaddr', 'the label'),
		('alice_add_label_badaddr1', 'adding a label with invalid address'),
		('alice_add_label_badaddr2', 'adding a label with invalid address for this chain'),
		('alice_add_label_badaddr3', 'adding a label with wrong MMGen address'),
		('alice_add_label_badaddr4', 'adding a label with wrong coin address'),

		('stop',                     'stopping regtest daemon'),
	)
	usr_subsids = { 'bob': {}, 'alice': {} }

	def __init__(self,trunner,cfgs,spawn):
		coin = g.coin.lower()
		for k in rt_data:
			globals()[k] = rt_data[k][coin] if coin in rt_data[k] else None
		return TestSuiteBase.__init__(self,trunner,cfgs,spawn)

	def _add_comments_to_addr_file(self,addrfile,outfile,use_labels=False):
		silence()
		gmsg("Adding comments to address file '{}'".format(addrfile))
		a = AddrList(addrfile)
		for n,idx in enumerate(a.idxs(),1):
			if use_labels:
				a.set_comment(idx,get_label())
			else:
				if n % 2: a.set_comment(idx,'Test address {}'.format(n))
		a.format(enable_comments=True)
		write_data_to_file(outfile,a.fmt_data,quiet=True,ignore_opt_outdir=True)
		end_silence()

	def setup(self):
		os.environ['MMGEN_BOGUS_WALLET_DATA'] = ''
		if g.testnet:
			die(2,'--testnet option incompatible with regtest test suite')
		try: shutil.rmtree(joinpath(self.tr.data_dir,'regtest'))
		except: pass
		os.environ['MMGEN_TEST_SUITE'] = '' # mnemonic is piped to stdin, so stop being a terminal
		t = self.spawn('mmgen-regtest',['-n','setup'])
		os.environ['MMGEN_TEST_SUITE'] = '1'
		for s in ('Starting setup','Creating','Mined','Creating','Creating','Setup complete'):
			t.expect(s)
		return t

	def walletgen(self,user):
		t = self.spawn('mmgen-walletgen',['-q','-r0','-p1','--'+user])
		t.passphrase_new('new MMGen wallet',rt_pw)
		t.label()
		t.expect('move it to the data directory? (Y/n): ','y')
		t.written_to_file('MMGen wallet')
		return t

	def walletgen_bob(self):   return self.walletgen('bob')
	def walletgen_alice(self): return self.walletgen('alice')

	def _user_dir(self,user,coin=None):
		return joinpath(self.tr.data_dir,'regtest',coin or g.coin.lower(),user)

	def _user_sid(self,user):
		return os.path.basename(get_file_with_ext(self._user_dir(user),'mmdat'))[:8]

	def _get_user_subsid(self,user,subseed_idx):

		if subseed_idx in self.usr_subsids[user]:
			return self.usr_subsids[user][subseed_idx]

		fn = get_file_with_ext(self._user_dir(user),'mmdat')
		t = self.spawn('mmgen-tool',['get_subseed',subseed_idx,'wallet='+fn],no_msg=True)
		t.passphrase('MMGen wallet',rt_pw)
		sid = t.read().strip()[:8]
		self.usr_subsids[user][subseed_idx] = sid
		return sid

	def addrgen(self,user,wf=None,addr_range='1-5',subseed_idx=None,mmtypes=[]):
		from mmgen.addr import MMGenAddrType
		for mmtype in mmtypes or g.proto.mmtypes:
			t = self.spawn('mmgen-addrgen',
				['--quiet','--'+user,'--type='+mmtype,'--outdir={}'.format(self._user_dir(user))] +
				([wf] if wf else []) +
				(['--subwallet='+subseed_idx] if subseed_idx else []) +
				[addr_range],
				extra_desc='({})'.format(MMGenAddrType.mmtypes[mmtype]['name']))
			t.passphrase('MMGen wallet',rt_pw)
			t.written_to_file('Addresses')
			ok_msg()
		t.skip_ok = True
		return t

	def addrgen_bob(self):   return self.addrgen('bob')
	def addrgen_alice(self): return self.addrgen('alice')

	def addrimport(self,user,sid=None,addr_range='1-5',num_addrs=5,mmtypes=[]):
		id_strs = { 'legacy':'', 'compressed':'-C', 'segwit':'-S', 'bech32':'-B' }
		if not sid: sid = self._user_sid(user)
		from mmgen.addr import MMGenAddrType
		for mmtype in mmtypes or g.proto.mmtypes:
			desc = MMGenAddrType.mmtypes[mmtype]['name']
			addrfile = joinpath(self._user_dir(user),
				'{}{}{}[{}]{x}.testnet.addrs'.format(
					sid,self.altcoin_pfx,id_strs[desc],addr_range,
					x='-α' if g.debug_utf8 else ''))
			if mmtype == g.proto.mmtypes[0] and user == 'bob':
				psave = g.proto
				g.proto = CoinProtocol(g.coin,True)
				self._add_comments_to_addr_file(addrfile,addrfile,use_labels=True)
				g.proto = psave
			t = self.spawn( 'mmgen-addrimport',
							['--quiet', '--'+user, '--batch', addrfile],
							extra_desc='({})'.format(desc))
			if g.debug:
				t.expect("Type uppercase 'YES' to confirm: ",'YES\n')
			t.expect('Importing')
			t.expect('{} addresses imported'.format(num_addrs))
			ok_msg()

		t.skip_ok = True
		return t

	def addrimport_bob(self):   return self.addrimport('bob')
	def addrimport_alice(self): return self.addrimport('alice')

	def fund_wallet(self,user,mmtype,amt,sid=None,addr_range='1-5'):
		if not sid: sid = self._user_sid(user)
		addr = self.get_addr_from_addrlist(user,sid,mmtype,0,addr_range=addr_range)
		t = self.spawn('mmgen-regtest', ['send',str(addr),str(amt)])
		t.expect('Sending {} {}'.format(amt,g.coin))
		t.expect('Mined 1 block')
		return t

	def fund_bob(self):   return self.fund_wallet('bob','C',rtFundAmt)
	def fund_alice(self): return self.fund_wallet('alice',('L','S')[g.proto.cap('segwit')],rtFundAmt)

	def user_twview(self,user,chk=None,sort='age'):
		t = self.spawn('mmgen-tool',['--'+user,'twview','sort='+sort])
		if chk: t.expect(chk,regex=True)
		t.read()
		return t

	def bob_twview1(self): return self.user_twview('bob',chk=r'1\).*\b{}\b'.format(rtAmts[0]))

	def user_bal(self,user,bal,args=['showempty=1'],skip_check=False,exit_val=0):
		t = self.spawn('mmgen-tool',['--'+user,'listaddresses'] + args)
		if skip_check:
			t.read()
		else:
			total = t.expect_getend('TOTAL: ')
			cmp_or_die('{} {}'.format(bal,g.coin),total)
		t.req_exit_val = exit_val
		return t

	def alice_bal1(self):
		return self.user_bal('alice',rtFundAmt)

	def alice_bal2(self):
		return self.user_bal('alice',rtBals[8])

	def bob_bal1(self):
		return self.user_bal('bob',rtFundAmt)

	def bob_bal2(self):
		return self.user_bal('bob',rtBals[0])

	def bob_bal2a(self):
		return self.user_bal('bob',rtBals[0],args=['showempty=1','age_fmt=confs'])

	def bob_bal2b(self):
		return self.user_bal('bob',rtBals[0],args=['showempty=1'])

	def bob_bal2c(self):
		return self.user_bal('bob',rtBals[0],args=['showempty=1','minconf=2','age_fmt=days'],skip_check=True)

	def bob_bal2d(self):
		return self.user_bal('bob',rtBals[0],args=['minconf=2'],skip_check=True)

	def bob_bal2e(self):
		return self.user_bal('bob',rtBals[0],args=['showempty=1','sort=age'])

	def bob_bal2f(self):
		return self.user_bal('bob',rtBals[0],args=['showempty=1','sort=age,reverse'])

	def bob_bal3(self):
		return self.user_bal('bob',rtBals[1])

	def bob_bal4(self):
		return self.user_bal('bob',rtBals[2])

	def bob_bal5(self):
		return self.user_bal('bob',rtBals[3])

	def bob_bal6(self):
		return self.user_bal('bob',rtBals[7])

	def bob_subwallet_addrgen1(self):
		return self.addrgen('bob',subseed_idx='29L',mmtypes=['C'])  # 29L: 2FA7BBA8

	def bob_subwallet_addrgen2(self):
		return self.addrgen('bob',subseed_idx='127S',mmtypes=['C']) # 127S: '09E8E286'

	def subwallet_addrimport(self,user,subseed_idx):
		sid = self._get_user_subsid(user,subseed_idx)
		return self.addrimport(user,sid=sid,mmtypes=['C'])

	def bob_subwallet_addrimport1(self): return self.subwallet_addrimport('bob','29L')
	def bob_subwallet_addrimport2(self): return self.subwallet_addrimport('bob','127S')

	def bob_subwallet_fund(self):
		sid1 = self._get_user_subsid('bob','29L')
		sid2 = self._get_user_subsid('bob','127S')
		chg_addr = self._user_sid('bob') + (':B:1',':L:1')[g.coin=='BCH']
		outputs_cl = [sid1+':C:2,0.29',sid2+':C:3,0.127',chg_addr]
		inputs = ('3','1')[g.coin=='BCH']
		return self.user_txdo('bob',rtFee[1],outputs_cl,inputs,extra_args=['--subseeds=127'])

	def bob_twview2(self):
		sid1 = self._get_user_subsid('bob','29L')
		return self.user_twview('bob',chk=r'\b{}:C:2\b\s+{}'.format(sid1,'0.29'),sort='twmmid')

	def bob_twview3(self):
		sid2 = self._get_user_subsid('bob','127S')
		return self.user_twview('bob',chk=r'\b{}:C:3\b\s+{}'.format(sid2,'0.127'),sort='amt')

	def bob_subwallet_txcreate(self):
		sid1 = self._get_user_subsid('bob','29L')
		sid2 = self._get_user_subsid('bob','127S')
		outputs_cl = [sid1+':C:5,0.0159',sid2+':C:5']
		t = self.spawn('mmgen-txcreate',['-d',self.tmpdir,'-B','--bob'] + outputs_cl)
		return self.txcreate_ui_common(t,
								menu            = ['a'],
								inputs          = ('1,2','2,3')[g.coin=='BCH'],
								interactive_fee = '0.00001')

	def bob_subwallet_txsign(self):
		fn = get_file_with_ext(self.tmpdir,'rawtx')
		t = self.spawn('mmgen-txsign',['-d',self.tmpdir,'--bob','--subseeds=127',fn])
		t.view_tx('t')
		t.passphrase('MMGen wallet',rt_pw)
		t.do_comment(None)
		t.expect('(Y/n): ','y')
		t.written_to_file('Signed transaction')
		return t

	def bob_subwallet_txdo(self):
		outputs_cl = [self._user_sid('bob')+':L:5']
		inputs = ('1,2','2,3')[g.coin=='BCH']
		return self.user_txdo('bob',rtFee[5],outputs_cl,inputs,menu=['a'],extra_args=['--subseeds=127']) # sort: amt

	def bob_twview4(self):
		sid = self._user_sid('bob')
		amt = ('0.4169328','0.41364')[g.coin=='LTC']
		return self.user_twview('bob',chk=r'\b{}:L:5\b\s+.*\s+\b{}\b'.format(sid,amt),sort='twmmid')

	def bob_getbalance(self,bals,confs=1):
		for i in (0,1,2):
			assert Decimal(bals['mmgen'][i]) + Decimal(bals['nonmm'][i]) == Decimal(bals['total'][i])
		t = self.spawn('mmgen-tool',['--bob','getbalance','minconf={}'.format(confs)])
		for k in ('mmgen','nonmm','total'):
			t.expect(r'\n\S+:\s+{} {c}\s+{} {c}\s+{} {c}'.format(*bals[k],c=g.coin),regex=True)
		t.read()
		return t

	def bob_0conf0_getbalance(self): return self.bob_getbalance(rtBals_gb['0conf0'],confs=0)
	def bob_0conf1_getbalance(self): return self.bob_getbalance(rtBals_gb['0conf1'],confs=1)
	def bob_1conf1_getbalance(self): return self.bob_getbalance(rtBals_gb['1conf1'],confs=1)
	def bob_1conf2_getbalance(self): return self.bob_getbalance(rtBals_gb['1conf2'],confs=2)

	def bob_alice_bal(self):
		t = self.spawn('mmgen-regtest',['get_balances'])
		t.expect('Switching')
		ret = t.expect_getend("Bob's balance:").strip()
		cmp_or_die(rtBals[4],ret)
		ret = t.expect_getend("Alice's balance:").strip()
		cmp_or_die(rtBals[5],ret)
		ret = t.expect_getend("Total balance:").strip()
		cmp_or_die(rtBals[6],ret)
		return t

	def user_txsend_status(self,user,tx_file,exp1='',exp2='',extra_args=[],bogus_send=False):
		os.environ['MMGEN_BOGUS_SEND'] = ('','1')[bool(bogus_send)]
		t = self.spawn('mmgen-txsend',['-d',self.tmpdir,'--'+user,'--status'] + extra_args + [tx_file])
		os.environ['MMGEN_BOGUS_SEND'] = '1'
		if exp1: t.expect(exp1)
		if exp2: t.expect(exp2)
		return t

	def user_txdo(  self, user, fee, outputs_cl, outputs_list,
					extra_args   = [],
					wf           = None,
					do_label     = False,
					bad_locktime = False,
					full_tx_view = False,
					menu         = ['M'],
					bogus_send   = False):
		os.environ['MMGEN_BOGUS_SEND'] = ('','1')[bool(bogus_send)]
		t = self.spawn('mmgen-txdo',
			['-d',self.tmpdir,'-B','--'+user] +
			(['--tx-fee='+fee] if fee else []) +
			extra_args + ([],[wf])[bool(wf)] + outputs_cl)
		os.environ['MMGEN_BOGUS_SEND'] = '1'

		self.txcreate_ui_common(t,
								caller          = 'txdo',
								menu            = menu,
								inputs          = outputs_list,
								file_desc       = 'Signed transaction',
								interactive_fee = (tx_fee,'')[bool(fee)],
								add_comment     = tx_label_jp,
								view            = 't',save=True)

		t.passphrase('MMGen wallet',rt_pw)
		t.written_to_file('Signed transaction')
		self._do_confirm_send(t)
		s,exit_val = (('Transaction sent',0),("can't be included",1))[bad_locktime]
		t.expect(s)
		t.req_exit_val = exit_val
		return t

	def bob_split1(self):
		sid = self._user_sid('bob')
		outputs_cl = [sid+':C:1,100', sid+':L:2,200',sid+':'+rtBobOp3]
		return self.user_txdo('bob',rtFee[0],outputs_cl,'1',do_label=True,full_tx_view=True)

	def get_addr_from_addrlist(self,user,sid,mmtype,idx,addr_range='1-5'):
		id_str = { 'L':'', 'S':'-S', 'C':'-C', 'B':'-B' }[mmtype]
		ext = '{}{}{}[{}]{x}.testnet.addrs'.format(
			sid,self.altcoin_pfx,id_str,addr_range,x='-α' if g.debug_utf8 else '')
		addrfile = get_file_with_ext(self._user_dir(user),ext,no_dot=True)
		psave = g.proto
		g.proto = CoinProtocol(g.coin,True)
		if hasattr(g.proto,'bech32_hrp_rt'):
			g.proto.bech32_hrp = g.proto.bech32_hrp_rt
		silence()
		addr = AddrList(addrfile).data[idx].addr
		end_silence()
		g.proto = psave
		return addr

	def _create_tx_outputs(self,user,data):
		sid = self._user_sid(user)
		return [self.get_addr_from_addrlist(user,sid,mmtype,idx-1)+amt_str for mmtype,idx,amt_str in data]

	def bob_rbf_1output_create(self):
		out_addr = self._create_tx_outputs('alice',(('B',5,''),))
		t = self.spawn('mmgen-txcreate',['-d',self.tr.trash_dir,'-B','--bob','--rbf'] + out_addr)
		return self.txcreate_ui_common(t,menu=[],inputs='3',interactive_fee='3s') # out amt: 199.99999343

	def bob_rbf_1output_bump(self):
		ext = '9343,3]{x}.testnet.rawtx'.format(x='-α' if g.debug_utf8 else '')
		txfile = get_file_with_ext(self.tr.trash_dir,ext,delete=False,no_dot=True)
		return self.user_txbump('bob',self.tr.trash_dir,txfile,'8s',has_label=False,signed_tx=False)

	def bob_rbf_send(self):
		outputs_cl = self._create_tx_outputs('alice',(('L',1,',60'),('C',1,',40'))) # alice_sid:L:1, alice_sid:C:1
		outputs_cl += [self._user_sid('bob')+':'+rtBobOp3]
		return self.user_txdo('bob',rtFee[1],outputs_cl,'3',
					extra_args=([],['--rbf'])[g.proto.cap('rbf')])

	def bob_send_non_mmgen(self):
		outputs_cl = self._create_tx_outputs('alice',(
			(('L','S')[g.proto.cap('segwit')],2,',10'),
			(('L','S')[g.proto.cap('segwit')],3,'')
		)) # alice_sid:S:2, alice_sid:S:3
		keyfile = joinpath(self.tmpdir,'non-mmgen.keys')
		return self.user_txdo('bob',rtFee[3],outputs_cl,'1,4-10',
			extra_args=['--keys-from-file='+keyfile,'--vsize-adj=1.02'])

	def alice_send_estimatefee(self):
		outputs_cl = self._create_tx_outputs('bob',(('L',1,''),)) # bob_sid:L:1
		return self.user_txdo('alice',None,outputs_cl,'1') # fee=None

	def user_txbump(self,user,outdir,txfile,fee,add_args=[],has_label=True,signed_tx=True):
		if not g.proto.cap('rbf'):
			msg('Skipping RBF'); return 'skip'
		os.environ['MMGEN_BOGUS_SEND'] = ''
		t = self.spawn('mmgen-txbump',
			['-d',outdir,'--'+user,'--tx-fee='+fee,'--output-to-reduce=c'] + add_args + [txfile])
		os.environ['MMGEN_BOGUS_SEND'] = '1'
		t.expect('OK? (Y/n): ','y') # output OK?
		t.expect('OK? (Y/n): ','y') # fee OK?
		t.do_comment(False,has_label=has_label)
		if signed_tx:
			t.passphrase('MMGen wallet',rt_pw)
			t.written_to_file('Signed transaction')
			self.txsend_ui_common(t,caller='txdo',bogus_send=False,file_desc='Signed transaction')
		else:
			t.expect('Save transaction? (y/N): ','y')
			t.written_to_file('Transaction')
		t.read()
		return t

	def bob_rbf_bump(self):
		ext = ',{}]{x}.testnet.sigtx'.format(rtFee[1][:-1],x='-α' if g.debug_utf8 else '')
		txfile = self.get_file_with_ext(ext,delete=False,no_dot=True)
		return self.user_txbump('bob',self.tmpdir,txfile,rtFee[2],add_args=['--send'])

	def generate(self,coin=None,num_blocks=1):
		int(num_blocks)
		if coin: opt.coin = coin
		t = self.spawn('mmgen-regtest',['generate',str(num_blocks)])
		t.expect('Mined {} block'.format(num_blocks))
		return t

	def _get_mempool(self):
		disable_debug()
		ret = self.spawn('mmgen-regtest',['show_mempool']).read()
		restore_debug()
		self.mempool = literal_eval(ret.split('\n')[0]) # allow for extra output by handler at end
		return self.mempool

	def get_mempool1(self):
		mp = self._get_mempool()
		if len(mp) != 1:
			rdie(2,'Mempool has more or less than one TX!')
		self.write_to_tmpfile('rbf_txid',mp[0]+'\n')
		return 'ok'

	def bob_rbf_status(self,fee,exp1,exp2='',skip_bch=False):
		if skip_bch and not g.proto.cap('rbf'):
			msg('skipping test {} for BCH'.format(self.test_name))
			return 'skip'
		ext = ',{}]{x}.testnet.sigtx'.format(fee[:-1],x='-α' if g.debug_utf8 else '')
		txfile = self.get_file_with_ext(ext,delete=False,no_dot=True)
		return self.user_txsend_status('bob',txfile,exp1,exp2)

	def bob_rbf_status1(self):
		return self.bob_rbf_status(rtFee[1],'in mempool, replaceable',skip_bch=True)

	def get_mempool2(self):
		if not g.proto.cap('rbf'):
			msg('Skipping post-RBF mempool check'); return 'skip'
		mp = self._get_mempool()
		if len(mp) != 1:
			rdie(2,'Mempool has more or less than one TX!')
		chk = self.read_from_tmpfile('rbf_txid')
		if chk.strip() == mp[0]:
			rdie(2,'TX in mempool has not changed!  RBF bump failed')
		return 'ok'

	def bob_rbf_status2(self):
		if not g.proto.cap('rbf'): return 'skip'
		return self.bob_rbf_status(rtFee[1],
			'Transaction has been replaced','{} in mempool'.format(self.mempool[0]),
			skip_bch=True)

	def bob_rbf_status3(self):
		if not g.proto.cap('rbf'): return 'skip'
		return self.bob_rbf_status(rtFee[2],'status: in mempool, replaceable',skip_bch=True)

	def bob_rbf_status4(self):
		if not g.proto.cap('rbf'): return 'skip'
		return self.bob_rbf_status(rtFee[1],
			'Replacement transaction has 1 confirmation',
			'Replacing transactions:\n  {}'.format(self.mempool[0]),
			skip_bch=True)

	def bob_rbf_status5(self):
		if not g.proto.cap('rbf'): return 'skip'
		return self.bob_rbf_status(rtFee[2],'Transaction has 1 confirmation',skip_bch=True)

	def bob_rbf_status6(self):
		if not g.proto.cap('rbf'): return 'skip'
		return self.bob_rbf_status(rtFee[1],
			'Replacement transaction has 2 confirmations',
			'Replacing transactions:\n  {}'.format(self.mempool[0]),
			skip_bch=True)

	@staticmethod
	def _gen_pairs(n):
		disable_debug()
		ret = [subprocess.check_output(
						['python3',joinpath('cmds','mmgen-tool'),'--testnet=1'] +
						(['--type=compressed'],[])[i==0] +
						['-r0','randpair']
					).decode().split() for i in range(n)]
		restore_debug()
		return ret

	def bob_pre_import(self):
		pairs = self._gen_pairs(5)
		self.write_to_tmpfile('non-mmgen.keys','\n'.join([a[0] for a in pairs])+'\n')
		self.write_to_tmpfile('non-mmgen.addrs','\n'.join([a[1] for a in pairs])+'\n')
		return self.user_txdo('bob',rtFee[4],[pairs[0][1]],'3')

	def user_import(self,user,args):
		t = self.spawn('mmgen-addrimport',['--quiet','--'+user]+args)
		if g.debug:
			t.expect("Type uppercase 'YES' to confirm: ",'YES\n')
		t.expect('Importing')
		t.expect('OK')
		return t

	def bob_import_addr(self):
		addr = self.read_from_tmpfile('non-mmgen.addrs').split()[0]
		return self.user_import('bob',['--rescan','--address='+addr])

	def bob_import_list(self):
		addrfile = joinpath(self.tmpdir,'non-mmgen.addrs')
		return self.user_import('bob',['--addrlist',addrfile])

	def bob_split2(self):
		addrs = self.read_from_tmpfile('non-mmgen.addrs').split()
		amts = (1.12345678,2.87654321,3.33443344,4.00990099,5.43214321)
		outputs1 = list(map('{},{}'.format,addrs,amts))
		sid = self._user_sid('bob')
		l1,l2 = (':S',':B') if 'B' in g.proto.mmtypes else (':S',':S') if g.proto.cap('segwit') else (':L',':L')
		outputs2 = [sid+':C:2,6.333', sid+':L:3,6.667',sid+l1+':4,0.123',sid+l2+':5']
		return self.user_txdo('bob',rtFee[5],outputs1+outputs2,'1-2')

	def user_add_label(self,user,addr,label):
		t = self.spawn('mmgen-tool',['--'+user,'add_label',addr,label])
		t.expect('Added label.*in tracking wallet',regex=True)
		return t

	def user_remove_label(self,user,addr):
		t = self.spawn('mmgen-tool',['--'+user,'remove_label',addr])
		t.expect('Removed label.*in tracking wallet',regex=True)
		return t

	def bob_add_label(self):
		sid = self._user_sid('bob')
		return self.user_add_label('bob',sid+':C:1',tw_label_lat_cyr_gr)

	def alice_add_label1(self):
		sid = self._user_sid('alice')
		return self.user_add_label('alice',sid+':C:1','Original Label - 月へ')

	def alice_add_label2(self):
		sid = self._user_sid('alice')
		return self.user_add_label('alice',sid+':C:1','Replacement Label')

	def alice_add_label_coinaddr(self):
		mmid = self._user_sid('alice') + (':S:1',':L:1')[g.coin=='BCH']
		t = self.spawn('mmgen-tool',['--alice','listaddress',mmid],no_msg=True)
		btcaddr = [i for i in t.read().splitlines() if i.lstrip()[0:len(mmid)] == mmid][0].split()[1]
		return self.user_add_label('alice',btcaddr,'Label added using coin address')

	def user_chk_label(self,user,addr,label):
		t = self.spawn('mmgen-tool',['--'+user,'listaddresses','all_labels=1'])
		t.expect(r'{}\s+\S{{30}}\S+\s+{}\s+'.format(addr,label),regex=True)
		return t

	def alice_chk_label_coinaddr(self):
		mmid = self._user_sid('alice') + (':S:1',':L:1')[g.coin=='BCH']
		return self.user_chk_label('alice',mmid,'Label added using coin address')

	def alice_add_label_badaddr(self,addr,reply):
		t = self.spawn('mmgen-tool',['--alice','add_label',addr,'(none)'])
		t.expect(reply,regex=True)
		return t

	def alice_add_label_badaddr1(self):
		return self.alice_add_label_badaddr(rt_pw,'Invalid coin address for this chain: ')

	def alice_add_label_badaddr2(self):
		addr = g.proto.pubhash2addr('00'*20,False) # mainnet zero address
		return self.alice_add_label_badaddr(addr,'Invalid coin address for this chain: '+addr)

	def alice_add_label_badaddr3(self):
		addr = self._user_sid('alice') + ':C:123'
		return self.alice_add_label_badaddr(addr,
			"MMGen address '{}' not found in tracking wallet".format(addr))

	def alice_add_label_badaddr4(self):
		addr = CoinProtocol(g.coin,True).pubhash2addr('00'*20,False) # testnet zero address
		return self.alice_add_label_badaddr(addr,
			"Address '{}' not found in tracking wallet".format(addr))

	def alice_bal_rpcfail(self):
		addr = self._user_sid('alice') + ':C:2'
		os.environ['MMGEN_RPC_FAIL_ON_COMMAND'] = 'listunspent'
		t = self.spawn('mmgen-tool',['--alice','getbalance'])
		os.environ['MMGEN_RPC_FAIL_ON_COMMAND'] = ''
		t.expect('Method not found')
		t.read()
		t.req_exit_val = 3
		return t

	def alice_remove_label1(self):
		sid = self._user_sid('alice')
		mmid = sid + (':S:3',':L:3')[g.coin=='BCH']
		return self.user_remove_label('alice',mmid)

	def alice_chk_label1(self):
		sid = self._user_sid('alice')
		return self.user_chk_label('alice',sid+':C:1','Original Label - 月へ')

	def alice_chk_label2(self):
		sid = self._user_sid('alice')
		return self.user_chk_label('alice',sid+':C:1','Replacement Label')

	def alice_edit_label1(self): return self.user_edit_label('alice','4',tw_label_lat_cyr_gr)
	def alice_edit_label2(self): return self.user_edit_label('alice','3',tw_label_zh)

	def alice_chk_label3(self):
		sid = self._user_sid('alice')
		mmid = sid + (':S:3',':L:3')[g.coin=='BCH']
		return self.user_chk_label('alice',mmid,tw_label_lat_cyr_gr)

	def alice_chk_label4(self):
		sid = self._user_sid('alice')
		mmid = sid + (':S:3',':L:3')[g.coin=='BCH']
		return self.user_chk_label('alice',mmid,'-')

	def user_edit_label(self,user,output,label):
		t = self.spawn('mmgen-txcreate',['-B','--'+user,'-i'])
		t.expect(r'add \[l\]abel:.','M',regex=True)
		t.expect(r'add \[l\]abel:.','l',regex=True)
		t.expect(r"Enter unspent.*return to main menu\):.",output+'\n',regex=True)
		t.expect(r"Enter label text.*return to main menu\):.",label+'\n',regex=True)
		t.expect(r'\[q\]uit view, .*?:.','q',regex=True)
		return t

	def stop(self):
		if opt.no_daemon_stop:
			self.spawn('',msg_only=True)
			msg_r('(leaving daemon running by user request)')
			return 'ok'
		else:
			return self.spawn('mmgen-regtest',['stop'])
