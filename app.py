import os, os.path
import sys
import arghandler
import uuid
import logging
import json

from flask import Flask, render_template, request, send_from_directory, Response, redirect, url_for
from flask.ext.socketio import SocketIO, emit, join_room, leave_room
from werkzeug.routing import BaseConverter
from werkzeug.utils import secure_filename
from flask.ext.login import LoginManager, UserMixin, login_required, login_user, logout_user

import user as enchant_user

logger = logging.getLogger(os.path.basename(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# for image upload
#app.config['UPLOAD_FOLDER'] = ??
#app.config['MAX_CONTENT_PATH'] = ??
IMAGE_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__),'upload','images')
ALLOWED_IMAGE_EXTENSIONS = set(['png','jpg','jpeg','gif'])

NOTEBOOKS_FOLDER = os.path.join(os.path.dirname(__file__),'notebooks')

socketio = SocketIO(app)

DEFAULT_NAMESPACE = '/'
JSON_OK_RESPONSE = '{"result":"ok"}'

def json_failed_response(msg):
    """
    Return an error JSON object response.
    """
    return '{"result":"failed","message":"%s"' % msg

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
def create_notebook(username,notebook):
    nb_dir = os.path.join(NOTEBOOKS_FOLDER,username,notebook)

    os.makedirs(nb_dir)

def get_notebook_names(username):
    user_dir = os.path.join(NOTEBOOKS_FOLDER,username)
    return filter(lambda x: not x.startswith('.'),os.listdir(user_dir))

def notebook_exists(username,notebook):
    nb_dir = os.path.join(NOTEBOOKS_FOLDER,username,notebook)

    return os.path.exists(nb_dir)

def save_to_notebook(username,notebook,content,block_type):
    
    nb_dir = os.path.join(NOTEBOOKS_FOLDER,username,notebook)

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

def replay_notebook_blocks(username,notebook):
    logger.info('replaying blocks for %s-%s' % (username,notebook))
        
    nb_dir = os.path.join(NOTEBOOKS_FOLDER,username,notebook)

    # if the directory doesn't exist, nothing to do
    if not os.path.exists(nb_dir):
        logger.warn("notebook directory doesn't exist: %s" % nb_dir)

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

        emit(msg_type,data,room=get_nb_room(username,notebook),namespace=DEFAULT_NAMESPACE)

    emit(REPLAY_DONE_MSG,room=get_nb_room(username,notebook),namespace=DEFAULT_NAMESPACE)

def get_nb_room(username,notebook):
    return '%s-%s' % (username,notebook)

#####
# serve necessary static content
#####
@app.route('/static/images/<filename>')
@login_required
def serve_image_data(filename):
    return send_from_directory(IMAGE_UPLOAD_FOLDER,filename)    

#####
# methods for user management
#####

class User(UserMixin):

    def __init__(self,username):
        self.id = username

@login_manager.user_loader
def load_user(username):
    return User(username)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if enchant_user.check_user_password(NOTEBOOKS_FOLDER,username,password):
            user = User(username)
            login_user(user)
            return redirect('/%s' % username)
        else:
            return Response('<p>Login failed</p>')
    else:
        return Response('''
        <form action="" method="post">
            <p><input type=text name=username></p>
            <p><input type=password name=password></p>
            <p><input type=submit value=Login></p>
        </form>
        ''')

"""
@app.route('/settings')
@login_required
def settings():
    pass
"""

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

#####
# methods for submitting content to the notebook
#####

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@app.route('/submit/image/<username>/<notebook>',methods=['POST'])
def submit_image(username,notebook):

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
    save_to_notebook(username,notebook,json.dumps(data),IMAGE_TYPE)

    emit(NEW_IMAGE_MSG, data, room=get_nb_room(username,notebook), namespace=DEFAULT_NAMESPACE, broadcast=True)

    return JSON_OK_RESPONSE

@app.route('/submit/table/<username>/<notebook>',methods=['POST'])
def submit_table(username,notebook):
    
    table_data = json.loads(request.data)

    if len(table_data) == 0:
        return '{"result":"failed","message":"no content delivered"}'

    save_to_notebook(username,notebook,json.dumps(table_data),TABLE_TYPE)
    emit(NEW_TABLE_MSG, data, room=get_nb_room(username,notebook), namespace=DEFAULT_NAMESPACE, broadcast=True)

    return JSON_OK_RESPONSE

@app.route('/submit/html/<username>/<notebook>',methods=['POST'])
def submit_html(username,notebook):
    
    html_data = request.data
    
    if len(html_data) == 0:
        return '{"result":"failed","message":"no content delivered"}'

    save_to_notebook(username,notebook,html_data,HTML_TYPE)
    emit(NEW_HTML_MSG, html_data, room=get_nb_room(username,notebook), namespace=DEFAULT_NAMESPACE, broadcast=True)

    return JSON_OK_RESPONSE

@app.route('/submit/text/<username>/<notebook>',methods=['POST'])
def submit_text(username,notebook):
    
    text_content = request.data

    if len(text_content) == 0:
        return '{"result":"failed","message":"no content delivered"}'

    save_to_notebook(username,notebook,text_content,TEXT_TYPE)
    emit(NEW_TEXT_MSG, text_content, room=get_nb_room(username,notebook), namespace=DEFAULT_NAMESPACE, broadcast=True)

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

@app.route('/favicon.ico')
def favicon():
    return ''

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<username>')
@login_required
def user_home(username):
    # List out the notebooks available
    notebook_names = get_notebook_names(username)
    return render_template('home.html',username=username,notebooks=notebook_names)

@app.route('/<username>/create_notebook')
@login_required
def create_notebook_handler(username):
    notebook_name = request.args.get('notebook_name')
    
    # if the argument wasn't supplied
    if notebook_name is None:
        return json_failed_response('notebook_name not specified')
    
    # check if the notebook already exists
    if notebook_exists(username,notebook_name):
        return json_failed_response('notebook already exists')
    
    # create the notebook
    create_notebook(username,notebook_name)
    
    return JSON_OK_RESPONSE

@app.route('/<username>/notebook/<notebook>')
@login_required
def load_notebook(username,notebook):
    # Check if the notebook with that name exists
    if not notebook_exists(username,notebook):
        return render_template('404_notebook.html')

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
    username,notebook_name = notebook.split('-')
    replay_notebook_blocks(username,notebook_name)

    # TODO: Handle race conditions here...

@socketio.on('leave')
def on_leave(data):
    notebook = data['notebook']
    leave_room(notebook)
    print 'leaving notebook %s' % notebook

#################
def main():
    handler = arghandler.ArgumentHandler('enchantd')
    handler.add_argument('-H','--host',help='the host the server should run on',
                         default='localhost')
    handler.add_argument('-P','--port',help='the port the server should run on',
                         type=int,default=13105)


    args = handler.parse_args()

    # setup the debugger
    logging.basicConfig(level=logging.DEBUG)

    # TODO: setup the login manager
    # login_manager = LoginManager()
    # login_manager.init_app(app)

    # start the server
    socketio.run(app,host=args.host,port=args.port)

if __name__ == '__main__':
    main()  
