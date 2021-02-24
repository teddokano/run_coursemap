#!/usr/bin/env python3

# .fit file read interface based on fitparse
#
#	https://github.com/dtcooper/python-fitparse
#	reference: http://johannesjacob.com/2019/03/13/analyze-your-cycling-data-python/
#
# Tedd OKANO, Tsukimidai Communications Syndicate 2021
# Version 0.4 25-February-2021

# Copyright (c) 2021 Tedd OKANO
# Released under the MIT license
# https://opensource.org/licenses/mit-license.php

import	pandas as pd
import	fitparse


def get_workout( file ):
	workout	= []
	units	= {}
	
	fitfile = fitparse.FitFile( file )
	
	for record in fitfile.get_messages( "record" ):
		r	= {}
		for record_data in record:
			r[ record_data.name ]	= record_data.value
			if record_data.units:
				units[ record_data.name ]	= record_data.units
		workout.append(r)
	
	session	= {}
	
	for s in fitfile.get_messages( "session" ):
		for session_data in s:
			session[ session_data.name ]	= session_data.value
			if session_data.units:
				units[ session_data.name ]	= session_data.units
	
	return pd.DataFrame( workout ), session, units



import	sys

if __name__ == "__main__":
	if 2 < len( sys.argv ):
		print( "error: no files given" )
		sys.exit( 1 )
		
	df, session, units	= get_workout( sys.argv[ 1 ] )
	print( df )
