#!/usr/bin/env python


import getpass
import datetime
import requests
import sys


SERVER_URL="http://127.0.0.1:5000"
SERVER_KEY="SECRET"

PRODUCT="mozilla.org"
COMPONENT="Security Assurance: Review Request"


def check_bugzilla_credentials(credentials):
    url = "https://api-dev.bugzilla.mozilla.org/latest/bug"
    params = { "id":800000, "username":credentials[0],"password":credentials[1] }
    headers = { "Accepts": "application/json" }
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    

def fetch_bug_ids(product, component, changed_after=None, changed_before=None, changed_field=None, resolution=None, status=None, advanced=None, credentials=None):
    headers = { "Accepts": "application/json" }
    params = { "product": product,
               "component": component,
               "include_fields": "id"}
    if changed_after:
        params["changed_after"] = changed_after
    if changed_before:
        params["changed_before"] = changed_before
    if changed_field:
        params["changed_field"] = changed_field
    if resolution:
        params["resolution"] = resolution
    if status:
        params["status"] = status
    if credentials:
        params["username"] = credentials[0]
        params["password"] = credentials[1]
    if advanced:
        for i,t in enumerate(advanced):
            params["field%d-0-0" % i] = t[0]
            params["type%d-0-0" % i] = t[1]
            if len(t) == 3:
                params["value%d-0-0" % i] = t[2]
    url = "https://api-dev.bugzilla.mozilla.org/latest/bug"
    json = requests.get(url, params=params, headers=headers).json()
    return [int(bug['id']) for bug in json['bugs']]


def current_quarter():
    """Return the current quarter"""
    d = datetime.datetime.now()
    return (d.month-1)//3+1

def current_quarter_spec():
    d = datetime.datetime.now()
    return "%dQ%d" % (d.year, (d.month-1)//3+1)

def quarter_date_range(year, quarter):
    """Return the bugzilla date range for the specified year and quarter"""
    after = "%4d-%.2d-01" % (year, (quarter-1)*3+1)
    if quarter < 4:
        before = "%4.d-%.2d-01" % (year, (quarter-1)*3+4)
    else:
        before = "%4d-01-01" % (year + 1)
    return (after,before)

def current_quarter_date_range():
    """Return the bugzilla date range for the current quarter"""
    d = datetime.datetime.now()
    return quarter_date_range(d.year, current_quarter())

def count_completed_for_date_range(date_range, credentials):
    return len(fetch_bug_ids(PRODUCT, COMPONENT, changed_after=date_range[0], changed_before=date_range[1], changed_field="resolution", resolution="FIXED", credentials=credentials))

def count_created_for_date_range(date_range, credentials):
    return len(fetch_bug_ids(PRODUCT, COMPONENT, changed_after=date_range[0], changed_before=date_range[1], changed_field="creation_time", credentials=credentials))

def count_total_outstanding(credentials):
    return len(fetch_bug_ids(PRODUCT, COMPONENT, status=["UNCONFIRMED","NEW","READY","ASSIGNED","REOPENED"], credentials=credentials))

def count_ready_for_review(credentials):
    advanced = [("status_whiteboard", "substring", "pending"), ("flagtypes.name", "notsubstring", "needinfo")]
    return len(fetch_bug_ids(PRODUCT, COMPONENT, status=["UNCONFIRMED","NEW","READY","ASSIGNED","REOPENED"], advanced=advanced, credentials=credentials))

def count_without_risk_rating(credentials):
    advanced = [("status_whiteboard", "notsubstring", "[needs info]"), ("status_whiteboard", "notsubstring", "[score:")]
    return len(fetch_bug_ids(PRODUCT, COMPONENT, status=["UNCONFIRMED","NEW","READY","ASSIGNED","REOPENED"], advanced=advanced, credentials=credentials))

def count_without_deadline(credentials):
    advanced = [("cf_due_date", "isempty")]
    return len(fetch_bug_ids(PRODUCT, COMPONENT, resolution="---", advanced=advanced, credentials=credentials))

def submit_quarterly_counts(server_url, server_key, quarter, submitted, completed):
    params = {
        "key": server_key,
        "quarter": quarter,
        "completed": completed,
        "submitted": submitted
    }
    r = requests.post(SERVER_URL + "/submit-quarterly-review-statistics", data=params)
    r.raise_for_status()

def submit_weekly_counts(server_url, server_key, date, completed_this_quarter, total_outstanding, ready_for_review, without_risk_rating, without_deadline):
    params = {
        "key": server_key,
        "date": "%.4d-%.2d-%.2d" % (date.year, date.month, date.day),
        "completed_this_quarter": completed_this_quarter,
        "total_outstanding": total_outstanding,
        "ready_for_review": ready_for_review,
        "without_risk_rating": without_risk_rating,
        "without_deadline": without_deadline
    }
    r = requests.post(SERVER_URL + "/submit-weekly-review-statistics", data=params)
    r.raise_for_status()


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print "usage: update-statistics.py <bugzilla-username>"
        sys.exit(1)

    password = getpass.getpass("Bugzilla password for %s: " % sys.argv[1])
    credentials=(sys.argv[1], password)

    check_bugzilla_credentials(credentials)

    print "COLLECTING QUARTERLY STATISTICS"

    created_this_quarter = count_created_for_date_range(current_quarter_date_range(), credentials)
    print "* CREATED THIS QUARTER   %4d" % created_this_quarter
    completed_this_quarter = count_completed_for_date_range(current_quarter_date_range(), credentials)
    print "* COMPLETED THIS QUARTER %4d" % completed_this_quarter

    print "SUBMITTING TO SERVER"
    submit_quarterly_counts(SERVER_URL, SERVER_KEY, current_quarter_spec(), created_this_quarter, completed_this_quarter)
    print "* OK"

    sys.exit(1)

    print "COLLECTING WEEKLY STATISTICS"

    completed_this_quarter = count_completed_for_date_range(current_quarter_date_range(), credentials)
    print "* COMPLETED_THIS_QUARTER %4d" % count_completed_for_date_range(current_quarter_date_range(), credentials)

    total_outstanding = count_total_outstanding(credentials)
    print "* TOTAL_OUTSTANDING      %4d" % count_total_outstanding(credentials)

    ready_for_review = count_ready_for_review(credentials)
    print "* READY_FOR_REVIEW       %4d" % count_ready_for_review(credentials)

    without_risk_rating = count_without_risk_rating(credentials)
    print "* WITHOUT_RISK_RATING    %4d" % count_without_risk_rating(credentials)

    without_deadline = count_without_deadline(credentials)
    print "* WITHOUT_DEADLINE       %4d" % count_without_deadline(credentials)

    print "SUBMITTING TO SERVER"
    submit_weekly_counts(SERVER_URL, SERVER_KEY, datetime.datetime.now(), completed_this_quarter, total_outstanding, ready_for_review, without_risk_rating, without_deadline)
    print "* OK"

