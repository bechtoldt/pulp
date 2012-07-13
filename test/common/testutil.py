#!/usr/bin/python
#
# Copyright (c) 2011 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public
# License as published by the Free Software Foundation; either version
# 2 of the License (GPLv2) or (at your option) any later version.
# There is NO WARRANTY for this software, express or implied,
# including the implied warranties of MERCHANTABILITY,
# NON-INFRINGEMENT, or FITNESS FOR A PARTICULAR PURPOSE. You should
# have received a copy of GPLv2 along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.

import base64
from datetime import timedelta
from paste.fixture import TestApp
import os
import random
import unittest
import sys
import time
import web

import mock

try:
    import mocks
except ImportError:
    mocks = None

try:
    import json
except ImportError:
    import simplejson as json

srcdir = os.path.abspath(os.path.dirname(__file__)) + "/../../src/"
sys.path.insert(0, srcdir)

commondir = os.path.abspath(os.path.dirname(__file__)) + '/../common/'
sys.path.insert(0, commondir)

from pulp.server import async
from pulp.repo_auth import repo_cert_utils
from pulp.server import auditing
from pulp.server import config
from pulp.server.api.cds import CdsApi
from pulp.server.api.cds_history import CdsHistoryApi
from pulp.server.api.consumer import ConsumerApi
from pulp.server.api.consumer_group import ConsumerGroupApi
from pulp.server.api.consumer_history import ConsumerHistoryApi
from pulp.server.api.distribution import DistributionApi
from pulp.server.api.repo import RepoApi
from pulp.server.api.auth import AuthApi
from pulp.server.api.user import UserApi
from pulp.server.api.permission import PermissionAPI
from pulp.server.api.role import RoleAPI
from pulp.server.api.filter import FilterApi
from pulp.server.api.package import PackageApi
from pulp.server.api.file import FileApi
from pulp.server.api.errata import ErrataApi
from pulp.server.api.role import RoleAPI
from pulp.server.content.types import database as types_database
from pulp.server.db import connection
from pulp.server.db.model import Delta, TaskHistory
from pulp.server.db.model.cds import CDSRepoRoundRobin
from pulp.server.logs import start_logging, stop_logging
import pulp.server.managers.factory as manager_factory
from pulp.server.util import random_string
from pulp.server.auth.cert_generator import SerialNumber
from pulp.server.tasking.taskqueue import queue
from pulp.server import constants

from pulp.server.auth import authorization
from pulp.server.webservices import http

SerialNumber.PATH = '/tmp/sn.dat'
constants.LOCAL_STORAGE = "/tmp/pulp/"
constants.CACHE_DIR = "/tmp/pulp/cache"

def load_test_config():
    if not os.path.exists('/tmp/pulp'):
        os.makedirs('/tmp/pulp')

    override_file = os.path.abspath(os.path.dirname(__file__)) + '/test-override-pulp.conf'
    override_repo_file = os.path.abspath(os.path.dirname(__file__)) + '/test-override-repoauth.conf'
    stop_logging()
    try:
        config.add_config_file(override_file)
        config.add_config_file(override_repo_file)
    except RuntimeError:
        pass
    start_logging()

    # The repo_auth stuff, which runs outside of the server codebase, needs to know
    # where to look for its config as well
    repo_cert_utils.CONFIG_FILENAME = override_file

    return config.config

def create_package(api, name, version="1.2.3", release="1.el5", epoch="1",
        arch="x86_64", description="test description text",
        checksum_type="sha256",
        checksum="9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e",
        filename="test-filename-1.2.3-1.el5.x86_64.rpm"):
    """
    Returns a SON object representing the package.
    """
    test_pkg_name = name
    test_epoch = epoch
    test_version = version
    test_release = release
    test_arch = arch
    test_description = description
    test_checksum_type = checksum_type
    test_checksum = checksum
    test_filename = filename
    p = api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
        release=test_release, arch=test_arch, description=test_description,
        checksum_type=checksum_type, checksum=test_checksum, filename=test_filename)
    # We are looking up package trough mongo so we get a SON object to return.
    # instead of returning the model.Package object
    lookedUp = api.package(p['id'])
    return lookedUp
    #p = api.package_by_ivera(name, test_version, test_epoch, test_release, test_arch)
    #if (p == None):
    #    p = api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
    #        release=test_release, arch=test_arch, description=test_description,
    #        checksum_type=checksum_type, checksum=test_checksum, filename=test_filename)
    #    lookedUp = api.package(p['id'])
    #    return lookedUp
    #else:
    #    return p

def create_random_package(api):
    test_pkg_name = random_string()
    test_epoch = random.randint(0, 2)
    test_version = "%s.%s.%s" % (random.randint(0, 100),
                                random.randint(0, 100), random.randint(0, 100))
    test_release = "%s.el5" % random.randint(0, 10)
    test_arch = "x86_64"
    test_description = ""
    test_requires = []
    test_provides = []
    for x in range(10):
        test_description = test_description + " " + random_string()
        test_requires.append(random_string())
        test_provides.append(random_string())

    test_checksum_type = "sha256"
    test_checksum = "9d05cc3dbdc94150966f66d76488a3ed34811226735e56dc3e7a721de194b42e"
    test_filename = "test-filename-zzz-%s-%s.x86_64.rpm" % (test_version, test_release)
    p = api.create(name=test_pkg_name, epoch=test_epoch, version=test_version,
        release=test_release, arch=test_arch, description=test_description,
        checksum_type="sha256", checksum=test_checksum, filename=test_filename)
    p['requires'] = test_requires
    p['provides'] = test_requires
    d = Delta(p, ('requires', 'provides',))
    api.update(p.id, d)
    return p

class PulpTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

        self._mocks = {}

        self.data_path = \
            os.path.join(
                os.path.join(
                    os.path.abspath(os.path.dirname(__file__)),
                    "../unit"),
                "data")
        self.config = load_test_config()
        connection.initialize()

        if mocks is not None:
            mocks.install()

        self.setup_async()

        manager_factory.initialize()

        self.repo_api = RepoApi()
        self.consumer_api = ConsumerApi()
        self.consumer_group_api = ConsumerGroupApi()
        self.cds_api = CdsApi()
        self.user_api = UserApi()
        self.auth_api = AuthApi()
        self.perm_api = PermissionAPI()
        self.role_api = RoleAPI()
        self.cds_history_api = CdsHistoryApi()
        self.consumer_history_api = ConsumerHistoryApi()
        self.distribution_api = DistributionApi()
        self.filter_api = FilterApi()
        self.package_api = PackageApi()
        self.file_api = FileApi()
        self.errata_api = ErrataApi()
        self.role_api = RoleAPI()

        self.clean()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.unmock_all()
        self.clean()
        self.teardown_async()

    def clean(self):
        '''
        Removes any entities written to the database in all used APIs.
        '''
        self.cds_api.clean()
        self.repo_api.clean()
        self.consumer_api.clean()
        self.consumer_group_api.clean()
        self.user_api.clean()
        self.perm_api.clean()
        self.role_api.clean()
        self.cds_history_api.clean()
        self.consumer_history_api.clean()
        self.distribution_api.clean()
        self.filter_api.clean()
        self.package_api.clean()
        self.file_api.clean()
        self.errata_api.clean()
        self.role_api.clean()

        # remove any content type definitions that have been added
        types_database.clean()

        # Flush the assignment algorithm cache
        CDSRepoRoundRobin.get_collection().remove(safe=True)

        TaskHistory.get_collection().remove(safe=True)

        auditing.cull_events(timedelta())

        if mocks is not None:
            mocks.reset()

    def setup_async(self):
        async._queue = mock.Mock()
        async._queue.find.return_value = []
        async._queue.waiting_tasks.return_value = []
        async._queue.running_tasks.return_value = []
        async._queue.incomplete_tasks.return_value = []
        async._queue.complete_tasks.return_value = []
        async._queue.all_tasks.return_value = []

    def teardown_async(self):
        async._queue.reset_mock()

    def mock(self, parent, attribute, mock_object=None):
        self._mocks.setdefault(parent, {})[attribute] = getattr(parent, attribute)
        if mock_object is None:
            mock_object = mock.Mock()
        setattr(parent, attribute, mock_object)

    def unmock_all(self):
        for parent in self._mocks:
            for mocked_attr, original_attr in self._mocks[parent].items():
                setattr(parent, mocked_attr, original_attr)


class PulpAsyncTest(PulpTest):

    def setup_async(self):
        async.config.config = self.config
        async.initialize()

    def teardown_async(self):
        if async._queue:
            async._queue._cancel_dispatcher()
        async._queue = None


class PulpWebserviceTest(PulpAsyncTest):

    WEB_APP = None
    TEST_APP = None
    ORIG_HTTP_REQUEST_INFO = None
    HEADERS = None

    @classmethod
    def setUpClass(cls):

        # The application setup is somewhat time consuming and really only needs
        # to be done once. We might be able to move it out to a single call for
        # the entire test suite, but for now I'm seeing performance improvements
        # by only doing it once per class instead of on every run.

        # Because our code is a tightly coupled mess, the test config has to be
        # laoded before we can import application
        load_test_config()
        from pulp.server.webservices import application

        PulpWebserviceTest.WEB_APP = web.subdir_application(application.URLS)
        PulpWebserviceTest.TEST_APP = TestApp(PulpWebserviceTest.WEB_APP.wsgifunc())

        def request_info(key):
            if key == "REQUEST_URI":
                key = "PATH_INFO"

            return web.ctx.environ.get(key, None)

        PulpWebserviceTest.ORIG_HTTP_REQUEST_INFO = http.request_info
        http.request_info = request_info

        base64string = base64.encodestring('%s:%s' % ('ws-user', 'ws-user'))[:-1]
        PulpWebserviceTest.HEADERS = {'Authorization' : 'Basic %s' % base64string}

    @classmethod
    def tearDownClass(cls):
        user_api = UserApi()
        user_api.delete('ws-user')

        http.request_info = PulpWebserviceTest.ORIG_HTTP_REQUEST_INFO

    def setUp(self):
        super(PulpWebserviceTest, self).setUp()

        # The built in PulpTest clean will automatically delete users between
        # test runs, so we can't just create the user in the class level setup.
        user_api = UserApi()
        user_api.create('ws-user', password='ws-user')
        user_api.update('ws-user', {'roles' : authorization.super_user_role})

    def get(self, uri, params=None, additional_headers=None):
        return self._do_request('get', uri, params, additional_headers)

    def post(self, uri, params=None, additional_headers=None):
        return self._do_request('post', uri, params, additional_headers)

    def delete(self, uri, params=None, additional_headers=None):
        return self._do_request('delete', uri, params, additional_headers)

    def put(self, uri, params=None, additional_headers=None):
        return self._do_request('put', uri, params, additional_headers)

    def _do_request(self, request_type, uri, params, additional_headers):
        """
        The calls and their pre/post processing are so similar, do it all in
        here and use magic to make the right call.
        """

        # Use the default headers established at setup and override/add any
        headers = dict(PulpWebserviceTest.HEADERS)
        if additional_headers is not None:
            headers.update(additional_headers)

        # Serialize the parameters if any are specified
        if params is None:
            params = {}
        params = json.dumps(params)

        # Invoke the API
        f = getattr(PulpWebserviceTest.TEST_APP, request_type)
        response = f('http://localhost' + uri, params=params, headers=headers, expect_errors=True)

        # Collect return information and deserialize it
        status = response.status
        try:
            body = json.loads(response.body)
        except ValueError:
            body = None

        return status, body