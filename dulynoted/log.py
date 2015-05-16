#
# Copyright 2014 Ross Hendrickson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import logging

from google.appengine.ext import ndb


class Log(ndb.Model):
    """Simple model to help linearize writes to another possibly more heavy
    process using lighter weight NDB entities and avoiding cross group
    transactions on the write portion of the work.
    """

    parent = ndb.KeyProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    latest_revision = ndb.IntegerProperty()
    applied_revision = ndb.IntegerProperty()

    @property
    def name(self):
        """The keyname of the model"""
        return str(self.key.id())

    @property
    def commits(self):
        """Will get all the commits for the Log in ascending order"""
        query = Commit.query()
        query = query.filter(Commit.parent_key == self.key,
                             Commit.revision <= self.latest_revision)
        query.order(Commit.revision)
        return query.fetch(100)

    @property
    def revisions(self):
        query = Commit.query(Commit.parent_key == self.key, projection=[Commit.revision])
        query.order(Commit.revision)
        return query.fetch(10)

    def commit_range(self, bottom, top, applied=False):

        query = Commit.query(Commit.parent_key == self.key, Commit.revision >= bottom,
                           Commit.revision <= top, Commit.applied == applied)
        query.order(Commit.revision)
        return query.fetch(10)

    def load_commit(revision):
        return Commit.query(Commit.revision == revision).fetch()

    @property
    def uncommitted():
        query = Commit.query(Commit.revision >= self.applied_revision,
                             Commit.applied == False)
        return query.fetch(10)

    def new_commit(self, data):
        """Will transcationally increment this model's revision and then use
        that new revision for the commit.
        """
        data = str(data)
        new_revision = get_new_revision(self.key)
        commit = Commit()
        commit.revision = new_revision
        commit.data = data
        commit.parent = self.name
        commit.parent_key = self.key
        logging.info("New Commit revision %s", new_revision)
        commit.put()


class Commit(ndb.Model):
    """Roughly designed to hold a unit of work to be done at another point of
    time or to store information for a specific revision of some process"""
    applied = ndb.BooleanProperty(default=False, indexed=True)
    revision = ndb.IntegerProperty(indexed=True)
    parent = ndb.StringProperty(indexed=True)
    parent_key = ndb.KeyProperty(indexed=True)
    data = ndb.BlobProperty(indexed=False)
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)

    @property
    def get_parent(self):
        return Log.get_by_id(self.parent)

@ndb.transactional()
def get_new_revision(log_key, num):
    """Handle a batch of writes"""
    pass


@ndb.transactional()
def get_new_revision(log_key):
    """Transactionally increments the revision of the counter"""
    log = log_key.get()

    if not log_key:
        raise Exception("No log!")

    if not log.latest_revision:
        log.latest_revision = 0

    log.latest_revision += 1
    log.put()

    return log.latest_revision
