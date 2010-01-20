#! /usr/bin/env python
"""Tests for Limpets
"""

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is the KBUS Lightweight Linux-kernel mediated
# message system
#
# The Initial Developer of the Original Code is Kynesim, Cambridge UK.
# Portions created by the Initial Developer are Copyright (C) 2009
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   Kynesim, Cambridge UK
#   Tibs <tony.ibbs@gmail.com>
#
# ***** END LICENSE BLOCK *****

import os
import select
import socket
import subprocess
import sys
import time
import nose
from multiprocessing import Process

from kbus import KSock, Message, MessageId, Announcement, \
                 Request, Reply, Status, reply_to
from limpet import run_a_limpet, GiveUp, OtherLimpetGoneAway

NUM_DEVICES = 5
TERMINATION_MESSAGE = '$.Terminate'

def our_limpet(is_server, sock_address, sock_family, kbus_device, network_id):
    """Run a standardised Limpet.
    """
    try:
        run_a_limpet(is_server, sock_address, sock_family, kbus_device,
                     network_id, termination_message=TERMINATION_MESSAGE,
                     verbosity=0)
    except GiveUp as exc:
        print 'KBUS %d %s'%(kbus_device, '; '.join(exc.args))
    except OtherLimpetGoneAway as exc:
        print 'KBUS %d The Limpet at the other end of the connection has closed'%kbus_device

# The "normal" KBUS test code uses a single KBUS, and tests open KSocks
# on it to send/receive messages.
#
# We, on the other hand, expect the tests to use different KBUSs for the
# two ends of a test, and provided a "blackbox" to mediate between them.
#
# This "blackbox" is actually a pair of Limpets, running as separate
# processes...

def run_limpets(sock_address, sock_family):
    """Run the Limpets for our "blackbox" KBUS communications.

    Returns the server and client
    """

    kbus_devices = (1,2)
    network_ids  = (1,2)

    # First, start the server Limpet
    server = Process(target=our_limpet,
                     args=(True, sock_address, sock_family, kbus_devices[0],
                           network_ids[0]))
    server.start()

    # Give it a little time to get ready for the client
    time.sleep(0.5)

    # And then *start* the client
    client = Process(target=our_limpet,
                     args=(False, sock_address, sock_family, kbus_devices[1],
                           network_ids[1]))
    client.start()

    # Again, give it time to do its connecting
    time.sleep(0.5)

    return (server, client)

g_client = None
g_server = None

def setup_module():
    # This path assumes that we are running the tests in the ``kbus/python/sandbox``
    # directory, and that the KBUS kernel module has been built in ``kbus/kbus``.
    retcode = system('sudo insmod ../../kbus/kbus.ko kbus_num_devices=%d'%NUM_DEVICES)
    try:
        assert retcode == 0
        # Via the magic of hotplugging, that should cause our device to exist
        # ...eventually
        time.sleep(1)
        # If the user has done the right magic, it should even have a predictable
        # set of permissions. We check KBUS 0 because that's the one we should
        # always find
        mode = os.stat('/dev/kbus0').st_mode
        assert mode == 020666

        global g_server, g_client
        g_server, g_client = run_limpets('fred', socket.AF_UNIX)
    except:
        system('sudo rmmod kbus')
        raise

def teardown_module():
    with KSock(1, 'rw') as sender:
        sender.send_msg(Message(TERMINATION_MESSAGE))

    print 'Limpet termination message sent'

    g_server.join()
    g_client.join()

    print 'Limpet server and client both finished'

    retcode = system('sudo rmmod kbus')
    assert retcode == 0
    # Via the magic of hotplugging, that should cause our device to go away
    # ...eventually
    time.sleep(1)
    assert not os.path.exists("/dev/kbus0")

# Let's be good and not use os.system...
def system(command):
    """Taken from the Python reference manual. Thank you.
    """
    try:
        retcode = subprocess.call(command, shell=True)
        if retcode < 0:
            print "'%s' was terminated by signal %s"%(command, -retcode)
        else:
            print "'%s' returned %s"%(command, retcode)
        return retcode
    except OSError, e:
        print "Execution of '%s' failed: %s"%(command, e)

if __name__ == '__main__':
    setup_module()
    teardown_module()

# vim: set tabstop=8 softtabstop=4 shiftwidth=4 expandtab:
