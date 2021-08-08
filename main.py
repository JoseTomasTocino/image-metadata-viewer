#!/usr/bin/env python
# coding: utf-8

import datetime
import subprocess
import logging
import json
import os
import sys
from io import BytesIO

import requests
from bottle import route, run, request
from bottle import jinja2_view as view, jinja2_template as template

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXIFTOOL_PATH = 'exiftool/exiftool'


@route('/favicon.ico')
def get_favicon():
    return ''


@route('/ads.txt')
def get_ads():
    return 'google.com, pub-0745898310693904, DIRECT, f08c47fec0942fa0'


@route('/')
@view('index')
def fetch_data():

    image_location = request.GET.get('img')

    template_data = {
        'state': 0,
        'image_location': image_location,
        'metadata': {}
    }

    # If no image location was specified, just return the initial page with no data
    if not image_location:
        logging.info("No image location specified")        
        return template_data

    
    template_data['state'] = 1
    logging.info("Fetching image at {}...".format(image_location))
    response = requests.get(image_location)

    if response.status_code != 200:
        logging.error("Problem fetching image :(")
        template_data['invalid_image'] = "Invalid image"

        return template_data

    logging.info("Image fetched properly")
    f = BytesIO(response.content)

    logging.info("Running exiftool process...")
    process = subprocess.Popen([EXIFTOOL_PATH, '-g0', '-j', '-c', '%+.6f', '-'],
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE)
    output, output_err = process.communicate(f.read())

    # TODO: check for errors running process

    logging.info("Decoding JSON from output...")

    metadata = json.loads(output)[0]
    # Filter metadata components that are not dictionaries
    metadata = {k: v for k, v in metadata.items() if isinstance(v, dict)}

    if 'ExifTool' in metadata:
        del metadata['ExifTool']

    # Try to build a summary of information
    basic_info = {}

    try:
        basic_info['Dimensions'] = u"{} × {} {}".format(
            metadata['File']['ImageWidth'],
            metadata['File']['ImageHeight'],
            metadata['File']['FileType']
        )
    except:
        pass

    if 'EXIF' in metadata:
        if 'Artist' in metadata['EXIF']:
            basic_info['Artist'] = metadata['EXIF']['Artist']

        if 'Copyright' in metadata['EXIF']:
            basic_info['Copyright'] = metadata['EXIF']['Copyright']

        if 'Model' in metadata['EXIF']:
            basic_info['Camera'] = metadata['EXIF']['Model']

        if 'LensModel' in metadata['EXIF']:
            basic_info['LensModel'] = metadata['EXIF']['LensModel']

        if {'ExposureMode', 'ExposureTime', 'FNumber', 'ISO'} <= set(metadata['EXIF'].keys()):
            m = metadata['EXIF']
            basic_info['Exposure'] = '{}, {}, {}, ISO {}'.format(
                m['ExposureMode'], m['ExposureTime'], m['FNumber'], m['ISO']
            )

    if 'Composite' in metadata:
        if 'GPSLongitude' in metadata['Composite'] and 'GPSLatitude' in metadata['Composite']:
            template_data['has_location'] = True

        if 'LensID' in metadata['Composite']:
            basic_info['Lens'] = metadata['Composite']['LensID']

    metadata['Basic'] = basic_info

    template_data['metadata'] = metadata

    # Get a sorted list of metadata keys
    template_data['metadata_sorted_keys'] = sorted(metadata.keys())

    # Try to get the referer
    referer = request.GET.get('page', request.headers.get('Referer', '/'))

    return template_data


run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
