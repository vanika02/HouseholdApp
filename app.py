from flask import Flask, render_template

app=Flask(__name__)

import config

import models 

import routes 

import api

if __name__ == "__main__":
    app.run(debug=True)