#!/usr/bin/env python3

# .fit file read interface based on fitparse
#
#	https://github.com/dtcooper/python-fitparse
#
# Tedd OKANO, Tsukimidai Communications Syndicate 2021
# Version 0.3 24-February-2021

# Copyright (c) 2021 Tedd OKANO
# Released under the MIT license
# https://opensource.org/licenses/mit-license.php

import	pandas as pd
import	fitparse
import	os.path
import	sys


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
		
	data	= get_records( sys.argv[ 1 ] )
	print( data )
