"""Python code for testing the kbus kernel module.

Intended for use with (for instance) nose -- so, for instance::

    $ cd kernel_module
    $ make
    $ nosetests test_kbus.py -d
    ...........................
    ----------------------------------------------------------------------
    Ran 27 tests in 2.048s

    OK

To get the doctests (for instance, in kbus.py's Message) as well, try::

    nosetests kbus.py test_kbus.py -d --doctest-tests --with-doctest
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

from __future__ import with_statement

import sys
import os
import subprocess
import fcntl
import time
import array
import errno
import nose

from kbus import KSock, Message, Request, Reply
from kbus import read_bindings, KbusBindStruct

NUM_DEVICES = 3

def setup_module():
    retcode = system('sudo insmod kbus.ko kbus_num_devices=%d'%NUM_DEVICES)
    assert retcode == 0
    # Via the magic of hotplugging, that should cause our device to exist
    # ...eventually
    time.sleep(1)

def teardown_module():
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
            print "'%s' was terminated by signal %s"%(command,-retcode)
        else:
            print "'%s' returned %s"%(command,retcode)
        return retcode
    except OSError, e:
        print "Execution of '%s' failed: %s"%(command,e)

class BindingsMemory(object):
    """A class for remembering message name bindings.

    We remember bindings in a dictionary, relating KSock instances to
    bindings made on those interfaces. So, for instance:
    
       bindings[if] = [(True,False,'$.Fred.Jim.Bob'),
                       (False,True,'$.Fred')]
    
    (the order in the tuple matches that in the /proc/kbus/bindings file).
    
    Automatically managed by the local bind and unbind *methods*
    """

    def __init__(self):
        self.bindings = {}

    def remember_ksock(self,ksock):
        self.bindings[ksock] = []

    def forget_ksock(self,ksock):
        del self.bindings[ksock]

    def remember_binding(self,ksock,name,replier=False):
        self.bindings[ksock].append( (replier,name) )

    def forget_binding(self,ksock,name,replier=False):
        if_list = self.bindings[ksock]
        # If there are multiple matches, we'll delete the first,
        # which is what we want (well, to delete a single instance)
        for index,thing in enumerate(if_list):
            if thing[-1] == name:       # the name is always the last element
                del if_list[index]
                break
        # No matches shouldn't occur, but let's ignore it anyway

    def check_bindings(self):
        """Check the bindings we think we have match those of kbus
        """
        expected = []
        for ksock,if_list in self.bindings.items():
            for r,n in if_list:
                expected.append( (ksock,r,n) )
        assert bindings_match(expected)

class RecordingKSock(KSock):
    """A variant of KSock which remembers and checks its bindings.

    Intended originally for use in writing test code.

    The constructor takes an extra argument, which should be a BindingsMemory
    instance, and which is used to remember our bindings. Otherwise, use it
    just like an ordinary KSock.
    """

    def __init__(self, which=0, mode='r', bindings=None):
        super(RecordingKSock,self).__init__(which,mode)
        self.bindings = bindings
        self.bindings.remember_ksock(self)

    def close(self):
        super(RecordingKSock,self).close()
        self.bindings.forget_ksock(self)
        self.bindings = None

    def bind(self,name,replier=False):
        """A wrapper around the 'bind' function. to keep track of bindings.
        """
        super(RecordingKSock,self).bind(name,replier)
        self.bindings.remember_binding(self,name,replier)

    def unbind(self,name,replier=False):
        """A wrapper around the 'unbind' function, to keep track of bindings.
        """
        super(RecordingKSock,self).unbind(name,replier)
        self.bindings.forget_binding(self,name,replier)

def str_rep(rep):
    if rep:
        return 'R'
    else:
        return 'L'

def bindings_match(bindings):
    """Look up the current bindings and check they match the list.

    'bindings' is a sequence of tuples, each of the form:

        ( file_descriptor, True|False, name )

    so for instance:

        ( (f,True,'$.Fred'), (g,False,'$.JimBob') )

    where the boolean means the binding is for a replier (or not).

    The function reads the contents of /proc/kbus/bindings. It translates each
    file descriptor to a listener id using ``bound_as``, and thus converts
    'bindings' to an equivalent list.

    Silently returns True if the bindings in /proc/kbus/bindings match
    those expected, returns False (and prints out the mismatch) if they do not.
    """
    testwith = []
    names = {}
    for (fd,rep,name) in bindings:
        if fd not in names:
            names[fd] = fd.bound_as()
        testwith.append((fd.bound_as(),rep,name))

    actual = read_bindings(names)

    # And compare the two lists - ideally they should match
    # (although we don't want to care about order, I think)
    actual.sort()
    testwith.sort()
    if actual == testwith:
        return True

    # If they're not the same, we need to let the user know in some not too
    # unfriendly manner
    found    = set(actual)
    expected = set(testwith)
    print 'The contents of /proc/kbus/bindings is not as expected'
    if len(found):
        print 'The following were expected but not found:'
        for f,r,n in expected-found:
            print '  %10u %c %s'%(f,str_rep(r),n)
    if len(expected):
        print 'The following were found but not expected:'
        for f,r,n in found-expected:
            print '  %10u %c %s'%(f,str_rep(r),n)
    return False

def check_IOError(expected_errno,fn,*stuff):
    """When calling apply(fn,stuff), check for IOError with the given errno.

    Check that is what happens...
    """
    try:
        apply(fn,stuff)
        # We're not expecting to get here...
        assert False, 'Applying %s%s did not fail with IOError'%(repr(fn),repr(stuff))
    except IOError, e:
        actual_errno = e.args[0]
        errno_name = errno.errorcode[actual_errno]
        expected_errno_name = errno.errorcode[expected_errno]
        assert actual_errno == expected_errno, \
                'expected %s, got %s'%(expected_errno_name,errno_name)
    except Exception, e:
        print e
        assert False, 'Applying %s%s failed with %s, not IOError'%(repr(fn),
                repr(stuff),sys.exc_type)

class TestKSock:
    """Some basic testing of KSock.

    Not much here, because most of its testing is done implicitly via
    its use in other tests. And it really is fairly simple.
    """

    def test_opening(self):
        """Test opening/closing KSock objects.
        """
        # We should be able to open each device that exists
        for ii in range(NUM_DEVICES):
            f = KSock(ii)
            f.close()
        # and not those that don't
        check_IOError(errno.ENOENT,KSock,-1)
        check_IOError(errno.ENOENT,KSock,NUM_DEVICES)

    def test_modes(self):
        """Test only the allowed modes are allowed
        """
        f = KSock(0,'r')
        f.close()
        f = KSock(0,'rw')
        f.close()
        nose.tools.assert_raises(ValueError,KSock,0,'fred')
        nose.tools.assert_raises(ValueError,KSock,0,'w+')
        nose.tools.assert_raises(ValueError,KSock,0,'x')

class TestKernelModule:

    def __init__(self):
        self.bindings = BindingsMemory()

    def _check_bindings(self):
        self.bindings.check_bindings()

    def _check_read(self,f,expected):
        """Check that we can read back an equivalent message to 'expected'
        """
        if expected:
            new_message = f.read_next_msg()
            assert new_message != None
            assert expected.equivalent(new_message)
        else:
            # We're not expecting anything -- check that's what we get
            # - first, directly
            data = f.fd.read(1)
            assert data == ''
            # - secondly, in terms of KSock and Message
            assert f.read_msg(1) == None

    def test_readonly(self):
        """If we open the device readonly, we can't do much(!)
        """
        f = RecordingKSock(0,'r',self.bindings)
        assert f != None
        try:
            # Nothing to read
            assert f.next_msg() == 0
            assert f.read_data(1) == ''

            # We can't write to it, by any of the obvious means
            msg2 = Message('$.Fred','data')
            check_IOError(errno.EBADF,f.write_data,msg2.array)
            check_IOError(errno.EBADF,f.write_msg,msg2)
            check_IOError(errno.EBADF,f.send_msg,msg2)
        finally:
            assert f.close() is None

    def test_readwrite_kbus0(self):
        """If we open the device read/write, we can read and write.
        """
        f = RecordingKSock(0,'rw',self.bindings)
        assert f != None

        try:
            f.bind('$.B')
            f.bind('$.C')

            # We start off with no message
            self._check_read(f,None)

            # We can send a message and read it back
            msg1 = Message('$.B','data')
            f.send_msg(msg1)
            self._check_read(f,msg1)

            # We can send a message and read it back, again
            msg2 = Message('$.C','fred')
            f.send_msg(msg2)
            self._check_read(f,msg2)

            # If we try to send a message that nobody is listening for,
            # it just disappears into the void
            msg3 = Message('$.D','fred')
            f.send_msg(msg3)

        finally:
            assert f.close() is None

    def test_two_opens_kbus0(self):
        """If we open the device multiple times, they communicate
        """
        f1 = RecordingKSock(0,'rw',self.bindings)
        assert f1 != None
        try:
            f2 = RecordingKSock(0,'rw',self.bindings)
            assert f2 != None
            try:
                # Both files listen to both messages
                f1.bind('$.B',False)
                f1.bind('$.C',False)
                f2.bind('$.B',False)
                f2.bind('$.C',False)

                # Nothing to read at the start
                self._check_read(f1,None)
                self._check_read(f2,None)

                # If we write, we can read appropriately
                msg1 = Message('$.B','data')
                f1.send_msg(msg1)
                self._check_read(f2,msg1)
                self._check_read(f1,msg1)

                msg2 = Message('$.C','data')
                f2.send_msg(msg2)
                self._check_read(f1,msg2)
                self._check_read(f2,msg2)
            finally:
                assert f2.close() is None
        finally:
            assert f1.close() is None

    def test_bind(self):
        """Initial ioctl/bind test.
        """
        f = RecordingKSock(0,'rw',self.bindings)
        assert f != None

        try:
            # - BIND
            # Low level check: The "Bind" ioctl requires a proper argument
            check_IOError(errno.EFAULT, fcntl.ioctl, f.fd, KSock.IOC_BIND, 0)
            # Said string must not be zero length
            check_IOError(errno.EBADMSG, f.bind, '', True)
            f.bind('$.Fred')
            # - UNBIND
            check_IOError(errno.EFAULT, fcntl.ioctl, f.fd, KSock.IOC_UNBIND, 0)
            check_IOError(errno.EBADMSG, f.unbind, '', True)
            f.unbind('$.Fred')
        finally:
            assert f.close() is None

    def test_many_bind_1(self):
        """Initial ioctl/bind test -- make lots of bindings
        """
        f = RecordingKSock(0,'rw',self.bindings)
        assert f != None

        try:
            f.bind('$.Fred')
            f.bind('$.Fred.Jim')
            f.bind('$.Fred.Bob')
            f.bind('$.Fred.Jim.Bob')
        finally:
            assert f.close() is None

    def test_many_bind_2(self):
        """Initial ioctl/bind test -- make lots of the same binding
        """
        f = RecordingKSock(0,'rw',self.bindings)
        assert f != None

        try:
            f.bind('$.Fred')
            f.bind('$.Fred',False)
            f.bind('$.Fred',False)
            f.bind('$.Fred',False)
        finally:
            assert f.close() is None

    def test_many_bind_3(self):
        """Initial ioctl/bind test -- multiple matching bindings/unbindings
        """
        f = RecordingKSock(0,'rw',self.bindings)
        assert f != None

        try:
            f.bind('$.Fred',True)  # But remember, only one replier
            f.bind('$.Fred',False)
            f.bind('$.Fred',False)
            f.unbind('$.Fred',True)
            f.unbind('$.Fred',False)
            f.unbind('$.Fred',False)
            # But not too many
            check_IOError(errno.EINVAL, f.unbind, '$.Fred')
            check_IOError(errno.EINVAL, f.unbind, '$.Fred',False)
            # We can't unbind something we've not bound
            check_IOError(errno.EINVAL, f.unbind, '$.JimBob',False)
        finally:
            assert f.close() is None

    def test_bind_more(self):
        """Initial ioctl/bind test - with more bindings.
        """
        f1 = RecordingKSock(0,'rw',self.bindings)
        assert f1 != None
        try:
            f2 = RecordingKSock(0,'rw',self.bindings)
            assert f2 != None
            try:
                # We can bind and unbind
                f1.bind('$.Fred',replier=True)
                f1.unbind( '$.Fred',replier=True)
                f1.bind('$.Fred',replier=False)
                f1.unbind( '$.Fred',replier=False)
                # We can bind many times
                f1.bind('$.Fred',replier=False)
                f1.bind('$.Fred',replier=False)
                f1.bind('$.Fred',replier=False)
                # But we can only have one replier
                f1.bind('$.Fred',replier=True)
                check_IOError(errno.EADDRINUSE, f1.bind, '$.Fred',True)

                # Two files can bind to the same thing
                f1.bind('$.Jim.Bob',replier=False)
                f2.bind('$.Jim.Bob',replier=False)
                # But we can still only have one replier
                f1.bind('$.Jim.Bob',replier=True)
                check_IOError(errno.EADDRINUSE, f2.bind, '$.Jim.Bob', True)
            finally:
                assert f2.close() is None
        finally:
            assert f1.close() is None

    def test_bindings_match1(self):
        """Check that bindings match inside and out.
        """
        f1 = RecordingKSock(0,'rw',self.bindings)
        assert f1 != None
        try:
            f2 = RecordingKSock(0,'rw',self.bindings)
            assert f2 != None
            try:
                f1.bind('$.Fred',True)
                f1.bind('$.Fred.Jim',True)
                f1.bind('$.Fred.Bob',True)
                f1.bind('$.Fred.Jim.Bob',True)
                f1.bind('$.Fred.Jim.Derek')
                # /proc/kbus/bindings should reflect all of the above, and none other
                self._check_bindings()
                f2.bind('$.Fred.Jim.Derek')
                f2.bind('$.William')
                f2.bind('$.William')
                f2.bind('$.William')
                f1.bind('$.Fred.Jim.Bob.Eric',True)
                self._check_bindings()
            finally:
                assert f2.close() is None
        finally:
            assert f1.close() is None
        # And now all of the bindings *should* have gone away
        self._check_bindings()

    def test_rw_single_file(self):
        """Test reading and writing two messages on a single file
        """
        f = RecordingKSock(0,'rw',self.bindings)
        assert f != None
        try:

            name1 = '$.Fred.Jim'
            data1 = array.array('L','datadata')

            name2 = '$.Fred.Bob.William'
            data2 = array.array('L','This is surely some data')

            # Bind so that we can write/read the first, but not the second
            f.bind(name1,False)
            f.bind('$.William',False)

            msg1 = Message(name1,data=data1)
            f.send_msg(msg1)
            print 'Wrote:',msg1

            # There are no listeners for '$.Fred.Bob.William'
            msg2 = Message(name2,data=data2)
            f.send_msg(msg2)
            # So it just gets ignored

            msg1r = f.read_next_msg()
            print 'Read: ',msg1r

            # The message read should essentially match
            assert msg1.equivalent(msg1r)

            msg2r = f.read_next_msg()
            assert msg2r == None

            # There shouldn't be anything else to read
            assert f.read_next_msg() == None

        finally:
            assert f.close() is None

    def test_read_write_2files(self):
        """Test reading and writing between two files.
        """
        f1 = RecordingKSock(0,'rw',self.bindings)
        assert f1 != None
        try:
            f2 = RecordingKSock(0,'rw',self.bindings)
            assert f2 != None
            try:
                f1.bind('$.Fred',False)
                f1.bind('$.Fred',False)
                f1.bind('$.Fred',False)

                f2.bind('$.Jim',False)

                # No one is listening for $.William, so we can just send it
                # and it will get ignored
                msgW = Message('$.William')
                f1.send_msg(msgW)
                f2.send_msg(msgW)

                # Writing to $.Fred on f1 - writes message id N
                msgF = Message('$.Fred','data')
                (ret,n0) = f1.send_msg(msgF)

                # Writing to $.Jim on f1 - writes message N+1
                msgJ = Message('$.Jim','moredata')
                (ret,n1) = f1.send_msg(msgJ)
                assert n1 == n0+1

                # Reading f1 - message N
                length = f1.next_msg()
                assert length == msgF.length*4
                data = f1.read_msg(length)
                assert n0 == data.id

                # Reading f2 - should be message N+1
                length = f2.next_msg()
                assert length == msgJ.length*4
                data = f2.read_msg(length)
                assert data.id == n0+1

                # Reading f1 - should be message N again
                length = f1.next_msg()
                assert length == msgF.length*4
                data = f1.read_msg(length)
                assert data.id == n0

                # Reading f1 - should be message N again
                length = f1.next_msg()
                assert length == msgF.length*4
                data = f1.read_msg(length)
                assert data.id == n0

                # No more messages on f1
                assert f1.next_msg() == 0
                assert f1.read_data(1) == ''

                # No more messages on f2
                assert f2.next_msg() == 0
                assert f2.read_data(1) == ''
            finally:
                assert f2.close() is None
        finally:
            assert f1.close() is None

    def test_message_names(self):
        """Test for message name legality.
        """
        f = RecordingKSock(0,'rw',self.bindings)
        assert f != None
        try:

            def _error(error,name):
                check_IOError(error, f.bind, name, True)

            def _ok(name):
                f.bind(name,True)

            # I don't necessarily know what name will be "too long",
            # but we can make a good guess as to a silly sort of length
            _error(errno.ENAMETOOLONG,'1234567890'*1000)

            # We need a leading '$.'
            _error(errno.EBADMSG,'')
            _error(errno.EBADMSG,'$')
            _error(errno.EBADMSG,'$x')
            _error(errno.EBADMSG,'Fred')

            _error(errno.EBADMSG,"$.Non-alphanumerics aren't allowed")
            _error(errno.EBADMSG,'$.#')

            # We cannot end with a dot
            _error(errno.EBADMSG,'$.Fred.')
            _error(errno.EBADMSG,'$.Fred..')
            # Or have two dots in a row
            _error(errno.EBADMSG,'$.Fred..Jim')
            _error(errno.EBADMSG,'$.Fred...Jim')
            _error(errno.EBADMSG,'$.Fred....Jim')

            # The following *are* legal
            _ok('$.Fred.Jim')
            _ok('$.Fred.Jim.Fred.Jim.MoreNames.And.More')
            _ok('$.QuiteLongWordsAreAllowedInNames')
            # Case matters
            _ok('$.This.is.a.different.name')
            _ok('$.THIS.is.a.different.name')
            # Top level wildcards are OK
            _ok('$.*')
            _ok('$.%')
        
        finally:
            assert f.close() is None

    def test_data_too_long(self):
        """Test for message name legality.
        """
        f = RecordingKSock(0,'rw',self.bindings)
        assert f != None
        try:
            # I don't necessarily know how much data will be "too long",
            # but we can make a good guess as to a silly sort of length
            m = Message('$.Fred',data='12345678'*1000)
            f.bind('$.Fred')
            check_IOError(errno.EMSGSIZE, f.send_msg, m)
        finally:
            assert f.close() is None

    def test_cant_write_to_wildcard(self):
        """It's not possible to send a message with a wildcard name.
        """
        f = RecordingKSock(0,'rw',self.bindings)
        assert f != None
        try:
            # Listen with a wildcard - this is OK
            f.bind('$.Fred.*')
            # Create a message with a silly name - Message doesn't care
            m = Message('$.Fred.*')
            # We can write the message out
            f.write_msg(m)
            # But we can't send it
            check_IOError(errno.EBADMSG, f.send)

            # Try a different wildcard, and a different mechanism
            f.bind('$.Jim.%')
            m = Message('$.Jim.%')
            check_IOError(errno.EBADMSG, f.send_msg, m)
        finally:
            assert f.close() is None

    def test_request_vs_message(self):
        """Test repliers and Requests versus Messages
        """
        with RecordingKSock(0,'rw',self.bindings) as f0:
            with RecordingKSock(0,'r',self.bindings) as listener:
                listener.bind('$.Fred.Message',False)
                
                # A listener receives Messages
                m = Message('$.Fred.Message')
                f0.send_msg(m)
                r = listener.read_next_msg()
                assert r.equivalent(m)
                assert not r.wants_us_to_reply()

                with RecordingKSock(0,'r',self.bindings) as replier:
                    replier.bind('$.Fred.Message',True)

                    # And a listener receives Requests (although it need not reply)
                    m = Request('$.Fred.Message')
                    f0.send_msg(m)
                    r = listener.read_next_msg()
                    assert r.equivalent(m)
                    assert not r.wants_us_to_reply()
                    
                    # The Replier receives the Request (and should reply)
                    r = replier.read_next_msg()
                    assert r.equivalent(m)
                    assert r.wants_us_to_reply()

                    # A replier does not receive Messages
                    # (presumably the listener still does, but we're not going
                    # to check)
                    m = Message('$.Fred.Message')
                    f0.send_msg(m)
                    assert replier.next_msg() == 0

    def test_wildcards_a_bit(self):
        """Some initial testing of wildcards. And use of 'with'
        """
        with RecordingKSock(0,'rw',self.bindings) as f:
            assert f != None
            # Note, binding just as a listener
            f.bind('$.Fred.*',False)

            # We should receive the message, it matches the wildcard
            m = Message('$.Fred.Jim')
            f.send_msg(m)
            r = f.read_next_msg()
            assert r.equivalent(m)

            # And again
            m = Message('$.Fred.JimBob.William')
            f.send_msg(m)
            r = f.read_next_msg()
            assert r.equivalent(m)

            # But this does not match the wildcard, so gets ignored
            m = Message('$.Fred')
            f.send_msg(m)

            # A more specific binding, overlapping the wildcard
            # Since we're bound as (just) a listener both times,
            # we should get the message twice, once for each binding
            f.bind('$.Fred.Jim',False)
            m = Message('$.Fred.Jim')
            f.send_msg(m)
            r = f.read_next_msg()
            assert r.equivalent(m)
            r = f.read_next_msg()
            assert r.equivalent(m)

    def test_wildcards_a_bit_more(self):
        """Some more initial testing of wildcards. And use of 'with'
        """
        with RecordingKSock(0,'rw',self.bindings) as f:
            assert f != None
            # Note, binding as a default replier
            f.bind('$.Fred.*',True)

            # We should receive the message, it matches the wildcard
            m = Request('$.Fred.Jim')
            f.send_msg(m)
            r = f.read_next_msg()
            assert r.equivalent(m)
            assert r.wants_us_to_reply()

            # And again
            m = Request('$.Fred.JimBob.William')
            f.send_msg(m)
            r = f.read_next_msg()
            assert r.equivalent(m)
            assert r.wants_us_to_reply()

            # But this does not match the wildcard
            m = Request('$.Fred')
            check_IOError(errno.EADDRNOTAVAIL, f.send_msg, m)

            # A more specific binding, overlapping the wildcard
            f.bind('$.Fred.Jim',True)
            m = Request('$.Fred.Jim')
            f.send_msg(m)
            r = f.read_next_msg()
            assert r.equivalent(m)
            assert r.wants_us_to_reply()

            # But we should only receive it once, on the more specific binding
            assert f.next_msg() == 0

    def test_message_equality(self):
        """Messages are not equal to non-messages, and so on.
        """
        a = Message('$.Fred')
        b = Message('$.Fred')
        c = Message('$.Jim')
        assert (a == b)
        assert (a != c)

        assert (a ==    3) == False
        assert (a == None) == False
        assert (a !=    3) == True
        assert (a != None) == True

        assert (3    == a) == False
        assert (None == a) == False
        assert (3    != a) == True
        assert (None != a) == True

    def test_iteration(self):
        """Test we can iterate over messages.
        """
        with RecordingKSock(0,'rw',self.bindings) as f:
            assert f != None
            f.bind('$.Fred')
            m = Message('$.Fred')
            for ii in range(5):
                f.send_msg(m)
            count = 0
            for r in f:
                count += 1
            assert count == 5
            # And again
            for ii in range(5):
                f.send_msg(m)
            count = 0
            for r in f:
                count += 1
            assert count == 5

    def test_wildcard_listening_1(self):
        """Test using wildcards to listen - 1, asterisk.
        """
        with RecordingKSock(0,'rw',self.bindings) as f0:

            with RecordingKSock(0,'r',self.bindings) as f1:
                f1.bind('$.This.Fred')
                f1.bind('$.That.Fred')

                with RecordingKSock(0,'r',self.bindings) as f2:
                    f2.bind('$.This.Jim.One')
                    f2.bind('$.This.Jim.Two')
                    f2.bind('$.That.Jim')

                    with RecordingKSock(0,'r',self.bindings) as f3:
                        f3.bind('$.This.*')

                        # For each tuple, we have:
                        #
                        # 1. The KSock we're meant to be sending the
                        #    message to
                        # 2. Whether it should be "seen" by f0 (via f0's
                        #    wildcard binding)
                        # 3. The actual message
                        msgs = [ (f1, True,  Message('$.This.Fred','dat1')),
                                 (f1, True,  Message('$.This.Fred','dat2')),
                                 (f1, False, Message('$.That.Fred','dat3')),
                                 (f1, False, Message('$.That.Fred','dat4')),
                                 (f2, True,  Message('$.This.Jim.One','dat1')),
                                 (f2, True,  Message('$.This.Jim.Two','dat2')),
                                 (f2, False, Message('$.That.Jim','dat3')),
                                 (f2, False, Message('$.That.Jim','dat4')),
                                ]

                        for fd,wild,m in msgs:
                            f0.send_msg(m)

                        for fd,wild,m in msgs:
                            if wild:
                                # This is a message that f3 should see
                                a = f3.read_next_msg()
                                assert a.equivalent(m)

                            # Who else should see this message?
                            b = fd.read_next_msg()
                            assert b.equivalent(m)

    def test_wildcard_listening_2(self):
        """Test using wildcards to listen - 2, percent.
        """
        with RecordingKSock(0,'rw',self.bindings) as f0:

            with RecordingKSock(0,'r',self.bindings) as f1:
                f1.bind('$.This.Fred')
                f1.bind('$.That.Fred')

                with RecordingKSock(0,'r',self.bindings) as f2:
                    f2.bind('$.This.Jim.One')
                    f2.bind('$.This.Jim.Two')
                    f2.bind('$.That.Jim')

                    with RecordingKSock(0,'r',self.bindings) as f3:
                        f3.bind('$.This.%')

                        # For each tuple, we have:
                        #
                        # 1. The KSock we're meant to be sending the
                        #    message to
                        # 2. Whether it should be "seen" by f0 (via f0's
                        #    wildcard binding)
                        # 3. The actual message
                        msgs = [ (f1, True,  Message('$.This.Fred','dat1')),
                                 (f1, True,  Message('$.This.Fred','dat2')),
                                 (f1, False, Message('$.That.Fred','dat3')),
                                 (f1, False, Message('$.That.Fred','dat4')),
                                 (f2, False, Message('$.This.Jim.One','dat1')),
                                 (f2, False, Message('$.This.Jim.Two','dat2')),
                                 (f2, False, Message('$.That.Jim','dat3')),
                                 (f2, False, Message('$.That.Jim','dat4')),
                                ]

                        for fd,wild,m in msgs:
                            f0.send_msg(m)

                        for fd,wild,m in msgs:
                            if wild:
                                # This is a message that f3 should see
                                a = f3.read_next_msg()
                                assert a.equivalent(m)

                            # Who else should see this message?
                            b = fd.read_next_msg()
                            assert b.equivalent(m)

    def test_reply_single_file(self):
        """Test replying with a single file
        """
        with RecordingKSock(0,'rw',self.bindings) as f:
            name1 = '$.Fred.Jim'
            name2 = '$.Fred.Bob.William'
            name3 = '$.Fred.Bob.Jonathan'

            f.bind(name1,True)     # replier
            f.bind(name1,False)    # and listener
            f.bind(name2,True)     # replier
            f.bind(name3,False)    # listener

            msg1 = Message(name1,data='dat1')
            msg2 = Request(name2,data='dat2')
            msg3 = Request(name3,data='dat3')

            f.send_msg(msg1)
            f.send_msg(msg2)

            # We are not a Replier for m3, and there *isn't* a replier,
            # so we can't send it
            check_IOError(errno.EADDRNOTAVAIL, f.send_msg, msg3)

            m1 = f.read_next_msg()
            m2 = f.read_next_msg()

            # For message 1, we only see it as a listener
            # (because it is not a Request) so there is no reply needed
            assert not m1.wants_us_to_reply()
            assert m1.equivalent(msg1)

            # For message 2, a reply is wanted, and we are the replier
            assert m2.wants_us_to_reply()
            assert m2.equivalent(msg2)

            # So, we should reply to message 2 - let's do so

            # We can make a reply "by hand" - remember that we want to
            # reply to the message we *received*, which has the id set
            # (by KBUS)
            (id,in_reply_to,to,from_,flags,name,data_array) = m2.extract()
            reply_by_hand = Message(name, data=None, in_reply_to=id, to=from_)

            # But it is easier to use the pre-packaged mechanism
            reply = Reply(m2)

            # These should, however, give the same result
            assert reply == reply_by_hand

            # And the obvious thing to do with a reply is
            f.send_msg(reply)

            # We should receive that reply, even though we're not
            # a listener for the message (that's the *point* of replies)
            m4 = f.read_next_msg()
            assert m4.equivalent(reply)
            assert not m4.wants_us_to_reply()

            # And there shouldn't be anything else to read
            assert f.next_msg() == 0

    def test_reply_three_files(self):
        """Test replying with two files in dialogue, and another listening
        """
        with RecordingKSock(0,'r',self.bindings) as listener:
            listener.bind('$.*')

            with RecordingKSock(0,'rw',self.bindings) as writer:

                with RecordingKSock(0,'rw',self.bindings) as replier:
                    replier.bind('$.Fred',replier=True)

                    msg1 = Message('$.Fred')    # no reply necessary
                    msg2 = Request('$.Fred')

                    writer.send_msg(msg1)
                    writer.send_msg(msg2)

                    # The replier should not see msg1
                    # But it should see msg2, which should ask *us* for a reply
                    rec2 = replier.read_next_msg()
                    assert rec2.wants_us_to_reply()
                    assert rec2.equivalent(msg2)

                    # Which we can reply to
                    rep = Reply(msg2)
                    replier.send_msg(rep)
                    assert not rep.wants_us_to_reply()       # just to check!

                    # But should not receive
                    assert replier.next_msg() == 0

                    # The listener should get all of those messages
                    # (the originals and the reply)
                    # but should not be the replier for any of them
                    a = listener.read_next_msg()
                    assert a.equivalent(msg1)
                    assert not a.wants_us_to_reply()
                    b = listener.read_next_msg()
                    assert b.equivalent(msg2)
                    assert not b.wants_us_to_reply()
                    c = listener.read_next_msg()
                    assert c.equivalent(rep)
                    assert not c.wants_us_to_reply()

                    # No-one should have any more messages
                    assert listener.next_msg() == 0
                    assert writer.next_msg()   == 0
                    assert replier.next_msg()  == 0

    def test_wildcard_generic_vs_specific_bind_1(self):
        """Test generic versus specific wildcard binding - fit the first
        """
        with RecordingKSock(0,'rw',self.bindings) as f0:
            # We'll use this interface to do all the writing of requests,
            # just to keep life simple.

            with RecordingKSock(0,'r',self.bindings) as f1:
                # f1 asks for generic replier status on everything below '$.Fred'
                f1.bind('$.Fred.*',replier=True)

                mJim = Request('$.Fred.Jim')
                f0.send_msg(mJim)
                r = f1.read_next_msg()
                assert r.wants_us_to_reply()
                assert r.equivalent(mJim)

                assert f1.next_msg() == 0

                # Hmm - apart from existential worries, nothing happens if we
                # don't *actually* reply..

                with RecordingKSock(0,'r',self.bindings) as f2:
                    # f2 knows it wants specific replier status on '$.Fred.Jim'
                    f2.bind('$.Fred.Jim',replier=True)

                    # So, now, any requests to '$.Fred.Jim' should only go to
                    # f2, who should need to reply to them.
                    # Any requests to '$.Fred.Bob' should only go to f1, who
                    # should need to reply to them.
                    mBob = Request('$.Fred.Bob')

                    f0.send_msg(mJim)      # should only go to f2
                    f0.send_msg(mBob)      # should only go to f1

                    rJim = f2.read_next_msg()
                    assert rJim.wants_us_to_reply()
                    assert rJim.equivalent(mJim)
                    assert f2.next_msg() == 0

                    rBob = f1.read_next_msg()
                    assert rBob.wants_us_to_reply()
                    assert rBob.equivalent(mBob)
                    assert f1.next_msg() == 0

    def test_wildcard_generic_vs_specific_bind_2(self):
        """Test generic versus specific wildcard binding - fit the second
        """
        with RecordingKSock(0,'rw',self.bindings) as f0:
            # We'll use this interface to do all the writing of requests,
            # just to keep life simple.

            with RecordingKSock(0,'r',self.bindings) as f1:
                # f1 asks for generic replier status on everything below '$.Fred'
                f1.bind('$.Fred.*',replier=True)

                mJim = Request('$.Fred.Jim')
                f0.send_msg(mJim)
                r = f1.read_next_msg()
                assert r.wants_us_to_reply()
                assert r.equivalent(mJim)

                assert f1.next_msg() == 0

                # Hmm - apart from existential worries, nothing happens if we
                # don't *actually* reply..

                with RecordingKSock(0,'r',self.bindings) as f2:
                    # f2 gets more specific
                    f2.bind('$.Fred.%',replier=True)

                    # So, now, any requests to '$.Fred.Jim' should only go to
                    # f2, who should need to reply to them.
                    # Any requests to '$.Fred.Jim.Bob' should only go to f1,
                    # who should need to reply to them.
                    mJimBob = Request('$.Fred.Jim.Bob')

                    f0.send_msg(mJim)      # should only go to f2
                    f0.send_msg(mJimBob)   # should only go to f1

                    rJim = f2.read_next_msg()
                    assert rJim.wants_us_to_reply()
                    assert rJim.equivalent(mJim)
                    assert f2.next_msg() == 0

                    rJimBob = f1.read_next_msg()
                    assert rJimBob.wants_us_to_reply()
                    assert rJimBob.equivalent(mJimBob)
                    assert f1.next_msg() == 0

                    with RecordingKSock(0,'r',self.bindings) as f3:
                        # f3 knows it wants specific replier status on '$.Fred.Jim'
                        f3.bind('$.Fred.Jim',replier=True)

                        # So, now, any requests to '$.Fred.Jim' should only go to
                        # f3, who should need to reply to them.
                        # Any requests to '$.Fred.James' should still go to f2
                        # Any requests to '$.Fred.Jim.Bob' should still only go to f1
                        mJames = Request('$.Fred.James')

                        f0.send_msg(mJim)      # should only go to f3
                        f0.send_msg(mJames)    # should only go to f2
                        f0.send_msg(mJimBob)   # should only go to f1

                        rJim = f3.read_next_msg()
                        assert rJim.wants_us_to_reply()
                        assert rJim.equivalent(mJim)
                        assert f3.next_msg() == 0

                        rJames = f2.read_next_msg()
                        assert rJames.wants_us_to_reply()
                        assert rJames.equivalent(mJames)
                        assert f2.next_msg() == 0

                        rJimBob = f1.read_next_msg()
                        assert rJimBob.wants_us_to_reply()
                        assert rJimBob.equivalent(mJimBob)
                        assert f1.next_msg() == 0

    def test_reads(self):
        """Test partial reads, next_msg, etc.
        """
        with RecordingKSock(0,'rw',self.bindings) as f0:
            # We'll use this interface to do all the writing of requests,
            # just to keep life simple.

            with RecordingKSock(0,'r',self.bindings) as f1:
                f1.bind('$.Fred')

                # At this point, nothing to read
                assert f1.next_msg() == 0

                # Stack up some useful writes
                m1 = Message('$.Fred','dat1')
                m2 = Message('$.Fred','dat2')
                m3 = Message('$.Fred','dat3')
                m4 = Message('$.Fred','dat4')
                m5 = Message('$.Fred','dat5')
                m6 = Message('$.Fred','dat6')

                f0.send_msg(m1)
                f0.send_msg(m2)
                f0.send_msg(m3)
                f0.send_msg(m4)
                f0.send_msg(m5)
                f0.send_msg(m6)

                # Low level reading, using explicit next_msg() and byte reading
                length = f1.next_msg()
                assert length == len(m1.array) * 4
                data = f1.read_data(length)
                assert len(data) == length
                msg = Message(data)
                assert msg.equivalent(m1)

                # Low level reading, using explicit next_msg() and byte reading
                # one byte at a time...
                # (Of course, this doesn't necessarily test anything at the low
                # level, as the file system will be doing larger reads under us
                # and buffering stuff)
                length = f1.next_msg()
                assert length == len(m2.array) * 4
                # So, when we haven't read anything, we've still got all of the
                # message data left
                assert f1.len_left() == length
                data = ''

                # If we read a single byte:
                data += f1.read_data(1)
                # the underlying file system will actually have read in a
                # "buffer load" of data, and for our small message size, this
                # means that it will have read the entire message, so we find:
                assert f1.len_left() == 0
                # which is a little misleading. Oh well.

                # Still, we can pretend to read the rest of the data
                # byte-by-byte
                for ii in range(length-1):
                    data += f1.read_data(1)
                assert len(data) == length
                msg = Message(data)
                assert msg.equivalent(m2)

                # Reading in parts
                length = f1.next_msg()
                left = f1.len_left()
                assert left == length
                m = f1.read_msg(length)
                assert m.equivalent(m3)
                left = f1.len_left()
                assert left == 0

                # Reading in one go
                m = f1.read_next_msg()
                assert m.equivalent(m4)

                # Skipping a message
                length = f1.next_msg()
                m = f1.read_next_msg()
                assert m.equivalent(m6) # *not* m5

                # Nothing more to read
                assert f1.next_msg() == 0

    def test_partial_writes(self):
        """Test partial writes, etc.
        """
        with RecordingKSock(0,'rw',self.bindings) as f0:
            # We'll use this interface to do all the writing of requests,
            # just to keep life simple.

            with RecordingKSock(0,'r',self.bindings) as f1:
                f1.bind('$.Fred')

                m = Message('$.Fred','data')

                # We can do it all in one go (the convenient way)
                f0.send_msg(m)
                r = f1.read_next_msg()
                assert r.equivalent(m)
                assert f1.next_msg() == 0

                # We can do it in two parts, but writing the whole message
                f0.write_msg(m)
                # Nothing sent yet
                assert f1.next_msg() == 0
                f0.send()
                r = f1.read_next_msg()
                assert r.equivalent(m)
                assert f1.next_msg() == 0

                # Or we can write our messsage out in convenient pieces
                # Note that (unlike reading) because of the magic of 'flush',
                # we can expect to be writing single bytes to our file
                # descriptor -- maximally inefficient!
                assert f1.next_msg() == 0
                data = m.array.tostring()
                for ch in data:
                    f0.write_data(ch)        # which also flushes
                    assert f1.next_msg() == 0
                f0.send()
                r = f1.read_next_msg()
                assert r.equivalent(m)
                assert f1.next_msg() == 0

                # Since writing and sending are distinct, we can, of course,
                # decide *not* to send a message we've written
                f0.write_msg(m)
                f0.discard()
                check_IOError(errno.ENOMSG, f0.send)
                assert f1.next_msg() == 0

    def test_reply_to_specific_id(self):
        """Test replying to a specific id.
        """
        with KSock(0,'rw') as f1:
            with KSock(0,'rw') as f2:
                with KSock(0,'rw') as f3:

                    print 'f1 is',f1.bound_as()
                    print 'f2 is',f2.bound_as()
                    print 'f3 is',f3.bound_as()

                    # f2 is listening for someone to say 'Hello'
                    f2.bind('$.Hello')

                    # f1 says 'Hello' to anyone listening
                    m = Message('$.Hello','data')
                    f1.send_msg(m)

                    # We read the next message - it's a 'Hello'
                    r = f2.read_next_msg()
                    assert r.name == '$.Hello'
                    print r

                    # Two interfaces decide to listen to '$.Reponse'
                    f1.bind('$.Response',True)
                    f3.bind('$.Response')
                    # However, f2 *cares* that f1 should receive its
                    # response, and is not worried about anyone else
                    # doing so
                    target_id = r.from_
                    print 'Hello from %d'%target_id
                    m2 = Request('$.Response',data='fred',to=target_id)
                    f2.send_msg(m2)

                    # So, both recipients should "see" it
                    r = f1.read_next_msg()
                    assert r.equivalent(m2)
                    r = f3.read_next_msg()
                    assert r.equivalent(m2)

                    # But if f1 should stop listening to the responses
                    # (either because it "goes away", or because it unbinds)
                    # then we want to know about this...
                    f1.unbind('$.Response',True)
                    check_IOError(errno.EADDRNOTAVAIL, f2.send_msg, m2)

                    # And if someone different starts to reply, we want to
                    # know about that as well
                    f3.bind('$.Response',True)
                    check_IOError(errno.EPIPE, f2.send_msg, m2)

    def test_request_with_replier_and_listener(self):
        """Send a request to replier/listener (same ksock)
        """
        with KSock(0,'rw') as f1:
            f1_id = f1.bound_as()
            f2_id = 0

            m = Request('$.Fred','data')
            print m

            with KSock(0,'rw') as f2:
                f2_id = f2.bound_as()
                f2.bind('$.Fred',replier=True)
                f2.bind('$.Fred',replier=False)

                f1.send_msg(m)

                # Once as a replier
                r = f2.read_next_msg()
                print r
                assert r.equivalent(m)
                assert r.wants_us_to_reply()

                # Once as a listner
                r = f2.read_next_msg()
                print r
                assert r.equivalent(m)
                assert not r.wants_us_to_reply()

                assert f1.next_msg() == 0

    def test_request_with_replier_absconding(self):
        """Send a request, but the replier goes away.
        """
        with KSock(0,'rw') as f1:
            f1_id = f1.bound_as()
            f2_id = 0

            m = Request('$.Fred','data')

            with KSock(0,'rw') as f2:
                f2_id = f2.bound_as()
                f2.bind('$.Fred',replier=True)

                f1.send_msg(m)
                m_id = f1.last_msg_id()

            # And f2 closes ("releases" internally)
            e = f1.read_next_msg()

            print 'f1 is',f1_id
            print 'f2 is',f2_id
            print m
            print e

            assert e.to    == f1_id
            assert e.from_ == f2_id
            assert e.in_reply_to == m_id
            assert e.name == '$.KBUS.Replier.GoneAway'
            assert e.is_synthetic()
            assert len(e.data) == 0
            assert f1.next_msg() == 0

    def test_request_with_replier_absconding_2(self):
        """Send a request, but the replier (who is also a listener) goes away.
        """
        with KSock(0,'rw') as f1:
            f1_id = f1.bound_as()
            f2_id = 0

            m = Request('$.Fred','data')

            with KSock(0,'rw') as f2:
                f2_id = f2.bound_as()
                f2.bind('$.Fred',replier=True)
                f2.bind('$.Fred',replier=False)

                f1.send_msg(m)
                m_id = f1.last_msg_id()

            # And f2 closes ("releases" internally)
            # - the Message should just be lost, but we should be told about
            #   the Request
            e = f1.read_next_msg()

            assert e.to    == f1_id
            assert e.from_ == f2_id
            assert e.in_reply_to == m_id
            assert e.name == '$.KBUS.Replier.GoneAway'
            assert e.is_synthetic()
            assert len(e.data) == 0

            assert f1.next_msg() == 0

    def test_request_with_replier_absconding_3(self):
        """Send a request, but the replier (who is also a listener) goes away.
        """
        with KSock(0,'rw') as f1:
            f1_id = f1.bound_as()
            f2_id = 0

            r1 = Request('$.Fred','data')
            r2 = Request('$.Fred','more')
            m1 = Message('$.Fred','data')
            m2 = Message('$.Fred','more')

            with KSock(0,'rw') as f2:
                f2_id = f2.bound_as()
                f2.bind('$.Fred',replier=True)
                f2.bind('$.Fred',replier=False)

                f1.send_msg(m1)
                f1.send_msg(r1)
                r1_id = f1.last_msg_id()

                f1.send_msg(m2)
                f1.send_msg(r2)
                r2_id = f1.last_msg_id()

            # And f2 closes ("releases" internally)
            # - the Messages should just be lost, but we should be told about
            #   the Requests
            e = f1.read_next_msg()

            assert e.to    == f1_id
            assert e.from_ == f2_id
            assert e.in_reply_to == r1_id
            assert e.name == '$.KBUS.Replier.GoneAway'
            assert e.is_synthetic()
            assert len(e.data) == 0

            e = f1.read_next_msg()

            assert e.to    == f1_id
            assert e.from_ == f2_id
            assert e.in_reply_to == r2_id
            assert e.name == '$.KBUS.Replier.GoneAway'
            assert e.is_synthetic()
            assert len(e.data) == 0

            assert f1.next_msg() == 0

    def test_request_with_replier_unbinding(self):
        """Send a request, but the replier goes unbinds.
        """
        with KSock(0,'rw') as f1:
            f1_id = f1.bound_as()
            f2_id = 0

            m = Request('$.Fred','data')

            with KSock(0,'rw') as f2:
                f2_id = f2.bound_as()
                f2.bind('$.Fred',replier=True)

                f1.send_msg(m)
                m_id = f1.last_msg_id()

                # And f2 unbinds
                f2.unbind('$.Fred',replier=True)

                e = f1.read_next_msg()

                print 'f1 is',f1_id
                print 'f2 is',f2_id
                print m
                print e

                assert e.to    == f1_id
                assert e.from_ == f2_id
                assert e.in_reply_to == m_id
                assert e.name == '$.KBUS.Replier.Unbound'
                assert e.is_synthetic()
                assert len(e.data) == 0
                assert f1.next_msg() == 0

                assert f2.next_msg() == 0

    def test_request_with_replier_unbinding_2(self):
        """Send a request, but the replier (who is also a listener) unbinds.
        """
        with KSock(0,'rw') as f1:
            f1_id = f1.bound_as()
            f2_id = 0

            m = Request('$.Fred','data')

            with KSock(0,'rw') as f2:
                f2_id = f2.bound_as()
                f2.bind('$.Fred',replier=True)
                f2.bind('$.Fred',replier=False)

                f1.send_msg(m)
                m_id = f1.last_msg_id()

                # And f2 unbinds as a replier
                #   the Request should be lost, and f1 should get told
                # - the Message should still be "in transit"
                f2.unbind('$.Fred',replier=True)

                e = f1.read_next_msg()

                assert e.to    == f1_id
                assert e.from_ == f2_id
                assert e.in_reply_to == m_id
                assert e.name == '$.KBUS.Replier.Unbound'
                assert e.is_synthetic()
                assert len(e.data) == 0

                assert f1.next_msg() == 0

                r = f2.read_next_msg()
                assert r.equivalent(m)
                assert not r.wants_us_to_reply()

                assert f2.next_msg() == 0

    def test_request_with_replier_unbinding_3(self):
        """Send a request, but the replier (who is also a listener) unbinds.
        """
        with KSock(0,'rw') as f1:
            f1_id = f1.bound_as()
            f2_id = 0

            r1 = Request('$.Fred','data')
            r2 = Request('$.Fred','more')
            r3 = Request('$.Jim','that')

            m1 = Message('$.Fred','data')
            m2 = Message('$.Fred','more')
            m3 = Message('$.Jim','what')

            with KSock(0,'rw') as f2:
                f2_id = f2.bound_as()
                f2.bind('$.Fred',replier=True)
                f2.bind('$.Fred',replier=False)
                f2.bind('$.Jim',replier=True)
                f2.bind('$.Jim',replier=False)

                f1.send_msg(m1)
                f1.send_msg(r1)
                r1_id = f1.last_msg_id()
                f1.send_msg(m3)

                f1.send_msg(m2)
                f1.send_msg(r2)
                r2_id = f1.last_msg_id()
                f1.send_msg(r3)

                # Timeline is:
                #
                #       m1, r1, [r1], m3, m2, r2, [r2], r3, [r3]
                #
                # where [r1] is request 1 as a message

                # And f2 unbinds as a replier for '$.Fred'
                #   the Request should be lost, and f1 should get told
                # - the Message should still be "in transit"
                # - the '$.Jim' messages should be unaffected
                f2.unbind('$.Fred',replier=True)

                e = f1.read_next_msg()

                assert e.to    == f1_id
                assert e.from_ == f2_id
                assert e.in_reply_to == r1_id
                assert e.name == '$.KBUS.Replier.Unbound'
                assert e.is_synthetic()
                assert len(e.data) == 0

                e = f1.read_next_msg()

                assert e.to    == f1_id
                assert e.from_ == f2_id
                assert e.in_reply_to == r2_id
                assert e.name == '$.KBUS.Replier.Unbound'
                assert e.is_synthetic()
                assert len(e.data) == 0

                assert f1.next_msg() == 0

                # So timeline should now be:
                #
                #       m1, [r1], m3, m2, [r2], r3, [r3]

                r = f2.read_next_msg()
                assert r.equivalent(m1)
                assert not r.wants_us_to_reply()

                r = f2.read_next_msg()
                assert r.equivalent(r1)
                assert not r.wants_us_to_reply()

                r = f2.read_next_msg()
                assert r.equivalent(m3)
                assert not r.wants_us_to_reply()

                r = f2.read_next_msg()
                assert r.equivalent(m2)
                assert not r.wants_us_to_reply()

                r = f2.read_next_msg()
                assert r.equivalent(r2)
                assert not r.wants_us_to_reply()

                r = f2.read_next_msg()
                assert r.equivalent(r3)
                assert r.wants_us_to_reply()

                r = f2.read_next_msg()
                assert r.equivalent(r3)
                assert not r.wants_us_to_reply()

                assert f2.next_msg() == 0

    def test_urgent(self):
        """Test adding urgent messages.
        """
        with KSock(0,'rw') as f1:
            with KSock(0,'rw') as f2:
                f2.bind('$.Message')
                f2.bind('$.Request',True)

                f2.bind('$.Urgent.Message')
                f2.bind('$.Urgent.Request',True)

                m1 = Message('$.Message')
                m2 = Message('$.Message')

                r1 = Request('$.Request')
                r2 = Request('$.Request')

                f1.send_msg(m1)
                m1_id = f1.last_msg_id()

                f1.send_msg(r1)
                r1_id = f1.last_msg_id()

                f1.send_msg(m2)
                m2_id = f1.last_msg_id()

                f1.send_msg(r2)
                r2_id = f1.last_msg_id()

                # Timeline should be: m1, r1, m2, r2

                mu1 = Message('$.Urgent.Message')
                mu1.set_urgent()
                f1.send_msg(mu1)
                mu1_id = f1.last_msg_id()

                ru1 = Request('$.Urgent.Request')
                ru1.set_urgent()
                f1.send_msg(ru1)
                ru1_id = f1.last_msg_id()

                # Timeline should be: ru1, mu1, m1, r1, m2, r2

                a = f2.read_next_msg()          # ru1
                assert a.equivalent(ru1)
                assert a.id == ru1_id
                assert a.is_urgent()
                assert a.wants_us_to_reply()

                a = f2.read_next_msg()          # mu1
                assert a.equivalent(mu1)
                assert a.id == mu1_id
                assert a.is_urgent()
                assert not a.wants_us_to_reply()

                a = f2.read_next_msg()          # m1
                assert a.equivalent(m1)
                assert a.id == m1_id
                assert not a.is_urgent()
                assert not a.wants_us_to_reply()

                a = f2.read_next_msg()          # r1
                assert a.equivalent(r1)
                assert a.id == r1_id
                assert not a.is_urgent()
                assert a.wants_us_to_reply()

                a = f2.read_next_msg()          # m2
                assert a.equivalent(m2)
                assert a.id == m2_id
                assert not a.is_urgent()
                assert not a.wants_us_to_reply()

                a = f2.read_next_msg()          # r2
                assert a.equivalent(r2)
                assert a.id == r2_id
                assert not a.is_urgent()
                assert a.wants_us_to_reply()

    def test_max_messages_readonly_1(self):
        """Test that we can set the maximum number of messages in a queue (R).
        """
        with KSock(0,'r') as f1:
            # Find out what the current value is
            orig_size = f1.set_max_messages(0)
            # It should stay the same if we ask again
            assert orig_size == f1.set_max_messages(0)
            # If we ask for a value, we should get it back
            new_size = orig_size + 100
            assert new_size == f1.set_max_messages(new_size)
            # And again if we just ask
            assert new_size == f1.set_max_messages(0)
            # And we should be able to put it back
            assert orig_size == f1.set_max_messages(orig_size)
            assert orig_size == f1.set_max_messages(0)

    def test_max_messages_readwrite_1(self):
        """Test that we can set the maximum number of messages in a queue (RW).
        """
        with KSock(0,'rw') as f1:
            # Find out what the current value is
            orig_size = f1.set_max_messages(0)
            # It should stay the same if we ask again
            assert orig_size == f1.set_max_messages(0)
            # If we ask for a value, we should get it back
            new_size = orig_size + 100
            assert new_size == f1.set_max_messages(new_size)
            # And again if we just ask
            assert new_size == f1.set_max_messages(0)
            # And we should be able to put it back
            assert orig_size == f1.set_max_messages(orig_size)
            assert orig_size == f1.set_max_messages(0)

    def test_max_messages_readwrite_1a(self):
        """Test that we can set the maximum number of messages in a queue (1a).
        """
        with KSock(0,'rw') as f1:
            # Find out what the current value is - use the More Pythonic method
            orig_size = f1.max_messages()
            # It should stay the same if we ask again
            assert orig_size == f1.max_messages()
            # If we ask for a value, we should get it back
            new_size = orig_size + 100
            assert new_size == f1.set_max_messages(new_size)
            # And again if we just ask
            assert new_size == f1.max_messages()
            # And we should be able to put it back
            assert orig_size == f1.set_max_messages(orig_size)
            assert orig_size == f1.max_messages()

    def test_write_too_many_messages_to_listener(self):
        """Writing too many messages to an ordinary listener.

        Some should get dropped.
        """
        with KSock(0,'rw') as sender:
            with KSock(0,'r') as listener:
                listener.bind('$.Fred')
                assert listener.set_max_messages(1) == 1

                m = Message('$.Fred')
                sender.send_msg(m)
                sender.send_msg(m)

                r = listener.read_next_msg()
                assert r.equivalent(m)

                assert listener.next_msg() == 0

    def test_write_too_many_messages_to_replier(self):
        """Writing too many messages to a replier.

        Some should get dropped.
        """
        with KSock(0,'rw') as sender:
            with KSock(0,'rw') as replier:
                replier.bind('$.Fred',replier=True)
                assert replier.set_max_messages(1) == 1

                m = Request('$.Fred')
                sender.send_msg(m)
                sender.send_msg(m)

                r = replier.read_next_msg()
                assert r.equivalent(m)

                assert replier.next_msg() == 0

                e = sender.read_next_msg()
                assert e.name == '$.KBUS.Replier.QueueFull'
                assert e.is_synthetic()

    def test_write_too_many_messages_to_replier_with_listener(self):
        """Writing too many messages to a replier (with listener)

        Some should get dropped.
        """
        with KSock(0,'rw') as sender:
            with KSock(0,'rw') as replier:
                with KSock(0,'r') as listener:
                    replier.bind('$.Fred',replier=True)
                    listener.bind('$.Fred',replier=False)

                    assert replier.set_max_messages(1) == 1

                    m = Request('$.Fred')
                    sender.send_msg(m)
                    ok_msg_id = sender.last_msg_id()
                    sender.send_msg(m)
                    failed_msg_id = sender.last_msg_id()

                    r = replier.read_next_msg()
                    assert r.equivalent(m)
                    assert r.id == ok_msg_id

                    assert replier.next_msg() == 0

                    e = sender.read_next_msg()
                    assert e.name == '$.KBUS.Replier.QueueFull'
                    assert e.is_synthetic()
                    assert e.in_reply_to == failed_msg_id

                    # And the listener should only see the message that succeeded
                    a = listener.read_next_msg()
                    assert a.equivalent(m)
                    assert a.id == ok_msg_id

                    assert listener.next_msg() == 0

    def test_send_ALL_OR_XX_flag_logic(self):
        """Check the logic of the ALL_OR_xxx flags
        """

        with KSock(0,'rw') as sender:
            with KSock(0,'rw') as listener:
                listener.bind('$.Fred')
                m1 = Message('$.Fred',flags=Message.ALL_OR_WAIT)
                sender.send_msg(m1)

                m2 = Message('$.Fred',flags=Message.ALL_OR_FAIL)
                sender.send_msg(m2)

                # But we can't send a message with both flags set
                m3 = Message('$.Fred',flags=Message.ALL_OR_WAIT|Message.ALL_OR_FAIL)
                check_IOError(errno.EINVAL,sender.send_msg,m3)

# vim: set tabstop=8 shiftwidth=4 expandtab:
