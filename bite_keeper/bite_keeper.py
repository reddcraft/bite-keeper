# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2017 reverendus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import os
import sys

import pkg_resources
from web3 import Web3, HTTPProvider

from pymaker import Address, Contract, Logger
from pymaker.gas import FixedGasPrice, DefaultGasPrice
from pymaker.lifecycle import Web3Lifecycle
from pymaker.sai import Tub
from pymaker.util import chain


class BiteKeeper:
    """Keeper to bite undercollateralized cups."""

    def __init__(self, args: list, **kwargs):
        parser = argparse.ArgumentParser(prog='bite-keeper')
        parser.add_argument("--rpc-host", help="JSON-RPC host (default: `localhost')", default="localhost", type=str)
        parser.add_argument("--rpc-port", help="JSON-RPC port (default: `8545')", default=8545, type=int)
        parser.add_argument("--eth-from", help="Ethereum account from which to send transactions", required=True, type=str)
        parser.add_argument("--tub-address", help="Ethereum address of the Tub contract", required=True, type=str)
        parser.add_argument("--gas-price", help="Gas price in Wei (default: node default)", default=0, type=int)
        parser.add_argument("--debug", help="Enable debug output", dest='debug', action='store_true')
        parser.add_argument("--trace", help="Enable trace output", dest='trace', action='store_true')
        self.arguments = parser.parse_args(args)

        self.web3 = kwargs['web3'] if 'web3' in kwargs else Web3(HTTPProvider(endpoint_uri=f"http://{self.arguments.rpc_host}:{self.arguments.rpc_port}"))
        self.web3.eth.defaultAccount = self.arguments.eth_from

        self.chain = chain(self.web3)
        self.our_address = Address(self.arguments.eth_from)
        self.tub = Tub(web3=self.web3, address=Address(self.arguments.tub_address))

        _json_log = os.path.abspath(pkg_resources.resource_filename(__name__, f"../logs/bite-keeper_{self.chain}_{self.our_address}.json.log".lower()))
        self.logger = Logger('bite-keeper', self.chain, _json_log, self.arguments.debug, self.arguments.trace)
        Contract.logger = self.logger

    def lifecycle(self):
        with Web3Lifecycle(self.web3, self.logger) as lifecycle:
            lifecycle.on_startup(self.startup)

    def startup(self, lifecycle):
        lifecycle.on_block(self.check_all_cups)

    def check_all_cups(self):
        for cup_id in range(self.tub.cupi()):
            self.check_cup(cup_id+1)

    def check_cup(self, cup_id):
        if not self.tub.safe(cup_id):
            self.tub.bite(cup_id).transact(gas_price=self.gas_price())

    def gas_price(self):
        if self.arguments.gas_price > 0:
            return FixedGasPrice(self.arguments.gas_price)
        else:
            return DefaultGasPrice()


if __name__ == '__main__':
    BiteKeeper(sys.argv[1:]).lifecycle()
