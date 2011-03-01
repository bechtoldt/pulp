#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
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

from pulp.server.api.base import BaseApi
from pulp.server.auditing import audit
from pulp.server.db import model
#from pulp.server.db.connection import get_object_db


errata_fields = model.Errata(None, None, None, None, None, None).keys()


class ErrataApi(BaseApi):

    def _getcollection(self):
        return model.Errata.get_collection()

    @audit(params=["id", "title", "type"])
    def create(self, id, title, description, version, release, type,
            status="", updated="", issued="", pushcount="", from_str="",
            reboot_suggested="", references=(), pkglist=(), severity="", 
            rights="", repo_defined=False, immutable=False):
        """
        Create a new Errata object and return it
        """
        e = model.Errata(id, title, description, version, release, type,
                status, updated, issued, pushcount, from_str,
                reboot_suggested, references, pkglist, severity, rights,
                repo_defined, immutable)
        self.collection.insert(e, safe=True)
        return e

    @audit()
    def update(self, delta):
        """
        Updates an errata object in the database
        """
        id = delta.pop('id')
        erratum = self.erratum(id)
        if not erratum:
            raise Exception('Erratum "%s", not-found', id)
        for key,value in delta.items():
            # anything but references
            if key not in ('references',):
                erratum[key] = value
                continue
            # unsupported
            raise Exception, \
                'update keyword "%s", not-supported' % key
        self.collection.save(erratum, safe=True)

    @audit()
    def delete(self, id):
        """
        Delete package version object based on "_id" key
        """
        self.collection.remove(dict(id=id), safe=True)

    def erratum(self, id):
        """
        Return a single Errata object based on the id
        """
        return self.collection.find_one({'id': id})

    def errata(self, id=None, title=None, description=None, version=None,
            release=None, type=None, status=None, updated=None, issued=None,
            pushcount=None, from_str=None, reboot_suggested=None, severity=None):
        """
        Return a list of all errata objects matching search terms
        """
        searchDict = {}
        if id:
            searchDict['id'] = id
        if title:
            searchDict['title'] = title
        if description:
            searchDict['description'] = description
        if version:
            searchDict['version'] = version
        if release:
            searchDict['release'] = release
        if type:
            searchDict['type'] = type
        if status:
            searchDict['status'] = status
        if updated:
            searchDict['updated'] = updated
        if issued:
            searchDict['issued'] = issued
        if pushcount:
            searchDict['pushcount'] = pushcount
        if from_str:
            searchDict['from_str'] = from_str
        if reboot_suggested:
            searchDict['reboot_suggested'] = reboot_suggested
        if severity:
            searchDict['severity'] = severity
        if (len(searchDict.keys()) == 0):
            return list(self.collection.find())
        else:
            return list(self.collection.find(searchDict))

    def search_by_packages(self):
        """
        Search for errata that are associated with specified package info
        """
        pass

    def search_by_issued_date_range(self):
        pass

    def query_by_bz(self, bzid):
        return self.query_by_reference('bugzilla', bzid)

    def query_by_cve(self, cveid):
        return self.query_by_reference('cve', cveid)

    def query_by_reference(self, type, refid):
        """
        Search Errata for all matches of this reference with id 'refid'
        @param type: reference type to search, example 'bugzilla', 'cve'
        @param refid: id to match on
        """
        # Will prob want to chunk the query to mongo and limit the data returned
        # to be only 'references' and 'id'.
        # OR...look into a better way to search inside errata through mongo
        all_errata = self.errata()
        matches = []
        for e in all_errata:
            for ref in e["references"]:
                if ref["type"] == type and ref["id"] == refid:
                    matches.append(e["id"])
                    continue
        return matches

