#!/usr/bin/env python
# coding: utf-8

import datetime
import subprocess
import requests
import logging
import json
from StringIO import StringIO
import pymongo
import os, sys
from bottle import route, run, request
from bottle import jinja2_view as view, jinja2_template as template

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXIFTOOL_PATH = 'exiftool/exiftool'

MONGODB_FULL_URI = os.environ.get('MONGODB_URI')
MONGODB_URI, MONGODB_DB = MONGODB_FULL_URI.rsplit('/', 1)

ELEMENTS_PER_PAGE = 50

@route('/favicon.ico')
def get_favicon():
    return ''


@route('/ads.txt')
def get_ads():
    return 'google.com, pub-0745898310693904, DIRECT, f08c47fec0942fa0'


@route('/list')
@view('list')
def list_images():
    # TODO: add auth

    page = request.GET.get('page', default=0, type=int)

    client = pymongo.MongoClient(MONGODB_FULL_URI)
    db = client[MONGODB_DB]
    total_images = db['images'].find().sort("date", pymongo.DESCENDING)
    num_total_images = total_images.count()
    images = total_images.skip(page * ELEMENTS_PER_PAGE).limit(ELEMENTS_PER_PAGE)
    num_pages = int(num_total_images / ELEMENTS_PER_PAGE)

    page_shortcuts = []

    # Add first three pages
    page_shortcuts.append(0)
    if num_pages > 1: page_shortcuts.append(1)
    if num_pages > 2: page_shortcuts.append(2)

    # Add last two pages
    page_shortcuts.append(num_pages - 1)
    page_shortcuts.append(num_pages - 2)
    page_shortcuts.append(num_pages - 3)

    # Add page before and after current_page
    page_shortcuts.append(page - 1)
    page_shortcuts.append(page + 1)

    # Add current page
    page_shortcuts.append(page)

    # Remove duplicates and sort pages
    page_shortcuts = sorted(set(x for x in page_shortcuts if x >= 0 and x < num_pages))

    return {
        'images': images,
        'current_page': page,
        'total_pages': num_pages,
        'page_shortcuts': page_shortcuts
    }


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
        process = subprocess.Popen([EXIFTOOL_PATH, '-g0', '-j', '-c', '%+.6f', '-'],
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

        # Logging image into mongodb:
        client = pymongo.MongoClient(MONGODB_FULL_URI)
        db = client[MONGODB_DB]

        db['images'].insert_one({
            'ip': request.remote_addr,
            'referrer': referer.strip(),
            'date': datetime.datetime.utcnow(),
            'image': image_location
        })

    return template_data
    
run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
