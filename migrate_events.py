#!/usr/bin/env python
"""Migration script for Active/Older events feature.

Run with: ../bin/python2.7 migrate_events.py

This script is idempotent -- safe to run multiple times.

Actions:
1. Sets on_air=0 for any on-air events
2. Sets last_active to file mtime for events that don't have it
3. Creates _order.json if it doesn't exist
"""
import os
import sys
import stat
import time

_src_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _src_dir)
sys.path.insert(0, os.path.join(_src_dir, 'website'))
import utils


def main():
    events = utils.ReadEvents()
    modified_count = 0

    for evt in events:
        changed = False
        fn = os.path.join(utils.kEventsLoc, evt.name + '.evt')

        # Turn off on_air
        if evt.on_air:
            print('  Turning off on_air: %s (%s)' % (evt.name, evt.title))
            evt.on_air = 0
            changed = True

        # Set last_active from file mtime if not already set
        if evt.last_active == 0.0:
            mtime = os.stat(fn)[stat.ST_MTIME]
            print('  Setting last_active from mtime: %s (%s) -> %s' % (
                evt.name, evt.title, time.strftime('%Y-%m-%d', time.localtime(mtime))))
            evt.last_active = mtime
            changed = True

        if changed:
            evt.WriteEvent()
            modified_count += 1

    print('\nModified %d of %d events.' % (modified_count, len(events)))

    # Create _order.json if it doesn't exist
    order_path = utils._EventOrderPath()
    if not os.path.exists(order_path):
        print('\nCreating initial _order.json...')
        order = utils.BuildInitialEventOrder()
        print('  Active: %d events' % len(order.get('active', [])))
        print('  Older: %d events' % len(order.get('older', [])))
    else:
        print('\n_order.json already exists.')
        order = utils.ReadEventOrder()
        if utils.EnsureEventOrder(events, order):
            utils.WriteEventOrder(order)
            print('  Updated to include all events.')
        print('  Active: %d events' % len(order.get('active', [])))
        print('  Older: %d events' % len(order.get('older', [])))

    print('\nDone.')


if __name__ == '__main__':
    main()
