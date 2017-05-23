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

## Create a notebook

After logging in, on the homepage, click the "Create new notebook" button,
enter a name for the notebook, and click "Create".

## Push some content to the notebook

To do this, you'll need the [enchant
client](https://github.com/druths/enchant-client). After installing this, run
the following command to add a text block to notebook `test`.

	enchant -H <hostname> -P <port> txt -u <username> -p <password> test "My First Block" "Hello world!"

You should see a new text block show up in your web browser. For more
information, check out the client.

# Relevant directories

The following directories within the install directory are used:

  * `notebooks` - this is the directory in which all notebook content (except
	for images) are stored. The structure inside this directory is
	`<username>/<notebook_name>/<blocks>`.
  * `upload/images` - this is the directory in which all notebook images are stored.

# Acknowledgements

Special thanks to the following for web design assets:

  * For the current logo: [iconninja](http://www.iconninja.com/round-shield-with-star-icon-832031)
  * For the webpage template: [One-column fixed-width responsive layout](https://github.com/russmaxdesign/example-layout-one-fixed)

I'm design-impaired, so these resources were hugely useful.
