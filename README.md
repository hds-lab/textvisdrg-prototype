Text Visualization DRG Protoype
====================

This repo contains a Django project for setting up 
a database and possibly web-based visualization prototypes
for the DRG on Online Text Visualization, 2014-2015.


Steps to set up
--------------

> These steps are probably not complete!

You must have Python 2.7 installed.
It is recommended to use virtualenv to set up a virtual
Python environment for this project.

1. Check out the repository.
2. Set up a MySQL database.
3. Copy `dot_env_example.txt` to a file named `.env` and edit with your database settings.
4. Install python libraries with `pip install -r requirements.txt`.
   If you have problems with this step, you might try running `pip install numpy`
   and `pip install scipy` beforehand.
5. Set up the database: `./manage.py migrate`


Areas of Interest
----------------

There are two different text dataset that this project
is prepared to store.

Tweets are stored in tables created by the michaelbrooks/django-twitter-stream
django app. The main tweets table is `twitter_stream_tweet`.

Chat messages are stored in tables created by the `textprizm` Django app.
The models for htis app are in the code at `textvis/textprizm/models.py`.

There is also code that *does not yet work* for extracting topic models
from tweets and chat messages in `textvis/textprizm/topics.py`.

There is code that *does* work for extracting
topic models from CSV files in `lda.py`,
but it outputs to flat files, not the database.
There are instructions for running this script at the top
of the file.
