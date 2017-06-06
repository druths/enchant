###
# All configurations for the server are stored here

import os, os.path

# Directories
IMAGE_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__),'upload','images')
ALLOWED_IMAGE_EXTENSIONS = set(['png','jpg','jpeg','gif'])

NOTEBOOKS_FOLDER = os.path.join(os.path.dirname(__file__),'notebooks')

