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
txsign: Sign a transaction generated by 'mmgen-txcreate'
"""

from mmgen.common import *
from mmgen.seed import *
from mmgen.tx import *
from mmgen.addr import *

pnm = g.proj_name

wmsg = {
	'mapping_error': """
{pnm} -> {c} address mappings differ!
{{:<23}} {{}} -> {{}}
{{:<23}} {{}} -> {{}}
""".strip().format(pnm=pnm,c=g.coin),
	'missing_keys_error': """
ERROR: a key file must be supplied for the following non-{pnm} address{{}}:\n    {{}}
""".format(pnm=pnm).strip()
}

saved_seeds = {}

def get_seed_for_seed_id(sid,infiles,saved_seeds):

	if sid in saved_seeds:
		return saved_seeds[sid]

	while True:
		if infiles:
			ss = SeedSource(infiles.pop(0),ignore_in_fmt=True)
		elif opt.in_fmt:
			qmsg('Need seed data for Seed ID {}'.format(sid))
			ss = SeedSource()
			msg('User input produced Seed ID {}'.format(ss.seed.sid))
		else:
			die(2,'ERROR: No seed source found for Seed ID: {}'.format(sid))

		saved_seeds[ss.seed.sid] = ss.seed
		if ss.seed.sid == sid: return ss.seed

def generate_kals_for_mmgen_addrs(need_keys,infiles,saved_seeds):
	mmids = [e.mmid for e in need_keys]
	sids = set(i.sid for i in mmids)
	vmsg('Need seed{}: {}'.format(suf(sids,'s'),' '.join(sids)))
	d = MMGenList()
	from mmgen.addr import KeyAddrList
	for sid in sids:
		# Returns only if seed is found
		seed = get_seed_for_seed_id(sid,infiles,saved_seeds)
		for t in MMGenAddrType.mmtypes:
			idx_list = [i.idx for i in mmids if i.sid == sid and i.mmtype == t]
			if idx_list:
				addr_idxs = AddrIdxList(idx_list=idx_list)
				d.append(KeyAddrList(seed=seed,addr_idxs=addr_idxs,mmtype=MMGenAddrType(t)))
	return d

def add_keys(tx,src,infiles=None,saved_seeds=None,keyaddr_list=None):
	need_keys = [e for e in getattr(tx,src) if e.mmid and not e.have_wif]
	if not need_keys: return []
	desc,m1 = ('key-address file','From key-address file:') if keyaddr_list else \
					('seed(s)','Generated from seed:')
	qmsg('Checking {} -> {} address mappings for {} (from {})'.format(pnm,g.coin,src,desc))
	d = MMGenList([keyaddr_list]) if keyaddr_list else \
		generate_kals_for_mmgen_addrs(need_keys,infiles,saved_seeds)
	new_keys = []
	for e in need_keys:
		for kal in d:
			for f in kal.data:
				mmid = '{}:{}'.format(kal.al_id,f.idx)
				if mmid == e.mmid:
					if f.addr == e.addr:
						e.have_wif = True
						if src == 'inputs':
							new_keys.append(f)
					else:
						die(3,wmsg['mapping_error'].format(m1,mmid,f.addr,'tx file:',e.mmid,e.addr))
	if new_keys:
		vmsg('Added {} wif key{} from {}'.format(len(new_keys),suf(new_keys,'s'),desc))
	return new_keys

def _pop_and_return(args,cmplist): # strips found args
	return list(reversed([args.pop(args.index(a)) for a in reversed(args) if get_extension(a) in cmplist]))

def get_tx_files(opt,args):
	ret = _pop_and_return(args,[MMGenTX.raw_ext])
	if not ret: die(1,'You must specify a raw transaction file!')
	return ret

def get_seed_files(opt,args):
	# favor unencrypted seed sources first, as they don't require passwords
	u,e = SeedSourceUnenc,SeedSourceEnc
	ret = _pop_and_return(args,u.get_extensions())
	from mmgen.filename import find_file_in_dir
	wf = find_file_in_dir(Wallet,g.data_dir) # Make this the first encrypted ss in the list
	if wf: ret.append(wf)
	ret += _pop_and_return(args,e.get_extensions())
	if not (ret or opt.mmgen_keys_from_file or opt.keys_from_file): # or opt.use_wallet_dat
		die(1,'You must specify a seed or key source!')
	return ret

def get_keyaddrlist(opt):
	if opt.mmgen_keys_from_file:
		return KeyAddrList(opt.mmgen_keys_from_file)
	return None

def get_keylist(opt):
	if opt.keys_from_file:
		l = get_lines_from_file(opt.keys_from_file,'key-address data',trim_comments=True)
		kal = KeyAddrList(keylist=[m.split()[0] for m in l]) # accept coin daemon wallet dumps
		kal.generate_addrs_from_keys()
		return kal
	return None

def txsign(tx,seed_files,kl,kal,tx_num_str=''):

	keys = MMGenList() # list of AddrListEntry objects
	non_mm_addrs = tx.get_non_mmaddrs('inputs')

	if non_mm_addrs:
		if not kl:
			die(2,'Transaction has non-{} inputs, but no flat key list is present'.format(g.proj_name))
		tmp = KeyAddrList(addrlist=non_mm_addrs)
		tmp.add_wifs(kl)
		m = tmp.list_missing('sec')
		if m: die(2,wmsg['missing_keys_error'].format(suf(m,'es'),'\n    '.join(m)))
		keys += tmp.data

	if opt.mmgen_keys_from_file:
		keys += add_keys(tx,'inputs',keyaddr_list=kal)
		add_keys(tx,'outputs',keyaddr_list=kal)

	keys += add_keys(tx,'inputs',seed_files,saved_seeds)
	add_keys(tx,'outputs',seed_files,saved_seeds)

	# this attr must not be written to file
	tx.delete_attrs('inputs','have_wif')
	tx.delete_attrs('outputs','have_wif')

	extra_sids = set(saved_seeds) - tx.get_input_sids() - tx.get_output_sids()
	if extra_sids:
		msg('Unused Seed ID{}: {}'.format(suf(extra_sids,'s'),' '.join(extra_sids)))

	return tx.sign(tx_num_str,keys) # returns True or False
