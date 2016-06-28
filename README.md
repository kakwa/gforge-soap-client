# gforge_stuff

A small library to recover trackers from gforge using its Soap API.

# Dependencies

* python-suds (soap client library)
* python-mako (template engin)

# Usage

## Command line

The url to the WSDL looks something like **http[s]://\<host\>[/gf]/xmlcompatibility/soap5/\?wsdl**

Simple printing:

```bash
# printing the trackers to stdout
$ gforge-cli -l <gforge login> -p <gforge password> -u <url to wsdl> -P <project unix name>
```

Printing with a mako template:

```bash
# building a document from a mako template

# to stdout
$ gforge-template -l <gforge login> -p <gforge password> -u <url to wsdl> \
    -P <project unix name> -t <path to mako template> -s

# to a file
$ gforge-template -l <gforge login> -p <gforge password> -u <url to wsdl> \
    -P <project unix name> -t <path to mako template> -o <out file>
```

A template example is available in **goodies/changelog.py**.

## Library

```python
import gforge_soap_client

# for utf-8 to stdout
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

login="<gforge login>"
password="<gforge password>"
url="<gforge url>"
project="<gforge project name>" # (unix name)

# initialize
gTracker = gforge_soap_client.SoapClient(url, login, password,  project)
# import the trackers
gTracker.import_trackers()

# print to stdout
#gTracker.print_trackers()

# printing the raw tracker information, without id resolution and html unescape
print(gTracker.trackers_raw)

# printing the list of trackers
print(gTracker.trackers_name)

# "pretty" printing of trackers (with extra fields id and users id resolution and html unescape)
print(gTracker.trackers)

# ordering trackers information
from distutils.version import LooseVersion

for t_name in gTracker.trackers_name:
    print('Tracker: ' + t_name + '\n')

    item_by_release = gTracker.organize_items_by_field(gTracker.trackers[t_name]['items'], field='Fixed In Release')

    for release in sorted(item_by_release, key=LooseVersion, reverse=True):

        print('Release: ' + release + '\n')

        item_by_type = gTracker.organize_items_by_field(item_by_release[release], field='Type')

        for itype in sorted(item_by_type):
            for item in item_by_type[itype]:
                print(item['Type'] + ', ' + item['tracker_item_id'] + ', ' + item['summary'])
        print("")
```
