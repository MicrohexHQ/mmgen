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
test/scrambletest.py: seed scrambling and addrlist data generation tests for all supported altcoins
"""

import sys,os,subprocess
repo_root = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),os.pardir)))
os.chdir(repo_root)
sys.path.__setitem__(0,repo_root)

# Import this _after_ local path's been added to sys.path
from mmgen.common import *

opts_data = lambda: {
	'desc': 'Test seed scrambling and addrlist data generation for all supported altcoins',
	'usage':'[options] [command]',
	'options': """
-h, --help          Print this help message
--, --longhelp      Print help message for long options (common options)
-l, --list-cmds     List and describe the tests and commands in this test suite
-s, --system        Test scripts and modules installed on system rather than
                    those in the repo root
-v, --verbose       Produce more verbose output
""",
	'notes': """

If no command is given, the whole suite of tests is run.
"""
}

cmd_args = opts.init(opts_data)

os.environ['MMGEN_DEBUG_ADDRLIST'] = '1'
if not opt.system:
	os.environ['PYTHONPATH'] = repo_root

from collections import OrderedDict
test_data = OrderedDict([
#                  SCRAMBLED_SEED[:8] SCRAMBLE_KEY      ID_STR LBL          FIRST ADDR
('btc',           ('456d7f5f1c4bfe3b','(none)',         '',    '',          '1MU7EdgqYy9JX35L25hR6CmXXcSEBDAwyv')),
('btc_compressed',('bf98a4af5464a4ef','compressed',     '-C',  'COMPRESSED','1F97Jd89wwmu4ELadesAdGDzg3d8Y6j5iP')),
('btc_segwit',    ('b56962d829ffc678','segwit',         '-S',  'SEGWIT',    '36TvVzU5mxSjJ3D9qKAmYzCV7iUqtTDezF')),
('bch',           ('456d7f5f1c4bfe3b','(none)',         '',    '',          '1MU7EdgqYy9JX35L25hR6CmXXcSEBDAwyv')),
('bch_compressed',('bf98a4af5464a4ef','compressed',     '-C',  'COMPRESSED','1F97Jd89wwmu4ELadesAdGDzg3d8Y6j5iP')),
('ltc',           ('b11f16632e63ba92','ltc:legacy',     '-LTC','LTC',       'LMxB474SVfxeYdqxNrM1WZDZMnifteSMv1')),
('ltc_compressed',('7ccf465d466ee7d3','ltc:compressed', '-LTC-C', 'LTC:COMPRESSED', 'LdkebBKVXSs6NNoPJWGM8KciDnL8LhXXjb')),
('ltc_segwit',    ('9460f5ba15e82768','ltc:segwit',     '-LTC-S', 'LTC:SEGWIT',     'MQrY3vEbqKMBgegXrSaR93R2HoTDE5bKrY')),
('eth',           ('213ed116869b19f2','eth',            '-ETH', 'ETH','e704b6cfd9f0edb2e6cfbd0c913438d37ede7b35')),
('etc',           ('909def37096f5ab8','etc',            '-ETC', 'ETC','1a6acbef8c38f52f20d04ecded2992b04d8608d7')),
('dash',          ('bb21cf88c198ab8c','dash:compressed','-DASH-C','DASH:COMPRESSED','XsjAJvCxkxYh55ZvCZMFEv2eJUVo5xxbwi')),
('zec',           ('637f7b8117b524ed','zec:compressed', '-ZEC-C', 'ZEC:COMPRESSED', 't1d47QeTehQye4Mms1Lmx7dPjKVoTtHXKmu')),
('zec_zcash_z',   ('b15570d033df9b1a','zec:zcash_z',    '-ZEC-Z', 'ZEC:ZCASH_Z',    'zcLMMsnzfFYZWU4avRBnuc83yh4jTtJXbtP32uWrs3ickzu1krMU4ppZCQPTwwfE9hLnRuFDSYF8VFW13aT9eeQK8aov3Ge')),
])

def run_tests():
	for test in test_data:
		try:    coin,mmtype = test.split('_',1)
		except: coin,mmtype = test,None
		cmd_name = 'cmds/mmgen-addrgen'
		wf = 'test/ref/98831F3A.mmwords'
		type_arg = ['--type='+mmtype] if mmtype else []
		cmd = [cmd_name,'-qS','--coin='+coin] + type_arg + [wf,'1']
		vmsg(green('Executing: {}'.format(' '.join(cmd))))
		msg_r('Testing: --coin {:4} {:22}'.format(coin.upper(),type_arg[0] if type_arg else ''))
		p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		o = p.stdout.read()
		vmsg(o)
		o = o.splitlines()
		d = [e for e in o if len(e) > 4 and e[:9] == 'sc_debug_']
		d.append('sc_debug_addr: ' + o[-2].split()[-1])
		for n,k in enumerate(['seed','str','id_str','lbl','addr']):
			kk = 'sc_debug_'+k
			a = test_data[test][n]
			b = [e for e in d if e[:len(kk)] == kk][0][len(kk)+2:]
			if b == a:
				vmsg('sc_{}: {}'.format(k,a))
			else:
				rdie(1,'\nError: sc_{} value {} does not match reference value {}'.format(k,b,a))
		msg('OK')

start_time = int(time.time())

run_tests()

t = int(time.time()) - start_time
m =	'\nAll requested tests finished OK, elapsed time: {:02}:{:02}'
msg(green(m.format(t/60,t%60)))
