#!/usr/bin/env python


import datetime
import json
import os

from flask import Flask, request, render_template, jsonify, redirect, url_for
from pymongo import MongoClient


KEY="SECRET"


application = Flask(__name__)


def vcap_services():
    if os.getenv('VCAP_SERVICES'):
        return json.loads(os.getenv('VCAP_SERVICES'))
    else:
        return { "mongodb-1.8": [{ "credentials": { "db": "db", "host": "127.0.0.1", "port": 27017 } }] }


def connect():
    services = vcap_services()
    credentials = services["mongodb-1.8"][0]["credentials"]
    if 'username' in credentials:
        url = "mongodb://%(username)s:%(password)s@%(host)s:%(port)d/%(db)s" % credentials
    else:
        url = "mongodb://%(host)s:%(port)d" % credentials
    client = MongoClient(url)
    return client[services["mongodb-1.8"][0]["credentials"]["db"]]


@application.route('/submit-weekly-review-statistics', methods=['POST'])
def submit_weekly_review_statistics():
    if request.form['key'] == KEY:
        db = connect()
        collection = db['weekly-review-statistics']
        record = { "_id": request.form['date'], "date": request.form['date'] }
        for counter in ('completed_this_quarter', 'total_outstanding', 'ready_for_review', 'without_risk_rating', 'without_deadline'):
            record[counter] = int(request.form[counter])
        collection.save(record)
    return ""

@application.route('/submit-quarterly-review-statistics', methods=['POST'])
def submit_quarterly_review_statistics():
    print request.form
    if request.form['key'] == KEY:
        db = connect()
        collection = db['quarterly-review-statistics']
        record = { "_id": request.form['quarter'], "quarter": request.form['quarter'] }
        for counter in ('submitted', 'completed'):
            record[counter] = int(request.form[counter])
        collection.save(record)
    return ""

def _date_to_category(date):
    return date[5:7] + "/" + date[8:10]

@application.route('/weekly-review-statistics')
def weekly_review_statistics():
    db = connect()
    collection = db['weekly-review-statistics']
    series = [{"name": counter, "data": []} for counter in ('completed_this_quarter', 'total_outstanding', 'ready_for_review', 'without_risk_rating', 'without_deadline')]
    categories = []
    for record in collection.find({}, {"_id": None}).sort("date"):
        categories.append(_date_to_category(record['date']))
        for i,counter in enumerate(('completed_this_quarter', 'total_outstanding', 'ready_for_review', 'without_risk_rating', 'without_deadline')):
            series[i]["data"].append(record[counter])
    return jsonify({"series": series, "categories": categories})

@application.route('/quarterly-review-statistics')
def quarterly_review_statistics():
    db = connect()
    collection = db['quarterly-review-statistics']
    series = [{"name": counter, "data": []} for counter in ('submitted', 'completed')]
    categories = []
    for record in collection.find({}, {"_id": None}).sort("quarter"):
        categories.append(record['quarter'])
        for i,counter in enumerate(('submitted', 'completed')):
            series[i]["data"].append(record[counter])
    return jsonify({"series": series, "categories": categories})


@application.route("/")
def index():
    return redirect(url_for('weekly'))

def current_year():
    """Return the current year"""
    d = datetime.datetime.now()
    return d.year

def current_quarter():
    """Return the current quarter"""
    d = datetime.datetime.now()
    return (d.month-1)//3+1

@application.route("/weekly")
def weekly():
    quarter = "%d-%.2d-01" % (current_year(), (current_quarter()-1)*3+1)
    return render_template('weekly.html', current_quarter_start=quarter)

@application.route("/quarterly")
def quarterly():
    return render_template('quarterly.html')


if __name__ == '__main__':
    application.debug = True
    application.run('0.0.0.0')
