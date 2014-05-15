#! /usr/bin/env python
# coding: utf-8
# LICENSE:
# Date:
# Author: konglx
# File:
# Description:

__author__ = 'Konglx'

import os

import ansible.inventory

inventory_file = os.path.split(os.path.realpath(__file__))[0] + '/inventory/hosts.conf'
inventory = ansible.inventory.Inventory(inventory_file)
