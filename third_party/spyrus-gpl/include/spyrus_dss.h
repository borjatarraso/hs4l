/*
 *  Copyright (c) 2008-2012 Guralp Systems Ltd.
 *  Author: Bob Dunlop   <rdunlop@guralp.com>
 *
 *  Released under the GNU GPLv3. See file COPYING or
 *  http://www.gnu.org/copyleft/gpl.html for details.
 */



/*! \defgroup dss Simplified DSS interface

This is a simplified Spyrus interface for applications interested in the
single operation of generating DSS signatures using a single installed Spyrus
device with the default Spyrus user credentials.

The header file <spyrus_dss.h> can be used in place of <spyrus.h> to limit
access to the functions defined here.

*/
/*!@{*/



/*! \brief Initialise Spyrus library link.

\param spyrus_slot Spyrus slot ID (0 = disabled).
\param connect_trys Number of connection attempts to make before failing.
       (0 = initial default or previous value).
\param connect_delay Delay between connection attempts in seconds.
       (0 = initial default or previous value).
\returns 0 on success, -1 on any failure.

This function initialises the link to the Spyrus library, or calling it with
a slot ID of 0 will close the link.

Progress (retrys) may be logged via \c syslog(3).

If the connection cannot be made or out of range parameters are passed a message
will be logged via \c syslog(3) and the function will return -1.

It is safe to call this function multiple times, which allows changing the
\a spyrus_slot (Spyrus card slot) in use.
\ref spyrus_dss_get_slot() can be called to retrieve the current slot ID.

*/
int spyrus_dss_init(
    uint32_t spyrus_slot,
    uint32_t connect_trys,
    uint32_t connect_delay );



/*! \brief Get signature slot ID.

\returns Signing slot ID.
\retval 0 if signing is disabled, or has not been initialised.

This function returns the Spyrus slot with which \ref spyrus_dss_init() was
last called. It can be tested against zero to see whether a call to
\ref spyrus_dss_sign() should succeed or not.

*/
uint32_t spyrus_dss_get_slot( void );



/*! \brief The number of bytes in a DSS signature instance. */
#ifndef DSS_SIGNATURE_SIZE
# define DSS_SIGNATURE_SIZE     40
#endif



/*! \brief Sign the hash of a block of data.

\param buf Pointer to data to sign.
\param buf_len Number of bytes to sign.
\param[out] dss A block of \ref DSS_SIGNATURE_SIZE bytes in which the
       signature is returned.
\returns 0 on success, -1 on any failure.

This function computes the SHA1 hash of a block of data \a buf of \a buf_len
bytes and then sends it to the Spyrus device for signing before returning the
signature in the buffer \a dss which must be of at least \ref DSS_SIGNATURE_SIZE
bytes. The Spyrus authentication slot to use must have been set by calling
\ref spyrus_dss_init().

If the device connection has been lost then reconnection will be attempted in
the same manner as \ref spyrus_dss_init().

On error, logs via \c syslog(3) and returns -1.

*/
int spyrus_dss_sign( const char *buf, uint32_t buf_len, char *dss )
    __attribute__((nonnull));



/*!@}*/
/* options for text editors
vim: expandtab:ts=4:sw=4:syntax=c.doxygen
*/
