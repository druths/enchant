enchant is a system for capturing research code output (plots, text, and
arbitrary HTML). The goal is to make it easy to push results generated to a
web-based interface.

# Quick Start

## Setup a user
In the enchant directory, create the folder `notebooks/<username>` for the user you want. (You can have multiple users).

In this directory, create the file `.passwd` containing the password for this user.

## Launch a user
To launch the server, from within the `enchant` directory, use the command:

	python app.py

by default it will listen on port 13105. Use command line arguments to configure this.

## Access the server in a web browser
Open a web-browser to the IP address+port combination on which the server is
running.

Navigate to `http://<hostname>:<port>/login`. You'll be prompted for a username
and	password. Enter the credentials for a user you've created (as described
above).

# Relevant directories

The following directories within the install directory are used:

  * `notebooks` - this is the directory in which all notebook content (except
	for images) are stored. The structure inside this directory is
	`<username>/<notebook_name>/<blocks>`.
  * `upload/images` - this is the directory in which all notebook images are stored.

