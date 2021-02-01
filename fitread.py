#!/usr/bin/env python3

# .fit file read interface based on fitparse
#
#	https://github.com/dtcooper/python-fitparse
#
# Tedd OKANO, Tsukimidai Communications Syndicate 2021
# Version 0.1 01 February 2021

# Copyright (c) 2021 Tedd OKANO
# Released under the MIT license
# https://opensource.org/licenses/mit-license.php

import	fitparse
import	os.path
import	sys

isnum		= [ int, float ]


def speed2pace( v ):
	if v != 0:
		return 1000.0 / v
	else:
		return float("inf")


def semicircles2dgree( v ):
	if type( v ) in isnum:
		return v * ( 180.0 / (2.0 ** 31.0) ) 
	else:
		return float("NaN")


def hr2hrr( val ):
	hr_max	= 180.0
	hr_rst	= 48.0
	return ((float( val ) - hr_rst) / (hr_max - hr_rst)) * 100


def get_data( file, *, ready3d = False ):
	fitfile = fitparse.FitFile( file )
	
	msg_type    = [ "record", "device_info", "file_creator", "event", "file_id", "device_settings", "training_file", "user_profile", "zones_target", "workout", "workout_step", "hrv", "climb_pro", "segment_lap", "lap", "session", "activity" ]

	data		= { "value": {}, "units": {}, "session": {} }
	checklist3d	= [ "altitude", "position_lat", "position_long" ]
	
	for x in fitfile.get_messages( "record" ):
		if ready3d:
			count   = 0

			for fit_data in x:
				if fit_data.name in checklist3d:
					if type( fit_data.value ) in isnum:
						count   += 1
			
			if 3 != count:
				continue
				
		for fit_data in x:
			if fit_data.name not in data[ "value" ]:
				data[ "value" ][ fit_data.name ]   = []
				data[ "units" ][ fit_data.name ]   = fit_data.units
				
			data[ "value" ][ fit_data.name ].append( fit_data.value )            

	# process read data
		
	for k, v in data[ "units" ].items():
		if v == "semicircles": 
			data[ "value" ][ k ] = [ semicircles2dgree( x ) for x in data[ "value" ][ k ] ]
			data[ "units" ][ k ] = "degree"
		elif v == "rpm": 
			data[ "value" ][ k ] = [ x * 2 for x in data[ "value" ][ k ] ]
			data[ "units" ][ k ] = "spm"
		elif v == "m/s": 
			data[ "value" ][ k ] = [ speed2pace( x ) for x in data[ "value" ][ k ] ]
			data[ "units" ][ k ] = "sec/km"
		elif k == "distance" and v == "m":
			data[ "value" ][ k ] = [ x / 1000 for x in data[ "value" ][ k ] ]
			data[ "units" ][ k ] = "km"

	for x in fitfile.get_messages( "session" ):
		for fit_data in x:
			if fit_data.name not in data[ "session" ]:
				data[ "session" ][ fit_data.name ]   = []
				if "semicircles" == fit_data.units:
					data[ "session" ][ fit_data.name ].append( semicircles2dgree( fit_data.value ) )            
					data[ "session" ][ fit_data.name ].append( "degree" )
				elif "m/s" == fit_data.units:
					data[ "session" ][ fit_data.name ].append( speed2pace( fit_data.value ) )            
					data[ "session" ][ fit_data.name ].append( "sec/km" )
				else:			
					data[ "session" ][ fit_data.name ].append( fit_data.value )            
					data[ "session" ][ fit_data.name ].append( fit_data.units )
	
	return data

if __name__ == "__main__":
	if 2 < len( sys.argv ):
		#print( "error: no files given to plot" )
		sys.exit( 1 )
		
	file = sys.argv[ 1 ]
	
	file_name, file_ext = os.path.splitext( os.path.basename( file ) )
	
	data	= get_data( file )
	
	print( "********************" )	
	for k, v in data[ "session" ].items():
	    print( k, v[ 0 ], v[ 1 ] )
	print( "********************" )
	for t, a, b, c, d in zip( data[ "value" ]["timestamp"], data[ "value" ][ "position_long" ], data[ "value" ][ "position_lat" ], data[ "value" ][ "distance" ], data[ "value" ][ "speed" ] ):
		print( t - data[ "value" ]["timestamp"][0], a, b, c, d )
