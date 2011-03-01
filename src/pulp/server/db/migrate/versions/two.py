# -*- coding: utf-8 -*-
#
# Copyright © 2011 Red Hat, Inc.
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

import logging

from pulp.server.auth.authorization import (ensure_builtin_roles,
    consumer_users_role, add_user_to_role,
    grant_automatic_permissions_to_consumer_user)

from pulp.server.db.model.resource import Repo, Consumer, Errata
from pulp.server.db.model.auth import User, Role


_log = logging.getLogger('pulp')

# migration module conventions ------------------------------------------------

version = 2


def _migrate_builtin_roles():
    collection = Repo.get_collection()
    for role in collection.find():
        # just delete the roles directly, we need to leave the user permissions
        # in tact
        if role['name'] in ('SuperUsers', 'ConsumerUsers'):
            collection.remove(role)
    # create the new roles
    ensure_builtin_roles()


def _migrate_consumer_model():
    collection = Consumer.get_collection()
    user_api = User.get_collection()
    for consumer in collection.find():
        key = 'credentials'
        if key not in consumer:
            consumer[key] = None
            collection.save(consumer)
        # look for the corresponding consumer user and create it if missing
        # NOTE deliberately using the api here for the side-effects
        user = user_api.user(consumer['id'])
        if not user:
            user = user_api.create(consumer['id'])
            add_user_to_role(consumer_users_role, user['login'])
            grant_automatic_permissions_to_consumer_user(user['login'])


def _migrate_repo_model():
    collection = Repo.get_collection()
    for repo in collection.find():
        modified = False
        if 'package_count' not in repo:
            repo['package_count'] = len(repo['packages'])
            modified = True
        if 'distributionid' not in repo:
            repo['distributionid'] = []
            modified = True
        if not isinstance(repo['packages'], list):
            repo['packages'] = [pkg_id for pkg_id in repo['packages']]
            modified = True
        if 'allow_upload' in repo:
            del repo['allow_upload']
            modified = True
        if 'checksum_type' not in repo:
            repo['checksum_type'] = u'sha256'
            modified = True
        if modified:
            collection.save(repo)


def _migrate_user_model():
    collection = User.get_collection()
    for user in collection.find():
        modified = False
        if 'roles' not in user or not isinstance(user['roles'], list):
            user['roles'] = []
            modified = True
        if 'SuperUsers' in user['roles']:
            user['roles'].remove('SuperUsers')
            user['roles'].append('super-users')
            modified = True
        if 'ConsumerUsers' in user['roles']:
            user['roles'].remove('ConsumerUsers')
            user['roles'].append('consumer-users')
            modified = True
        if modified:
            collection.save(user)
            
def _migrate_errata_model():
    collection = Errata.get_collection()
    for erratum in collection.find():
        modified = False
        print erratum
        if 'severity' not in erratum:
            erratum['severity'] = u""
            modified = True
        if 'rights' not in erratum:
            erratum['rights'] = u""
            modified = True
        if modified:
            collection.save(erratum)


def migrate():
    _log.info('migration to data model version 2 started')
    _migrate_builtin_roles()
    _migrate_consumer_model()
    _migrate_repo_model()
    _migrate_user_model()
    _migrate_errata_model()
    _log.info('migration to data model version 2 complete')
