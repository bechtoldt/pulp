from ConfigParser import NoOptionError
import unittest

from mock import patch, Mock, call

from pulp.server import config
from pulp.server.db import connection


class MongoEngineConnectionError(Exception):
    pass


class TestDatabaseSeeds(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseSeeds, self).tearDown()

    def test_seeds_default(self):
        self.assertEqual(config.config.get('database', 'seeds'), 'localhost:27017')

    @patch('pulp.server.db.connection.mongoengine')
    def test_seeds_is_empty(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize(seeds='')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        database = config.config.get('database', 'name')
        mock_mongoengine.connect.assert_called_once_with(database, max_pool_size=max_pool_size)

    @patch('pulp.server.db.connection.mongoengine')
    def test_seeds_is_set_from_argument(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize(seeds='firsthost:1234,secondhost:5678')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        database = config.config.get('database', 'name')
        mock_mongoengine.connect.assert_called_once_with(database, max_pool_size=max_pool_size,
                                                         host='firsthost', port=1234)

    @patch('pulp.server.db.connection.mongoengine')
    def test_seeds_from_config(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        config.config.set('database', 'seeds', 'firsthost:1234,secondhost:5678')
        connection.initialize()
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        database = config.config.get('database', 'name')
        mock_mongoengine.connect.assert_called_once_with(database, max_pool_size=max_pool_size,
                                                         host='firsthost', port=1234)


class TestDatabaseName(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseName, self).tearDown()

    @patch('pulp.server.db.connection.mongoengine')
    def test__DATABASE_uses_default_name(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        name = config.config.get('database', 'name')
        mock_mongoengine.connect.assert_called_once_with(name,
                                                         host='localhost',
                                                         max_pool_size=10,
                                                         port=27017)

    @patch('pulp.server.db.connection.mongoengine')
    def test_name_is_set_from_argument(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        name = 'name_set_from_argument'
        connection.initialize(name=name)
        mock_mongoengine.connect.assert_called_once_with(name,
                                                         host='localhost',
                                                         max_pool_size=10,
                                                         port=27017)


class TestDatabaseReplicaSet(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseReplicaSet, self).tearDown()

    def test_replica_set_default_does_not_exist(self):
        self.assertRaises(NoOptionError, config.config.get, 'database', 'replica_set')

    @patch('pulp.server.db.connection.mongoengine')
    def test_database_sets_replica_set(self, mock_mongoengine):
        mock_replica_set = Mock()
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize(replica_set=mock_replica_set)
        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        mock_mongoengine.connect.assert_called_once_with(database, host='localhost',
                                                         max_pool_size=max_pool_size, port=27017,
                                                         replicaset=mock_replica_set)

    @patch('pulp.server.db.connection.mongoengine')
    def test_database_replica_set_from_config(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        config.config.set('database', 'replica_set', 'real_replica_set')
        connection.initialize()
        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        mock_mongoengine.connect.assert_called_once_with(database, host='localhost',
                                                         max_pool_size=max_pool_size, port=27017,
                                                         replicaset='real_replica_set')


class TestDatabaseMaxPoolSize(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseMaxPoolSize, self).tearDown()

    @patch('pulp.server.db.connection.mongoengine')
    def test_database_max_pool_size_default_is_10(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        database = config.config.get('database', 'name')
        mock_mongoengine.connect.assert_called_once_with(database, host='localhost',
                                                         max_pool_size=10, port=27017)

    @patch('pulp.server.db.connection.mongoengine')
    def test_database_max_pool_size_uses_default(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        mock_mongoengine.connect.assert_called_once_with(database, host='localhost',
                                                         max_pool_size=max_pool_size, port=27017)

    @patch('pulp.server.db.connection.mongoengine')
    def test_database_max_pool_size(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize(max_pool_size=5)
        database = config.config.get('database', 'name')
        mock_mongoengine.connect.assert_called_once_with(database, host='localhost',
                                                         max_pool_size=5, port=27017)


class TestDatabase(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabase, self).tearDown()

    @patch('pulp.server.db.connection.mongoengine')
    def test_mongoengine_connect_is_called(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        mock_mongoengine.connect.assert_called_once()

    @patch('pulp.server.db.connection.mongoengine')
    def test__DATABASE_is_returned_from_get_db_call(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        expected_database = mock_mongoengine.connection.get_db.return_value
        self.assertTrue(connection._DATABASE is expected_database)
        mock_mongoengine.connection.get_db.assert_called_once_with()

    @patch('pulp.server.db.connection.NamespaceInjector')
    @patch('pulp.server.db.connection.mongoengine')
    def test__DATABASE_receives_namespace_injector(self, mock_mongoengine, mock_namespace_injector):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        mock_son_manipulator = connection._DATABASE.add_son_manipulator
        mock_namespace_injector.assert_called_once_with()
        mock_son_manipulator.assert_called_once_with(mock_namespace_injector.return_value)

    @patch('pulp.server.db.connection.mongoengine')
    def test__DATABASE_collection_names_is_called(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        connection._DATABASE.collection_names.assert_called_once_with()

    @patch('pulp.server.db.connection.mongoengine')
    @patch('pulp.server.db.connection._logger')
    def test_unexpected_Exception_is_logged(self, mock__logger, mock_mongoengine):
        mock_mongoengine.connect.side_effect = IOError()
        self.assertRaises(IOError, connection.initialize)
        self.assertTrue(connection._CONNECTION is None)
        self.assertTrue(connection._DATABASE is None)
        mock__logger.critical.assert_called_once()


class TestDatabaseSSL(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseSSL, self).tearDown()

    def test_ssl_off_by_default(self):
        self.assertEqual(config.config.getboolean('database', 'ssl'), False)

    @patch('pulp.server.db.connection.mongoengine')
    def test_ssl_is_skipped_if_off(self, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        config.config.set('database', 'ssl', 'false')
        connection.initialize()
        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        mock_mongoengine.connect.assert_called_once_with(database, max_pool_size=max_pool_size,
                                                         host='localhost', port=27017)

    @patch('pulp.server.db.connection.ssl')
    @patch('pulp.server.db.connection.mongoengine')
    def test_ssl_is_configured_with_verify_ssl_on(self, mock_mongoengine, mock_ssl):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        config.config.set('database', 'verify_ssl', 'true')
        config.config.set('database', 'ssl', 'true')
        connection.initialize()
        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        ssl_cert_reqs = mock_ssl.CERT_REQUIRED
        ssl_ca_certs = config.config.get('database', 'ca_path')
        mock_mongoengine.connect.assert_called_once_with(database, max_pool_size=max_pool_size,
                                                         ssl=True, ssl_cert_reqs=ssl_cert_reqs,
                                                         ssl_ca_certs=ssl_ca_certs,
                                                         host='localhost', port=27017)

    @patch('pulp.server.db.connection.ssl')
    @patch('pulp.server.db.connection.mongoengine')
    def test_ssl_is_configured_with_verify_ssl_off(self, mock_mongoengine, mock_ssl):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        config.config.set('database', 'verify_ssl', 'false')
        config.config.set('database', 'ssl', 'true')
        connection.initialize()
        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        ssl_cert_reqs = mock_ssl.CERT_NONE
        ssl_ca_certs = config.config.get('database', 'ca_path')
        mock_mongoengine.connect.assert_called_once_with(database, max_pool_size=max_pool_size,
                                                         ssl=True, ssl_cert_reqs=ssl_cert_reqs,
                                                         ssl_ca_certs=ssl_ca_certs,
                                                         host='localhost', port=27017)

    @patch('pulp.server.db.connection.ssl')
    @patch('pulp.server.db.connection.mongoengine')
    def test_ssl_is_configured_with_ssl_keyfile(self, mock_mongoengine, mock_ssl):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        config.config.set('database', 'ssl_keyfile', 'keyfilepath')
        config.config.set('database', 'verify_ssl', 'false')
        config.config.set('database', 'ssl', 'true')
        connection.initialize()
        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        ssl_cert_reqs = mock_ssl.CERT_NONE
        ssl_ca_certs = config.config.get('database', 'ca_path')
        mock_mongoengine.connect.assert_called_once_with(database, max_pool_size=max_pool_size,
                                                         ssl=True, ssl_cert_reqs=ssl_cert_reqs,
                                                         ssl_ca_certs=ssl_ca_certs,
                                                         ssl_keyfile='keyfilepath',
                                                         host='localhost', port=27017)

    @patch('pulp.server.db.connection.ssl')
    @patch('pulp.server.db.connection.mongoengine')
    def test_ssl_is_configured_with_ssl_certfile(self, mock_mongoengine, mock_ssl):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        config.config.set('database', 'ssl_certfile', 'certfilepath')
        config.config.set('database', 'verify_ssl', 'false')
        config.config.set('database', 'ssl', 'true')
        connection.initialize()
        database = config.config.get('database', 'name')
        max_pool_size = connection._DEFAULT_MAX_POOL_SIZE
        ssl_cert_reqs = mock_ssl.CERT_NONE
        ssl_ca_certs = config.config.get('database', 'ca_path')
        mock_mongoengine.connect.assert_called_once_with(database, max_pool_size=max_pool_size,
                                                         ssl=True, ssl_cert_reqs=ssl_cert_reqs,
                                                         ssl_ca_certs=ssl_ca_certs,
                                                         ssl_certfile='certfilepath',
                                                         host='localhost', port=27017)


class TestDatabaseVersion(unittest.TestCase):

    """
    test DB version parsing. Info on expected versions is at
    https://github.com/mongodb/mongo/blob/master/src/mongo/util/version.cpp#L39-45
    """
    @patch('pulp.server.db.connection.mongoengine')
    def _test_initialize(self, version_str, mock_mongoengine):
        mock_mongoclient_connect = mock_mongoengine.connect.return_value
        mock_mongoclient_connect.server_info.return_value = {'version': version_str}
        connection.initialize()

    def test_database_version_bad_version(self):
        try:
            self._test_initialize('1.2.3')
            self.fail("RuntimeError not raised")
        except RuntimeError:
            pass  # expected exception

    def test_database_version_good_version(self):
        # the version check succeeded if no exception was raised
        self._test_initialize('2.6.0')

    def test_database_version_good_equal_version(self):
        # the version check succeeded if no exception was raised
        self._test_initialize('2.4.0')

    def test_database_version_good_rc_version(self):
        # the version check succeeded if no exception was raised
        self._test_initialize('2.8.0-rc1')

    def test_database_version_bad_rc_version(self):
        try:
            self._test_initialize('2.3.0-rc1')
            self.fail("RuntimeError not raised")
        except RuntimeError:
            pass  # expected exception


class TestDatabaseAuthentication(unittest.TestCase):

    def tearDown(self):
        # Reload the configuration so that things are cleaned up properly
        config.load_configuration()
        super(TestDatabaseAuthentication, self).tearDown()

    @patch('pulp.server.db.connection.mongoengine')
    def test_initialize_username_and_password(self, mock_mongoengine):
        mock_mongoengine_instance = mock_mongoengine.connect.return_value
        mock_mongoengine_instance.server_info.return_value = {"version":
                                                              connection.MONGO_MINIMUM_VERSION}
        config.config.set('database', 'username', 'admin')
        config.config.set('database', 'password', 'admin')
        connection.initialize()
        mock_mongoengine.connect.assert_called_once_with('pulp_unittest', username='admin',
                                                         host='localhost', password='admin',
                                                         max_pool_size=10, port=27017)

    @patch('pulp.server.db.connection.mongoengine')
    def test_initialize_no_username_or_password(self, mock_mongoengine):
        mock_mongoengine_instance = mock_mongoengine.connect.return_value
        mock_mongoengine_instance.server_info.return_value = {"version":
                                                              connection.MONGO_MINIMUM_VERSION}
        config.config.set('database', 'username', '')
        config.config.set('database', 'password', '')
        connection.initialize()
        self.assertFalse(connection._DATABASE.authenticate.called)

    @patch('pulp.server.db.connection.mongoengine')
    def test_initialize_username_no_password(self, mock_mongoengine):
        mock_mongoengine_instance = mock_mongoengine.connect.return_value
        mock_mongoengine_instance.server_info.return_value = {"version":
                                                              connection.MONGO_MINIMUM_VERSION}
        config.config.set('database', 'username', 'admin')
        config.config.set('database', 'password', '')
        self.assertRaises(Exception, connection.initialize)

    @patch('pulp.server.db.connection.mongoengine')
    def test_initialize_password_no_username(self, mock_mongoengine):
        mock_mongoengine_instance = mock_mongoengine.connect.return_value
        mock_mongoengine_instance.server_info.return_value = {"version":
                                                              connection.MONGO_MINIMUM_VERSION}
        config.config.set('database', 'username', '')
        config.config.set('database', 'password', 'foo')
        self.assertRaises(Exception, connection.initialize)

    @patch('pulp.server.db.connection.OperationFailure', new=MongoEngineConnectionError)
    @patch('pulp.server.db.connection.mongoengine')
    def test_authentication_fails_with_RuntimeError(self, mock_mongoengine):
        mock_mongoengine_instance = mock_mongoengine.connect.return_value
        mock_mongoengine_instance.server_info.return_value = {"version":
                                                              connection.MONGO_MINIMUM_VERSION}
        exc = MongoEngineConnectionError()
        exc.code = 18
        mock_mongoengine.connection.get_db.side_effect = exc
        self.assertRaises(RuntimeError, connection.initialize)


class TestDatabaseRetryOnInitialConnectionSupport(unittest.TestCase):

    @patch('pulp.server.db.connection.mongoengine')
    def test_retry_waits_when_mongoengine_connection_error_is_raised(self, mock_mongoengine):
        def break_out_on_second(*args, **kwargs):
            mock_mongoengine.connect.side_effect = StopIteration()
            raise MongoEngineConnectionError()

        mock_mongoengine.connect.side_effect = break_out_on_second
        mock_mongoengine.connection.ConnectionError = MongoEngineConnectionError

        self.assertRaises(StopIteration, connection.initialize)

    @patch('pulp.server.db.connection.time.sleep')
    @patch('pulp.server.db.connection.mongoengine')
    def test_retry_sleeps_with_backoff(self, mock_mongoengine, mock_sleep):
        def break_out_on_second(*args, **kwargs):
            mock_sleep.side_effect = StopIteration()

        mock_sleep.side_effect = break_out_on_second
        mock_mongoengine.connect.side_effect = MongoEngineConnectionError()
        mock_mongoengine.connection.ConnectionError = MongoEngineConnectionError

        self.assertRaises(StopIteration, connection.initialize)
        mock_sleep.assert_has_calls([call(1), call(2)])

    @patch('pulp.server.db.connection.time.sleep')
    @patch('pulp.server.db.connection.mongoengine')
    def test_retry_with_max_timeout(self, mock_mongoengine, mock_sleep):
        def break_out_on_second(*args, **kwargs):
            mock_sleep.side_effect = StopIteration()

        mock_sleep.side_effect = break_out_on_second
        mock_mongoengine.connect.side_effect = MongoEngineConnectionError()
        mock_mongoengine.connection.ConnectionError = MongoEngineConnectionError

        self.assertRaises(StopIteration, connection.initialize, max_timeout=1)
        mock_sleep.assert_has_calls([call(1), call(1)])

    @patch('pulp.server.db.connection.mongoengine')
    @patch('pulp.server.db.connection.itertools')
    def test_retry_uses_itertools_chain_and_repeat(self, mock_itertools, mock_mongoengine):
        mock_mongoengine.connect.return_value.server_info.return_value = {'version': '2.6.0'}
        connection.initialize()
        mock_itertools.repeat.assert_called_once_with(32)
        mock_itertools.chain.assert_called_once_with([1, 2, 4, 8, 16],
                                                     mock_itertools.repeat.return_value)


class TestGetDatabaseFunction(unittest.TestCase):

    @patch('pulp.server.db.connection._DATABASE')
    def test_get_database(self, mock__DATABASE):
        self.assertEqual(mock__DATABASE, connection.get_database())


class TestGetConnectionFunction(unittest.TestCase):

    @patch('pulp.server.db.connection._CONNECTION')
    def test_get_connection(self, mock__CONNECTION):
        self.assertEqual(mock__CONNECTION, connection.get_connection())
