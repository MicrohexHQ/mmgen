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
common.py:  Common imports for all MMGen scripts
"""

import sys,os
from mmgen.exception import *
from mmgen.globalvars import *
import mmgen.opts as opts
from mmgen.opts import opt
from mmgen.util import *

def help_notes(k):
	from mmgen.obj import SubSeedIdxRange
	from mmgen.seed import SeedSource
	from mmgen.tx import MMGenTX
	def fee_spec_letters(use_quotes=False):
		cu = g.proto.coin_amt.units
		sep,conj = ((',',' or '),("','","' or '"))[use_quotes]
		return sep.join(u[0] for u in cu[:-1]) + ('',conj)[len(cu)>1] + cu[-1][0]
	def fee_spec_names():
		cu = g.proto.coin_amt.units
		return ', '.join(cu[:-1]) + ('',' and ')[len(cu)>1] + cu[-1] + ('',',\nrespectively')[len(cu)>1]
	return {
		'rel_fee_desc': MMGenTX().rel_fee_desc,
		'fee_spec_letters': fee_spec_letters(),
		'subwallet': """
SUBWALLETS:

Subwallets (subseeds) are specified by a "Subseed Index" consisting of:

  a) an integer in the range 1-{}, plus
  b) an optional single letter, 'L' or 'S'

The letter designates the length of the subseed.  If omitted, 'L' is assumed.

Long ('L') subseeds are the same length as their parent wallet's seed
(typically 256 bits), while short ('S') subseeds are always 128-bit.
The long and short subseeds for a given index are derived independently,
so both may be used.

MMGen has no notion of "depth", and to an outside observer subwallets are
identical to ordinary wallets.  This is a feature rather than a bug, as it
denies an attacker any way of knowing whether a given wallet has a parent.

Since subwallets are just wallets, they may be used to generate other
subwallets, leading to hierarchies of arbitrary depth.  However, this is
inadvisable in practice for two reasons:  Firstly, it creates accounting
complexity, requiring the user to independently keep track of a derivation
tree.  More importantly, however, it leads to the danger of Seed ID
collisions between subseeds at different levels of the hierarchy, as
MMGen checks and avoids ID collisions only among sibling subseeds.

An exception to this caveat would be a multi-user setup where sibling
subwallets are distributed to different users as their default wallets.
Since the subseeds derived from these subwallets are private to each user,
Seed ID collisions among them doesn't present a problem.

A safe rule of thumb, therefore, is for *each user* to derive all of his/her
subwallets from a single parent.  This leaves each user with a total of two
million subwallets, which should be enough for most practical purposes.
""".strip().format(SubSeedIdxRange.max_idx),
		'passwd': """
PASSPHRASE NOTE:

For passphrases all combinations of whitespace are equal, and leading and
trailing space are ignored.  This permits reading passphrase or brainwallet
data from a multi-line file with free spacing and indentation.
""".strip(),
		'brainwallet': """
BRAINWALLET NOTE:

To thwart dictionary attacks, it's recommended to use a strong hash preset
with brainwallets.  For a brainwallet passphrase to generate the correct
seed, the same seed length and hash preset parameters must always be used.
""".strip(),
		'txcreate': """
The transaction's outputs are specified on the command line, while its inputs
are chosen from a list of the user's unspent outputs via an interactive menu.

If the transaction fee is not specified on the command line (see FEE
SPECIFICATION below), it will be calculated dynamically using network fee
estimation for the default (or user-specified) number of confirmations.
If network fee estimation fails, the user will be prompted for a fee.

Network-estimated fees will be multiplied by the value of '--tx-fee-adj',
if specified.

Ages of transactions are approximate based on an average block discovery
interval of one per {g.proto.secs_per_block} seconds.

All addresses on the command line can be either {pnu} addresses or {pnm}
addresses of the form <seed ID>:<index>.

To send the value of all inputs (minus TX fee) to a single output, specify
one address with no amount on the command line.
""".format(g=g,pnm=g.proj_name,pnu=g.proto.name.capitalize()),
		'fee': """
FEE SPECIFICATION: Transaction fees, both on the command line and at the
interactive prompt, may be specified as either absolute {c} amounts, using
a plain decimal number, or as {r}, using an integer followed by
'{l}', for {u}.
""".format( c=g.coin,
			r=MMGenTX().rel_fee_desc,
			l=fee_spec_letters(use_quotes=True),
			u=fee_spec_names() ),
		'txsign': """
Transactions may contain both {pnm} or non-{pnm} input addresses.

To sign non-{pnm} inputs, a {dn} wallet dump or flat key list is used
as the key source ('--keys-from-file' option).

To sign {pnm} inputs, key data is generated from a seed as with the
{pnl}-addrgen and {pnl}-keygen commands.  Alternatively, a key-address file
may be used (--mmgen-keys-from-file option).

Multiple wallets or other seed files can be listed on the command line in
any order.  If the seeds required to sign the transaction's inputs are not
found in these files (or in the default wallet), the user will be prompted
for seed data interactively.

To prevent an attacker from crafting transactions with bogus {pnm}-to-{pnu}
address mappings, all outputs to {pnm} addresses are verified with a seed
source.  Therefore, seed files or a key-address file for all {pnm} outputs
must also be supplied on the command line if the data can't be found in the
default wallet.
""".format( dn=g.proto.daemon_name,
			pnm=g.proj_name,
			pnu=g.proto.name.capitalize(),
			pnl=g.proj_name.lower())
	}[k] + ('-α' if g.debug_utf8 else '')

def exit_if_mswin(feature):
	if g.platform == 'win':
		m = capfirst(feature) + ' not supported on the MSWin / MSYS2 platform'
		ydie(1,m)

def mswin_pw_warning():
	if g.platform == 'win' and not opt.echo_passphrase and g.mswin_pw_warning:
		m  = 'due to a bug in the MSYS2 Python implementation, if your passphrase\n'
		m += 'contains non-ASCII characters, you must turn on passphrase echoing with the\n'
		m += '--echo-passphrase option or use a password file.  Otherwise, the non-ASCII\n'
		m += 'characters in your passphrase will be silently ignored!'
		msg(red('WARNING: ') + yellow(m))
