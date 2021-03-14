#!/usr/bin/env python3

# run_coursemap.py
# 
# script for running course map in 3D. 
# plotting 3D course from .fit or .gpx file
# 
# usage:  run_coursemap.py data.fit
#
# Tedd OKANO, Tsukimidai Communications Syndicate 2021
# Version 0.14 14-March-2021

# Copyright (c) 2021 Tedd OKANO
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

	data[ "distance" ]	= data[ "distance" ].apply( lambda x: x / 1000.0 )	# convert from meter to kilometer

	#####
	##### plot range calculation
	#####
	if not args.quiet: print( "calculating plot range..." )

	data	= data.dropna( subset = REQUIRED_DATA_COLUMNS )
	data	= data[ (data[ "distance" ] >= args.start) & (data[ "distance" ] <= args.fin) ]
	data.reset_index( inplace = True, drop = True )	

	lim_val	= fu.limit_values( data, args )

	if args.screen_off and not args.output_to_file:
		print( "no plot processed since \"--screen_off\" option given without \"-o\" (output to file)" )
		return	# do nothing and quit

	#####
	##### plot settings
	#####
	fig	= plt.figure( figsize=( 11, 11 ) )
	ax	= fig.add_subplot( 111, projection = "3d" )

	# ax.set_title( "course plot of " + args.input_file  )
	fig.text( 0.2, 0.92, "course plot by \"" + args.input_file + "\"", fontsize = 9, alpha = 0.5, ha = "left", va = "top" )	
	fig.text( 0.8, 0.92, info( s_data, lim_val ), fontsize = 9, alpha = 0.5, ha = "right", va = "top" )	
	fig.text( 0.8, 0.1, FOOTNOTE + "\n" + (OSM_CREDIT if args.map_resolution != "off" else ""), fontsize = 9, alpha = 0.5, ha = "right" )	

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

	"""
	trace_lngth	= len( data[ "altitude" ] )
	cm			= plt.get_cmap( "jet" )
	cm_interval	= [ i / trace_lngth for i in range(1, trace_lngth + 1) ]
	cm			= cm( cm_interval )
	"""
	cm	= fu.color_map( len( data[ "altitude" ] ) )
	
	dist_marker	= (ds[ 0 ] // dm_interval + 1) * dm_interval
	dm_format	= dmformat( dm_interval )

	xs	= data[ "long_km"  ].tolist()
	ys	= data[ "lat_km"   ].tolist()
	zs	= data[ "altitude" ].tolist()

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
	parser.add_argument( "-e", "--elevation",		help = "view setting: elevation", 			type = float, default =  60 )
	parser.add_argument( "-a", "--azimuth",			help = "view setting: azimuth", 			type = float, default = -86 )
	parser.add_argument( "-m", "--map_resolution",	help = "map resolution",		choices=[ "low", "mid", "high", "off" ], default = "low" )
	parser.add_argument( "-f", "--alt_filt",		help = "altitude filtering",	choices=[ "norm", "avg", "off" ], default = "avg" )
	parser.add_argument(       "--start",			help = "set start point", 					type = float, default =   0 )
	parser.add_argument(       "--fin",				help = "set finish point", 					type = float, default = float("inf") )
	parser.add_argument( "-t", "--thining_factor",	help = "data point thining out ratio",		type = int,   default =   1 )
	parser.add_argument( "-b", "--map_alpha",		help = "view setting: map alpha on base", 	type = float, default = 0.1 )
	parser.add_argument( "-c", "--curtain_alpha",	help = "view setting: curtain alpha", 		type = float, default = 0.1 )
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
	
	
if __name__ == "__main__":
	args	= command_line_handling()
	main()

