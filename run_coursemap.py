#!/usr/bin/env python3

# run_coursemap.py
# 
# script for running data analisis. 
# plotting 3D course from .csv file
# 
# usage:  run_coursemap.py data.csv
#
# Tedd OKANO, Tsukimidai Communications Syndicate 2021
# Version 0.1 28 January 2021

# Copyright (c) 2021 Tedd OKANO
# Released under the MIT license
# https://opensource.org/licenses/mit-license.php

import	csv
import	pprint
import	matplotlib.pyplot as plt
import	numpy as np
import	sys

from mpl_toolkits.mplot3d import Axes3D
from enum import IntEnum, auto

#####
##### files from command-line
#####

input_files		= sys.argv[ 1 : ]

if 0 == len( input_files ):
	print( "error: no files given to plot" )
	sys.exit( 1 )
	

#####
##### reading data format
#####

class runSeries( IntEnum ):	# copy this class as "Series"
	# colmns of CSV data
	SECONDS		= 0
	DISTANCE	= auto()
	HEARTRATE	= auto()
	SPEED		= auto()
	ALTITUDE	= auto()
	LATITUDE	= auto()
	LONGITUDE	= auto()
	GRADE		= auto()
	TEMPERATURE	= auto()
	BALANCE		= auto()
	CADENCE		= auto()
	VER_OSC		= auto()
	GCT			= auto()
	
	
class bikeSeries( IntEnum ): # copy this class as "Series"
	# colmns of CSV data
	SECONDS		= 0
	DISTANCE	= auto()
	POWER		= auto()
	CADENCE		= auto()	
	HEARTRATE	= auto()
	SPEED		= auto()
	ALTITUDE	= auto()
	LATITUDE	= auto()
	LONGITUDE	= auto()
	GRADE		= auto()
	TEMPERATURE	= auto()
	BALANCE		= auto()


Series	= runSeries
#Series	= bikeSeries

	
def speed2pace( val ):
	v	= float( val )
	if v >= 10.0:
		return 3600 / v
	else:
		return 360


def cadence2pitch( val ):
	return float( val ) * 2.0


def hr2hrr( val ):
	hr_max	= 180.0
	hr_rst	= 48.0
	return ((float( val ) - hr_rst) / (hr_max - hr_rst)) * 100


def findscale( x ):
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
	ax.scatter(   x, y, z, s = dotsize,	color = color,	alpha = av )
#	ax.text( 	  x, y, z, text,		color = [0,0,0],	alpha = .5, size = textsize, ha = align, va = "bottom" )
	ax.text( 	  x, y, z, text,		color = color,	alpha = av, size = textsize, ha = align, va = "bottom" )


#####
#####	preparation for plot
#####


fig	= plt.figure(figsize=(11, 11))
ax	= fig.add_subplot( 111, projection='3d' )

ax.view_init( elev = 45, azim = 45 )

av_wndw		= 6
av_wndw2	= int( av_wndw / 2 )

##### rectangular window
#b			= np.ones(av_wndw)/av_wndw	# mv-avg		
#ax2.text( X_MAX / 2, Y_A2_MIN + (Y_A2_MAX - Y_A2_MIN) * 0.02, "averaging window length =" + str( av_wndw ) + "samples (sample/sec)", size = 9 )
#bx2.text( X_MAX / 2, Y_B2_MIN + (Y_B2_MAX - Y_B2_MIN) * 0.02, "averaging window length =" + str( av_wndw ) + "samples (sample/sec)", size = 9 )
##### /rectangular window


##### hann window
a			= np.linspace( -np.pi, np.pi, av_wndw)
b			= [ 0.5 * (np.cos( z ) + 1.0)	for z in a ]
b			= [ z / sum( b ) for z in b ]
#ax2.text( X_MAX / 2, Y_A2_MIN + (Y_A2_MAX - Y_A2_MIN) * 0.02, "window function: hann, length =" + str( av_wndw ) + " samples (sample/sec)", size = 9 )
#bx2.text( X_MAX / 2, Y_B2_MIN + (Y_B2_MAX - Y_B2_MIN) * 0.02, "window function: hann, length =" + str( av_wndw ) + " samples (sample/sec)", size = 9 )
##### /hann window






#####
#####	read file and plot
#####

alpha_value	= 1.0

for file in input_files: 

	with open( file ) as f:
		reader	= csv.reader( f )
		l	= [row for row in reader]
	
	data	= [ [ float( v ) for v in row ] for row in l ]
	data	= np.array(data).T.tolist()
	
	distance_s	= data[ Series.DISTANCE ][ av_wndw2 : -av_wndw2 ]
	
	lat_s		= data[ Series.LATITUDE  ][ av_wndw2 : -av_wndw2 ]
	lon_s		= data[ Series.LONGITUDE ][ av_wndw2 : -av_wndw2 ]
	alt_s		= np.convolve( data[ Series.ALTITUDE ], b, mode = 'same' )[ av_wndw2 : -av_wndw2 ]

	x_min	= min( lon_s )
	y_min	= min( lat_s )
	z_min	= min( alt_s )

	cx	= np.cos( y_min / 180 * np.pi) * 2 * np.pi * 6378.137
	cx	= cx / 360
	cy	= (2 * np.pi * 6378.137) / 360

	lon_s	= [ (z - x_min) * cx for z in lon_s ]
	lat_s	= [ (z - y_min) * cy for z in lat_s ]

	x_max	= max( lon_s )
	y_max	= max( lat_s )
	z_max	= max( alt_s )

	if (x_max < y_max):
		span	= y_max
	else:
		span	= x_max
	
	span	*= 1.1

	xlim	= [ (x_max / 2) - (span / 2), (x_max / 2) + (span / 2) ]
	ylim	= [ (y_max / 2) - (span / 2), (y_max / 2) + (span / 2) ]

	ax.set_xlim( xlim )
	ax.set_ylim( ylim )
	ax.set_zlim( [ z_min, z_max ] )

	cm=plt.get_cmap('jet')
	
	cm_interval	= [ (i / (len( alt_s ))) for i in range(1, len( alt_s ) + 1) ]
	cm			= cm(cm_interval)

	count	= 0
	dm_interval	= findscale( data[ Series.DISTANCE ][ -1 ] )
	dist_marker	= dm_interval
	dm_format	= dmformat( dm_interval )

	for alt in alt_s:
		xx	= [ lon_s[ count ], lon_s[ count ] ]	
		yy	= [ lat_s[ count ], lat_s[ count ] ]
		zz	= [ alt_s[ count ], z_min ]	
		cc	= cm[ count ]
		
		ax.plot( xx, yy, zz, color = cc, alpha = 0.05 )
		
		if ( dist_marker < distance_s[ count ] ):
			marktext( ax, lon_s[  count ], lat_s[ count ], alt_s[ count ], 10, (dm_format % dist_marker) + "km", 10, cc, 0.99, "center" )
			dist_marker	+= dm_interval

		count	+= 1
			
	ax.plot( lon_s, lat_s, z_min, color = [ 0, 0, 0 ], alpha = 0.2 )
	ax.plot( lon_s, lat_s, alt_s, color = [ 0, 0, 0 ], alpha = 0.2 )
	
	dotsize		= 200
	textsize	=  20
	alpha_value	= 0.5

	marktext( ax, lon_s[  0 ], lat_s[  0 ], alt_s[  0 ], dotsize, "start", textsize, [ 0, 1, 0 ], alpha_value, "left" )
	marktext( ax, lon_s[ -1 ], lat_s[ -1 ], alt_s[ -1 ], dotsize, "fin",   textsize, [ 1, 0, 0 ], alpha_value, "right" )

	alpha_value	*= 0.5	

marktext( ax, xlim[ 0 ], span / 2 + ylim[ 0 ], z_min, 0, "W", 12, [ 0, 0, 0 ], 0.2, "center" )
marktext( ax, xlim[ 1 ], span / 2 + ylim[ 0 ], z_min, 0, "E", 12, [ 0, 0, 0 ], 0.2, "center" )
marktext( ax, span / 2 + xlim[ 0 ], ylim[ 0 ], z_min, 0, "S", 12, [ 0, 0, 0 ], 0.2, "center" )
marktext( ax, span / 2 + xlim[ 0 ], ylim[ 1 ], z_min, 0, "N", 12, [ 0, 0, 0 ], 0.2, "center" )

ax.set_title( "course plot of " + file  )

ax.set_xlabel( "longitude (-):west / (+): east¥n[km]"  )
ax.set_ylabel( "latiitude (-):south / (+): north¥n[km]" )
ax.set_zlabel( "altitude [m]" )

ax.grid()

plt.savefig( "-".join( sys.argv ) + ".png", dpi=600, bbox_inches="tight", pad_inches=0.05 )
plt.show()
