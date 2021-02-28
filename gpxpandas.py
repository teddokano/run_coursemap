#!/usr/bin/env python3

# .gpx file read interface based on fitparse
#
#	reference: https://ocefpaf.github.io/python4oceanographers/blog/2014/08/18/gpx/
#
# Tedd OKANO, Tsukimidai Communications Syndicate 2021
# Version 0.1 27-February-2021

import	pandas as pd
import	gpxpy
import	gpxpy.gpx

import	numpy as np


def get_course( file_name ):
	gpx_file = open( file_name, "r" )
	gpx = gpxpy.parse( gpx_file )

	course_list = []
		
	gpx		= gpxpy.parse( open( file_name ) )
	track	= gpx.tracks[0]
	segment = track.segments[0]
	dist	= 0

	for point_idx, point in enumerate( segment.points ):
		speed	 = segment.get_speed( point_idx )
		dist	+= speed
		course_list.append( [ point.latitude, point.longitude, point.elevation, point.time, speed, dist] )

	columns = [ "position_lat", "position_long", "altitude", "timestamp", "speed", "distance" ]
	course	= pd.DataFrame( course_list, columns = columns )
	stat	= course.describe()
	
	session	= {}
	session[ "nec_lat"   ] 	= stat[ "position_lat"  ][ "max" ]
	session[ "swc_lat"   ]	= stat[ "position_lat"  ][ "min" ]
	session[ "nec_long"  ]	= stat[ "position_long" ][ "max" ]
	session[ "swc_long"  ]	= stat[ "position_long" ][ "min" ]
	session[ "start_time" ]	= course.iloc[ 0 ][ "timestamp" ]
	session[ "total_timer_time" ]	= course.iloc[ -1 ][ "timestamp" ] - course.iloc[ 0 ][ "timestamp" ]
	session[ "total_distance" ]	= course.iloc[ -1 ][ "distance" ]
	session[ "sport" ]		= "NA (\".gpx\" data)"
	session[ "avg_speed" ]	=  stat[ "speed" ][ "mean" ]

	units	= {}

	print( course )

	return course, session, units


import	sys

def main():
	if len( sys.argv ) < 2:
		print( "error: no files given" )
		sys.exit( 1 )
		
	file_name	= sys.argv[ 1 ]

	df, session, units	= get_gpx( file_name )

	
	output_filename	= "_df_" + "_".join( sys.argv ) + ".csv"
	df.to_csv( output_filename )
	print( '\n---- data written into file: "{}"'.format( output_filename ) )
	
	print( "\n---- list of 'session' and 'units' data" )
	for k in sorted( set( [*session] + [*units] ) ):
		print( "{:<30}{:>30}{:>15}".format( k, str( session.get( k, "---" ) ), str( units.get( k, "---" ) ) ) )
		
	print( "\n---- 'DataFrame' data" )
	print( df )


if __name__ == "__main__":
	main()
