#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright © 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

import datetime
import functools
import inspect
import logging
import sys
import traceback
from pprint import pformat

import pymongo

from pulp.api.base import BaseApi
from pulp.model import Event

# globals ---------------------------------------------------------------------

# setup the database connection, collection, and indices
# XXX this use a centralized connection manager....
_connection = pymongo.Connection()
_objdb = _connection._database.events
_objdb.ensure_index([('id', pymongo.DESCENDING)], unique=True, background=True)
for index in ['timestamp', 'principal', 'api']:
    _objdb.ensure_index([(index, pymongo.DESCENDING)], background=True)

# setup log - do not change this to __name__
_log = logging.getLogger('auditing')

# auditing decorator ----------------------------------------------------------

class MethodInspector(object):
    """
    Class for method inspection.
    """
    def __init__(self, method, params):
        """
        @type method: unbound class instance method
        @param method: method to build spec of
        @type params: list of str's or None
        @param params: ordered list of method parameters of interest,
                       None means all parameters are of interest
        """
        self.method = method.__name__
        
        # returns a tuple: (args, varargs, keywords, defaults)
        spec = inspect.getargspec(method)
        
        args = spec[0]
        self.__param_to_index = dict((a,i+1) for i,a in
                                     enumerate(args)
                                     if params is None or a in params)
        
        self.params = params if params is not None else list(args)
            
        defaults = spec[3]
        if defaults:
            self.__param_defaults = dict((a,d) for a,d in
                                         zip(args[0-len(defaults):], defaults)
                                         if params is None or a in params)
        else:
            self.__param_defaults = {}
            
    def api_name(self, args):
        """
        Return the api class name for the given instance method positional
        arguments.
        @type args: list
        @param args: positional arguments of an api instance method
        @return: name of api class
        """
        assert args
        api_obj = args[0]
        if not isinstance(api_obj, BaseApi):
            return 'Unknown'
        return api_obj.__class__.__name__
    
    def param_values(self, args, kwargs):
        """
        Grep through passed in arguments and keyword arguments and return a list
        of values corresponding to the parameters of interest.
        @type args: list or tuple
        @param args: positional arguments
        @type kwargs: dict
        @param kwargs: keyword arguments
        @return: list of values corresponding to parameters of interest
        """
        values = []
        for p in self.params:
            i = self.__param_to_index[p]
            if i < len(args):
                values.append(args[i])
            else:
                value = kwargs.get(p, self.__param_defaults.get(p, 'Unknown Parameter: %s' % p))
                values.append(value)
        return values
        

def audit(params=None, record_result=False, pass_principal=False):
    """
    API class instance method decorator meant to log calls that constitute
    events on pulp's model instances.
    Any call to a decorated method will both record the event in the database
    and log it to a special log file.
    
    A decorated method may have an optional keyword argument, 'principal',
    passed in that represents the user or other entity making the call.
    This optional keyword argument is not passed to the underlying method,
    unless the pass_principal flag is True.
    
    @type params: list or tuple of str's or None
    @param params: list of names of parameters to record the values of,
                   None records all parameters
    @type record_result: bool
    @param record_result: whether or not to record the result
    @type pass_principal: bool
    @param pass_principal: whether or not to pass the principal as a key word
                           argument to the method
    """
    def _audit_decorator(method):
        
        spec = MethodInspector(method, params)
        
        @functools.wraps(method)
        def _audit(*args, **kwargs):
            # build up the data to record
            principal = kwargs.get('principal', None)
            if not pass_principal:
                kwargs.pop('principal', None)
            api = spec.api_name(args)
            param_values = spec.param_values(args, kwargs)
            param_values_repr = ', '.join(pformat(v) for v in param_values)
            action = '%s.%s: %s' % (api,
                                    spec.method,
                                    param_values_repr)
            event = Event(principal,
                          action,
                          api,
                          spec.method,
                          param_values)
                
            # convenience function for recording
            def _record_event():
                _objdb.insert(event, safe=False, check_keys=False)
                _log.info('[%s] %s called %s.%s on %s' %
                          (event.timestamp,
                           principal,
                           api,
                           spec.method,
                           param_values_repr))
                
            # execute the wrapped method and record the results
            try:
                result = method(*args, **kwargs)
            except Exception, e:
                event.exception = pformat(e)
                exc = sys.exc_info()
                event.traceback = ''.join(traceback.format_exception(*exc))
                _record_event()
                raise
            else:
                event.result = pformat(result) if record_result else None
                _record_event()
                return result
    
        return _audit
    
    return _audit_decorator

# auditing api ----------------------------------------------------------------

def events(spec=None, fields=None, limit=None, errors_only=False):
    """
    Query function that returns events according to the pymongo spec.
    The results are sorted by timestamp into descending order.
    @type spec: dict or pymongo.son.SON instance
    @param spec: pymongo spec for filtering events
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have 
                        an exception associated with them, otherwise return all
                        events that match spec
    @return: list of events containing fields and matching spec
    """
    assert isinstance(spec, dict) or isinstance(spec, pymongo.son.SON) or spec is None
    assert isinstance(fields, list) or isinstance(fields, tuple) or fields is None
    if errors_only:
        spec = spec or {}
        spec['exception'] = {'$ne': None}
    events_ = _objdb.find(spec=spec, fields=fields)
    if limit is not None:
        events_.limit(limit)
    events_.sort('timestamp', pymongo.DESCENDING)
    return list(events_)


def events_on_api(api, fields=None, limit=None, errors_only=False):
    """
    Return all recorded events for a given api.
    @type api: str
    @param api: name of the api
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have 
                        an exception associated with them, otherwise return all
                        events that match spec
    @return: list of events for the given api containing fields
    """
    return events({'api': api}, fields, limit, errors_only)


def events_by_principal(principal, fields=None, limit=None, errors_only=False):
    """
    Return all recorded events for a given principal (caller).
    @type api: model object or dict
    @param api: principal that triggered the event (i.e. User instance)
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have 
                        an exception associated with them, otherwise return all
                        events that match spec
    @return: list of events for the given principal containing fields
    """
    return events({'principal': unicode(principal)}, fields, limit, errors_only)


def events_in_datetime_range(lower_bound=None, upper_bound=None,
                             fields=None, limit=None, errors_only=False):
    """
    Return all events in a given time range.
    @type lower_bound: datetime.datetime instance or None
    @param lower_bound: lower time bound, None = oldest in db
    @type lower_bound: datetime.datetime instance or None
    @param lower_bound: upper time bound, None = newest in db
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have 
                        an exception associated with them, otherwise return all
                        events that match spec
    @return: list of events in the given time range containing fields
    """
    assert isinstance(lower_bound, datetime.datetime) or lower_bound is None
    assert isinstance(upper_bound, datetime.datetime) or upper_bound is None
    timestamp_range = {}
    if lower_bound is not None:
        timestamp_range['$gt'] = lower_bound
    if upper_bound is not None:
        timestamp_range['$lt'] = upper_bound
    spec = {'timestamp': timestamp_range} if timestamp_range else None
    return events(spec, fields, limit, errors_only)

def events_since_delta(delta, fields=None, limit=None, errors_only=False):
    """
    Return all the events that occurred in the last time delta from now.
    @type delta: datetime.timedelta instance
    @param delta: length of time frame to return events from
    @type fields: list or tuple of str
    @param fields: iterable of fields to include from each document
    @type limit: int or None
    @param limit: limit the number of results, None means no limit
    @type errors_only: bool
    @param errors_only: if True, only return events that match the spec and have 
                        an exception associated with them, otherwise return all
                        events that match spec
    @return: list of events in the given length of time containing fields
    """
    assert isinstance(delta, datetime.timedelta)
    now = datetime.datetime.now()
    lower_bound = now - delta
    return events({'timestamp': {'$gt': lower_bound}}, fields, limit, errors_only)


def cull_events(delta):
    """
    Reaper function that removes all events older than a given length of time
    from the database.
    @type delta: datetime.timedelta instance or None
    @param delta: length of time frame to remove events before,
                  None means remove all events
    @return: the number of events removed from the database
    """
    assert isinstance(delta, datetime.timedelta) or delta is None
    spec = None
    if delta is not None:
        now = datetime.datetime.now()
        upper_bound = now - delta
        spec = {'timestamp': {'$lt': upper_bound}}
    count = _objdb.find(spec).count()
    _objdb.remove(spec, safe=False)
    return count
