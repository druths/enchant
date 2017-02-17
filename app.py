import os, os.path
import uuid
import logging
import json

from flask import Flask, render_template, request, send_from_directory 
from flask.ext.socketio import SocketIO, emit, join_room, leave_room
from werkzeug.routing import BaseConverter
from werkzeug.utils import secure_filename

logger = logging.getLogger(os.path.basename(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# for image upload
#app.config['UPLOAD_FOLDER'] = ??
#app.config['MAX_CONTENT_PATH'] = ??
IMAGE_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__),'upload','images')
ALLOWED_IMAGE_EXTENSIONS = set(['png','jpg','jpeg','gif'])

NOTEBOOKS_FOLDER = os.path.join(os.path.dirname(__file__),'notebooks')

socketio = SocketIO(app)

DEFAULT_NAMESPACE = '/'
JSON_OK_RESPONSE = '{"result":"ok"}'

#####
# outbound message types
NEW_HTML_MSG = 'html added'
NEW_IMAGE_MSG = 'image added'
NEW_TABLE_MSG = 'table added'
NEW_TEXT_MSG = 'text added'

REPLAY_DONE_MSG = 'replay done'

#####
# Block types
HTML_TYPE = 'html'
IMAGE_TYPE = 'image'
TABLE_TYPE = 'table'
TEXT_TYPE = 'text'

BLOCK_TYPES = [HTML_TYPE,IMAGE_TYPE,TABLE_TYPE,TEXT_TYPE]

#####
# Notebook management
def save_to_notebook(notebook,content,block_type):
	
	nb_dir = os.path.join(NOTEBOOKS_FOLDER,notebook)

	# if the directory doesn't exist, create it
	if not os.path.exists(nb_dir):
		logger.info('creating directory for notebook: %s' % nb_dir)
		os.mkdir(nb_dir)

	# find the latest block
	block_files = filter(lambda x: x.startswith('block'), os.listdir(nb_dir))
	block_indices = [int(x.replace('block','').rsplit('.',1)[0]) for x in block_files]
	block_indices.append(-1)
	next_block_idx = max(block_indices) + 1

	# create the file
	block_fname = os.path.join(nb_dir,'block%d.%s' % (next_block_idx,block_type))
	logger.debug('writing content to %s' % block_fname)
	fh = open(block_fname,'w')
	fh.write(content)
	fh.close()

	return

def replay_notebook_blocks(notebook):
		
	nb_dir = os.path.join(NOTEBOOKS_FOLDER,notebook)

	# if the directory doesn't exist, nothing to do
	if not os.path.exists(nb_dir):
		# nothing to replay
		return

	block_files = filter(lambda x: x.startswith('block'), os.listdir(nb_dir))
	def block_index(fname):
		return int(fname.replace('block','').rsplit('.',1)[0])
	block_files.sort(key=block_index)

	for bfname in block_files:
		block_type = bfname.rsplit('.',1)[1]
		full_fname = os.path.join(nb_dir,bfname)

		msg_type = None
		data = None

		if block_type == IMAGE_TYPE:
			msg_type = NEW_IMAGE_MSG

			# load the data as a JSON
			data = json.load(open(full_fname,'r'))

		elif block_type == HTML_TYPE:
			msg_type = NEW_HTML_MSG
			data = open(full_fname,'r').read()

		elif block_type == TABLE_TYPE:
			msg_type = NEW_TABLE_MSG
			data = json.load(open(full_fname,'r'))

		elif block_type == TEXT_TYPE:
			msg_type = NEW_TEXT_MSG
			data = open(full_fname,'r').read()
		else:
			logger.error('unknown block type encountered: %s' % block_type)
			raise Exception, 'unknown block type encountered: %s' % block_type

		emit(msg_type,data,namespace=DEFAULT_NAMESPACE)

	emit(REPLAY_DONE_MSG,namespace=DEFAULT_NAMESPACE)

#####
# serve necessary static content
#####
@app.route('/static/images/<filename>')
def serve_image_data(filename):
	return send_from_directory(IMAGE_UPLOAD_FOLDER,filename)	

#####
# methods for submitting content to the notebook
#####

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@app.route('/submit/image/<notebook>',methods=['POST'])
def submit_image(notebook):

	# store the image to a file
	if 'file' not in request.files:
		return '{"result":"failed","message":"no file specified"}'	

	header = request.form
	title = None
	if 'title' in header:
		title = header['title']
	else:
		return '{"result":"failed","message":"no title specified"}'

	timestamp = None
	if 'timestamp' in header:
		timestamp = header['timestamp']
	else:
		return '{"result":"failed","message":"no timestamp specified"}'

	# get the file
	f = request.files['file']
	

	if not allowed_file(f.filename):
		return '{"result":"failed","message":"not a supported image type"}'

	# make a unique filename
	ext = ''
	if '.' in f.filename:
		ext = '.%s' % f.filename.rsplit('.',1)[1].lower()
	filename = '%s%s' % (uuid.uuid4(),ext)

	# store the file
	f.save(os.path.join(IMAGE_UPLOAD_FOLDER, filename))

	# notify all notebook users
	data = {'title':title,'timestamp':timestamp,'filename':filename}
	save_to_notebook(notebook,json.dumps(data),IMAGE_TYPE)

	emit(NEW_IMAGE_MSG, data, room=notebook, namespace=DEFAULT_NAMESPACE, broadcast=True)

	return JSON_OK_RESPONSE

@app.route('/submit/table/<notebook>',methods=['POST'])
def submit_table(notebook):
	
	table_data = json.loads(request.data)

	if len(table_data) == 0:
		return '{"result":"failed","message":"no content delivered"}'

	save_to_notebook(notebook,json.dumps(table_data),TABLE_TYPE)
	emit(NEW_TABLE_MSG, data, room=notebook, namespace=DEFAULT_NAMESPACE, broadcast=True)

	return JSON_OK_RESPONSE

@app.route('/submit/html/<notebook>',methods=['POST'])
def submit_html(notebook):
	
	html_data = request.data
	
	if len(html_data) == 0:
		return '{"result":"failed","message":"no content delivered"}'

	save_to_notebook(notebook,html_data,HTML_TYPE)
	emit(NEW_HTML_MSG, html_data, room=notebook, namespace=DEFAULT_NAMESPACE, broadcast=True)

	return JSON_OK_RESPONSE

@app.route('/submit/text/<notebook>',methods=['POST'])
def submit_text(notebook):
	
	text_content = request.data

	if len(text_content) == 0:
		return '{"result":"failed","message":"no content delivered"}'

	save_to_notebook(notebook,text_content,TEXT_TYPE)
	emit(NEW_TEXT_MSG, text_content, room=notebook, namespace=DEFAULT_NAMESPACE, broadcast=True)

	return JSON_OK_RESPONSE

#####
# all websocket related notebook stuff
#####
"""
@app.route('/static/<path:path>')
def static_resource(path):
	print 'fetching a static resource: %s' % path
	return app.send_static_file(path)
"""

@app.route('/')
def index():
	# TODO: List out the notebooks available
	return render_template('index.html')

@app.route('/notebook/<name>')
def load_notebook(name):
	# TODO: Check if the notebook with that name exists

	# TODO: generate the HTML that supplies that notebook...

	return render_template('notebook.html')

@socketio.on('connect') #, namespace='/test')
def test_connect():
    emit('my response', {'data': 'Connected'})

@socketio.on('disconnect') #, namespace='/test')
def test_disconnect():
    print('Client disconnected')

@socketio.on('join')
def on_join(data):
	notebook = data['notebook']
	join_room(notebook)
	print 'joining notebook %s' % notebook

	# replay the notebook events
	replay_notebook_blocks(notebook)

	# TODO: Handle race conditions here...

@socketio.on('leave')
def on_leave(data):
	notebook = data['notebook']
	leave_room(notebook)
	print 'leaving notebook %s' % notebook

def main():
	# setup the debugger
	logging.basicConfig(level=logging.DEBUG)

	# start the server
	socketio.run(app)

if __name__ == '__main__':
	main()	
