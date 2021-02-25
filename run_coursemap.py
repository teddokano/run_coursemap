#!/usr/bin/env python3

# run_coursemap.py
# 
# script for running course map in 3D. 
# plotting 3D course from .fit file
# 
# usage:  run_coursemap.py data.fit
#
# Tedd OKANO, Tsukimidai Communications Syndicate 2021
# Version 0.8.1 26-February-2021

# Copyright (c) 2021 Tedd OKANO
# Released under the MIT license
# https://opensource.org/licenses/mit-license.php

import	fitpandas
import	fitpandas_util as fu
import	staticmaps
import	pprint
import	matplotlib.pyplot as plt
import	numpy as np
import	os.path
import	sys
import	argparse
import	datetime
from	mpl_toolkits.mplot3d import Axes3D
import	pytz
from 	timezonefinder import TimezoneFinder


FOOTNOTE		= "plotted by 'run_coursemap'\nhttps://github.com/teddokano/run_coursemap"
K				= 40075.016686
OVERSIZE_RATIO	= 1.1
MAP_RESOLUTION	= { "low": 256, "mid": 512, "high": 1024 }

REQUIRED_DATA_COLUMNS	= [ 	
	"distance", 
	"altitude", 
	"position_long", 
	"position_lat"
]


def main():	
	file_name, file_ext = os.path.splitext( args.input_file )

	if ".fit" != file_ext.lower():
		print( "cannot read .fit format file only" )
		sys.exit( 1 )

	print_v( "\"{}\" started".format( sys.argv[ 0 ] )  )
		
	output_filename	= "_".join( sys.argv ) + ".png"

	if args.verbose:
		print( "setting:" )
		print( "  elevation         = {}˚".format( args.elevation ) )
		print( "  azimuth           = {}˚".format( args.azimuth ) )
		print( "  map_resolution    = {} (max resolution = {} pixels)".format( args.map_resolution, MAP_RESOLUTION[ args.map_resolution ] )  )
		print( "  no_map            = {}".format( args.no_map ) )
		print( "  alpha for map     = {}".format( args.map_alpha ) )
		print( "  alpha for curtain = {}".format( args.curtain_alpha ) )
		print( "  output_to_file    = {}{}".format( args.output_to_file, ", file name: \"" + output_filename + "\"" if args.output_to_file else "" )  )

	#####
	##### .fit file reading
	#####
	if not args.quiet: print( "reading file: \"{}\"".format( args.input_file )  )

	data, s_data, units	= fitpandas.get_workout( args.input_file )

	#####
	##### plot range calculation
	#####
	if not args.quiet: print( "calculating plot range..." )

	data[ "distance"      ]	= data[ "distance"      ].apply( lambda x: x / 1000.0 )
	data[ "position_lat"  ]	= data[ "position_lat"  ].apply( fu.semicircles2dgree )
	data[ "position_long" ]	= data[ "position_long" ].apply( fu.semicircles2dgree )

	data	= data.dropna( subset = REQUIRED_DATA_COLUMNS )
	data	= data[ (data[ "distance" ] >= args.start) & (data[ "distance" ] <= args.fin) ]
	data.reset_index(inplace=True, drop=True)	

	lim_val	= limit_values( data )

	#####
	##### plot settings
	#####
	fig	= plt.figure( figsize=( 11, 11 ) )
	ax	= fig.add_subplot( 111, projection = "3d" )

	# ax.set_title( "course plot of " + args.input_file  )
	fig.text( 0.2, 0.92, "course plot by \"" + args.input_file + "\"", fontsize = 9, alpha = 0.5, ha = "left", va = "top" )	
	fig.text( 0.8, 0.92, info( s_data, lim_val ), fontsize = 9, alpha = 0.5, ha = "right", va = "top" )	
	fig.text( 0.8, 0.1, FOOTNOTE, fontsize = 9, alpha = 0.5, ha = "right" )	

	if not args.quiet:
		print( "plot values:" )
		print( "  latitude  - north  : {:+.5f}˚ as {:+.3f}km".format( fu.semicircles2dgree( s_data[ "nec_lat"   ] ), lim_val[ "north" ] )  )
		print( "            - south  : {:+.5f}˚ as {:+.3f}km".format( fu.semicircles2dgree( s_data[ "swc_lat"   ] ), lim_val[ "south" ] )  )
		print( "  longitude - east   : {:+.5f}˚ as {:+.3f}km".format( fu.semicircles2dgree( s_data[ "nec_long"  ] ), lim_val[ "east"  ] )  )
		print( "            - west   : {:+.5f}˚ as {:+.3f}km".format( fu.semicircles2dgree( s_data[ "swc_long"  ] ), lim_val[ "west"  ] )  )
		print( "  altitude  - top    : {:.1f}m".format( lim_val[ "top" ] )  )
		print( "            - bottom : {:.1f}m".format( lim_val[ "bottom" ] )  )
		print( "  course distance    : {:.3f}km".format( data.iloc[ -1 ][ "distance" ] - data.iloc[ 0 ][ "distance" ])  )

	#####
	##### getting/drawing map
	#####
	if not args.no_map:
		if not args.quiet: print( "getting map data and draw..." )
		map_arr	= get_map( ax, args.map_resolution, lim_val )
	
	#####
	##### 3D course plot
	#####
	if not args.quiet: print( "3D prot in progress..." )
	plot( ax, data, lim_val )

	# make_gif_mp( "-".join( sys.argv ) ) # <-- to make GIF animation. enabling this will take time to process

	#####
	##### output to file | screen
	#####
	ax.view_init( args.elevation, args.azimuth )

	if args.output_to_file:
		if not args.quiet: print( "output to file..." )
		plt.savefig( output_filename, dpi=600, bbox_inches="tight", pad_inches=0.05 )

	if not args.quiet: print( "output to screen..." )
	plt.show()


def limit_values( data ):	
	stat	= data.describe()
	
	n_deg		= stat[ "position_lat"  ][ "max" ]
	s_deg		= stat[ "position_lat"  ][ "min" ]
	e_deg		= stat[ "position_long" ][ "max" ]
	w_deg		= stat[ "position_long" ][ "min" ]
	v_start_deg	= data[ "position_lat"  ][ 0 ]
	h_start_deg	= data[ "position_long" ][ 0 ]
	v_start_deg	= data.iloc[ 0 ][ "position_lat" ]
	h_start_deg	= data.iloc[ 0 ][ "position_long" ]
 
	v_cntr_deg	= (n_deg - s_deg) / 2 + s_deg
	h_cntr_deg	= (e_deg - w_deg) / 2 + w_deg

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
	
	limit_values	= {
		"v_cntr_deg":	v_cntr_deg,
		"h_cntr_deg":	h_cntr_deg,
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
	
	print_v( "  map center: latitude = {}˚, longitude = {}˚".format( v_start_deg, h_start_deg ) )
	
	return limit_values


def get_localtimef( v, h, dt ):
	tf		= TimezoneFinder()
	tz		= pytz.timezone( tf.timezone_at( lat = v, lng = h )  )
	offset	= tz.utcoffset( dt )
	seconds	= offset.total_seconds()
	return "{} (UTC{:0=+3}{:02} {})".format( dt + offset, int( seconds // 3600 ), int((seconds % 3600) // 60), tz )


def info( s, lv ):
	dt	= get_localtimef( lv[ "v_cntr_deg" ], lv[ "h_cntr_deg" ], s[ "start_time" ] )
	sp	= s[ "sport" ]
	
	if sp == "running":
		avg	= "{}/km".format( fu.second2MS( fu.speed2pace( s[ "avg_speed" ] ) ) )
	else:
		avg	= "{:.2f}km/h".format( s[ "avg_speed" ] * 3.6 )
	"""
	if sp in fu.SYMBOL_CHAR.keys():
		print( fu.SYMBOL_CHAR[ sp ] )
		sp	= fu.SYMBOL_CHAR[ sp ] + " " + sp
	"""
	
	str	= "{} for {:.3f}km, {} (avg:{})".format( sp, s[ "total_distance" ] / 1000.0, fu.second2HMS( s[ "total_timer_time" ] ), avg )

	print_v( "  {}\n  started on {}".format( str, dt ) )
	
	return "{}\n{}".format( str, dt )


def plot( ax, data, lv ):

	##### data preparation
	#####	convert position data from degree (lat, long) to kilometer (offset-zero = start point)

	data[ "position_lat"  ]	= data[ "position_lat"  ].apply( lambda y: lv[ "Cv" ] * (y - data[ "position_lat"  ][ 0 ]) )
	data[ "position_long" ]	= data[ "position_long" ].apply( lambda x: lv[ "Ch" ] * (x - data[ "position_long" ][ 0 ]) )

	span	= lv[ "vh_span" ]

	ds	= data[ "distance" ].tolist()
	dm_interval	= findinterval( ds[ -1 ] - ds[ 0 ] )	# finding distance marker interval

	print_v( "  distance marker interval {}km".format( dm_interval ) )

	#####
	##### start plotting
	#####	

	ax.set_xlim( [ lv[ "west"   ],  lv[ "east"  ] ] )
	ax.set_ylim( [ lv[ "south"  ],  lv[ "north" ] ] )
	ax.set_zlim( [ lv[ "bottom" ],  lv[ "top"   ] ] )

	trace_lngth	= len( data[ "altitude" ] )
	cm			= plt.get_cmap( "jet" )
	cm_interval	= [ i / trace_lngth for i in range(1, trace_lngth + 1) ]
	cm			= cm( cm_interval )

	dist_marker	= (ds[ 0 ] // dm_interval + 1) * dm_interval
	dm_format	= dmformat( dm_interval )

	xs	= data[ "position_long" ].tolist()
	ys	= data[ "position_lat"  ].tolist()
	zs	= data[ "altitude"      ].tolist()

	count		= 0
	 
	z_min	= lv[ "bottom" ]
	for x, y, z in zip( xs, ys, zs ):
		cc	= cm[ count ]
		
		ax.plot( [ x, x ], [ y, y ], [ z, z_min ], color = cc, alpha = args.curtain_alpha )
		
		if ( dist_marker < ds[ count ] ):
			marktext( ax, xs[  count ], ys[ count ], zs[ count ], 10, (dm_format % dist_marker) + "km", 10, cc, 0.99, "center" )
			dist_marker	+= dm_interval

		count	+= 1
	
	ax.plot( xs, ys, z_min, color = [ 0, 0, 0 ], alpha = 0.1 )	# course shadow plot on bottom
	ax.plot( xs, ys, zs,    color = [ 0, 0, 0 ], alpha = 0.2 )	# course plot on trace edge
	
	marktext( ax, xs[  0 ], ys[  0 ], zs[  0 ], 200, "start", 20, [ 0, 1, 0 ], 0.5, "left" )
	marktext( ax, xs[ -1 ], ys[ -1 ], zs[ -1 ], 200, "fin",   20, [ 1, 0, 0 ], 0.5, "right" )
	
	marktext( ax, lv[ "west"   ], lv[ "v_cntr" ], z_min, 0, "W", 12, [ 0, 0, 0 ], 0.2, "center" )
	marktext( ax, lv[ "east"   ], lv[ "v_cntr" ], z_min, 0, "E", 12, [ 0, 0, 0 ], 0.2, "center" )
	marktext( ax, lv[ "h_cntr" ], lv[ "south"  ], z_min, 0, "S", 12, [ 0, 0, 0 ], 0.2, "center" )
	marktext( ax, lv[ "h_cntr" ], lv[ "north"  ], z_min, 0, "N", 12, [ 0, 0, 0 ], 0.2, "center" )
	
	ax.set_xlabel( "longitude (-):west / (+): east\n[km]"  )
	ax.set_ylabel( "latiitude (-):south / (+): north\n[km]" )
	ax.set_zlabel( "altitude [m]" )
	ax.grid()
	
	return	limit_values


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
	
	return ( r )


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
	context	= staticmaps.Context()
	context.set_tile_provider( staticmaps.tile_provider_OSM )
	
	# finding zoom level
	# reference: https://wiki.openstreetmap.org/wiki/Zoom_levels
	# reference: https://wiki.openstreetmap.org/wiki/Tiles
	
	ZOOM_SCALE		= [ 360, 180, 90, 45, 22.5, 11.25, 5.625, 2.813, 1.406, 0.703, 0.352, 0.176, 0.088, 0.044, 0.022, 0.011, 0.005, 0.003, 0.001, 0.0005, 0.00025 ]
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
	
	context.set_zoom( zoom_level )	
	context.set_center( staticmaps.create_latlng( lv[ "v_cntr_deg" ], lv[ "h_cntr_deg" ] ) )
	image = context.render_cairo( size, size )

	# image.write_to_png("_map_img.png")
	
	buf = image.get_data()

	arri = np.ndarray( shape=( size, size, 4 ), dtype = np.uint8, buffer = buf )
	ar	= [ x / 255.0 for x in arri ]
	ar	= np.array( ar )
	
	arr	= np.ndarray( shape=( size, size, 4 ), dtype = np.float32 )
	for x in range( size ):
		for y in range( size ):
			arr[ y ][ (size - 1) - x ]	= [ ar[ x ][ y ][ 2 ], ar[ x ][ y ][ 1 ], ar[ x ][ y ][ 0 ], args.map_alpha ]

	surface_x	= [ [x] for x in np.linspace( lv[ "west"  ],  lv[ "east"  ],  size ) ]
	surface_y	= [  y  for y in np.linspace( lv[ "south" ],  lv[ "north" ] , size ) ]

	stride	= 1
	axis.plot_surface( surface_x, surface_y, np.atleast_2d( lv[ "bottom" ] ), rstride = stride, cstride = stride, facecolors = arr, shade = False )
	
	return	arr


def command_line_handling():
	parser		= argparse.ArgumentParser( description = "plots 3D course map in from .fit file" )
	map_group	= parser.add_mutually_exclusive_group()
	qv_group	= parser.add_mutually_exclusive_group()
	
	parser.add_argument( "-e", "--elevation",		help = "view setting: elevation", 			type = float, default =  60 )
	parser.add_argument( "-a", "--azimuth",			help = "view setting: azimuth", 			type = float, default = -86,  )
	parser.add_argument(       "--start",			help = "set start point", 					type = float, default =   0,  )
	parser.add_argument(       "--fin",				help = "set finish point", 					type = float, default = float("inf"),  )
	parser.add_argument( "-b", "--map_alpha",		help = "view setting: map alpha on base", 	type = float, default =  0.1,  )
	parser.add_argument( "-c", "--curtain_alpha",	help = "view setting: curtain alpha", 		type = float, default =  0.1,  )
	parser.add_argument( "-o", "--output_to_file", 	help = "output to file = ON", action = "store_true" )
	parser.add_argument( "input_file",				help = "input file (.fit format)" )
	qv_group.add_argument( "-v", "--verbose", 		help = "verbose mode", action = "store_true" )
	qv_group.add_argument( "-q", "--quiet", 		help = "quiet mode",   action = "store_true" )
	map_group.add_argument( "-m", "--map_resolution", 	help = "map resolution", default = "low", choices=[ "low", "mid", "high" ] )
	map_group.add_argument( "-n", "--no_map", 			help = "no map shown", action = "store_true" )
	
	return	parser.parse_args()


def print_v( s ):
	if args.verbose:
		print( s  )


def arktext( ax, x, y, z, dotsize, text, textsize, color, av, align ):
	ax.scatter(   x, y, z, s = dotsize,	color = color,	alpha = av )
	ax.text( 	  x, y, z, text,		color = color,	alpha = av, size = textsize, ha = align, va = "bottom" )


def save_gif_mp( v ):
	file_name, i	= v
	elv		= (np.cos( 1 * (i / 720) * 2 * np.pi) ) * 0.5 + 0.5
	print( "plotting rotating image " + ("%3d" % i) )
	
	plt.gca().view_init( azim = i - 90, elev = 84 * elv + 5 )
	plt.savefig( file_name + ("%03d" % i) + ".png" )


def make_gif_mp( base_name ):
	print( "make_gif" )
	dir_name	= "temp_3d_" + base_name + "/"
	file_name	= dir_name + base_name
	subprocess.call( "mkdir " + dir_name, shell=True)
	fig.set_size_inches( 13, 11 )

	for i in range( 720 ):
		save_gif_mp( (file_name, i) )
		
	cmd = "convert -delay 4 -layers Optimize " + dir_name + base_name+ "*.png " + base_name + ".gif"
	subprocess.call(cmd, shell=True) 
	subprocess.call( "rm -rf " + dir_name, shell=True )
	
	
if __name__ == "__main__":
	args	= command_line_handling()
	main()
