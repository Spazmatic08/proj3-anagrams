"""
Simple Flask web site 
"""

import flask
from flask import request  # Data from a submitted form
from flask import url_for
from flask import jsonify # For AJAX transactions

import json
import logging
import argparse  # For the vocabulary list
import sys

# Our own modules
from letterbag import LetterBag
from vocab import Vocab
from jumble import jumbled

###
# Globals
###
app = flask.Flask(__name__)
import CONFIG
app.secret_key = CONFIG.secret_key  # Should allow using session variables

#
# One shared 'Vocab' object, read-only after initialization,
# shared by all threads and instances.  Otherwise we would have to
# store it in the browser and transmit it on each request/response cycle, 
# or else read it from the file on each request/responce cycle,
# neither of which would be suitable for responding keystroke by keystroke.

WORDS = Vocab( CONFIG.vocab )

###
# Pages
###

@app.route("/")
@app.route("/index")
def index():
  flask.g.vocab = WORDS.as_list();
  flask.session["target_count"] = min( len(flask.g.vocab), CONFIG.success_at_count )
  flask.session["jumble"] = jumbled(flask.g.vocab, flask.session["target_count"])
  flask.session["matches"] = [ ]
  app.logger.debug("Session variables have been set")
  assert flask.session["matches"] == [ ]
  assert flask.session["target_count"] > 0
  app.logger.debug("At least one seems to be set correctly")
  return flask.render_template('vocab.html')

@app.route("/keep_going")
def keep_going():
  """
  After initial use of index, we keep the same scrambled
  word and try to get more matches
  """
  flask.g.vocab = WORDS.as_list();
  return flask.render_template('vocab.html')
  

@app.route("/success")
def success():
  return flask.render_template('success.html')

#######################
# JSON request handler
#######################

@app.route("/_check")
def check():
  # Get the passed text from the client
  text = request.args.get("text", type=str)

  # Interpret the results
  rslt = gen_result(text)

  # If it's a new word, we need to add it to
  # the matches so it can be displayed and
  # prevent it from being chosen again
  if rslt["valid"] and not rslt["oldmatch"]:
    matches = flask.session.get("matches")
    matches.append(text)
    flask.session["matches"] = matches

  # Find the url to redirect to
  if rslt["complete"]:
    redirect = url_for("success")
  else:
    redirect = url_for("keep_going")

  # Attach the url
  rslt["url"] = redirect

  # Return the requested JSON
  return jsonify(result=rslt)


def gen_result(text):
  valid = WORDS.has(text)

  matches = flask.session.get("matches", [])
  oldmatch = text in matches

  complete = len(matches) >= flask.session["target_count"]

  # We don't need to scan for non-jumble letters,
  # the JS does that already. We just need to check
  # if it's a match not yet found, and if we have
  # the target number of matches yet.

  rslt = { "valid": valid,
           "oldmatch": oldmatch,
           "complete": complete }

  return rslt



###############
# AJAX request handlers 
#   These return JSON, rather than rendering pages. 
###############

@app.route("/_example")
def example():
  """
  Example ajax request handler
  """
  app.logger.debug("Got a JSON request");
  rslt = { "key": "value" }
  return jsonify(result=rslt)


#################
# Functions used within the templates
#################

@app.template_filter( 'filt' )
def format_filt( something ):
    """
    Example of a filter that can be used within
    the Jinja2 code
    """
    return "Not what you asked for"
  
###################
#   Error handlers
###################
@app.errorhandler(404)
def error_404(e):
  app.logger.warning("++ 404 error: {}".format(e))
  return render_template('404.html'), 404

@app.errorhandler(500)
def error_500(e):
   app.logger.warning("++ 500 error: {}".format(e))
   assert app.debug == False #  I want to invoke the debugger
   return render_template('500.html'), 500

@app.errorhandler(403)
def error_403(e):
  app.logger.warning("++ 403 error: {}".format(e))
  return render_template('403.html'), 403



#############

# Set up to run from cgi-bin script, from
# gunicorn, or stand-alone.
#

if __name__ == "__main__":
    # Standalone. 
    app.debug = True
    app.logger.setLevel(logging.DEBUG)
    print("Opening for global access on port {}".format(CONFIG.PORT))
    app.run(port=CONFIG.PORT, host="0.0.0.0")
else:
    # Running from cgi-bin or from gunicorn WSGI server, 
    # which makes the call to app.run.  Gunicorn may invoke more than
    # one instance for concurrent service.
    #FIXME:  Debug cgi interface 
    app.debug=False

