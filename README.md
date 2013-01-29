
Change the following two lines in `scripts/update-review-statistics.py` to match your server:

```
SERVER_URL="http://127.0.0.1:5000"
SERVER_KEY="SECRET"
```

Then run the stats like this:

```
$ cd security-review-statistics
$ virtualenv env
$ source env/bin/activate
(env) $ pip install requests
(env) $ cd scripts
(env) $ ./update-review-statistics.py username@mozilla.com
```

Enter your bugzilla account password and the script will collect statistics and report them back to the server to make fancy charts.

