#!/usr/bin/env python3

# utility routines for fitpandas
# Tedd OKANO, Tsukimidai Communications Syndicate 2021
# Version 0.7 16-March-2021

# Copyright (c) 2021 Tedd OKANO
# Released under the MIT license
# https://opensource.org/licenses/mit-license.php

import	numpy as np
from datetime import timedelta
from geopy.geocoders import Nominatim
from geopy.distance import great_circle

K				= 40075.016686
OVERSIZE_RATIO	= 1.1

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
    

def limit_values( data, args ):	
	limit_values	= attributes( data )

	if not args.negative_alt:
		bottom	= limit_values[ "bottom" ]
		if bottom < 0:
			data[ "altitude" ]	= data[ "altitude" ].apply( lambda x: x - bottom )
			limit_values[ "bottom" ]	-= bottom,
			limit_values[ "top" ]		-= bottom,		

	if args.verbose:	print( "  start     : latitude = {}˚, longitude = {}˚".format( limit_values[ "start_lat"    ], limit_values[ "start_long"    ] ) )
	if args.verbose:	print( "  farend    : latitude = {}˚, longitude = {}˚".format( limit_values[ "farthest_lat" ], limit_values[ "farthest_long" ] ) )
	
	#####
	##### altitude data filtering options
	#####
	if args.alt_filt == "off":
		return limit_values
		
	if args.alt_filt == "avg":
	
		#####
		##### spacial filtering
		#####
		
		am_size	= 300	# altitude map grid resolution
		olr		= 2		# overlapping range
		span_d	= limit_values[ "span_deg" ]
		s_deg	= limit_values[ "s_deg" ]
		w_deg	= limit_values[ "w_deg" ]
		Rcv		= limit_values[ "Rcv" ]

		altmap	= [ [ [] for j in range( am_size + olr * 2 ) ] for i in range( am_size + olr * 2 ) ]
		
		for i in range( len( data ) ):
			lat, long, alt	= data.iloc[ i ][ "position_lat" ], data.iloc[ i ][ "position_long" ], data.iloc[ i ][ "altitude" ]
			y	= int( (lat  - s_deg) * Rcv / span_d * (am_size - 1) )
			x	= int( (long - w_deg)       / span_d * (am_size - 1) )	
			for p in range( olr * 2 + 1 ):	
				for q in range( olr * 2 + 1 ):	
					altmap[ x + p ][ y + q ].append( alt )
			
		for p in range( am_size ):
			for q in range( am_size ):
				x	= p + olr
				y	= q + olr
				if altmap[ x ][ y ] != 0:
					t	= altmap[ x ][ y ]
					if 0 == len( t ):
						altmap[ x ][ y ]	= None
					else:
						altmap[ x ][ y ]	= sum( t )/len( t )

		z	= []
		for i in range( len( data ) ):
			lat, long	= data.iloc[ i ][ "position_lat" ], data.iloc[ i ][ "position_long" ]
			y	= int( (lat  - s_deg) * Rcv / span_d * (am_size - 1) ) + olr
			x	= int( (long - w_deg)       / span_d * (am_size - 1) ) + olr
			z.append( altmap[ x ][ y ] )
	else:
		z	= data[ "altitude" ]
	
	#####
	##### temporal filtering
	#####
	z	= filtering( z, 30 )

	limit_values[ "bottom" ]	= min( z )
	limit_values[ "top"    ]	= max( z )

	data[ "altitude" ]	= z
	
	return limit_values


def attributes( data ):	
	stat	= data.describe()
	
	s_deg, n_deg	= stat[ "position_lat"  ][ "min" ], stat[ "position_lat"  ][ "max" ]
	w_deg, e_deg	= stat[ "position_long" ][ "min" ], stat[ "position_long" ][ "max" ]
	v_start_deg	= data.iloc[ 0 ][ "position_lat"  ]
	h_start_deg	= data.iloc[ 0 ][ "position_long" ]
 
	v_span_deg	= n_deg - s_deg
	h_span_deg	= e_deg - w_deg
	v_cntr_deg	= v_span_deg / 2 + s_deg
	h_cntr_deg	= h_span_deg / 2 + w_deg

	Rcv			= np.cos( v_cntr_deg / 180.0 * np.pi )
	Cv			= K / 360.0
	Ch			= (K * Rcv) / 360.0

	north	= Cv * (n_deg - v_start_deg)
	south	= Cv * (s_deg - v_start_deg)
	east	= Ch * (e_deg - h_start_deg)
	west	= Ch * (w_deg - h_start_deg)
	
	v_span	= north - south
	h_span	= east  - west
	
	v_cntr	= v_span / 2 + south
	h_cntr	= h_span / 2 + west

	if  h_span < v_span:
		vh_span	= v_span
	else:
		vh_span	= h_span

	vh_span	*= OVERSIZE_RATIO
	vh_span_half	= vh_span / 2.0
	
	attr	= {
		"s_deg"		:	s_deg,
		"w_deg"		:	w_deg,
		"v_cntr_deg":	v_cntr_deg,
		"h_cntr_deg":	h_cntr_deg,
		"span_deg"	:	v_span_deg if h_span_deg < v_span_deg else h_span_deg,
		"north"		:	v_cntr + vh_span_half,		
		"south"		:	v_cntr - vh_span_half,
		"east"		:	h_cntr + vh_span_half,
		"west"		:	h_cntr - vh_span_half,
		"bottom"	:	stat[ "altitude" ][ "min" ],
		"top"		:	stat[ "altitude" ][ "max" ],
		"v_cntr"	:	v_cntr,
		"h_cntr"	:	h_cntr,
		"vh_span" 	:	vh_span,
		"Rcv"		:	Rcv,
		"Cv"		:	Cv,
		"Ch"		:	Ch,
		"start"		:	data.iloc[  0 ][ "distance" ],
		"fin"		:	data.iloc[ -1 ][ "distance" ]
	}
	
	data[ "lat_km"  ]	= data[ "position_lat"  ].apply( lambda y: Cv * (y - data[ "position_lat"  ][ 0 ]) )
	data[ "long_km" ]	= data[ "position_long" ].apply( lambda x: Ch * (x - data[ "position_long" ][ 0 ]) )
	data[ "DIST"    ]	= data.apply( lambda x: ( ( x[ "lat_km" ] ** 2 ) + ( x[ "long_km" ] ** 2 ) ) ** 0.5, axis = 1 )

#	print( data[ "lat_km"  ] )
#	print( data[ "long_km"  ] )

	# data.apply( lambda x: print( "{}, {}".format( x[ "distance" ], x[ "DIST" ] ) ), axis = 1 )
	i	= data[ "DIST" ].idxmax()
	attr[ "farthest_lat"  ]	= data[ "position_lat"  ][ i ]
	attr[ "farthest_long" ]	= data[ "position_long" ][ i ]
	attr[ "start_lat"     ]	= data.iloc[  0 ][ "position_lat"  ]
	attr[ "start_long"    ]	= data.iloc[  0 ][ "position_long" ]

	return attr


def p2p_distance( lat0, long0, lat1, long1 ):
	return ( great_circle( (lat0, long0), (lat1, long1) ).meters )


def filtering( z, len ):
	len_half	= len // 2
	coeff		= [ 0.5 * (np.cos( x ) + 1.0) for x in np.linspace( -np.pi, np.pi, len) ]	
	coeff		= [ x / sum( coeff ) for x in coeff ]

	z	= np.append( np.full( len_half, z[  0 ] ), z )
	z	= np.append( z, np.full( len_half, z[ -1 ] ) )
	z	= np.convolve( z, coeff, mode = 'same' )[ len_half : -len_half ]
	
	return z


def city_name_list( data ):
	d	= data[:: len( data.index ) // 5 ]
	
	cities	= d.apply( lambda x: get_city_name( x[ "position_lat" ], x[ "position_long" ] ), axis = 1 )
	
	return cities


def get_city_name( lat, long ):
	ctv	= [
		[ "tourism", "islet", "borough" ],	# "quarter" had been removed
		[ "island", "suburb", "village", "town", "city" ]
	]
		# https://wiki.openstreetmap.org/wiki/JA:Key:place
		
	s	= ""
	
	location	= reverse_geocoding( lat, long )
	
	for level in ctv:
		for label in level:
			if label in location.raw[ "address" ].keys():
				if s != "":
					s += ", " + location.raw[ "address" ][ label ]
				else:
					s	= location.raw[ "address" ][ label ]
					
				# print( "place name was found \"{}\" as {}".format( location.raw[ "address" ][ label ], label ) )
				# print( location.raw[ "address" ] )
				break
	
	return s

	
def reverse_geocoding( lat, long ):
	geolocator = Nominatim(user_agent="run_coursemap.py")
	return geolocator.reverse( "{}, {}".format( lat, long ), language = "en" )


def color_map( length ):
	cycle	= np.pi
	n	= np.linspace( 0, cycle, length )
	
	cm	= []
	for i in n:
		r	= (np.cos( i + cycle ) * 0.5 + 0.5) ** 2
		g	= (np.sin( i )) ** 2
		b	= (np.cos( i ) * 0.5 + 0.5) ** 2
		cm.append( [ r, g, b ] )
	
	return cm
