# -*- coding: utf-8 -*-
# vim:set expandtab tabstop=4 shiftwidth=4:

from __future__ import unicode_literals
import sys
import codecs
from datetime import datetime
from suds.client import Client
from suds.transport.http import HttpAuthenticated
import suds
import HTMLParser


class SoapClient:

    """Soap gforge client

    Attributes:

    self.GFapi: the soap client object
    self.trackers: list of list of trackers items (empty before import)
    self.trackers_name: list of trackers name (idem)
    self.trackers_raw: the raw trackers and trackers items (without id resolution)
    """

    def __init__(self, url, login, password, project):
        """ Init a gforge client
        :param url: url to the soap entry point
        :param login: api login
        :param password: api password
        :param project: project to query
        :rtype: SoapClient object
        """
        self.login = login
        self.password = password
        self.url = url
        self.project = project
        t = HttpAuthenticated(username=login, password=password)
        self.client = Client(url, transport=t)
        self.GFapi = self.client.service
        self.trackers = {}
        self.trackers_name = []
        self.trackers_raw = {}

    @staticmethod
    def _tracker_post_treat(gforge_trackeritems, map_ef, map_efe, map_t):
        """Post treatment to have something readable
        :param gforge_trackeritems: list of tracker items
        :param map_ef: map extra field id => extra field name (dict)
        :param map_efe: map extra field value id => extra field value (dict)
        :param map_t: map user id => user login
        :rtype: list of clean tracker items
        """
        # used to unescape html
        parser = HTMLParser.HTMLParser()

        trackers = []

        # iterate on tracker items
        for ti in gforge_trackeritems:
            # one item
            tracker = {}

            # iterate on each tracker fields
            for field in ti:

                # resolve extra fields and extra fields value
                if field[0] == 'extra_field_data':
                    for ef in ti.extra_field_data:
                        tracker_extra_field = map_ef[ef.tracker_extra_field_id]
                        tracker_extra_field_data = ""
                        try:
                            tracker_extra_field_data = map_efe[ef.field_data]
                        except:
                            # if there is no mapping,
                            # just keep the original value
                            tracker_extra_field_data = ef.field_data
                            # print("### FAIL ####")
                            # print(tracker_extra_field)
                            # print(ef.tracker_extra_field_data_id)
                            # print(ef)
                            # print("### END ####")
                            pass
                        tracker[tracker_extra_field] = tracker_extra_field_data

                # various html unescape
                elif field[0] == 'details':
                    tracker['details'] = parser.unescape(field[1])
                elif field[0] == 'summary':
                    tracker['summary'] = parser.unescape(field[1])

                # TODO, resolv commits, for now, this is just ignored
                elif field[0] == 'scm_commits':
                    pass

                # handle item messages
                elif field[0] == 'messages':
                    val = []
                    for e in field[1]:
                        d = {}
                        # resolve user ID
                        try:
                            d['submitted_by'] = map_t[e['submitted_by']]
                        except:
                            d['submitted_by'] = None
                        d['adddate'] = e['adddate']
                        # unescape html
                        d['body'] = parser.unescape(e['body'])
                        val.append(d)
                    tracker[field[0]] = val

                # handle list of assignees
                elif field[0] == 'assignees':
                    val = []
                    for e in field[1]:
                        d = {}
                        try:
                            # resolve user ID
                            d['assignee'] = map_t[e['assignee']]
                        except:
                            # sometime, the assignee doesn't
                            # exist or is not set
                            d['assignee'] = None
                        val.append(d)
                    tracker[field[0]] = val

                # resolve user ID
                elif field[0] == 'submitted_by':
                    try:
                        tracker[field[0]] = map_t[field[1]]
                    except:
                        tracker[field[0]] = None
                elif field[0] == 'last_modified_by':
                    try:
                        tracker[field[0]] = map_t[field[1]]
                    except:
                        tracker[field[0]] = None

                # default handling
                else:
                    tracker[field[0]] = field[1]
            trackers.append(tracker)

        # cleaning a little (encoding mess)
        for t in trackers:
            for k in t:
                if type(t[k]) is int:
                    t[k] = str(t[k])
                elif type(t[k]) is str:
                    t[k] = t[k].decode('utf-8', 'ignore')
                elif type(t[k]) is list:
                    val = []
                    for e in t[k]:
                        if type(e) is str:
                            e = e.decode('utf-8', 'ignore')
                        val.append(e)
                    t[k] = val
        return trackers

    @staticmethod
    def _build_element_extrafield_map(extra_field_elements):
        """ Build reverse mapping for extra field values"""
        ret = {}
        for ef in extra_field_elements:
            if 'element_name' in ef:
                ret[str(ef.element_id)] = ef.element_name
        return ret

    @staticmethod
    def _build_field_extrafield_map(extra_field_elements):
        """ Build reverse mapping for extra field name"""
        ret = {}
        for ef in extra_field_elements:
            if 'field_name' in ef:
                ret[ef.tracker_extra_field_id] = ef.field_name
        return ret

    @staticmethod
    def _build_map_techinicians(techinicians):
        """ Build reverse mapping for users"""
        ret = {}
        for t in techinicians:
            ret[t.user_id] = t.unix_name
        return ret

    def import_trackers(self):
        """ Import all the trackers of the project"""
        # gforge login to recover session
        GFsession = self.GFapi.login(self.login, self.password)

        # get login user id
        GFuserid = GFsession.split(":")[0]

        # recover the project by it's name (mostly, only for the project ID)
        p = self.GFapi.getProjectByUnixName(GFsession, self.project)

        # Recover all Public and Private trackers of the project
        # TODO, understand what does "datatype" (the last argument) means
        trackers = self.GFapi.getTrackers(GFsession, p.project_id, 0, 1)
        trackers = trackers + \
            self.GFapi.getTrackers(GFsession, p.project_id, 1, 1)

        # reiniatialize self.trackers to zero before filling it
        self.trackers = {}
        self.trackers_name = []

        # iterate on trackers
        for t in trackers:
            # Record some general information on the tracker
            self.trackers[t.tracker_name] = {
                'tracker_name': t.tracker_name,
                'description': t.description,
                'is_public': t.is_public,
                'item_total': t.item_total,
                'open_count': t.open_count,
                'tracker_id': t.tracker_id,
                'items': []
            }
            self.trackers_name.append(t.tracker_name)

            # recover all the tracker information
            # (stuff like extra fields, extra fields values, users)
            full = self.GFapi.getTrackerFull(GFsession, t.tracker_id)

            # record the raw tracker (no id resolution)
            self.trackers_raw[t.tracker_id] = full

            # create reverse mappings to replace
            # the uggly IDs by their real values
            # mapping for extra fields
            map_ef = self._build_field_extrafield_map(full.extra_fields)
            # mapping for extra fields values
            map_efe = self._build_element_extrafield_map(
                full.extra_field_elements)
            # mapping for "technicians" (aka the users)
            map_t = self._build_map_techinicians(full.techinicians)

            # Recover all the trackers
            # generate a tracker query ID
            # (used because we recover paginated results here)
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            qid = self.GFapi.addTrackerQuery(
                GFsession,
                t.tracker_id,
                GFuserid,
                "CRAP - %s" % timestamp,
                0
            )
            # initialize some stuff
            gforge_trackeritems = []
            offset = 0
            GFMAXRESULTS = 50
            # recover all the trackers items 50 by 50 until nothing's left
            while offset < t.item_total:
                items = self.GFapi.getTrackerItemsFullByQueryId(
                    GFsession,
                    qid,
                    GFMAXRESULTS,
                    offset
                )
                gforge_trackeritems.extend(items)
                offset += len(items)

            # record the raw items
            self.trackers_raw[t.tracker_id]['items'] = gforge_trackeritems

            # Post Treatment to resolve IDs
            # (mainly extra fields/extra fields values, and users name)
            self.trackers[t.tracker_name]['items'] = self._tracker_post_treat(
                gforge_trackeritems,
                map_ef,
                map_efe,
                map_t
            )

    @staticmethod
    def organize_items_by_field(items, field):
        """ Organize a list of items by a given field
        :param items: list of items (list of dict)
        :param field: field by which to organize the items
        :rtype: dict <field value> => list of items
        """
        ret = {}
        for item in items:
            value = item[field]
            if value not in ret:
                ret[value] = []
            ret[value].append(item)
        return ret

    def print_trackers(self):
        """ print the trackers/trackers items to stdout """
        for tracker in self.trackers:
            tmp_tracker = self.trackers[tracker]
            print(
                "#################### Tracker[" +
                tmp_tracker['tracker_name'] +
                "]  ####################\n")
            for t in tmp_tracker['items']:
                print(
                    "********************* Item[" +
                    t['tracker_item_id'] +
                    "] *********************")
                for k in t:
                    if type(t[k]) is unicode \
                        or type(t[k]) is str \
                            or type(t[k]) is suds.sax.text.Text:
                        print(u'    ' + k + ': ' + t[k])
                    elif type(t[k]) is list:
                        print(u'    ' + k + ': [')
                        for e in t[k]:
                            if type(e) is unicode \
                                or type(e) is str \
                                    or type(e) is suds.sax.text.Text:
                                print(u'        ' + e + ',')
                            elif type(e) is dict:
                                print('        {')
                                for k in e:
                                    if e[k] is None:
                                        print(
                                            u'          ' +
                                            k +
                                            ' => nobody')
                                    else:
                                        print(
                                            u'          ' +
                                            k +
                                            ' => ' +
                                            e[k])
                                print('        },')
                            else:
                                print(type(e))
                                # print(e)
                        print('    ]')
                    elif t[k] is None:
                        print(u'    ' + k + ': None')
                    else:
                        try:
                            print(u'    ' + k + ': None')
                        except Exception as e:
                            print(
                                u'    ' +
                                k +
                                ': ' +
                                str(e) +
                                ', type ' +
                                type(t[k]))
                print('\n')
