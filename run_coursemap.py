#!/usr/bin/env python3

# run_coursemap.py
# 
# script for running course map in 3D. 
# plotting 3D course from .fit or .gpx file
# 
# usage:  run_coursemap.py data.fit
#
# Tedd OKANO, Tsukimidai Communications Syndicate 2021
# Version 0.24 04-January-2022   # z-axis data can be changed
# Version 0.23 25-December-2021  # colorbar option switch added / "heart_rate" added for color_key
# Version 0.22 24-December-2021  # color bar added
# Version 0.21 22-December-2021  # code cleaned (in marker plotting loop)
# Version 0.20 19-December-2021  # curtain color can be changed by altitude/speed/power
# Version 0.14 14-March-2021

# Copyright (c) 2021-2022 Tedd OKANO
# Released under the MIT license
# https://opensource.org/licenses/mit-license.php

import	fitpandas
import	gpxpandas
import	fitpandas_util as fu
import	staticmaps
import	matplotlib.pyplot as plt
import	numpy as np
import	os.path
import	sys
import	argparse
import	datetime
from	mpl_toolkits.mplot3d import Axes3D
import	pytz
from 	timezonefinder import TimezoneFinder
import	subprocess
import	pickle
import	pandas as pd
import	re

import	time


FOOTNOTE		= "plotted by 'run_coursemap'\nhttps://github.com/teddokano/run_coursemap"
OSM_CREDIT		= "Maps & data © OpenStreetMap contributors"
K				= 40075.016686
OVERSIZE_RATIO	= 1.1
MAP_RESOLUTION	= { "low": 256, "mid": 512, "high": 1024, "off": "" }

REQUIRED_DATA_COLUMNS	= [ 	
	"distance", 
	"altitude", 
	"position_long", 
	"position_lat"
]

COLORKEY	= { "distance": "km", "altitude": "m", "speed": "km/h", "power": "W", "heart_rate": "bpm" }


class ColorScale:
	def __init__( self, series, smoothing = False, logscale = False ):
		d	= series.copy()

		if logscale:
			d	= np.log( d )
			d.replace( float( "-inf" ), 0, inplace = True )

		if smoothing:
			WNDW_LEN	= 120
			WINDOW		= [ 0.5 * (np.cos( z ) + 1.0)	for z in np.linspace( -np.pi, np.pi, WNDW_LEN) ]
			WINDOW		= [ x / sum( WINDOW ) for x in WINDOW ]

			s	= []
			
			padding	= [ 0 for x in range( len( WINDOW ) // 2 ) ]
			s.extend( padding )
			
			s.extend( smooth( d, WINDOW ) )
			
			padding	= [ s[ -1 ] for x in range( len( WINDOW ) // 2 ) ]
			s.extend( padding )
			
			self.series	= pd.Series( s )

		else:
			self.series	= d

		self.min	= self.series.min()
		self.max	= self.series.max()
		self.fullscale	= self.max - self.min
		self.series	-= self.min
		self.series	/= self.fullscale

	def ratio( self, count ):
		return self.series[ count ]


def main():
	file_name, file_ext = os.path.splitext( args.input_file )

	print_v( "\"{}\" started".format( sys.argv[ 0 ] )  )
	
	file_suffix	= file_ext.lower()
	output_filename	= "_".join( sys.argv )

	if args.verbose:	show_given_parameters( output_filename )

	#####
	##### data file reading
	#####
	if not args.quiet: print( "reading file: \"{}\"".format( args.input_file )  )

	if ".fit" == file_suffix:
		data, s_data, units	= fitpandas.get_workout( args.input_file )
		
		data[ "position_lat"  ]	= data[ "position_lat"  ].apply( fu.semicircles2dgree )
		data[ "position_long" ]	= data[ "position_long" ].apply( fu.semicircles2dgree )
		s_data[ "nec_lat"  ]	= fu.semicircles2dgree( s_data[ "nec_lat"  ] )
		s_data[ "swc_lat"  ]	= fu.semicircles2dgree( s_data[ "swc_lat"  ] )
		s_data[ "nec_long" ]	= fu.semicircles2dgree( s_data[ "nec_long" ] )
		s_data[ "swc_long" ]	= fu.semicircles2dgree( s_data[ "swc_long" ] )
		
	elif ".gpx" == file_suffix:
		data, s_data, units	= gpxpandas.get_course( args.input_file )

	print_v( "available data {}".format( data.columns.to_list() ) )

	data[ "distance" ]	/= 1000.0	# convert from meter to kilometer
	data[ "speed" ]		*= 3.6		# convert from m/s to km/h

	#####
	##### plot range calculation
	#####
	if not args.quiet: print( "calculating plot range..." )
	
	if args.color_key not in data.columns:
		print( "WARNING:" )
		print( "  color key: \"{}\" was specified but not available.".format( args.color_key ) )
		print( "  default key \"{}\" had been chosen for plot".format( "distance" ) )
		print( "  available keying data are.. {}".format( set(COLORKEY.keys()) & set(data.columns) ) )
		args.color_key	= "distance"
	
	if args.z_axis != "altitude":
		args.color_key	= args.z_axis
	
	if args.color_key != "distance":
		REQUIRED_DATA_COLUMNS.append( args.color_key )
	if args.color_key in [ "speed", "power" ]:
		max	= data[ "speed" ].max()
		mean	= data[ "speed" ].mean()
		lim		= mean - (max - mean)
		data.loc[ data[ "speed" ] < lim, "speed" ] = float( "NaN" )

	data	= data.dropna( subset = REQUIRED_DATA_COLUMNS )
	data	= data[ (data[ "distance" ] >= args.start) & (data[ "distance" ] <= args.fin) ]
	data.reset_index( inplace = True, drop = True )	

	lim_val	= fu.limit_values( data, args )
	lim_val[ "sport" ]	= s_data[ "sport" ]	# tentative implementation for colorbar drawing
	
	if args.screen_off and not args.output_to_file:
		print( "no plot processed since \"--screen_off\" option given without \"-o\" (output to file)" )
		return	# do nothing and quit

	#####
	##### plot settings
	#####
	fig	= plt.figure( figsize=( 11, 11 ) )
	ax	= fig.add_subplot( 111, projection = "3d" )

	if not args.quiet:
		print( "plot values:" )
		print( "  latitude  - north  : {:+10.5f}˚ as {:+8.3f}km".format( s_data[ "nec_lat"  ], lim_val[ "north" ] )  )
		print( "            - south  : {:+10.5f}˚ as {:+8.3f}km".format( s_data[ "swc_lat"  ], lim_val[ "south" ] )  )
		print( "  longitude - east   : {:+10.5f}˚ as {:+8.3f}km".format( s_data[ "nec_long" ], lim_val[ "east"  ] )  )
		print( "            - west   : {:+10.5f}˚ as {:+8.3f}km".format( s_data[ "swc_long" ], lim_val[ "west"  ] )  )
		print( "  altitude  - top    : {:5.1f}m".format( lim_val[ "top"    ] )  )
		print( "            - bottom : {:5.1f}m".format( lim_val[ "bottom" ] )  )
		print( "  course distance    : {:7.3f}km".format( data.iloc[ -1 ][ "distance" ] - data.iloc[ 0 ][ "distance" ])  )

	#####
	##### getting/drawing map
	#####
	if args.map_resolution != "off":
		if not args.quiet: print( "getting map data and draw..." )
		map_arr	= get_map( ax, args.map_resolution, lim_val )
	
	#####
	##### 3D course plot
	#####
	if not args.quiet: print( "3D prot in progress..." )
	plot( ax, data, lim_val )

	# ax.set_title( "course plot of " + args.input_file  )
	fig.text( 0.2, 0.92, "course plot by \"{}\"\n * curtain color: \"{}\"".format( args.input_file, args.color_key ), fontsize = 9, alpha = 0.5, ha = "left", va = "top" )
	fig.text( 0.8, 0.92, info( s_data, lim_val ), fontsize = 9, alpha = 0.5, ha = "right", va = "top" )
	fig.text( 0.8, 0.1, FOOTNOTE + "\n" + (OSM_CREDIT if args.map_resolution != "off" else ""), fontsize = 9, alpha = 0.5, ha = "right" )
	
	#####
	##### output to file | screen
	#####

	if args.pickle_output:
		if not args.quiet: print( "output pickle data..." )
		with open( output_filename + ".pickle", 'wb') as ofs:
			pickle.dump( fig, ofs )

	if args.gifanm:
		if not args.quiet: print( "making GIF animation..." )
		make_gif_mp( "-".join( sys.argv ), fig ) # <-- to make GIF animation. enabling this will take time to process

	ax.view_init( args.elevation, args.azimuth )

	if args.output_to_file:
		if not args.quiet: print( "output to .png file..." )
		plt.savefig( output_filename + ".png", dpi=600, bbox_inches="tight", pad_inches=0.05 )

	if not args.screen_off:
		if not args.quiet: print( "output to screen..." )
		plt.show()


def info( s, lv ):
	dt	= get_localtimef( lv[ "v_cntr_deg" ], lv[ "h_cntr_deg" ], s[ "start_time" ] )
	sp	= s[ "sport" ]
	
	if sp == "running":
		avg	= "{}/km".format( fu.second2MS( fu.speed2pace( s[ "avg_speed" ] ) ) )
	else:
		avg	= "{:.2f}km/h".format( s[ "avg_speed" ] * 3.6 )
		
	if args.map_resolution != "off":
		start_place		= fu.get_city_name( lv[ "start_lat"    ], lv[ "start_long"    ] )
		farend_place	= fu.get_city_name( lv[ "farthest_lat" ], lv[ "farthest_long" ] )
		if start_place == farend_place:
			place	= start_place
		else:
			place	= "{} - {}".format( start_place, farend_place )
	else:
		place	= ""

	"""
	if sp in fu.SYMBOL_CHAR.keys():
		print( fu.SYMBOL_CHAR[ sp ] )
		sp	= fu.SYMBOL_CHAR[ sp ] + " " + sp
	"""
	
	str		= "{} for {:.3f}km, {} (avg:{})".format( sp, s[ "total_distance" ] / 1000.0, fu.second2HMS( s[ "total_timer_time" ] ), avg )
	print_v( "  {}\n  started on {}".format( str, dt ) )
	
	return "{}\n{}\n{}".format( str, dt, place )


def get_localtimef( v, h, dt ):
	tf	= TimezoneFinder()
	tz	= pytz.timezone( tf.timezone_at( lat = v, lng = h ) )

	if dt.tzinfo:
		dt.replace( tzinfo = None )
	else:
		dt	+= tz.utcoffset( dt )
		dt	 = tz.localize( dt )
		
	return "{}".format( dt.astimezone( tz ) )


def get_localtimef_pre( v, h, dt ):
	tf		= TimezoneFinder()
	tz		= pytz.timezone( tf.timezone_at( lat = v, lng = h ) )
	offset	= tz.utcoffset( dt )
	seconds	= offset.total_seconds()
	return "{} (UTC{:0=+3}{:02} {})".format( dt + offset, int( seconds // 3600 ), int((seconds % 3600) // 60), tz )


def plot( ax, data, lv ):
	span	= lv[ "vh_span" ]
	
	if args.thining_factor < 1:	args.thining_factor	= 1   
	data	= data[ ::args.thining_factor ]

	ds	= data[ "distance" ].tolist()
	dm_interval	= findinterval( ds[ -1 ] - ds[ 0 ] )	# finding distance marker interval

	print_v( "  distance marker interval {}km".format( dm_interval ) )

	#####
	##### start plotting
	#####	

	ax.set_xlim( [ lv[ "west"   ],  lv[ "east"  ] ] )
	ax.set_ylim( [ lv[ "south"  ],  lv[ "north" ] ] )
	ax.set_zlim( [ lv[ "bottom" ],  lv[ "top"   ] ] )

	COLORS	= 360
	COLOR_REVERSE	= [ "altitude", "speed" ]
	
	cm	= fu.color_map( COLORS + 1 )
	
	if args.color_key in COLOR_REVERSE:
		cm.reverse()
	
	smoothing_flag	= True if args.color_key == "power" else False
	col_scale	= ColorScale( data[ args.color_key ], smoothing = smoothing_flag, logscale = False )

	dm_format	= dmformat( dm_interval )

	xs	= data[ "long_km"  ].tolist()
	ys	= data[ "lat_km"   ].tolist()
#	zs	= data[ args.z_axis ].tolist()

	if args.z_axis != "altitude":
		zs	 = pd.Series( data[ args.z_axis ] )
		zs	-= zs.min()
		zs	/= zs.max()
		zs	*= (data[ "altitude" ].max() - data[ "altitude" ].min())
		zs	+= data[ "altitude" ].min()
		zs	 = zs.tolist()
	else:
		zs	= data[ "altitude" ].tolist()

	cs	= [ cm[ int(COLORS * col_scale.ratio( i ) ) ] for i in range( len( zs ) ) ]

	m_val	= range( int(ds[ 0 ] / dm_interval + 1) * dm_interval, int(ds[ -1 ] / dm_interval) * dm_interval, dm_interval )
	m_dic	= marker_index( ds, m_val )
	
	z_min	= lv[ "bottom" ]

	w	= 0.01
	r	= 0.8

	if ( args.colorbar != "off" ):
		direction	= args.colorbar

		if ( direction == None ):
			if ( args.azimuth != None ):
				dir	= [ "e", "n", "w", "s" ]
				pos0	= dir[ int( (args.azimuth        % 360) / 90 ) ]
				pos1	= dir[ int( ((args.azimuth + 90) % 360) / 90 ) ]
				direction	= "{}{}".format( pos0, pos1 )
			else:
				direction	= "se"
	
		if args.colorbarall: direction	= "nsew"

		direction	= re.findall( "[n]|[s]|[e]|[w]", direction )

		for p in direction:
			colorbar( ax, cm, lv, col_scale.min, col_scale.max, position = p, ratio = r, width = w )

	if ( args.colorbarV != "off" ):
		vc		= [ "se", "nw", "ne", "sw", "wn", "es", "ws", "en" ]
		if ( args.colorbarV not in vc ):
			corner	= [ vc[ int( (args.azimuth % 360) / 45 ) ] ]
		else:
			corner	= [ args.colorbarV ]
	
		if args.colorbarall: corner	= [ "ne", "nw", "se", "sw" ]

		for c in corner:
			colorbar( ax, cm, lv, col_scale.min, col_scale.max, orientation = "vertical", corner = c, ratio = 1, width = w )


#	t = time.time()

	for x, y, z, cc in zip( xs, ys, zs, cs ):
		ax.plot( [ x, x ], [ y, y ], [ z, z_min ], color = cc, alpha = args.curtain_alpha )

#	print( "elapsed time {}".format( time.time() - t ) )

	if args.color_key != "distance":
		for v, i in m_dic.items():
			cs[ i ]	= [ 0.5, 0.5, 0.5 ]
	
	for v, i in m_dic.items():
		marktext( ax, xs[ i ], ys[ i ], zs[ i ], 10, (dm_format % v) + "km", 10, cs[ i ], 0.99, "center" )

	if args.z_axis != "altitude":
		zs	= data[ "altitude" ].tolist()
		
	ax.plot( xs, ys, z_min, color = [ 0, 0, 0 ], alpha = 0.1 )	# course shadow plot on bottom
	ax.plot( xs, ys, zs,    color = [ 0, 0, 0 ], alpha = 0.2 )	# course plot on trace edge

	marktext( ax, xs[  0 ], ys[  0 ], zs[  0 ], 200, "start", 20, [ 0, 1, 0 ], 0.5, "left" )
	marktext( ax, xs[ -1 ], ys[ -1 ], zs[ -1 ], 200, "fin",   20, [ 1, 0, 0 ], 0.5, "right" )
	
	marktext( ax, lv[ "west"   ], lv[ "v_cntr" ], z_min, 0, "W", 12, [ 0, 0, 0 ], 0.2, "center" )
	marktext( ax, lv[ "east"   ], lv[ "v_cntr" ], z_min, 0, "E", 12, [ 0, 0, 0 ], 0.2, "center" )
	marktext( ax, lv[ "h_cntr" ], lv[ "south"  ], z_min, 0, "S", 12, [ 0, 0, 0 ], 0.2, "center" )
	marktext( ax, lv[ "h_cntr" ], lv[ "north"  ], z_min, 0, "N", 12, [ 0, 0, 0 ], 0.2, "center" )
	
	ax.set_xlabel( "[km]\nlongitude (-):west / (+): east"  )
	ax.set_ylabel( "[km]\nlatiitude (-):south / (+): north" )
	ax.set_zlabel( "altitude [m]" )
	ax.grid()


def colorbar( ax, cm, lv, min, max, orientation = "horizontal", corner = "ne", position = "n", width = 0.02, ratio = 0.5, alpha = 0.5 ):
	pos	= { "n": "north", "s": "south", "e": "east", "w": "west" }
	position	= pos[ position ]
	
	d	= pd.DataFrame()
	d[ "i" ]	= range( 360 )
	
	if orientation == "horizontal":
		if position == "north" or position == "south":
			span_x		= lv[ "east" ] - lv[ "west" ]
			start_x		= lv[ "west" ] + span_x * (1 - ratio) * 0.5
			end_x		= lv[ "east" ] - span_x * (1 - ratio) * 0.5
			center_x	= lv[ "west" ] + span_x * 0.5

			span_x		= 0

			span_y		= (lv[ "north" ] - lv[ "south" ]) * width
			start_y		= lv[ position ]
			center_y	= lv[ position ]
			end_y		= lv[ position ]

			d[ "x" ]	= np.linspace( start_x,  end_x, 360 )
			d[ "y" ]	= lv[ position ]
			d[ "z" ]	= lv[ "bottom" ]

		else:
			span_y		= lv[ "north" ] - lv[ "south" ]
			start_y		= lv[ "south" ] + span_y * (1 - ratio) * 0.5
			end_y		= lv[ "north" ] - span_y * (1 - ratio) * 0.5
			center_y	= lv[ "south" ] + span_y * 0.5

			span_y		= 0

			span_x		= (lv[ "east" ] - lv[ "west" ]) * width
			start_x		= lv[ position ]
			center_x	= lv[ position ]
			end_x		= lv[ position ]

			d[ "x" ]	= lv[ position ]
			d[ "y" ]	= np.linspace( start_y,  end_y, 360 )
			d[ "z" ]	= lv[ "bottom" ]
		
		start_z		= lv[ "bottom" ]
		end_z		= lv[ "bottom" ]
		center_z	= lv[ "bottom" ]
	else:
		span_z		= lv[ "top"    ] - lv[ "bottom"  ]
		start_z		= lv[ "bottom" ] + span_z * (1 - ratio) * 0.5
		end_z		= lv[ "top"    ] - span_z * (1 - ratio) * 0.5
		center_z	= lv[ "bottom" ] + span_z * 0.5

		xc	= "east"  if "e" in corner else "west"
		yc	= "north" if "n" in corner else "south"

		span_x		= (lv[ "east"  ] - lv[ "west"  ]) * width
		span_y		= (lv[ "north" ] - lv[ "south" ]) * width

		span_x		*= 1 if xc == "east"  else -1
		span_y		*= 1 if yc == "north" else -1

		d[ "x" ]	= lv[ xc ]
		d[ "y" ]	= lv[ yc ]
		d[ "z" ]	= np.linspace( start_z,  end_z, 360 )

		start_x		= lv[ xc ]
		center_x	= lv[ xc ]
		end_x		= lv[ xc ]
		start_y		= lv[ yc ]
		end_y		= lv[ yc ]
		center_y	= lv[ yc ]

	if position == "south" or position == "west":
		span_x	*= -1
		span_y	*= -1

	for i, x, y, z in zip( d[ "i" ], d[ "x" ].to_list(), d[ "y" ].to_list(), d[ "z" ].to_list() ):
		ax.plot( [ x, x  + span_x ], [ y, y + span_y ], [ z, z ], color = cm[ i ], alpha = alpha )

	if lv["sport"] == "running" and args.color_key == "speed":
		lbl	= "pace"
		min	= "{}/km".format( fu.second2MS( fu.speed2pace( min / 3.6 ) ) )
		max	= "{}/km".format( fu.second2MS( fu.speed2pace( max / 3.6 ) ) )
	else:
		lbl	= args.color_key
		min	= "{:.1f}{}".format( min, COLORKEY[ args.color_key ] )
		max	= "{:.1f}{}".format( max, COLORKEY[ args.color_key ] )

	size	= 9
	color	= [ 0, 0, 0 ]
	pos		= "center"
	marktext( ax, start_x,  start_y,  start_z,  0, min, size, color, alpha, pos )
	marktext( ax, end_x,    end_y,    end_z,    0, max, size, color, alpha, pos )
	marktext( ax, center_x, center_y, center_z, 0, lbl, size, color, alpha, pos )


def findinterval( x ):
	e	= np.floor(np.log10( x ) )
	m	= x / (10 ** e)

	if ( m <= 2 ):
		r	= 1
	elif ( m <= 5 ):
		r	= 2
	else:
		r	= 5
	
	r	*= (10 ** (e-1))
	
	return ( int( r ) )


def dmformat( di ):
	e	= 0 - np.floor( np.log10( di ) )
	if ( 0 < e ):
		f	= "%." + "{:.0f}".format( 0 - np.floor( np.log10( di ) ) ) + "f"
	else:
		f	= "%.0f"
	return ( f )


def marktext( ax, x, y, z, dotsize, text, textsize, color, av, align ):
	ax.scatter(	x, y, z, s = dotsize,	color = color,	alpha = av )
	ax.text(	x, y, z, text,			color = color,	alpha = av, size = textsize, ha = align, va = "bottom" )


def get_map( axis, size_idx, lv ):

	# finding zoom level
	# reference: https://wiki.openstreetmap.org/wiki/Zoom_levels
	# reference: https://wiki.openstreetmap.org/wiki/Tiles
	
	ZOOM_SCALE		= [ 360,
		180,	90,		45,		22.5, 	11.25, 	
		5.625, 	2.813,	1.406,	0.703,	0.352,	
		0.176,	0.088,	0.044,	0.022,	0.011,	
		0.005,	0.003,	0.001,	0.0005, 0.00025
	]
	TILE_SIZE		= 256.0

	size	= MAP_RESOLUTION[ size_idx ]
	span	= lv[ "vh_span" ] * TILE_SIZE / size

	for zoom_level in range( 1, len( ZOOM_SCALE) + 1 ):
		if (span / lv[ "Ch" ]) > ZOOM_SCALE[ zoom_level ]:
			break
			
	zoom_level	-= 1
	
	map_span_by_size	= (K * lv[ "Rcv" ]) / (2 ** zoom_level) * (size / TILE_SIZE)
	size	= int( np.ceil( size * (lv[ "vh_span" ] / map_span_by_size) ) )

	print_v( "  reruested max map size = {} pixels (equals to {:.3f}km span)".format( MAP_RESOLUTION[ size_idx ], map_span_by_size ) )
	if not args.quiet:	print( "  zoom_level = {}, map size = {} pixels".format( zoom_level, size ) )
	
	context	= staticmaps.Context()
	context.set_tile_provider( staticmaps.tile_provider_OSM )	
	context.set_zoom( zoom_level )	
	context.set_center( staticmaps.create_latlng( lv[ "v_cntr_deg" ], lv[ "h_cntr_deg" ] ) )
	image = context.render_cairo( size, size )

	# image.write_to_png("_map_img.png")
	
	buf = image.get_data()

	arri	= np.ndarray( shape=( size, size, 4 ), dtype = np.uint8, buffer = buf ).astype(np.uint8)
	ar		= np.array( arri / 255.0, dtype = np.float16 )
	arr		= np.ndarray( shape=( size, size, 4 ), dtype = np.float16 )
	
	for x in range( size ):
		for y in range( size ):
			arr[ y ][ (size - 1) - x ]	= [ ar[ x ][ y ][ 2 ], ar[ x ][ y ][ 1 ], ar[ x ][ y ][ 0 ], args.map_alpha ]

	surface_x	= [ [x] for x in np.linspace( lv[ "west"  ],  lv[ "east"  ],  size ) ]
	surface_y	= [  y  for y in np.linspace( lv[ "south" ],  lv[ "north" ] , size ) ]

	stride	= 1
	axis.plot_surface( surface_x, surface_y, np.atleast_2d( lv[ "bottom" ] ), rstride = stride, cstride = stride, facecolors = arr, shade = False )

	return	arr

def command_line_handling():
	parser	= argparse.ArgumentParser( description = "plots 3D course map in from .fit file" )
	qv_grp	= parser.add_mutually_exclusive_group()
	parser.add_argument( "input_file",				help = "input file (.fit or .gpx format)" )
	parser.add_argument( "-z", "--z_axis",			help = "z_axis data", 	choices = COLORKEY.keys(), default = "altitude" )
	parser.add_argument( "-e", "--elevation",		help = "view setting: elevation", 			type = float, default =  60 )
	parser.add_argument( "-a", "--azimuth",			help = "view setting: azimuth", 			type = float, default = -86 )
	parser.add_argument( "-m", "--map_resolution",	help = "map resolution",		choices = [ "low", "mid", "high", "off" ], default = "low" )
	parser.add_argument( "-f", "--alt_filt",		help = "altitude filtering",	choices = [ "norm", "avg", "off" ], default = "avg" )
	parser.add_argument(       "--start",			help = "set start point", 					type = float, default =   0 )
	parser.add_argument(       "--fin",				help = "set finish point", 					type = float, default = float("inf") )
	parser.add_argument( "-t", "--thining_factor",	help = "data point thining out ratio",		type = int,   default =   1 )
	parser.add_argument( "-b", "--map_alpha",		help = "view setting: map alpha on base", 	type = float, default = 0.1 )
	parser.add_argument( "-c", "--curtain_alpha",	help = "view setting: curtain alpha", 		type = float, default = 0.1 )
	parser.add_argument( "-k", "--color_key",		help = "color keying data", 	choices = COLORKEY.keys(), default = "distance" )
	parser.add_argument(       "--colorbar",		help = "horizontal colorbar position", type=ascii )
	parser.add_argument(       "--colorbarV",		help = "vertical colorbar position" )
	parser.add_argument(       "--colorbarall",		help = "show colorbar all sides",	action = "store_true" )
	parser.add_argument( "-n", "--negative_alt",	help = "negative altitude enable",	action = "store_true" )
	parser.add_argument( "-o", "--output_to_file",	help = "output to file = ON",		action = "store_true" )
	parser.add_argument( "-p", "--pickle_output",	help = "output to .pickle = ON",	action = "store_true" )
	parser.add_argument( 	   "--screen_off",		help = "output to screen = OFF",	action = "store_true" )
	parser.add_argument( 	   "--gifanm",			help = "make GIF animation",		action = "store_true" )
	qv_grp.add_argument( "-v", "--verbose", 		help = "verbose mode",				action = "store_true" )
	qv_grp.add_argument( "-q", "--quiet", 			help = "quiet mode",				action = "store_true" )
	
	return	parser.parse_args()


def show_given_parameters( output_filename ):
	if args.map_resolution == "off":
		map_setting	= "no map shown"
	else:
		map_setting	= "{} (max resolution = {} pixels)".format( args.map_resolution, MAP_RESOLUTION[ args.map_resolution ] )

	if args.fin == float( "inf" ):
		finish_setting	= "maximum"
	else:
		finish_setting	= "{:4.1f}km".format( args.fin )
		
	print( "setting:" )
	print( "  input file        = \"{}\"˚".format( args.input_file ) )
	print( "  elevation         = {:4}˚".format( args.elevation ) )
	print( "  azimuth           = {:4}˚".format( args.azimuth ) )
	print( "  map_resolution    = {}".format( map_setting ) )
	print( "  altitude filter   = {}".format( args.alt_filt ) )
	print( "  negative alt en   = {}".format( args.negative_alt ) )
	print( "  plot start        = {:4.1f}km".format( args.start ) )
	print( "  plot finish       = {}".format( finish_setting ) )
	print( "  thining out ratio = {}".format( args.thining_factor ) )
	print( "  alpha for map     = {}".format( args.map_alpha ) )
	print( "  alpha for curtain = {}".format( args.curtain_alpha ) )
	print( "  verbose/quiet     = {}/{}".format( args.verbose, args.quiet ) )
	print( "  output_to_file    = {}{}".format( args.output_to_file, ", file name: \"" + output_filename + "\"" if args.output_to_file else "" )  )


def print_v( s ):
	if args.verbose:
		print( s  )


def make_gif_mp( base_name, fig ):
	dir_name	= "temp_3d_" + base_name + "/"
	file_name	= dir_name + base_name
	subprocess.call( "mkdir " + dir_name, shell=True)
	fig.set_size_inches( 13, 11 )

	n	= 720
	for i in range( n ):
		print( "plotting rotating image {:3}/{}".format( i, n ) )
		elv		= (np.cos( 1 * (i / n) * 2 * np.pi) ) * 0.5 + 0.5
		
		plt.gca().view_init( azim = i - 90, elev = 84 * elv + 5 )
		plt.savefig( file_name + ("%03d" % i) + ".png" )
	
	if not args.quiet: print( "  converting GIF files into an animation file" )
	cmd = "convert -delay 4 -layers Optimize " + dir_name + base_name+ "*.png " + base_name + ".gif" # using "ImageMagick" command
	subprocess.call( cmd, shell = True ) 
	subprocess.call( "rm -rf " + dir_name, shell=True )
	

def smooth( d, w ):
	return np.convolve( d, w, mode = 'same' )[ len( w )// 2 : -len( w ) // 2 ]


def marker_index( data, marker_list ):
	d	= np.array( data )
	idx	= [ np.argmin( np.abs( d - v ) ) for v in marker_list ]
	return dict( zip( marker_list, idx ) )
	

if __name__ == "__main__":
	args	= command_line_handling()
	main()

