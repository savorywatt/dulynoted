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

"""
    Example of using Logs to quickly create revisioned data.

    The whole goal of the log is to allow you to have a single process generate
    a series of writes to another entity that are linearized in the context of
    that original process. In async behavior this will end up with last man
    wins style behavior
"""


import logging

import webapp2

from dulynoted import Log

class ContextEventsHandler(webapp2.RequestHandler):
    """Demonstrate using Context Events to make work flows."""
    def get(self):
        from furious.async import Async
        from furious import context

        count = int(self.request.get('tasks', 5))

        # Create a new furious Context.
        with context.new() as ctx:

            # Set a completion event handler.
            log = Log()
            log.put()
            ctx.set_event_handler('complete',
                                  Async(context_complete, args=[ctx.id, log.key.id()]))

            # Insert some Asyncs.
            for i in xrange(count):
                ctx.add(target=async_worker, args=[ctx.id, i, log.key.id()])
                logging.info('Added job %d to context.', i)

        # When the Context is exited, the tasks are inserted (if there are no
        # errors).
        logging.info('Async jobs for context batch inserted.')

        self.response.out.write(
            'Successfully inserted a group of Async jobs.')


def async_worker(*args, **kwargs):
    """This function is called by furious tasks to demonstrate usage."""
    logging.info("---------------------------------------------------------------------------")

    log = Log.get_by_id(args[2])
    log.new_commit(args[1])

    logging.info('Context %s, function %s other %s', *args)

    return args

def calculate_rate(log):

    delta = log.created - log.updated

    return delta.microseconds / log.latest_revision

def context_complete(context_id, log_id):
    """Log out that the context is complete."""
    logging.info('Context %s is.......... DONE.', context_id)
    log = Log.get_by_id(log_id)
    logging.info('Log Revision %s', log.latest_revision)
    rate = calculate_rate(log)
    logging.info('rate %s microseconds per revision', rate)
    seconds = 1000000 / rate
    logging.info('%s revisions per second', seconds)
    commits = len(log.commits)
    logging.info('%s commits in the log', commits)
    for commit in log.commits:
        print commit
    revisions = len(log.revisions)
    logging.info('revisions %s', revisions)
    revisions = log.commit_range(1, 3)
    for commit in revisions:
        print commit

    return context_id