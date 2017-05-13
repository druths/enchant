import os,os.path

def check_user_password(notebooks_folder,username,password):

    # does the user exist?
    user_dir = os.path.join(notebooks_folder,username)

    if not os.path.exists(user_dir):
        return False
    else:
        # check the password file
        pfile = os.path.join(user_dir,'.passwd')
        if not os.path.exists(user_dir):
            return True

        pcontents = open(pfile,'r').read().strip()
        return pcontents == password

def set_user_password(notebooks_folder,username,password):

    pfile = os.path.join(notebooks_folder,username,'.passwd')
    fh = open(pfile,'w')
    fh.write(password)
    fh.close()

def create_user(notebooks_folder,username,password):
    
    user_dir = os.path.join(notebooks_folder,username)

    if os.path.exists(user_dir):
        raise Exception('user directory already exists')
    else:
        os.mkdir(user_dir)
        set_user_password(notebooks_folder,username,password)

    return
