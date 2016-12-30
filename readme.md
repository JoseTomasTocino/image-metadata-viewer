# Image metadata viewer

So I had this Google Chrome's extension called [Send to Jeffrey's Exif Viewer](https://chrome.google.com/webstore/detail/send-to-jeffreys-exif-vie/gogiienhpamfmodmlnhdljokkjiapfck) that allowed users to right-click an image and quickly check the Exif information using [Jeffrey Friedl's Exif viewer](http://exif.regex.info/exif.cgi). It was simple and worked ok.

Problem is, Jeffrey added a reCaptcha to his viewer, rendering my extension useless, so I decided to create my own exif (metadata) viewer. And here it is.

## Technologies

This _image metadata viewer_ uses:

* Python 2.7
* [Bottle web framework](http://bottlepy.org/docs/dev/)
* [Jinja2 template engine](http://jinja.pocoo.org/)
* And more importantly, [Phil Harvey's ExifTool](http://www.sno.phy.queensu.ca/~phil/exiftool/) to get the metadata.

At the end of the day, this app is just a simple web front-end for `exiftool`.

## Deployment

This app is currently deployed on [Heroku: http://metadataviewer.herokuapp.com](https://metadataviewer.herokuapp.com). If you want to deploy it privately or something like that, just fetch the code and run `main.py`. It will start listening at port 5000.

