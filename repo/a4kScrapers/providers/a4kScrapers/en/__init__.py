# -*- coding: utf-8 -*-

from . import torrent
from . import hosters
from . import direct

def get_torrent():
    return torrent.__all__

def get_hosters():
    return hosters.__all__

def get_direct():
    return direct.__all__
