#!/usr/bin/env python
#
# mmgen = Multi-Mode GENerator, command-line Bitcoin cold storage solution
# Copyright (C)2013-2016 Philemon <mmgen-py@yandex.com>
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
mmgen-txsign: Sign a transaction generated by 'mmgen-txcreate'
"""

from mmgen.common import *
from mmgen.seed import *
from mmgen.tx import *
from mmgen.addr import *

pnm = g.proj_name

# -w is unneeded - use bitcoin-cli walletdump instead
# -w, --use-wallet-dat  Get keys from a running bitcoind
opts_data = {
	'desc':    'Sign Bitcoin transactions generated by {pnl}-txcreate'.format(pnl=pnm.lower()),
	'usage':   '[opts] <transaction file>... [seed source]...',
	'options': """
-h, --help            Print this help message
--, --longhelp        Print help message for long options (common options)
-b, --brain-params=l,p Use seed length 'l' and hash preset 'p' for brainwallet
                      input
-d, --outdir=      d  Specify an alternate directory 'd' for output
-D, --tx-id           Display transaction ID and exit
-e, --echo-passphrase Print passphrase to screen when typing it
-i, --in-fmt=      f  Input is from wallet format 'f' (see FMT CODES below)
-H, --hidden-incog-input-params=f,o  Read hidden incognito data from file
                      'f' at offset 'o' (comma-separated)
-O, --old-incog-fmt   Specify old-format incognito input
-l, --seed-len=    l  Specify wallet seed length of 'l' bits. This option
                      is required only for brainwallet and incognito inputs
                      with non-standard (< {g.seed_len}-bit) seed lengths.
-p, --hash-preset=p   Use the scrypt hash parameters defined by preset 'p'
                      for password hashing (default: '{g.hash_preset}')
-z, --show-hash-presets Show information on available hash presets
-k, --keys-from-file=f Provide additional keys for non-{pnm} addresses
-K, --key-generator=m Use method 'm' for public key generation
                      Options: {kgs} (default: {kg})
-M, --mmgen-keys-from-file=f Provide keys for {pnm} addresses in a key-
                      address file (output of '{pnl}-keygen'). Permits
                      online signing without an {pnm} seed source. The
                      key-address file is also used to verify {pnm}-to-BTC
                      mappings, so the user should record its checksum.
-P, --passwd-file= f  Get {pnm} wallet or bitcoind passphrase from file 'f'
-q, --quiet           Suppress warnings; overwrite files without prompting
-I, --info            Display information about the transaction and exit
-t, --terse-info      Like '--info', but produce more concise output
-v, --verbose         Produce more verbose output
""".format(
		g=g,pnm=pnm,pnl=pnm.lower(),
		kgs=' '.join(['{}:{}'.format(n,k) for n,k in enumerate(g.key_generators,1)]),
		kg=g.key_generator),
	'notes': """

Transactions may contain both {pnm} or non-{pnm} input addresses.

To sign non-{pnm} inputs, a bitcoind wallet dump or flat key list is used
as the key source ('--keys-from-file' option).

To sign {pnm} inputs, key data is generated from a seed as with the
{pnl}-addrgen and {pnl}-keygen commands.  Alternatively, a key-address file
may be used (--mmgen-keys-from-file option).

Multiple wallets or other seed files can be listed on the command line in
any order.  If the seeds required to sign the transaction's inputs are not
found in these files (or in the default wallet), the user will be prompted
for seed data interactively.

To prevent an attacker from crafting transactions with bogus {pnm}-to-Bitcoin
address mappings, all outputs to {pnm} addresses are verified with a seed
source.  Therefore, seed files or a key-address file for all {pnm} outputs
must also be supplied on the command line if the data can't be found in the
default wallet.

Seed source files must have the canonical extensions listed in the 'FileExt'
column below:

  {f}
""".format(
		f='\n  '.join(SeedSource.format_fmt_codes().splitlines()),
		pnm=pnm,pnl=pnm.lower(),
		w=Wallet,s=SeedFile,m=Mnemonic,b=Brainwallet,x=IncogWalletHex,h=IncogWallet
	)
}

wmsg = {
	'mapping_error': """
{pnm} -> BTC address mappings differ!
%-23s %s -> %s
%-23s %s -> %s
""".strip().format(pnm=pnm),
	'missing_keys_error': """
A key file must be supplied for the following non-{pnm} address%s:\n    %s
""".format(pnm=pnm).strip()
}

def get_seed_for_seed_id(seed_id,infiles,saved_seeds):

	if seed_id in saved_seeds:
		return saved_seeds[seed_id]

	while True:
		if infiles:
			ss = SeedSource(infiles.pop(0),ignore_in_fmt=True)
		elif opt.in_fmt:
			qmsg('Need seed data for Seed ID %s' % seed_id)
			ss = SeedSource()
			msg('User input produced Seed ID %s' % ss.seed.sid)
		else:
			die(2,'ERROR: No seed source found for Seed ID: %s' % seed_id)

		saved_seeds[ss.seed.sid] = ss.seed
		if ss.seed.sid == seed_id: return ss.seed

def generate_keys_for_mmgen_addrs(mmgen_addrs,infiles,saved_seeds):
	seed_ids = set([i[:8] for i in mmgen_addrs])
	vmsg('Need seed%s: %s' % (suf(seed_ids,'k'),' '.join(seed_ids)))
	d = []
	from mmgen.addr import KeyAddrList
	for seed_id in seed_ids:
		# Returns only if seed is found
		seed = get_seed_for_seed_id(seed_id,infiles,saved_seeds)
		addr_idxs = AddrIdxList(idx_list=[int(i[9:]) for i in mmgen_addrs if i[:8] == seed_id])
		d += KeyAddrList(seed=seed,addr_idxs=addr_idxs,do_chksum=False).flat_list()
	return d

def add_keys(tx,src,infiles=None,saved_seeds=None,keyaddr_list=None):
	need_keys = [e for e in getattr(tx,src) if e.mmid and not e.have_wif]
	if not need_keys: return []
	desc,m1 = ('key-address file','From key-address file:') if keyaddr_list else \
					('seed(s)','Generated from seed:')
	qmsg('Checking {} -> BTC address mappings for {} (from {})'.format(pnm,src,desc))
	d = keyaddr_list.flat_list() if keyaddr_list else \
		generate_keys_for_mmgen_addrs([e.mmid for e in need_keys],infiles,saved_seeds)
	new_keys = []
	for e in need_keys:
		for f in d:
			if f.mmid == e.mmid:
				if f.addr == e.addr:
					e.have_wif = True
					if src == 'inputs':
						new_keys.append(f.wif)
				else:
					die(3,wmsg['mapping_error'] % (m1,f.mmid,f.addr,'tx file:',e.mmid,e.addr))
	if new_keys:
		vmsg('Added %s wif key%s from %s' % (len(new_keys),suf(new_keys,'k'),desc))
	return new_keys

# main(): execution begins here

infiles = opts.init(opts_data,add_opts=['b16'])

if not infiles: opts.usage()
for i in infiles: check_infile(i)

c = bitcoin_connection()

saved_seeds = {}
tx_files   = [i for i in infiles if get_extension(i) == MMGenTX.raw_ext]
seed_files = [i for i in infiles if get_extension(i) in SeedSource.get_extensions()]

from mmgen.filename import find_file_in_dir
wf = find_file_in_dir(Wallet,g.data_dir)
if wf: seed_files.append(wf)

if not tx_files:
	die(1,'You must specify a raw transaction file!')
if not (seed_files or opt.mmgen_keys_from_file or opt.keys_from_file): # or opt.use_wallet_dat):
	die(1,'You must specify a seed or key source!')

if not opt.info and not opt.terse_info:
	do_license_msg(immed=True)

kal,kl = None,None
if opt.mmgen_keys_from_file:
	kal = KeyAddrList(opt.mmgen_keys_from_file)

if opt.keys_from_file:
	l = get_lines_from_file(opt.keys_from_file,'key-address data',trim_comments=True)
	kl = KeyAddrList(keylist=[m.split()[0] for m in l]) # accept bitcoind wallet dumps
	if kal: kl.remove_dups(kal,key='wif')
	kl.generate_addrs()

tx_num_str = ''
for tx_num,tx_file in enumerate(tx_files,1):
	if len(tx_files) > 1:
		msg('\nTransaction #%s of %s:' % (tx_num,len(tx_files)))
		tx_num_str = ' #%s' % tx_num

	tx = MMGenTX(tx_file)

	if tx.check_signed(c):
		die(1,'Transaction is already signed!')

	vmsg("Successfully opened transaction file '%s'" % tx_file)

	if opt.tx_id: die(0,tx.txid)

	if opt.info or opt.terse_info:
		tx.view(pause=False,terse=opt.terse_info)
		sys.exit()

	tx.view_with_prompt('View data for transaction%s?' % tx_num_str)

	# Start
	keys = []
	non_mm_addrs = tx.get_non_mmaddrs('inputs')
	if non_mm_addrs:
		tmp = KeyAddrList(addrlist=non_mm_addrs,do_chksum=False)
		tmp.add_wifs(kl)
		m = tmp.list_missing('wif')
		if m: die(2,wmsg['missing_keys_error'] % (suf(m,'es'),'\n    '.join(m)))
		keys += tmp.get_wifs()

	if opt.mmgen_keys_from_file:
		keys += add_keys(tx,'inputs',keyaddr_list=kal)
		add_keys(tx,'outputs',keyaddr_list=kal)

	keys += add_keys(tx,'inputs',seed_files,saved_seeds)
	add_keys(tx,'outputs',seed_files,saved_seeds)

	tx.delete_attrs('inputs','have_wif')
	tx.delete_attrs('outputs','have_wif')

	extra_sids = set(saved_seeds) - tx.get_input_sids()
	if extra_sids:
		msg('Unused Seed ID%s: %s' %
			(suf(extra_sids,'k'),' '.join(extra_sids)))

# 	if opt.use_wallet_dat:
# 		ok = sign_tx_with_bitcoind_wallet(c,tx,tx_num_str,keys)
# 	else:
	ok = tx.sign(c,tx_num_str,keys)

	if ok:
		tx.add_comment()   # edits an existing comment
		tx.write_to_file(ask_write_default_yes=True,add_desc=tx_num_str)
	else:
		die(3,'failed\nSome keys were missing.  Transaction %scould not be signed.' % tx_num_str)
