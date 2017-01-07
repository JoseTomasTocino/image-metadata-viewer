#!/usr/bin/env python
# coding: utf-8

import subprocess
import requests
import logging
import json
from StringIO import StringIO
import os
from bottle import route, run, request
from bottle import jinja2_view as view, jinja2_template as template

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

exiftool_location = 'exiftool/exiftool'

@route('/favicon.ico')
def get_favicon():
    return ''

@route('/')
@view('index')
def fetch_data():

    image_location = request.GET.get('img')

    template_data = {
        'state': 0,
        'image_location': image_location,
        'metadata': {}
    }

    if not image_location:
        logging.info("No image location specified")
        
    else:
        template_data['state'] = 1
        logging.info("Fetching image at {}...".format(image_location))
        response = requests.get(image_location)

        if response.status_code != 200:
            logging.error("Problem fetching image :(")
            sys.exit(1)
            
        logging.info("Image fetched properly")
        f = StringIO(response.content)

        logging.info("Running exiftool process...")
        process = subprocess.Popen([exiftool_location, '-g0', '-j', '-c', '%+.6f', '-'],
                                   stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE)
        output, output_err = process.communicate(f.read())

        # TODO: check for errors running process

        logging.info("Decoding JSON from output...")
        
        metadata = json.loads(output)[0]       
        # Filter metadata components that are not dictionaries
        metadata = {k:v for k,v in metadata.items() if isinstance(v, dict)}

        if 'ExifTool' in metadata:
            del metadata['ExifTool']
        
        # Try to build a summary of information
        basic_info = { }

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

            if set(['ExposureMode','ExposureTime', 'FNumber', 'ISO']) <= set(metadata['EXIF'].keys()):
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


    
    return template_data
    
run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
