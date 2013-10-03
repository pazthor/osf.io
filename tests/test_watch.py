#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Unit tests for Node/Project watching.'''
from __future__ import absolute_import
import unittest
import datetime as dt
from pytz import utc
from nose.tools import *  # PEP8 asserts
from framework.auth.model import User
from website.project.model import ApiKey, Node, Tag, WatchConfig
from framework import Q

from tests.base import OsfTestCase
from tests.factories import UserFactory

class TestOsfTestCase(OsfTestCase):
    '''Whoa, so meta.'''

    def test_creating_a_user(self):
        user = UserFactory()
        print(user.username)
        assert_equal(len(User.find()), 1)
        user = UserFactory()
        print(user.username)
        assert_equal(User.find().count(), 2)
        assert False


class TestWatching(unittest.TestCase):

    def setUp(self):
        # FIXME(sloria): This affects the development database;
        # Assumes a user and Node have been created. Use
        # fixtures/factories later
        self.user = User.load("Or8W0")
        self.project = Node.find(Q('category', 'eq', 'project'))[0]
        # add some log objects
        # FIXME(sloria): Assumes user has an API Key
        api_key = self.user.api_keys[0]
        # Clear project logs
        self.project.logs = []
        self.project.save()
        # A log added 100 days ago
        self.project.add_log('project_created',
                        params={'project': self.project._primary_key},
                        user=self.user, log_date=dt.datetime.utcnow(),
                        do_save=True, api_key=api_key)
        # A log added now
        self.last_log = self.project.add_log('tag_added', params={'project': self.project._primary_key},
                        user=self.user, log_date=dt.datetime.utcnow(),
                        do_save=True, api_key=api_key)
        # Clear watched list
        self.user.watched = []
        self.user.save()

    def test_watch_adds_to_watched_list(self):
        n_watched_then = len(self.user.watched)
        # A user watches a WatchConfig
        config = WatchConfig(node=self.project)
        self.user.watch(config)
        n_watched_now = len(self.user.watched)
        assert_equal(n_watched_now, n_watched_then + 1)

    def test_unwatch_removes_from_watched_list(self):
        # The user has already watched a project
        self._watch_project(self.project)
        config = WatchConfig(node=self.project)
        n_watched_then = len(self.user.watched)
        self.user.unwatch(config)
        n_watched_now = len(self.user.watched)
        assert_equal(n_watched_now, n_watched_then - 1)

    @unittest.skip("Won't work because the old log's id doesn't encode the correct log date")
    def test_get_recent_log_ids(self):
        self._watch_project(self.project)
        log_ids = list(self.user.get_recent_log_ids())
        assert_equal(self.last_log._id, log_ids[0])
        # This part won't work
        # TODO(sloria): Rethink.
        assert_equal(len(log_ids), 1)

    def test_get_recent_log_ids_since(self):
        self._watch_project(self.project)
        since = dt.datetime.utcnow().replace(tzinfo=utc) - dt.timedelta(days=101)
        log_ids = list(self.user.get_recent_log_ids(since=since))
        assert_equal(len(log_ids), 2)

    def _watch_project(self, project):
        watch_config = WatchConfig(node=project)
        self.user.watch(watch_config)
        self.user.save()

    def _unwatch_project(self, project):
        watch_config = WatchConfig(node=project)
        self.user.watch(watch_config)
        self.user.save()

if __name__ == '__main__':
    unittest.main()
