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
ts_main.py: Basic operations tests for the test.py test suite
"""

from mmgen.globalvars import g
from mmgen.opts import opt
from test.common import *
from test.test_py_d.common import *
from test.test_py_d.ts_base import *
from test.test_py_d.ts_shared import *

def make_brainwallet_file(fn):
	# Print random words with random whitespace in between
	wl = rwords.split()
	nwords,ws_list,max_spaces = 10,'    \n',5
	def rand_ws_seq():
		nchars = getrandnum(1) % max_spaces + 1
		return ''.join([ws_list[getrandnum_range(1,200) % len(ws_list)] for i in range(nchars)])
	rand_pairs = [wl[getrandnum_range(1,200) % len(wl)] + rand_ws_seq() for i in range(nwords)]
	d = ''.join(rand_pairs).rstrip() + '\n'
	if opt.verbose: msg_r('Brainwallet password:\n{}'.format(cyan(d)))
	write_data_to_file(fn,d,'brainwallet password',quiet=True,ignore_opt_outdir=True)

def verify_checksum_or_exit(checksum,chk):
	if checksum != chk:
		raise TestSuiteFatalException('Checksum error: {}'.format(chk))
	vmsg(green('Checksums match: ') + cyan(chk))

addrs_per_wallet = 8

# 100 words chosen randomly from here:
#   https://github.com/bitcoin/bips/pull/432/files/6332230d63149a950d05db78964a03bfd344e6b0
rwords = """
	алфавит алый амнезия амфора артист баян белый биатлон брат бульвар веревка вернуть весть возраст
	восток горло горный десяток дятел ежевика жест жизнь жрать заговор здание зона изделие итог кабина
	кавалер каждый канал керосин класс клятва князь кривой крыша крючок кузнец кукла ландшафт мальчик
	масса масштаб матрос мрак муравей мычать негодяй носок ночной нрав оборот оружие открытие оттенок
	палуба пароход период пехота печать письмо позор полтора понятие поцелуй почему приступ пруд пятно
	ранее режим речь роса рынок рябой седой сердце сквозь смех снимок сойти соперник спичка стон
	сувенир сугроб суть сцена театр тираж толк удивить улыбка фирма читатель эстония эстрада юность
	"""

class TestSuiteMain(TestSuiteBase,TestSuiteShared):
	'basic operations with emulated tracking wallet'
	tmpdir_nums = [1,2,3,4,5,14,15,16,20,21]
	networks = ('btc','btc_tn','ltc','ltc_tn','bch','bch_tn')
	passthru_opts = ('coin','testnet')
	segwit_opts_ok = True
	cmd_group = (
		('walletgen_dfl_wallet', (15,'wallet generation (default wallet)',[[[],15]])),
		('subwalletgen_dfl_wallet', (15,'subwallet generation (default wallet)',[[[pwfile],15]])),
		('export_seed_dfl_wallet',(15,'seed export to mmseed format (default wallet)',[[[pwfile],15]])),
		('addrgen_dfl_wallet',(15,'address generation (default wallet)',[[[pwfile],15]])),
		('txcreate_dfl_wallet',(15,'transaction creation (default wallet)',[[['addrs'],15]])),
		('txsign_dfl_wallet',(15,'transaction signing (default wallet)',[[['rawtx',pwfile],15]])),
		('passchg_dfl_wallet',(16,'password, label and hash preset change (default wallet)',[[[pwfile],15]])),
		('walletchk_newpass_dfl_wallet',(16,'wallet check with new pw, label and hash preset',[[[pwfile],16]])),
		('delete_dfl_wallet',(15,'delete default wallet',[[[pwfile],15]])),

		('walletgen',       (1,'wallet generation',        [[['del_dw_run'],15]])),
		('subwalletgen',    (1,'subwallet generation',     [[['mmdat'],1]])),
		('subwalletgen_mnemonic',(1,'subwallet generation (to mnemonic format)',[[['mmdat'],1]])),
#		('walletchk',       (1,'wallet check',             [[['mmdat'],1]])),
		('passchg',         (5,'password, label and hash preset change',[[['mmdat',pwfile],1]])),
		('passchg_keeplabel',(5,'password, label and hash preset change (keep label)',[[['mmdat',pwfile],1]])),
		('passchg_usrlabel',(5,'password, label and hash preset change (interactive label)',[[['mmdat',pwfile],1]])),
		('walletchk_newpass',(5,'wallet check with new pw, label and hash preset',[[['mmdat',pwfile],5]])),
		('addrgen',         (1,'address generation',       [[['mmdat',pwfile],1]])),
		('txcreate',        (1,'transaction creation',     [[['addrs'],1]])),
		('txbump',          (1,'transaction fee bumping (no send)',[[['rawtx'],1]])),
		('txsign',          (1,'transaction signing',      [[['mmdat','rawtx',pwfile,'txbump'],1]])),
		('txsend',          (1,'transaction sending',      [[['sigtx'],1]])),
		# txdo must go after txsign
		('txdo',            (1,'online transaction',       [[['sigtx','mmdat'],1]])),

		('export_seed',     (1,'seed export to mmseed format',   [[['mmdat'],1]])),
		('export_hex',      (1,'seed export to hexadecimal format',  [[['mmdat'],1]])),
		('export_mnemonic', (1,'seed export to mmwords format',  [[['mmdat'],1]])),
		('export_bip39',    (1,'seed export to bip39 format',    [[['mmdat'],1]])),
		('export_incog',    (1,'seed export to mmincog format',  [[['mmdat'],1]])),
		('export_incog_hex',(1,'seed export to mmincog hex format', [[['mmdat'],1]])),
		('export_incog_hidden',(1,'seed export to hidden mmincog format', [[['mmdat'],1]])),

		('addrgen_seed',    (1,'address generation from mmseed file', [[['mmseed','addrs'],1]])),
		('addrgen_hex',     (1,'address generation from mmhex file', [[['mmhex','addrs'],1]])),
		('addrgen_mnemonic',(1,'address generation from mmwords file',[[['mmwords','addrs'],1]])),
		('addrgen_incog',   (1,'address generation from mmincog file',[[['mmincog','addrs'],1]])),
		('addrgen_incog_hex',(1,'address generation from mmincog hex file',[[['mmincox','addrs'],1]])),
		('addrgen_incog_hidden',(1,'address generation from hidden mmincog file', [[[hincog_fn,'addrs'],1]])),

		('keyaddrgen',    (1,'key-address file generation', [[['mmdat',pwfile],1]])),
		('txsign_keyaddr',(1,'transaction signing with key-address file', [[['akeys.mmenc','rawtx'],1]])),

		('txcreate_ni',   (1,'transaction creation (non-interactive)',     [[['addrs'],1]])),

		('walletgen2',(2,'wallet generation (2), 128-bit seed',     [[['del_dw_run'],15]])),
		('addrgen2',  (2,'address generation (2)',    [[['mmdat'],2]])),
		('txcreate2', (2,'transaction creation (2)',  [[['addrs'],2]])),
		('txsign2',   (2,'transaction signing, two transactions',[[['mmdat','rawtx'],1],[['mmdat','rawtx'],2]])),
		('export_mnemonic2', (2,'seed export to mmwords format (2)',[[['mmdat'],2]])),

		('walletgen3',(3,'wallet generation (3)',                  [[['del_dw_run'],15]])),
		('addrgen3',  (3,'address generation (3)',                 [[['mmdat'],3]])),
		('txcreate3', (3,'tx creation with inputs and outputs from two wallets', [[['addrs'],1],[['addrs'],3]])),
		('txsign3',   (3,'tx signing with inputs and outputs from two wallets',[[['mmdat'],1],[['mmdat','rawtx'],3]])),

		('walletgen14', (14,'wallet generation (14)',        [[['del_dw_run'],15]],14)),
		('addrgen14',   (14,'address generation (14)',        [[['mmdat'],14]])),
		('keyaddrgen14',(14,'key-address file generation (14)', [[['mmdat'],14]],14)),
		('walletgen4',(4,'wallet generation (4) (brainwallet)',    [[['del_dw_run'],15]])),
		('addrgen4',  (4,'address generation (4)',                 [[['mmdat'],4]])),
		('txcreate4', (4,'tx creation with inputs and outputs from four seed sources, key-address file and non-MMGen inputs and outputs', [[['addrs'],1],[['addrs'],2],[['addrs'],3],[['addrs'],4],[['addrs','akeys.mmenc'],14]])),
		('txsign4',   (4,'tx signing with inputs and outputs from incog file, mnemonic file, wallet, brainwallet, key-address file and non-MMGen inputs and outputs', [[['mmincog'],1],[['mmwords'],2],[['mmdat'],3],[['mmbrain','rawtx'],4],[['akeys.mmenc'],14]])),
		('txdo4', (4,'tx creation,signing and sending with inputs and outputs from four seed sources, key-address file and non-MMGen inputs and outputs', [[['addrs'],1],[['addrs'],2],[['addrs'],3],[['addrs'],4],[['addrs','akeys.mmenc'],14],[['mmincog'],1],[['mmwords'],2],[['mmdat'],3],[['mmbrain','rawtx'],4],[['akeys.mmenc'],14]])), # must go after txsign4
		('txbump4', (4,'tx fee bump + send with inputs and outputs from four seed sources, key-address file and non-MMGen inputs and outputs', [[['akeys.mmenc'],14],[['mmincog'],1],[['mmwords'],2],[['mmdat'],3],[['akeys.mmenc'],14],[['mmbrain','sigtx','mmdat','txdo'],4]])), # must go after txsign4

		('walletgen5',(20,'wallet generation (5)',                   [[['del_dw_run'],15]],20)),
		('addrgen5',  (20,'address generation (5)',                  [[['mmdat'],20]])),
		('txcreate5', (20,'transaction creation with bad vsize (5)', [[['addrs'],20]])),
		('txsign5',   (20,'transaction signing with bad vsize',      [[['mmdat','rawtx'],20]])),
		('walletgen6',(21,'wallet generation (6)',                   [[['del_dw_run'],15]],21)),
		('addrgen6',  (21,'address generation (6)',                  [[['mmdat'],21]])),
		('txcreate6', (21,'transaction creation with corrected vsize (6)', [[['addrs'],21]])),
		('txsign6',   (21,'transaction signing with corrected vsize',      [[['mmdat','rawtx'],21]])),
	)

	def __init__(self,trunner,cfgs,spawn):
		rpc_init()
		self.lbl_id = ('account','label')['label_api' in g.rpch.caps]
		if g.coin in ('BTC','BCH','LTC'):
			self.tx_fee     = {'btc':'0.0001','bch':'0.001','ltc':'0.01'}[g.coin.lower()]
			self.txbump_fee = {'btc':'123s','bch':'567s','ltc':'12345s'}[g.coin.lower()]
		return TestSuiteBase.__init__(self,trunner,cfgs,spawn)

	def _get_addrfile_checksum(self,display=False):
		addrfile = self.get_file_with_ext('addrs')
		silence()
		from mmgen.addr import AddrList
		chk = AddrList(addrfile).chksum
		if opt.verbose and display: msg('Checksum: {}'.format(cyan(chk)))
		end_silence()
		return chk

	def walletgen_dfl_wallet(self,seed_len=None):
		return self.walletgen(seed_len=seed_len,gen_dfl_wallet=True)

	def subwalletgen_dfl_wallet(self,pf):
		return self.subwalletgen(wf='default')

	def export_seed_dfl_wallet(self,pf,desc='seed data',out_fmt='seed'):
		return self.export_seed(wf=None,desc=desc,out_fmt=out_fmt,pf=pf)

	def addrgen_dfl_wallet(self,pf=None,check_ref=False):
		return self.addrgen(wf=None,pf=pf,check_ref=check_ref)

	def txcreate_dfl_wallet(self,addrfile):
		return self.txcreate_common(sources=['15'])

	def txsign_dfl_wallet(self,txfile,pf='',save=True,has_label=False):
		return self.txsign(txfile,wf=None,pf=pf,save=save,has_label=has_label)

	def passchg_dfl_wallet(self,pf):
		return self.passchg(wf=None,pf=pf)

	def walletchk_newpass_dfl_wallet(self,pf):
		return self.walletchk_newpass(wf=None,pf=pf)

	def delete_dfl_wallet(self,pf):
		self.write_to_tmpfile('del_dw_run',b'',binary=True)
		if opt.no_dw_delete: return 'skip'
		for wf in [f for f in os.listdir(g.data_dir) if f[-6:]=='.mmdat']:
			os.unlink(joinpath(g.data_dir,wf))
		self.spawn('',msg_only=True)
		self.have_dfl_wallet = False
		return 'ok'

	def walletgen(self,del_dw_run='dummy',seed_len=None,gen_dfl_wallet=False):
		self.write_to_tmpfile(pwfile,self.wpasswd+'\n')
		args = ['-p1']
		if not gen_dfl_wallet: args += ['-d',self.tmpdir]
		if seed_len: args += ['-l',str(seed_len)]
		t = self.spawn('mmgen-walletgen', args + [self.usr_rand_arg])
		t.license()
		t.usr_rand(self.usr_rand_chars)
		t.expect('Generating')
		t.passphrase_new('new MMGen wallet',self.wpasswd)
		t.label()
		if not self.have_dfl_wallet and gen_dfl_wallet:
			t.expect('move it to the data directory? (Y/n): ','y')
			self.have_dfl_wallet = True
		t.written_to_file('MMGen wallet')
		return t

	def subwalletgen(self,wf):
		args = [self.usr_rand_arg,'-p1','-d',self.tr.trash_dir,'-L','Label']
		if wf != 'default': args += [wf]
		t = self.spawn('mmgen-subwalletgen', args + ['10s'])
		t.license()
		t.passphrase('MMGen wallet',self.cfgs['1']['wpasswd'])
		t.expect('Generating subseed 10S')
		t.passphrase_new('new MMGen wallet','foo')
		t.usr_rand(self.usr_rand_chars)
		fn = t.written_to_file('MMGen wallet')
		assert fn[-6:] == '.mmdat','incorrect file extension: {}'.format(fn[-6:])
		return t

	def subwalletgen_mnemonic(self,wf):
		args = [self.usr_rand_arg,'-p1','-d',self.tr.trash_dir,'-o','words',wf,'3L']
		t = self.spawn('mmgen-subwalletgen', args)
		t.license()
		t.passphrase('MMGen wallet',self.cfgs['1']['wpasswd'])
		t.expect('Generating subseed 3L')
		fn = t.written_to_file('MMGen native mnemonic data')
		assert fn[-8:] == '.mmwords','incorrect file extension: {}'.format(fn[-8:])
		return t

	def passchg(self,wf,pf,label_action='cmdline'):
		silence()
		self.write_to_tmpfile(pwfile,get_data_from_file(pf))
		end_silence()
		add_args = {'cmdline': ['-d',self.tmpdir,'-L','Changed label (UTF-8) α'],
					'keep':    ['-d',self.tr.trash_dir,'--keep-label'],
					'user':    ['-d',self.tr.trash_dir]
					}[label_action]
		t = self.spawn('mmgen-passchg', add_args + [self.usr_rand_arg, '-p2'] + ([],[wf])[bool(wf)])
		t.license()
		t.passphrase('MMGen wallet',self.cfgs['1']['wpasswd'],pwtype='old')
		t.expect_getend('Hash preset changed to ')
		t.passphrase('MMGen wallet',self.wpasswd,pwtype='new') # reuse passphrase?
		t.expect('Repeat passphrase: ',self.wpasswd+'\n')
		t.usr_rand(self.usr_rand_chars)
		if label_action == 'user':
			t.expect('Enter a wallet label.*: ','Interactive Label (UTF-8) α\n',regex=True)
		t.expect_getend(('Label changed to ','Reusing label ')[label_action=='keep'])
#		t.expect_getend('Key ID changed: ')
		if not wf:
			t.expect("Type uppercase 'YES' to confirm: ",'YES\n')
			t.written_to_file('New wallet')
			t.expect('Securely deleting old wallet')
#			t.expect('Okay to WIPE 1 regular file ? (Yes/No)','Yes\n')
			t.expect('Wallet passphrase has changed')
			t.expect_getend('has been changed to ')
		else:
			t.written_to_file('MMGen wallet')
		return t

	def passchg_keeplabel(self,wf,pf):
		return self.passchg(wf,pf,label_action='keep')

	def passchg_usrlabel(self,wf,pf):
		return self.passchg(wf,pf,label_action='user')

	def walletchk_newpass(self,wf,pf):
		return self.walletchk(wf,pf,pw=True)

	def _write_fake_data_to_file(self,d):
		unspent_data_file = joinpath(self.tmpdir,'unspent.json')
		write_data_to_file(unspent_data_file,d,'Unspent outputs',quiet=True,ignore_opt_outdir=True)
		os.environ['MMGEN_BOGUS_WALLET_DATA'] = unspent_data_file
		bwd_msg = 'MMGEN_BOGUS_WALLET_DATA={}'.format(unspent_data_file)
		if opt.print_cmdline: msg(bwd_msg)
		if opt.log: self.tr.log_fd.write(bwd_msg + ' ')
		if opt.verbose or opt.exact_output:
			sys.stderr.write("Fake transaction wallet data written to file {!r}\n".format(unspent_data_file))

	def _create_fake_unspent_entry(self,coinaddr,al_id=None,idx=None,lbl=None,non_mmgen=False,segwit=False):
		if 'S' not in g.proto.mmtypes: segwit = False
		if lbl: lbl = ' ' + lbl
		k = coinaddr.addr_fmt
		if not segwit and k == 'p2sh': k = 'p2pkh'
		s_beg,s_end = { 'p2pkh':  ('76a914','88ac'),
						'p2sh':   ('a914','87'),
						'bech32': (g.proto.witness_vernum_hex + '14','') }[k]
		amt1,amt2 = {'btc':(10,40),'bch':(10,40),'ltc':(1000,4000)}[g.coin.lower()]
		ret = {
			self.lbl_id: '{}:{}'.format(g.proto.base_coin.lower(),coinaddr) if non_mmgen \
				else ('{}:{}{}'.format(al_id,idx,lbl)),
			'vout': int(getrandnum(4) % 8),
			'txid': os.urandom(32).hex(),
			'amount': g.proto.coin_amt('{}.{}'.format(amt1 + getrandnum(4) % amt2, getrandnum(4) % 100000000)),
			'address': coinaddr,
			'spendable': False,
			'scriptPubKey': '{}{}{}'.format(s_beg,coinaddr.hex,s_end),
			'confirmations': getrandnum(3) // 2 # max: 8388608 (7 digits)
		}
		return ret

	def _create_fake_unspent_data(self,adata,tx_data,non_mmgen_input='',non_mmgen_input_compressed=True):

		out = []
		for d in tx_data.values():
			al = adata.addrlist(al_id=d['al_id'])
			for n,(idx,coinaddr) in enumerate(al.addrpairs()):
				lbl = get_label(do_shuffle=True)
				out.append(self._create_fake_unspent_entry(coinaddr,d['al_id'],idx,lbl,segwit=d['segwit']))
				if n == 0:  # create a duplicate address. This means addrs_per_wallet += 1
					out.append(self._create_fake_unspent_entry(coinaddr,d['al_id'],idx,lbl,segwit=d['segwit']))

		if non_mmgen_input:
			from mmgen.obj import PrivKey
			privkey = PrivKey(os.urandom(32),compressed=non_mmgen_input_compressed,pubkey_type='std')
			from mmgen.addr import AddrGenerator,KeyGenerator
			rand_coinaddr = AddrGenerator('p2pkh').to_addr(KeyGenerator('std').to_pubhex(privkey))
			of = joinpath(self.cfgs[non_mmgen_input]['tmpdir'],non_mmgen_fn)
			write_data_to_file(of,  privkey.wif+'\n','compressed {} key'.format(g.proto.name),
									quiet=True,ignore_opt_outdir=True)
			out.append(self._create_fake_unspent_entry(rand_coinaddr,non_mmgen=True,segwit=False))

		return out

	def _create_tx_data(self,sources,addrs_per_wallet=addrs_per_wallet):
		from mmgen.addr import AddrData,AddrList
		from mmgen.obj import AddrIdxList
		tx_data,ad = {},AddrData()
		for s in sources:
			afile = get_file_with_ext(self.cfgs[s]['tmpdir'],'addrs')
			al = AddrList(afile)
			ad.add(al)
			aix = AddrIdxList(fmt_str=self.cfgs[s]['addr_idx_list'])
			if len(aix) != addrs_per_wallet:
				raise TestSuiteFatalException(
					'Address index list length != {}: {}'.format(addrs_per_wallet,repr(aix)))
			tx_data[s] = {
				'addrfile': afile,
				'chk': al.chksum,
				'al_id': al.al_id,
				'addr_idxs': aix[-2:],
				'segwit': self.cfgs[s]['segwit']
			}
		return ad,tx_data

	def _make_txcreate_cmdline(self,tx_data):
		from mmgen.obj import PrivKey
		privkey = PrivKey(os.urandom(32),compressed=True,pubkey_type='std')
		t = ('p2pkh','segwit')['S' in g.proto.mmtypes]
		from mmgen.addr import AddrGenerator,KeyGenerator
		rand_coinaddr = AddrGenerator(t).to_addr(KeyGenerator('std').to_pubhex(privkey))

		# total of two outputs must be < 10 BTC (<1000 LTC)
		mods = {'btc':(6,4),'bch':(6,4),'ltc':(600,400)}[g.coin.lower()]
		for k in self.cfgs:
			self.cfgs[k]['amts'] = [None,None]
			for idx,mod in enumerate(mods):
				self.cfgs[k]['amts'][idx] = '{}.{}'.format(getrandnum(4) % mod, str(getrandnum(4))[:5])

		cmd_args = ['--outdir='+self.tmpdir]
		for num in tx_data:
			s = tx_data[num]
			cmd_args += [
				'{}:{},{}'.format(s['al_id'],s['addr_idxs'][0],self.cfgs[num]['amts'][0]),
			]
			# + one change address and one BTC address
			if num is list(tx_data.keys())[-1]:
				cmd_args += ['{}:{}'.format(s['al_id'],s['addr_idxs'][1])]
				cmd_args += ['{},{}'.format(rand_coinaddr,self.cfgs[num]['amts'][1])]

		return cmd_args + [tx_data[num]['addrfile'] for num in tx_data]

	def txcreate_common(self,
						sources=['1'],
						non_mmgen_input='',
						do_label=False,
						txdo_args=[],
						add_args=[],
						view='n',
						addrs_per_wallet=addrs_per_wallet,
						non_mmgen_input_compressed=True,
						cmdline_inputs=False):

		if opt.verbose or opt.exact_output:
			sys.stderr.write(green('Generating fake tracking wallet info\n'))

		silence()
		ad,tx_data = self._create_tx_data(sources,addrs_per_wallet)
		dfake = self._create_fake_unspent_data(ad,tx_data,non_mmgen_input,non_mmgen_input_compressed)
		self._write_fake_data_to_file(repr(dfake))
		cmd_args = self._make_txcreate_cmdline(tx_data)
		if cmdline_inputs:
			from mmgen.tx import TwLabel
			cmd_args = ['--inputs={},{},{},{},{},{}'.format(
				TwLabel(dfake[0][self.lbl_id]).mmid,dfake[1]['address'],
				TwLabel(dfake[2][self.lbl_id]).mmid,dfake[3]['address'],
				TwLabel(dfake[4][self.lbl_id]).mmid,dfake[5]['address']
				),'--outdir='+self.tr.trash_dir] + cmd_args[1:]
		end_silence()

		if opt.verbose or opt.exact_output: sys.stderr.write('\n')

		t = self.spawn(
			'mmgen-'+('txcreate','txdo')[bool(txdo_args)],
			([],['--rbf'])[g.proto.cap('rbf')] +
			['-f',self.tx_fee,'-B'] + add_args + cmd_args + txdo_args)

		if t.expect([('Get','Transac')[cmdline_inputs],'Unable to connect to \S+'],regex=True) == 1:
			raise TestSuiteException('\n'+t.p.after)

		if cmdline_inputs:
			t.written_to_file('tion')
			return t

		t.license()

		if txdo_args and add_args: # txdo4
			t.do_decrypt_ka_data(hp='1',pw=self.cfgs['14']['kapasswd'])

		for num in tx_data:
			t.expect_getend('ting address data from file ')
			chk=t.expect_getend(r'Checksum for address data .*?: ',regex=True)
			verify_checksum_or_exit(tx_data[num]['chk'],chk)

		# not in tracking wallet warning, (1 + num sources) times
		for num in range(len(tx_data) + 1):
			t.expect('Continue anyway? (y/N): ','y')

		outputs_list = [(addrs_per_wallet+1)*i + 1 for i in range(len(tx_data))]
		if non_mmgen_input: outputs_list.append(len(tx_data)*(addrs_per_wallet+1) + 1)

		self.txcreate_ui_common(t,
					menu=(['M'],['M','D','m','g'])[self.test_name=='txcreate'],
					inputs=' '.join(map(str,outputs_list)),
					add_comment=('',tx_label_lat_cyr_gr)[do_label],
					non_mmgen_inputs=(0,1)[bool(non_mmgen_input and not txdo_args)],
					view=view)

		return t

	def txcreate(self,addrfile):
		return self.txcreate_common(sources=['1'],add_args=['--vsize-adj=1.01'])

	def txbump(self,txfile,prepend_args=[],seed_args=[]):
		if not g.proto.cap('rbf'):
			msg('Skipping RBF'); return 'skip'
		args = prepend_args + ['--quiet','--outdir='+self.tmpdir,txfile] + seed_args
		t = self.spawn('mmgen-txbump',args)
		if seed_args:
			t.do_decrypt_ka_data(hp='1',pw=self.cfgs['14']['kapasswd'])
		t.expect('deduct the fee from (Hit ENTER for the change output): ','1\n')
		# Fee must be > tx_fee + network relay fee (currently 0.00001)
		t.expect('OK? (Y/n): ','\n')
		t.expect('Enter transaction fee: ',self.txbump_fee+'\n')
		t.expect('OK? (Y/n): ','\n')
		if seed_args: # sign and send
			t.do_comment(False,has_label=True)
			for cnum,desc in (('1','incognito data'),('3','MMGen wallet'),('4','MMGen wallet')):
				t.passphrase(desc,self.cfgs[cnum]['wpasswd'])
			self._do_confirm_send(t,quiet=not g.debug,confirm_send=True)
			if g.debug:
				t.written_to_file('Transaction')
		else:
			t.do_comment(False)
			t.expect('Save transaction? (y/N): ','y')
			t.written_to_file('Transaction')
		os.unlink(txfile) # our tx file replaces the original
		cmd = 'touch ' + joinpath(self.tmpdir,'txbump')
		os.system(cmd)
		return t

	def txsend(self,sigfile,bogus_send=True,extra_opts=[]):
		if not bogus_send: os.environ['MMGEN_BOGUS_SEND'] = ''
		t = self.spawn('mmgen-txsend', extra_opts + ['-d',self.tmpdir,sigfile])
		if not bogus_send: os.environ['MMGEN_BOGUS_SEND'] = '1'
		self.txsend_ui_common(t,view='t',add_comment='')
		return t

	def txdo(self,addrfile,wallet):
		t = self.txcreate_common(sources=['1'],txdo_args=[wallet])
		self.txsign_ui_common(t,view='n',do_passwd=True)
		self.txsend_ui_common(t)
		return t

	def _walletconv_export(self,wf,desc,uargs=[],out_fmt='w',pf=None,out_pw=False):
		opts = ['-d',self.tmpdir,'-o',out_fmt] + uargs + \
			([],[wf])[bool(wf)] + ([],['-P',pf])[bool(pf)]
		t = self.spawn('mmgen-walletconv',opts)
		t.license()
		if not pf:
			t.passphrase('MMGen wallet',self.wpasswd)
		if out_pw:
			t.passphrase_new('new '+desc,self.wpasswd)
			t.usr_rand(self.usr_rand_chars)

		if ' '.join(desc.split()[-2:]) == 'incognito data':
			m = 'Generating encryption key from OS random data '
			t.expect(m); t.expect(m)
			incog_id = t.expect_getend('New Incog Wallet ID: ')
			t.expect(m)
		if desc == 'hidden incognito data':
			self.write_to_tmpfile(incog_id_fn,incog_id)
			ret = t.expect(['Create? (Y/n): ',"'YES' to confirm: "])
			if ret == 0:
				t.send('\n')
				t.expect('Enter file size: ',str(hincog_bytes)+'\n')
			else:
				t.send('YES\n')
		if out_fmt == 'w': t.label()
		return t.written_to_file(capfirst(desc),oo=True),t

	def export_seed(self,wf,desc='seed data',out_fmt='seed',pf=None):
		f,t = self._walletconv_export(wf,desc=desc,out_fmt=out_fmt,pf=pf)
		silence()
		msg('{}: {}'.format(capfirst(desc),cyan(get_data_from_file(f,desc))))
		end_silence()
		return t

	def export_hex(self,wf,desc='hexadecimal seed data',out_fmt='hex',pf=None):
		return self.export_seed(wf,desc=desc,out_fmt=out_fmt,pf=pf)

	def export_mnemonic(self,wf):
		return self.export_seed(wf,desc='MMGen native mnemonic data',out_fmt='words')

	def export_bip39(self,wf):
		return self.export_seed(wf,desc='BIP39 mnemonic data',out_fmt='bip39')

	def export_incog(self,wf,desc='incognito data',out_fmt='i',add_args=[]):
		uargs = ['-p1',self.usr_rand_arg] + add_args
		f,t = self._walletconv_export(wf,desc=desc,out_fmt=out_fmt,uargs=uargs,out_pw=True)
		return t

	def export_incog_hex(self,wf):
		return self.export_incog(wf,desc='hex incognito data',out_fmt='xi')

	# TODO: make outdir and hidden incog compatible (ignore --outdir and warn user?)
	def export_incog_hidden(self,wf):
		rf = joinpath(self.tmpdir,hincog_fn)
		add_args = ['-J','{},{}'.format(rf,hincog_offset)]
		return self.export_incog(
			wf,desc='hidden incognito data',out_fmt='hi',add_args=add_args)

	def addrgen_seed(self,wf,foo,desc='seed data',in_fmt='seed'):
		stdout = desc == 'seed data' # capture output to screen once
		add_args = ([],['-S'])[bool(stdout)] + self.segwit_arg
		t = self.spawn('mmgen-addrgen', add_args +
				['-i'+in_fmt,'-d',self.tmpdir,wf,self.addr_idx_list])
		t.license()
		t.expect_getend('Valid {} for Seed ID '.format(desc))
		vmsg('Comparing generated checksum with checksum from previous address file')
		chk = t.expect_getend(r'Checksum for address data .*?: ',regex=True)
		if stdout: t.read()
		verify_checksum_or_exit(self._get_addrfile_checksum(),chk)
		if in_fmt != 'seed':
			t.no_overwrite()
			t.req_exit_val = 1
		return t

	def addrgen_hex(self,wf,foo,desc='hexadecimal seed data',in_fmt='hex'):
		return self.addrgen_seed(wf,foo,desc=desc,in_fmt=in_fmt)

	def addrgen_mnemonic(self,wf,foo):
		return self.addrgen_seed(wf,foo,desc='MMGen native mnemonic data',in_fmt='words')

	def addrgen_incog(self,wf=[],foo='',in_fmt='i',desc='incognito data',args=[]):
		t = self.spawn('mmgen-addrgen', args + self.segwit_arg + ['-i'+in_fmt,'-d',self.tmpdir]+
				([],[wf])[bool(wf)] + [self.addr_idx_list])
		t.license()
		t.expect_getend('Incog Wallet ID: ')
		t.hash_preset(desc,'1')
		t.passphrase('{} \w{{8}}'.format(desc),self.wpasswd)
		vmsg('Comparing generated checksum with checksum from address file')
		chk = t.expect_getend(r'Checksum for address data .*?: ',regex=True)
		verify_checksum_or_exit(self._get_addrfile_checksum(),chk)
		t.no_overwrite()
		t.req_exit_val = 1
		return t

	def addrgen_incog_hex(self,wf,foo):
		return self.addrgen_incog(wf,'',in_fmt='xi',desc='hex incognito data')

	def addrgen_incog_hidden(self,wf,foo):
		rf = joinpath(self.tmpdir,hincog_fn)
		return self.addrgen_incog([],'',in_fmt='hi',desc='hidden incognito data',
			args=['-H','{},{}'.format(rf,hincog_offset),'-l',str(hincog_seedlen)])

	def txsign_keyaddr(self,keyaddr_file,txfile):
		t = self.spawn('mmgen-txsign', ['-d',self.tmpdir,'-p1','-M',keyaddr_file,txfile])
		t.license()
		t.do_decrypt_ka_data(hp='1',pw=self.kapasswd)
		t.view_tx('n')
		self.txsign_end(t)
		return t

	def txcreate_ni(self,addrfile):
		return self.txcreate_common(sources=['1'],cmdline_inputs=True,add_args=['--yes'])

	def walletgen2(self,del_dw_run='dummy'):
		return self.walletgen(seed_len=128)

	def addrgen2(self,wf):
		return self.addrgen(wf,pf='')

	def txcreate2(self,addrfile):
		return self.txcreate_common(sources=['2'])

	def txsign2(self,txf1,wf1,txf2,wf2):
		t = self.spawn('mmgen-txsign', ['-d',self.tmpdir,txf1,wf1,txf2,wf2])
		t.license()
		for cnum in ('1','2'):
			t.view_tx('n')
			t.passphrase('MMGen wallet',self.cfgs[cnum]['wpasswd'])
			self.txsign_end(t,cnum)
		return t

	def export_mnemonic2(self,wf):
		return self.export_mnemonic(wf)

	def walletgen3(self,del_dw_run='dummy'):
		return self.walletgen()

	def addrgen3(self,wf):
		return self.addrgen(wf,pf='')

	def txcreate3(self,addrfile1,addrfile2):
		return self.txcreate_common(sources=['1','3'])

	def txsign3(self,wf1,wf2,txf2):
		t = self.spawn('mmgen-txsign', ['-d',self.tmpdir,wf1,wf2,txf2])
		t.license()
		t.view_tx('n')
		for cnum in ('1','3'):
			t.passphrase('MMGen wallet',self.cfgs[cnum]['wpasswd'])
		self.txsign_end(t)
		return t

	walletgen14 = walletgen
	addrgen14 = TestSuiteShared.addrgen
	keyaddrgen14 = TestSuiteShared.keyaddrgen

	def walletgen4(self,del_dw_run='dummy'):
		bwf = joinpath(self.tmpdir,self.bw_filename)
		make_brainwallet_file(bwf)
		seed_len = str(self.seed_len)
		args = ['-d',self.tmpdir,'-p1',self.usr_rand_arg,'-l'+seed_len,'-ib']
		t = self.spawn('mmgen-walletconv', args + [bwf])
		t.license()
		t.passphrase_new('new MMGen wallet',self.wpasswd)
		t.usr_rand(self.usr_rand_chars)
		t.label()
		t.written_to_file('MMGen wallet')
		return t

	def addrgen4(self,wf):
		return self.addrgen(wf,pf='')

	def txcreate4(self,f1,f2,f3,f4,f5,f6):
		return self.txcreate_common(sources=['1','2','3','4','14'],non_mmgen_input='4',do_label=True,view='y')

	def txsign4(self,f1,f2,f3,f4,f5,f6):
		non_mm_file = joinpath(self.tmpdir,non_mmgen_fn)
		a = ['-d',self.tmpdir,'-i','brain','-b'+self.bw_params,'-p1','-k',non_mm_file,'-M',f6,f1,f2,f3,f4,f5]
		t = self.spawn('mmgen-txsign',a)
		t.license()
		t.do_decrypt_ka_data(hp='1',pw=self.cfgs['14']['kapasswd'])
		t.view_tx('t')

		for cnum,desc in (('1','incognito data'),('3','MMGen wallet')):
			t.passphrase('{}'.format(desc),self.cfgs[cnum]['wpasswd'])

		self.txsign_end(t,has_label=True)
		return t

	def txdo4(self,f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12):
		non_mm_file = joinpath(self.tmpdir,non_mmgen_fn)
		add_args = ['-d',self.tmpdir,'-i','brain','-b'+self.bw_params,'-p1','-k',non_mm_file,'-M',f12]
		self.get_file_with_ext('sigtx',delete_all=True) # delete tx signed by txsign4
		t = self.txcreate_common(sources=['1','2','3','4','14'],
					non_mmgen_input='4',do_label=True,txdo_args=[f7,f8,f9,f10],add_args=add_args)

		for cnum,desc in (('1','incognito data'),('3','MMGen wallet')):
			t.passphrase('{}'.format(desc),self.cfgs[cnum]['wpasswd'])

		self.txsign_ui_common(t)
		self.txsend_ui_common(t)

		cmd = 'touch ' + joinpath(self.tmpdir,'txdo')
		os.system(cmd)
		return t

	def txbump4(self,f1,f2,f3,f4,f5,f6,f7,f8,f9): # f7:txfile,f9:'txdo'
		non_mm_file = joinpath(self.tmpdir,non_mmgen_fn)
		return self.txbump(f7,prepend_args=['-p1','-k',non_mm_file,'-M',f1],seed_args=[f2,f3,f4,f5,f6,f8])

	def walletgen5(self,del_dw_run='dummy'):
		return self.walletgen()

	def addrgen5(self,wf):
		return self.addrgen(wf,pf='')

	def txcreate5(self,addrfile):
		return self.txcreate_common(sources=['20'],non_mmgen_input='20',non_mmgen_input_compressed=False)

	def txsign5(self,txf,wf,bad_vsize=True,add_args=[]):
		non_mm_file = joinpath(self.tmpdir,non_mmgen_fn)
		t = self.spawn('mmgen-txsign', add_args + ['-d',self.tmpdir,'-k',non_mm_file,txf,wf])
		t.license()
		t.view_tx('n')
		t.passphrase('MMGen wallet',self.cfgs['20']['wpasswd'])
		if bad_vsize:
			t.expect('Estimated transaction vsize')
			t.expect('1 transaction could not be signed')
			exit_val = 2
		else:
			t.do_comment(False)
			t.expect('Save signed transaction? (Y/n): ','y')
			exit_val = 0
		t.read()
		t.req_exit_val = exit_val
		return t

	def walletgen6(self,del_dw_run='dummy'):
		return self.walletgen()

	def addrgen6(self,wf):
		return self.addrgen(wf,pf='')

	def txcreate6(self,addrfile):
		return self.txcreate_common(
			sources=['21'],non_mmgen_input='21',non_mmgen_input_compressed=False,add_args=['--vsize-adj=1.08'])

	def txsign6(self,txf,wf):
		return self.txsign5(txf,wf,bad_vsize=False,add_args=['--vsize-adj=1.08'])
