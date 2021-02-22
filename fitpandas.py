#!/usr/bin/env python3

# .fit file read interface based on fitparse
#
#	https://github.com/dtcooper/python-fitparse
#
# Tedd OKANO, Tsukimidai Communications Syndicate 2021
# Version 0.2 14-February-2021

# Copyright (c) 2021 Tedd OKANO
# Released under the MIT license
# https://opensource.org/licenses/mit-license.php

import	pandas as pd
import	fitparse
import	os.path
import	sys
from tqdm import tqdm


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
	s	= round( s )
	str	= "{:1}:{:02}".format( s // 60, s % 60 )
	return str
    

def second2HMS( s ):
	s	= round( s )
	str	= "{}h{:02}m{:02}s".format( s // 3600, (s % 3600) // 60, s % 60 )
	return str
    

def filter_labels( labels, keywords ):
	tmp_labels	= []
	
	if len( keywords ):
		for filter_key in keywords:
			tmp_labels	+= [ lb for lb in labels if filter_key in lb ]
	
	return tmp_labels


def get_session( file ):
	labels	= []
	records	= []
	n		= 0		# to get total number of records
	
	if verbose:
		print( '  fitpandas: getting session from "{}"'.format( file ) )
	
	fitfile = fitparse.FitFile( file )
	
	session = [ rec for rec in fitfile.get_messages( "session" ) ]
		
	for rec in records:
		for fit_data in rec:
			if fit_data.name not in labels:
				labels.append( fit_data.name )
				if fit_data.units:
					labels.append( "{}_unit".format( fit_data.name ) )
		n	+= 1

	if ( len( filter ) ):
		labels	= filter_labels( labels, filter )
	
	tmp_array	= []

	if verbose:
		bar = tqdm( total = n )
		bar.set_description('  data reading')

	for rec in records:
		labels_and_values	= dict.fromkeys( labels )
		for fit_data in rec:
			if fit_data.name in labels:
				labels_and_values[ fit_data.name ]	= fit_data.value
				if fit_data.units:
					labels_and_values[ "{}_unit".format( fit_data.name ) ]	= fit_data.units

		tmp_array.append( labels_and_values )

		if verbose:
			bar.update( 1 )

	return pd.DataFrame( tmp_array )
	

def get_records( file, *, filter = [], verbose = False ):
	labels	= []
	records	= []
	n		= 0		# to get total number of records
	
	if verbose:
		print( '  fitpandas: getting records from "{}"'.format( file ) )
	
	fitfile = fitparse.FitFile( file )
	
	records = [ rec for rec in fitfile.get_messages( "record" ) ]
		
	for rec in records:
		for fit_data in rec:
			if fit_data.name not in labels:
				labels.append( fit_data.name )
				if fit_data.units:
					labels.append( "{}_unit".format( fit_data.name ) )
		n	+= 1

	if ( len( filter ) ):
		labels	= filter_labels( labels, filter )
	
	tmp_array	= []

	if verbose:
		bar = tqdm( total = n )
		bar.set_description('  data reading')

	for rec in records:
		labels_and_values	= dict.fromkeys( labels )
		for fit_data in rec:
			if fit_data.name in labels:
				labels_and_values[ fit_data.name ]	= fit_data.value
				if fit_data.units:
					labels_and_values[ "{}_unit".format( fit_data.name ) ]	= fit_data.units

		tmp_array.append( labels_and_values )

		if verbose:
			bar.update( 1 )

	dic		= {}
	sessions = [ s for s in fitfile.get_messages( "session" ) ]
	
	for s in sessions:
		for fit_data in s:
			dic[ fit_data.name ]	= fit_data.value
			if fit_data.units:
				dic[ "{}_unit".format( fit_data.name ) ]	= fit_data.units
	
	return pd.DataFrame( tmp_array ), dic


if __name__ == "__main__":
	if 2 < len( sys.argv ):
		#print( "error: no files given to plot" )
		sys.exit( 1 )
		
	file = sys.argv[ 1 ]
	
#	data	= get_records( file, filter = [ "distance" ], verbose = False )
#	data	= get_records( file, filter = [ "distance", "altitude" ] )
	data	= get_records( file )

	print( data )
	print( data.columns )

	check	= data[ "speed" ].to_list()

	sys.exit( 1 )
	
	print( "********************" )	
	for k, v in data[ "session" ].items():
	    print( k, v[ 0 ], v[ 1 ] )
	print( "********************" )
	for t, a, b, c, d in zip( data[ "value" ]["timestamp"], data[ "value" ][ "position_long" ], data[ "value" ][ "position_lat" ], data[ "value" ][ "distance" ], data[ "value" ][ "speed" ] ):
		print( t - data[ "value" ]["timestamp"][0], a, b, c, d )
