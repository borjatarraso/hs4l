/*
 * Spyrus Lynks crypto card (PCMCIA) support library.
 *
 * Copyright (C) 2008 Guralp Systems Ltd.
 * Author: Bob Dunlop   <rdunlop@guralp.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.
 *
 *  Util library interface
 */

#define LCK_USE_POSIX_SEMA      0       /* They don't work on our builds */
                                        /* We'll fall back to using flock on
                                         * the device fd */
#include <stdint.h>
#if LCK_USE_POSIX_SEMA
#include <semaphore.h>
#endif


/* Library per card information.  Applications should treat this as opaque */
struct spyrus_info {
        int fd;
        int debug;
#if LCK_USE_POSIX_SEMA
        sem_t *use_lock;        /* Exclusive use of card (not memory access) */
#endif
        int use_count;          /* How nested our lock is */
        int mem_lock;           /* Host software has the memory access lock */
        uint8_t *mem;
        int slot;               /* Slot the user has validated for encryption */
        uint32_t slot_issue;    /* Sequence number or similar to keep track of
                                 * the validation */
};


/*
 *      Spyrus card command response codes.
 *
 * Most of the methods below return a int error code as follows.
 *
 *   0   == no error/success.
 *   +ve == Spyrus command response see list below.
 *    -1 == unix error. See errno.
 *   <-1 == library errors. See second list below.
 *
 * Use spyrus_strerror() to produce a user readable string.
 */
#define SPYRUS_RESP_Passed                      0x00
#define SPYRUS_RESP_Failed                      0x01
#define SPYRUS_RESP_Checkword_Failure           0x02
#define SPYRUS_RESP_Invalid_Type_Value          0x03
#define SPYRUS_RESP_Invalid_Mode_Value          0x04
#define SPYRUS_RESP_Invalid_Key_Index           0x05
#define SPYRUS_RESP_Invalid_Certificate_Index   0x06
#define SPYRUS_RESP_Invalid_Data_Size           0x07
#define SPYRUS_RESP_Invalid_Header              0x08
#define SPYRUS_RESP_Invalid_State               0x09
#define SPYRUS_RESP_Execution_Failure           0x0A
#define SPYRUS_RESP_No_Key_Loaded               0x0B
#define SPYRUS_RESP_No_IV_Loaded                0x0C
#define SPYRUS_RESP_No_X_Value                  0x0D
#define SPYRUS_RESP_RESERVED                    0x0E
#define SPYRUS_RESP_No_Saved_Value              0x0F
#define SPYRUS_RESP_Register_In_Use             0x10
#define SPYRUS_RESP_Invalid_Command             0x11
#define SPYRUS_RESP_Invalid_Pointer             0x12
#define SPYRUS_RESP_Bad_Clock                   0x13
#define SPYRUS_RESP_NO_PQG_Loaded               0x14

/* Library internal errors */
#define SPYRUS_ERR_UNIX         (-1)    /* See errno */
#define SPYRUS_ERR_OPENSSL      (-2)    /* See ERR_get_error */

#define SPYRUS_ERR_NOTIMP       (-3)
#define SPYRUS_ERR_NOMEM        (-4)
#define SPYRUS_ERR_BUSY         (-5)
#define SPYRUS_ERR_NULL_PTR     (-6)
#define SPYRUS_ERR_BAD_DEV      (-7)
#define SPYRUS_ERR_BAD_NAME     (-8)
#define SPYRUS_ERR_INDEX        (-9)
#define SPYRUS_ERR_NO_SLOT      (-10)
#define SPYRUS_ERR_SLOT_INVALID (-11)
#define SPYRUS_ERR_SLOT_CHANGED (-12)
#define SPYRUS_ERR_CERT_INVALID (-13)
#define SPYRUS_ERR_RQ_TOOMANY   (-14)
#define SPYRUS_ERR_RQ_MISSING   (-15)
#define SPYRUS_ERR_BAD_KEY      (-16)
#define SPYRUS_ERR_NOT_FOUND    (-17)
#define SPYRUS_ERR_BAD_DSAPARAM (-18)


/*
 *      Functions to support DSS signing
 *
 * Certificate/key slot identifiers
 */
#define SPYRUS_TRUSTED_SLOT     0       /* Slot 0 is our trusted CA root */
#define SPYRUS_FIRST_SLOT       1       /* First user slot */
#define SPYRUS_LAST_SLOT        19      /* Last user slot */
#define SPYRUS_DEFAULT_SLOT     0       /* Whichever user slot has been
                                         * designated as the current default */


/* Open and initialise the card.
 * Only one card available at present so card should be 0.
 * Debug enables additional printfs in the library if it is compiled for
 * debug, 0 == off, 1 == report error conditions, 2 == report normal operations/
 * hexdump card transactions.
 */
extern int spyrus_open( unsigned int card, unsigned int debug,
                                        struct spyrus_info **sinfo );

/* Finish using the device and cleanup, releasing all resources
 */
extern int spyrus_close( struct spyrus_info *sinfo );


/* Login to the card enabling crypto functions.
 * Supplying NULL for the pin_phrase will attempt to use a stored or default
 * value, unless the card is already enabled.
 */
extern int spyrus_user_login( struct spyrus_info *sinfo, char *pin_phrase );


/* Return a string for a spyrus/unix/library error, looking up errno if
 * necessary
 */
extern char *spyrus_strerror( int err );


/* Use the card to perform an SHA1 hash on the input data and return the 20
 * byte result.
 */
#define SPYRUS_HASH_LENGTH      20

extern int spyrus_sha1( struct spyrus_info *sinfo, uint8_t *data,
                                unsigned int data_len, uint8_t *hash );


/* Get the PEM encoded, 0 padded certificate for a slot.
 * Space for SPYRUS_CERT_LENGTH bytes must be available in *cert
 */
#define SPYRUS_CERT_LENGTH      0x800
#define SPYRUS_CERT_LENGTH_STR  "2048"  /* User string version */

extern int spyrus_get_cert( struct spyrus_info *sinfo, int index,
                                uint8_t *cert, unsigned int *len );


/* Check that the slot contains a correctly signed certificate/key and is
 * available for signing.  If valid the slot is selected for future signatures.
 */
extern int spyrus_validate_slot( struct spyrus_info *sinfo, int slot );


/* Identify the applications currently selected personality slot.
 * Useful to identify the physical slot selected when a default was requested.
 *
 * Returns -1 for no slot selected.  A postive slot number does not guarantee
 * the slot remains valid.
 */
extern int spyrus_which_slot( struct spyrus_info *sinfo );


/* Sign a 20 byte input hash and return the 40 byte signature.
 *
 * The slot used will be the last one indicated via spyrus_validate_slot()
 */
#define SPYRUS_SIGNATURE_LENGTH 40

extern int spyrus_sign( struct spyrus_info *sinfo,
                                uint8_t *hash, uint8_t *signature );

