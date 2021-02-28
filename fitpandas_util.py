#!/usr/bin/env python3

# utility routines for fitpandas
# Tedd OKANO, Tsukimidai Communications Syndicate 2021

# Copyright (c) 2021 Tedd OKANO
# Released under the MIT license
# https://opensource.org/licenses/mit-license.php

from datetime import timedelta

CHAR_BICYCLIST	= chr( 0x1F6B4 )
CHAR_RUNNER		= chr( 0x1F3C3 )
CHAR_PEDESTRIAN	= chr( 0x1F6B6 )

SYMBOL_CHAR	= {
	"running": CHAR_RUNNER,
	"cycling": CHAR_BICYCLIST,
	"walking": CHAR_PEDESTRIAN
}

def speed2pace( v ):
	if v != 0:
		return 1000.0 / v
	else:
		return float("inf")


def semicircles2dgree( v ):
	return v * ( 180.0 / (2.0 ** 31.0) ) 


def half( v ):
	return v / 2.0 


def hr2hrr( val ):
	hr_max	= 180.0
	hr_rst	= 48.0
	return ((float( val ) - hr_rst) / (hr_max - hr_rst)) * 100


def m2km( v ):
	return v / 1000.0


def cadence2pitch( v ):
	return v * 2.0


def second2MS( s ):
	if isinstance( s, timedelta ):
		s	= s.total_seconds()

	s	= round( s )
	str	= "{:1}:{:02}".format( s // 60, s % 60 )
	return str
    

def second2HMS( s ):
	if isinstance( s, timedelta ):
		s	= s.total_seconds()

	s	= round( s )
		
	str	= "{}h{:02}m{:02}s".format( s // 3600, (s % 3600) // 60, s % 60 )
	return str
    

