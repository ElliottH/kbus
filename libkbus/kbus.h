/*
 * ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is the KBUS Lightweight Linux-kernel mediated
 * message system
 *
 * The Initial Developer of the Original Code is Kynesim, Cambridge UK.
 * Portions created by the Initial Developer are Copyright (C) 2009
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *   Kynesim, Cambridge UK
 *   Gareth Bailey <gb@kynesim.co.uk>
 *   Tony Ibbs <tibs@tonyibbs.co.uk>
 *
 * Alternatively, the contents of this file may be used under the terms of the
 * GNU Public License version 2 (the "GPL"), in which case the provisions of
 * the GPL are applicable instead of the above.  If you wish to allow the use
 * of your version of this file only under the terms of the GPL and not to
 * allow others to use your version of this file under the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL.  If you do not delete the
 * provisions above, a recipient may use your version of this file under either
 * the MPL or the GPL. 
 *
 * ***** END LICENSE BLOCK *****
 */

#ifndef _LKBUS_H_INCLUDED_
#define _LKBUS_H_INCLUDED_

#ifdef __cplusplus
extern "C" {
#endif 

#include <kbus/kbus_defns.h>

#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdint.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>

// NOTE that the middle portion of this file is autogenerated from libkbus.c
// so that the function header comments and function prototypes may be
// automatically kept in-step. This allows me to treat the C file as the main
// specification of the functions it defines, and also to keep C header
// comments in the C file, which I find easier when keeping the comments
// correct as the code is edited.
//
// The Python script extract_hdrs.py is used to perform this autogeneration.
// It should transfer any C function marked as 'extern' and with a header
// comment (of the '/*...*...*/' form).

/*
 * In kernel modules (and thus in the kbus_defns.h header, which is used by the
 * KBUS kernel module) ``typedef`` is strongly discouraged. Therefore the KBUS
 * kernel module header does not provide a typedef for, well, anything.
 * However, in the outside C programming world, typedefs are often a good thing,
 * allowing simpler programming, so we provide some here.
 */

typedef struct kbus_msg_id              kbus_msg_id_t;
typedef struct kbus_orig_from           kbus_orig_from_t;
typedef struct kbus_bind_request        kbus_bind_request_t;
typedef struct kbus_bind_query          kbus_bind_query_t;

typedef struct kbus_message_header      kbus_message_t;

typedef struct kbus_entire_message      kbus_entire_message_t;

typedef struct kbus_replier_bind_event_data     kbus_replier_bind_event_data_t;

/** A Ksock is just a file descriptor, an integer, as returned by 'open'.
 */
typedef int kbus_ksock_t;

/*
 * Please, however, do consult the kbus_defns.h header file for many useful
 * definitions, and also some key functions, such as:
 *
 * * kbus_msg_name_ptr(msg)
 * * kbus_msg_data_ptr(msg)
 *
 * which are really what you want for extracting KBUS message name and data
 * from the message datastructures (regardless of whether they are pointy or
 * not).
 *
 * If you haven't read kbus_defns.h, you *are* missing important information.
 */

// The following are used in kbus_wait_for_message.
#define KBUS_KSOCK_READABLE 1
#define KBUS_KSOCK_WRITABLE 2

/* Ksock Functions */

/** @file
 *
 * Note that all of the functions here are non-blocking: there is no such
 * thing as a synchronous kbus socket (though there are wait() functions here
 * to emulate one).
 */

// -------- TEXT AFTER THIS AUTOGENERATED - DO NOT EDIT --------
// Autogenerated by extract_hdrs.py on 2010-02-25 (Thu 25 Feb 2010) at 13:52
/*
 * Open a Ksock.
 *
 * `device_number` indicates which KSock device to open, as
 * "/dev/kbus<device_number>".
 *
 * Which device numbers are available depends upon how many KBUS devices have
 * been initialised, either when the KBUS kernel module was installed, or by
 * use of `kbus_new_device()`.
 *
 * `flags` may be one of ``O_RDONLY``, ``O_WRONLY`` or ``O_RDWR``.
 *
 * Returns the file descriptor for the new Ksock, or a negative value on error.
 * The negative value will be ``-errno``.
 */
extern kbus_ksock_t kbus_ksock_open(uint32_t device_number,
                                    int      flags);

/*
 * Open a Ksock by device name. Since KBUS currrently only supports devices
 * of the for ``/dev/kbus<device_number>``, this function has no advantage
 * over `kbus_ksock_open``.
 *
 * `device_name` indicates which KSock device to open, as "/dev/kbus<device_number>",
 * where ``<device_number>`` is zero or more, depending on how many KBUS
 * devices are initialised.
 *
 * `flags` may be one of ``O_RDONLY``, ``O_WRONLY`` or ``O_RDWR``.
 *
 * Returns the file descriptor for the new Ksock, or a negative value on error.
 * The negative value will be ``-errno``.
 */
extern kbus_ksock_t kbus_ksock_open_by_name(const char *device_name,
                                            int         flags);

/*
 * Close a Ksock.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_close(kbus_ksock_t ksock);

/*
 * Bind the given message name to the specified Ksock.
 *
 * If `is_replier`, then bind as a Replier, otherwise as a Listener.
 *
 * Only one KSock at a time may be bound to a particular message as a Replier.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_bind(kbus_ksock_t         ksock,
                           const char          *name,
                           uint32_t             is_replier);

/*
 * Unbind the given message name to the specified Ksock.
 *
 * If `is_replier`, then unbind as a Replier, otherwise as a Listener.
 *
 * The unbinding must exactly match a previous binding (i.e., both message name
 * and `is_replier` must match).
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_unbind(kbus_ksock_t         ksock,
                             const char          *name,
                             uint32_t             is_replier);

/*
 * Return the internal (to KBUS) Ksock id for this Ksock.
 *
 * The Ksock id is a positive, non-zero number. It is used in message ``to``
 * and ``from`` fields.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_id(kbus_ksock_t   ksock,
                         uint32_t      *ksock_id);

/*
 * Indicate that we wish to start reading the next message.
 *
 * Each Ksock has an (internal to KBUS) "next message" list. This function
 * pops the next message from that list, and makes it the "being read" message.
 * If there was still data for an earlier "being read" message, this will be
 * thrown away.
 *
 * `message_length` is set to the length of the message - that is, the value
 * to be passed to a subsequent call of ``kbus_ksock_next_msg()`` - or 0 if
 * there is no next message.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_next_msg(kbus_ksock_t     ksock,
                               uint32_t        *message_length);

/*
 * Find out how many bytes of the "being read" message are still to be read.
 *
 * `len_left` is set to the remaining number of bytes, or 0 if there are no
 * more bytes in the "being read" message, or if there is no "being read"
 * message (i.e., ``kbus_ksock_next_msg()`` has not been called since the
 * last message was finished or discarded).
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_len_left(kbus_ksock_t   ksock,
                               uint32_t      *len_left);

/*
 * Determine the message id of the last message written on this Ksock.
 *
 * This will be {0,0} if there was no previous message.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_last_msg_id(kbus_ksock_t          ksock,
                                  kbus_msg_id_t        *msg_id);

/*
 * Find the Ksock id of the Replier for the given message name.
 *
 * `replier_ksock_id` will either be the Replier's Ksock id, or 0 if there
 * is no Replier bound for this message name.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_find_replier(kbus_ksock_t   ksock,
                                   const char    *name,
                                   uint32_t      *replier_ksock_id);

/*
 * Determine the number of (unread) messages that can be queued for this Ksock.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_max_messages(kbus_ksock_t   ksock,
                                   uint32_t      *max_messages);

/*
 * Set the maximum number of (unread) messages that can be queued for this Ksock.
 *
 * If `num_messages` is greater than 0, then the maximum number of (unread)
 * messages that can be queued for this Ksock will be set.
 *
 * If 'num_messages' is 0, then the maximum is not changed - this may thus be
 * used to query the current maximum number of messages.
 *
 * Returns a positive number indicating the current (possibly just changed)
 * maximum number of messages, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_num_messages(kbus_ksock_t   ksock,
                                   uint32_t      *num_messages);

/*
 * Determine the number of (unread) messages queued for this Ksock.
 *
 * Returns the current (unread) message count for this Ksock, or a negative
 * number (``-errno``) for failure.
 */
extern int kbus_ksock_num_unreplied_to(kbus_ksock_t   ksock,
                                       uint32_t      *num_messages);

/*
 * Send the last written message.
 *
 * Used to send a message when all of it has been written.
 *
 * Once the messge has been sent, the message and any name/data pointed to may
 * be freed.
 *
 * `msg_id` returns the message id assigned to the message by KBUS.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_send(kbus_ksock_t         ksock,
                           kbus_msg_id_t       *msg_id);

/*
 * Discard the message being written.
 *
 * Indicates that KBUS should throw away the (partial) message that has been
 * written. If there is no current message being written (for instance, because
 * ``kbus_ksock_send()`` has just been called), then this function has no
 * effect.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_discard(kbus_ksock_t         ksock);

/*
 * Determine whether multiply-bound messages are only received once.
 *
 * Determine whether this Ksock should receive a particular message once, even
 * if it is both a Replier and Listener for the message, or if it is registered
 * more than once as a Listener for the message name.  
 *
 * Note that in the case of a Request that the Ksock should reply to, it will
 * always get the Request, and it will be the Listener's version of the message
 * that will be "dropped".
 *
 * If `request` is 1, then only one copy of the message is wanted.
 *
 * If `request` is 0, then as many copies as implied by the bindings are wanted.
 *
 * If `request` is 0xFFFFFFFF, then the number of copies is not to be changed.
 * This may be used to query the current state of the "only once" flag for this
 * Ksock.
 *
 * Beware that setting this flag affects how messages are added to the Ksock's
 * message queue *as soon as it is set* - so changing it and then changing it
 * back "at once" is not (necessarily) a null operation.
 *
 * Returns 0 or 1, according to the state of the "only once" flag *before* this
 * function was called, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_only_once(kbus_ksock_t   ksock,
                                uint32_t       request);

/*
 * Determine whether Replier bind/unbind events should be reported.
 *
 * If `request` is 1, then each time a Ksock binds or unbinds as a Replier,
 * a Replier bind/unbind event should be sent (a "$.KBUS.ReplierBindEvent"
 * message).
 *
 * If `request` is 0, then Replier bind/unbind events should not be sent.
 *
 * If `request` is 0xFFFFFFFF, then the current state should not be changed.
 * This may be used to query the current state of the "send Replier bind event"
 * flag.
 *
 * Note that although this call is made via an individual Ksock, it affects the
 * behaviour of the entire KBUS device to which this Ksock is attached.
 *
 * Returns 0 or 1, according to the state of the "send Replier bind event" flag
 * *before* this function was called, or a negative number (``-errno``) for
 * failure.
 */
extern int kbus_ksock_report_replier_binds(kbus_ksock_t       ksock,
                                           uint32_t           request);

/*
 * Request verbose kernel module messages.
 *
 * KBUS writes message via the normal kernel module mechanisms (which may be
 * inspected, for instance, via the ``dmesg`` command). Normal output is meant
 * to be reasonably minimal. Verbose messages can be useful for debugging the
 * kernel module.
 *
 * If `request` is 1, then verbose kernel messages are wanted.
 *
 * If `request` is 0, then verbose kernel messages are not wanted.
 *
 * If `request` is 0xFFFFFFFF, then the current state should not be changed.
 * This may be used to query the current state of the "verbose" flag.
 *
 * Note that although this call is made via an individual Ksock, it affects the
 * behaviour of the entire KBUS kernel module.
 *
 * Returns 0 or 1, according to the state of the "verbose" flag *before* this
 * function was called, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_kernel_module_verbose(kbus_ksock_t       ksock,
                                            uint32_t           request);

/*
 * Request the KBUS kernel module to create a new device (``/dev/kbus<n>``).
 *
 * `device_number` is the ``<n>`` for the new device.
 *
 * Note that it takes the kernel's hotplugging mechanisms a little while to
 * notice/activate the device, so do not expect it to be available immediately
 * on return.
 *
 * Note that although this call is made via an individual Ksock, it affects the
 * behaviour of the entire KBUS kernel module.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_new_device(kbus_ksock_t  ksock,
                                 uint32_t     *device_number);

/*
 * Wait until either the Ksock may be read from or written to.
 *
 * Returns when there is data to be read from the Ksock, or the Ksock
 * may be written to.
 *
 * `wait_for` indicates what to wait for. It should be set to
 * ``KBUS_SOCK_READABLE``, ``KBUS_SOCK_WRITABLE``, or the two "or"ed together,
 * as appropriate.
 *
 * This is a convenience routine for when polling indefinitely on a Ksock is
 * appropriate. It is not intended as a generic routine for any more
 * complicated situation, when specific "poll" (or "select") code should be
 * written.
 *
 * Returns ``KBUS_SOCK_READABLE``, ``KBUS_SOCK_WRITABLE``, or the two "or"ed
 * together to indicate which operation is ready, or a negative number
 * (``-errno``) for failure.
 */
extern int kbus_wait_for_message(kbus_ksock_t  ksock,
                                 int           wait_for);

/*
 * Read a message of length `msg_len` bytes from this Ksock.
 *
 * It is assumed that `msg_len` was returned by a previous call of
 * ``kbus_ksock_next_msg()``. It must be large enough to cause the entire
 * message to be read.
 *
 * `msg` is the message read. This will be an "entire" message, and should be
 * freed by the caller when no longer needed.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 * Specifically, -EBADMSG will be returned if the underlying ``read``
 * returned 0.
 */
extern int kbus_ksock_read_msg(kbus_ksock_t      ksock,
                               kbus_message_t  **msg, 
                               size_t            msg_len);

/*
 * Read the next message from this Ksock.
 *
 * This is equivalent to a call of ``kbus_ksock_next_msg()`` followed by a call
 * of ``kbus_ksock_read_msg()``.
 *
 * If there is no next message, ``msg`` will be NULL.
 *
 * If there is a next message, then ``msg`` will be the message read. This will
 * be an "entire" message, and should be freed by the caller when no longer
 * needed.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_read_next_msg(kbus_ksock_t          ksock,
                                    kbus_message_t      **msg);

/*
 * Write the given message to this Ksock. Does not send it.
 *
 * The `msg` may be an "entire" or "pointy" message.
 *
 * If the `msg` is a "pointy" message, then the name and any data must not be
 * freed until the message has been sent (as the pointers are only "followed"
 * when the message is sent).
 *
 * It is normally easier to use ``kbus_ksock_send_msg()``.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_write_msg(kbus_ksock_t             ksock,
                                const kbus_message_t    *msg);

/*
 * Write data to the Ksock. Does not send.
 *
 * This may be used to write message data in parts. It is normally better to use
 * the "whole message" routines.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_write_data(kbus_ksock_t    ksock,
                                 uint8_t        *data,
                                 size_t          data_len);

/*
 * Write and send a message on the given Ksock.
 *
 * This combines the "write" and "send" functions into one call, and is the
 * normal way to send a message.
 *
 * The `msg` may be an "entire" or "pointy" message.
 *
 * Once the message has been sent, the message and any name/data pointed to may
 * be freed.
 *
 * `msg_id` returns the message id assigned to the message by KBUS.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_ksock_send_msg(kbus_ksock_t             ksock,
                               const kbus_message_t    *msg,
                               kbus_msg_id_t           *msg_id);

/*
 * Create a message (specifically, a "pointy" message).
 *
 * Note that the message name and data are not copied, and thus should not be
 * freed until the message has been sent (with ``kbus_ksock_send_msg()``).
 *
 * `msg` is the new message, as created by this function.
 *
 * `name` is the name for the message, and `name_len` the length of the name
 * (the number of characters in the name). A message name is required.
 *
 * 'data' is the data for this message, or NULL if there is no data. `data_len`
 * is then the length of the data, in bytes.
 *
 * `flags` may be any KBUS message flags required. Most messages with flags set
 * can more easily be created by one of the other message creation routines.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_msg_create(kbus_message_t **msg, 
                           const char *name,
                           uint32_t name_len, /* bytes  */
                           const void *data,
                           uint32_t data_len, /* bytes */
                           uint32_t flags);

/*
 * Create an "entire" message.
 *
 * Copies are taken of both `name` and `data` (and placed at the end of the
 * message datastructure).
 *
 * Unless you need to be able to free the name and/or data before sending
 * the message, it is more usual to use ``kbus_msg_create()`` instead.
 *
 * `msg` is the new message, as created by this function.
 *
 * `name` is the name for the message, and `name_len` the length of the name
 * (the number of characters in the name). A message name is required. The
 * name will be copied when the message is created.
 *
 * 'data' is the data for this message, or NULL if there is no data. `data_len`
 * is then the length of the data, in bytes. The data will be copied when the
 * message is created.
 *
 * `flags` may be any KBUS message flags required. Most messages with flags set
 * can more easily be created by one of the other message creation routines.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_msg_create_entire(kbus_message_t        **msg, 
                                  const char             *name,
                                  uint32_t                name_len, /* bytes  */
                                  const void             *data,
                                  uint32_t                data_len, /* bytes */
                                  uint32_t                flags);

/*
 * Create a Request (specifically, a "pointy" Request message).
 *
 * Note that the message name and data are not copied, and thus should not be
 * freed until the message has been sent (with ``kbus_ksock_send_msg()``).
 *
 * `msg` is the new message, as created by this function.
 *
 * `name` is the name for the message, and `name_len` the length of the name
 * (the number of characters in the name). A message name is required.
 *
 * 'data' is the data for this message, or NULL if there is no data. `data_len`
 * is then the length of the data, in bytes.
 *
 * `flags` may be any KBUS message flags required. These will be set on the
 * message, and then (after that) the KBUS_BIT_WANT_A_REPLY flag will be set
 * to make the new message a Request.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_msg_create_request(kbus_message_t **msg, 
                                   const char *name,
                                   uint32_t name_len, /* bytes  */
                                   const void *data,
                                   uint32_t data_len, /* bytes */
                                   uint32_t flags);

/*
 * Create an "entire" Request message.
 *
 * This is identical in behaviour to ``kbus_msg_create_request()``, except
 * that an "entire" message is created, and thus both the message name and data
 * are copied. This means that the original `name` and `data` may be freed as
 * soon as the `msg` has been created.
 *
 * Unless you need to be able to free the name and/or data before sending
 * the message, it is more usual to use ``kbus_msg_create_request()`` instead.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_msg_create_entire_request(kbus_message_t        **msg, 
                                          const char             *name,
                                          uint32_t                name_len, /* bytes  */
                                          const void             *data,
                                          uint32_t                data_len, /* bytes */
                                          uint32_t                flags);

/*
 * Create a Reply message, based on a previous Request.
 *
 * This is a convenience mechanism for creating the Reply to a previous
 * Request.
 *
 * The Request must have been marked as wanting this particular recipient to
 * reply to it (i.e., ``kbus_msg_wants_us_to_reply()`` returns true). If this
 * is not so, -EBADMSG will be returned.
 *
 * `msg` is the new Reply message. `in_reply_to` is the Request message for
 * which a Reply is wanted.
 *
 * The message name for the new message will be taken from the old message.
 *
 * The 'to' field for the new message will be set to the 'from' field in the old.
 *
 * The 'in_reply_to' field for the new message will be set to the message id of the old.
 *
 * 'data' is the data for the new message, or NULL if there is none. 'data_len'
 * is the length of the data, in bytes.
 *
 * As normal, the message name and data should not be freed until `msg` has
 * been sent. In the normal case, where `in_reply_to` is an "entire" message
 * read from KBUS, this means that `in_reply_to` and `data` should not be
 * freed, since the message name "inside" `in_reply_to` is being referenced.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_msg_create_reply_to(kbus_message_t **msg, 
                                    const kbus_message_t *in_reply_to,
                                    const void *data,
                                    uint32_t data_len, /* bytes */
                                    uint32_t flags);

/*
 * Create an "entire" Reply message, based on a previous Request.
 *
 * This is identical in behaviour to ``kbus_msg_create_reply_to()``, except
 * that an "entire" message is created, and thus both the message name and data
 * are copied. This means that the original (`in_reply_to`) message and the
 * `data` may be freed as soon as the `msg` has been created.
 *
 * Unless you need to be able to free the original message and/or data before
 * sending * the message, it is more usual to use
 * ``kbus_msg_create_reply_to()`` instead.
 * 
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_msg_create_entire_reply_to(kbus_message_t          **msg, 
                                           const kbus_message_t     *in_reply_to,
                                           const void               *data, 
                                           uint32_t                  data_len, /* bytes */
                                           uint32_t                  flags);

/*
 * Create a Stateful Request message, based on a previous Reply or Request.
 *
 * This is a convenience mechanism for creating a Stateful Request message
 * (a Request which must be delivered to a particular Ksock).
 *
 * `msg` is the new Stateful Request message.
 *
 * `earlier_msg` is either a Reply message from the desired Ksock, or a
 * previous Stateful Request to the same Ksock.
 *
 * If the earlier message is a Reply, then the 'to' and 'final_to' fields for
 * the new message will be set to the 'from' and 'orig_from' fields in the old.
 *
 * If the earlier message is a Stateful Request, then the 'to' and 'final_to'
 * fields for the new message will be copied from the old.
 *
 * If the earlier message is neither a Reply nor a Stateful Request, then
 * -EBADMSG will be returned.
 *
 * 'name' is the name for the new message, and 'name_len' is the length of that
 * name.
 *
 * 'data' is the data for the new message, or NULL if there is none. 'data_len'
 * is the length of the data, in bytes.
 *
 * 'flags' is any KBUS flags to set on the message (flags will not be copied
 * from the earlier message).
 *
 * As normal, the message name and data should not be freed until `msg` has
 * been sent. `earlier_msg` may be freed after this call has completed, as
 * any necessary data will have been copied from it.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_msg_create_stateful_request(kbus_message_t         **msg, 
                                            const kbus_message_t    *earlier_msg,
                                            const char          *name,
                                            uint32_t             name_len,
                                            const void          *data, 
                                            uint32_t             data_len, /* bytes */
                                            uint32_t             flags);

/*
 * Create an "entire" Stateful Request message, based on a previous Reply or
 * Request.
 *
 * This is identical in behaviour to ``kbus_msg_create_stateful_request()``,
 * except that an "entire" message is created, and thus both the message name
 * and data are copied. This means that both the `name` and the `data` may be
 * freed as soon as the `msg` has been created.
 *
 * Unless you need to be able to free the name and/or data before sending
 * the message, it is more usual to use ``kbus_msg_create_statefule_request()``
 * instead.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_msg_create_entire_stateful_request(kbus_message_t       **msg, 
                                                   const kbus_message_t  *earlier_msg,
                                                   const char            *name,
                                                   uint32_t               name_len,
                                                   const void            *data, 
                                                   uint32_t               data_len, /* bytes */
                                                   uint32_t               flags);

/*
 * Delete a message datastructure.
 *
 * Does nothing if `msg_p` is NULL, or `*msg_p` is NULL.
 *
 * Frees the message datastructure, but does not free any name or data that is
 * pointed to.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern void kbus_msg_delete(kbus_message_t **msg_p);

/*
 * Determine the size of a KBUS message.
 *
 * For a "pointy" message, returns the size of the message header.
 *
 * For an "entire" message, returns the size of the entire message.
 *
 * In either case, this is the length of data that would (for instance)
 * be written to a Ksock to actually write the message. In other words::
 *
 *   int len, rv;
 *   len = kbus_msg_sizeof(&msg);
 *   rv = kbus_ksock_write_data(ksock, &msg, len);
 *   if (rv < 0) return rv;
 *
 * is the "low level" equivalent of::
 *
 *   int rv = kbus_ksock_write_msg(ksock, &msg);
 *   if (rv < 0) return rv;
 *
 * Returns the length of 'msg', as described above.
 */
extern int kbus_msg_sizeof(const kbus_message_t *msg);

/*
 * A convenience routine to split the data of a Replier bind event.
 *
 * Replier bind events contain the following information:
 *
 * * `is_replier` is true if the event was a "bind", false it if was an
 *   "unbind".
 * * `binder` is the Ksock id of the binder.
 * * `name` is the name of the message that was being (un)bound.
 *
 * Note that `name` is a copy of the name (from the original `msg`), so that
 * the user may free the original message immediately. Clearly this copy will
 * also need freeing when finished with.
 *
 * Returns 0 for success, or a negative number (``-errno``) for failure.
 */
extern int kbus_msg_split_bind_event(const kbus_message_t  *msg,
                                     uint32_t              *is_bind,
                                     uint32_t              *binder,
                                     char                 **name);

/*
 * Print our a representation of a message.
 *
 * `stream` is the output stream to print to -- typically stdout.
 *
 * Does not print a newline.
 */
extern void kbus_msg_print(FILE                 *stream,
                           const kbus_message_t *msg);

/*
 * Print out (on stdout) information about a message.
 *
 * If `dump_data` is true, also print out the message data (in several forms).
 */
extern void kbus_msg_dump(const kbus_message_t *msg,
                          int                   dump_data);

// -------- TEXT BEFORE THIS AUTOGENERATED - DO NOT EDIT --------

/*
 * Check if a message is "entire".
 *
 * Returns true if the message is "entire", false if it is "pointy".
 * Strongly assumes the message is well-structured.
 */
static inline int kbus_msg_is_entire(const kbus_message_t     *msg)
{
  return msg->name == NULL;
}

/*
 * Check if a message is a Reply.
 */
static inline int kbus_msg_is_reply(const kbus_message_t    *msg)
{
  return msg->in_reply_to.network_id != 0 ||
         msg->in_reply_to.serial_num != 0;
}

/*
 * Check if a message is a Request.
 */
static inline int kbus_msg_is_request(const kbus_message_t      *msg)
{
  return (msg->flags & KBUS_BIT_WANT_A_REPLY) != 0;
}

/*
 * Check if a message is a Stateful Request.
 */
static inline int kbus_msg_is_stateful_request(const kbus_message_t      *msg)
{
  return (msg->flags & KBUS_BIT_WANT_A_REPLY) && (msg->to != 0);
}

/*
 * Check if a message is a Request to which we should reply.
 */
static inline int kbus_msg_wants_us_to_reply(const kbus_message_t       *msg)
{
  return (msg->flags & KBUS_BIT_WANT_A_REPLY) &&
         (msg->flags & KBUS_BIT_WANT_YOU_TO_REPLY);
}

/*
 * Compare two message ids.
 *
 * Returns -1 if id1 < id2, 0 if id1 == id2, +1 if id1 > id2.
 */
static inline int kbus_msg_compare_ids(const kbus_msg_id_t  *id1,
                                       const kbus_msg_id_t  *id2)
{
  if (id1->network_id == id2->network_id) {
    if (id1->serial_num == id2->serial_num)
      return 0;
    else if (id1->serial_num < id2->serial_num)
      return -1;
    else
      return 1;
  } else if (id1->network_id < id2->network_id)
    return -1;
  else
    return 1;
}

#ifdef __cplusplus
}
#endif 

#endif /* _LKBUS_H_INCLUDED_ */

// Local Variables:
// tab-width: 8
// indent-tabs-mode: nil
// c-basic-offset: 2
// End:
// vim: set tabstop=8 shiftwidth=2 softtabstop=2 expandtab:
