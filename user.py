import os,os.path
import json
import crypt

from flask_login import UserMixin

from config import *

USER_PROFILE_FNAME = '.user'

class User(UserMixin):

    def __init__(self,username):
        self.id = username

        # check if the user exists
        if not os.path.exists(os.path.join(NOTEBOOKS_FOLDER,username,USER_PROFILE_FNAME)):
            raise Exception('User %s does not exist' % username)

    def get_user_dir(self):
        return os.path.join(NOTEBOOKS_FOLDER,self.id)

    def get_profile_path(self):
        return os.path.join(self.get_user_dir(),USER_PROFILE_FNAME)

    def load_data(self):
        return json.load(open(self.get_profile_path(),'r'))

    def save_data(self,data):
        # BUGBUG: Make this threadsafe
        json.dump(data,open(self.get_profile_path(),'w'))

    def is_admin(self):
        return self.load_data()['is_admin']

    def set_admin(self,is_admin):
        udata = self.load_data()
        udata['is_admin'] = is_admin
        self.save_data(udata)

    def check_password(self,password):
        user_dir = self.get_user_dir()

        if not os.path.exists(user_dir):
            return False
        else:
            udata = self.load_data()
    
            # encrypt the password
            crypt_passwd = hash_password(password)

            return crypt_passwd == udata['crypt_passwd']

    def set_password(self,password):
        udata = self.load_data()
        udata['crypt_passwd'] = hash_password(password)
        self.save_data(udata)

def hash_password(password):
    return crypt.crypt(password,password)

def create_user(username,password,is_admin=False):
    user_dir = os.path.join(NOTEBOOKS_FOLDER,username)

    if os.path.exists(user_dir):
        raise Exception('user directory already exists')
    else:
        os.mkdir(user_dir)

        # create a basic profile file
        profile = {
                    'crypt_passwd': hash_password(password),
                    'is_admin': is_admin
                   }
        json.dump(profile,open(os.path.join(user_dir,USER_PROFILE_FNAME),'w'))

        return User(username)

def is_user_dir(upath):
    return os.path.exists(os.path.join(upath,USER_PROFILE_FNAME))
    
def user_exists(username):
    return os.path.exists(os.path.join(NOTEBOOKS_FOLDER,username,USER_PROFILE_FNAME))

def get_all_users():
    user_dirs = os.listdir(os.path.join(NOTEBOOKS_FOLDER))

    return filter(lambda x: is_user_dir(os.path.join(NOTEBOOKS_FOLDER,x)),user_dirs)

if __name__ == '__main__':
    import arghandler
    import getpass
    
    handler = arghandler.ArgumentHandler()
    handler.add_argument('user')

    args = handler.parse_args()

    user = args.user
    passwd = getpass.getpass('password: ')
    is_admin = input('is admin (y/n)? ') == 'y'

    create_user(user,passwd,is_admin)

    print(f'created user {user}')

