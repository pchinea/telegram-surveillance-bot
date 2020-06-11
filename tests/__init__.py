"""
Test suite package for Surveillance Bot.
"""
import os
import sys

path = os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, path)

src_path = os.path.join(path, 'src')
sys.path.insert(0, src_path)
