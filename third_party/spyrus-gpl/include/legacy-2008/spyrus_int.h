/*
 * Spyrus Lynks crypto card (PCMCIA) test and support utils.
 *
 * Copyright (C) 2008 Guralp Systems Ltd.
 * Author: Bob Dunlop   <rdunlop@guralp.com>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.
 *
 *  Util library internals.
 *
 *  Lot's of calls and structures that we don't admit to in the simple
 *  signing only interface.
 */

#include <stdio.h>
#include <stdint.h>
#include <arpa/inet.h>

/* Convert 4 bytes to and from Spyrus byte ordering */
#define htospyl htonl
#define spytohl ntohl


/* Where to find the user PIN and default signing slot info */
#define SPYRUS_CONF_FILE        SPYRUS_CONF_DIR "/spyrus.local"



/*
 *      Structures for individual Spyrus commands
 */
/* The Get_Status command response structure */
#define SPYRUS_SERIAL_LENGTH    8

struct spyrus_status {
         uint32_t len;
         uint8_t  serial[SPYRUS_SERIAL_LENGTH];
         uint32_t state;
         uint32_t mode;
         uint32_t pers;
         uint32_t key_count;
         uint32_t key_flags;
         uint32_t cert_count;
         uint32_t cert_flags[4];
};


/* Check_PIN command */
#define SPYRUS_PIN_LENGTH       12
#define SPYRUS_PIN_TYPE_SSO     0x25
#define SPYRUS_PIN_TYPE_USER    0x2A

#define SPYRUS_CHALLENGE_LENGTH 20

#define SPYRUS_RS_VAL_LENGTH    40

struct spyrus_check_pin_in {
        uint32_t len;
        uint32_t type;
        uint8_t  pin_phrase[SPYRUS_PIN_LENGTH];
        uint8_t  challenge[SPYRUS_CHALLENGE_LENGTH];
};

struct spyrus_check_pin_out {
        uint32_t len;
        uint8_t  r[SPYRUS_RS_VAL_LENGTH];
        uint8_t  s[SPYRUS_RS_VAL_LENGTH];
};

/* and Change_PIN */
struct spyrus_change_pin_in {
        uint32_t len;
        uint32_t type;
        uint8_t  old_phrase[SPYRUS_PIN_LENGTH];
        uint8_t  new_phrase[SPYRUS_PIN_LENGTH];
};

#define SPYRUS_PIN_MIN          4       /* Arbitrary minimum length we impose */
#define SPYRUS_PIN_MIN_STR      "4"     /* String version */


/* Load_Initialization_Values command */
#define SPYRUS_RSEED_LENGTH     8
#define SPYRUS_KS_LENGTH        10

struct spyrus_load_init_values_in {
        uint32_t len;
        uint8_t  rseed[SPYRUS_RSEED_LENGTH];
        uint8_t  ks[SPYRUS_KS_LENGTH];
};

/* Generate_X (key pair) command */
#define SPYRUS_PUBLIC_Y_LENGTH  0x80

struct spyrus_generate_x_in {
        uint32_t len;
        uint32_t index;
        uint32_t type;
        uint8_t  buf[0];                /* Three length/data block P,Q,G */
};

struct spyrus_generate_x_out {
        uint32_t len;
        uint32_t pub_len;
        uint8_t pub_buf[SPYRUS_PUBLIC_Y_LENGTH];
};


/* Load_Certificate command */
#define SPYRUS_LABEL_LENGTH     0x20

#define PKEY_LABEL      "TEMPXXXX"      /* Label for stored private key */

struct spyrus_load_cert_in {
         uint32_t len;
         uint32_t index;
         uint8_t  label[SPYRUS_LABEL_LENGTH];
         uint32_t cert_len;
         uint8_t  cert[SPYRUS_CERT_LENGTH];
};

/* Get_Certificate command */
struct spyrus_get_cert_in {
        uint32_t len;
        uint32_t index;
};

struct spyrus_get_cert_out {
        uint32_t len;
        uint8_t  cert[SPYRUS_CERT_LENGTH];
};

/* Delete_Certificate command */
struct spyrus_delete_cert_in {
        uint32_t len;
        uint32_t index;
};


/* Hash and Get_Hash commands */
#define SPYRUS_HASH_HEADER_LENGTH       12

struct spyrus_hash_in {
        uint32_t len;
        uint32_t blk_len_bits;
        uint32_t blk_ptr;
};

struct spyrus_hash_out {
        uint32_t len;
        uint8_t  hash[SPYRUS_HASH_LENGTH];
};


/* Sign command */
struct spyrus_sign_in {
        uint32_t len;
        uint8_t  hash[SPYRUS_HASH_LENGTH];
};

struct spyrus_sign_out {
        uint32_t len;
        uint8_t  r[SPYRUS_RS_VAL_LENGTH];
        uint8_t  s[SPYRUS_RS_VAL_LENGTH];
};


/* Verify Signature command */
struct spyrus_verify_in {
        uint32_t len;
        uint8_t  hash[SPYRUS_HASH_LENGTH];
        uint8_t  r[SPYRUS_RS_VAL_LENGTH];
        uint8_t  s[SPYRUS_RS_VAL_LENGTH];
        uint32_t y_len;
        uint8_t  y[SPYRUS_PUBLIC_Y_LENGTH];
};



/* GetPublicKey command */
/* Not sure these map directly to the alg_type but are the most common Spyrus
 * values */
#define SPYRUS_KEY_TYPE_DSA     0x00000000A
#define SPYRUS_KEY_TYPE_KEA     0x000000005

struct spyrus_get_key_in {
         uint32_t len;
         uint32_t index;
         uint32_t alg_type;
};

struct spyrus_get_key_out {
         uint32_t len;
         uint32_t key_len;
         uint32_t p_size_bits;
         uint32_t q_size_bits;
         uint8_t  buf[1024];
};


/* Set_Personality command */
struct spyrus_set_personality_in {
         uint32_t len;
         uint32_t index;
};


/* Get_Personality_List */
#define MAX_PERSONALITY 20

struct spyrus_pbuf_out {
        uint32_t len;
        char     strings[ MAX_PERSONALITY * SPYRUS_LABEL_LENGTH ];
};


/*
 *      Spyrus card command codes
 *
 * This combines the 12 bit opcode with the 8 bit command set indicator for a
 * total of 20 bits.  The card implements sets 0x00 and 0x80.
 */
#define SPYRUS_CMD_Check_Pin_Phrase             0x00004
#define SPYRUS_CMD_Decrypt                      0x00007
#define SPYRUS_CMD_Delete_Key                   0x0000B
#define SPYRUS_CMD_Encrypt                      0x0000D
#define SPYRUS_CMD_Generate_IV                  0x0000E
#define SPYRUS_CMD_Generate_MEK                 0x00013
#define SPYRUS_CMD_Generate_Ra                  0x00016
#define SPYRUS_CMD_Generate_Random_Number       0x00019
#define SPYRUS_CMD_Get_Certificate              0x0001A
#define SPYRUS_CMD_Get_Hash                     0x00020
#define SPYRUS_CMD_Get_Personality_List         0x00025
#define SPYRUS_CMD_Get_Status                   0x00026
#define SPYRUS_CMD_Get_Time                     0x00029
#define SPYRUS_CMD_Hash                         0x0002A
#define SPYRUS_CMD_Initialize_Hash              0x0002C
#define SPYRUS_CMD_Load_Certificate             0x0002F
#define SPYRUS_CMD_Load_IV                      0x00031
#define SPYRUS_CMD_Restore                      0x0003B
#define SPYRUS_CMD_Save                         0x0003E
#define SPYRUS_CMD_Set_Key                      0x00051
#define SPYRUS_CMD_Set_Mode                     0x00054
#define SPYRUS_CMD_Set_Personality              0x00057
#define SPYRUS_CMD_Set_Time                     0x00058
#define SPYRUS_CMD_Sign                         0x0005B
#define SPYRUS_CMD_Timestamp                    0x00061
#define SPYRUS_CMD_Verify_Signature             0x00064
#define SPYRUS_CMD_Verify_Timestamp             0x00068
#define SPYRUS_CMD_Wrap_Key                     0x0006B
#define SPYRUS_CMD_Zeroize                      0x0006D
#define SPYRUS_CMD_Change_Pin_Phrase            0x0006E
#define SPYRUS_CMD_Firmware_Upgrade             0x00070
#define SPYRUS_CMD_Unwrap_Key                   0x00079
#define SPYRUS_CMD_Extract_X                    0x0007C
#define SPYRUS_CMD_Generate_TEK                 0x00083
#define SPYRUS_CMD_Generate_X                   0x00085
#define SPYRUS_CMD_Install_X                    0x00086
#define SPYRUS_CMD_Load_DSA_Parameters          0x00089
#define SPYRUS_CMD_Load_Initialization_Values   0x0008A
#define SPYRUS_CMD_Load_X                       0x0008F
#define SPYRUS_CMD_Relay                        0x00091
#define SPYRUS_CMD_Delete_Certificate           0x00092
#define SPYRUS_C80_LoadKey                      0x80312
#define SPYRUS_C80_GenRSAPublicPrivate          0x80305
#define SPYRUS_C80_LoadRSAPublicPrivate         0x80306
#define SPYRUS_C80_Conceal_Key                  0x80307
#define SPYRUS_C80_RevealKey                    0x80308
#define SPYRUS_C80_Sign                         0x80309
#define SPYRUS_C80_VerifySignature              0x8030A
#define SPYRUS_C80_GetHash                      0x8030B
#define SPYRUS_C80_RSAExtractPrivate            0x8030C
#define SPYRUS_C80_RSAInstallPrivate            0x8030D
#define SPYRUS_C80_GetCertificate               0x8030E
#define SPYRUS_C80_Load_Certificate             0x8030F
#define SPYRUS_C80_GenRSAPublicPrivateSplitKeys 0x80315
#define SPYRUS_C80_SignRSASplitSignature        0x80316
#define SPYRUS_C80_OAEP_Decrypt                 0x8031A
#define SPYRUS_C80_OAEP_Encrypt                 0x8031B
#define SPYRUS_C80_GenDHPublicPrivate           0x80332
#define SPYRUS_C80_LoadDHPublicPrivate          0x80335
#define SPYRUS_C80_GenDHTEK                     0x80336
#define SPYRUS_C80_GetPublicKey                 0x80338


/*
 *      Utility library functions
 */

/* Get and release the exclusive use lock on the card.
 * This is the interprocess right to use the card, not the memory lock.
 * The use lock get can be called inside itself and simply nests.
 */
extern int spyrus_get_use_lock( struct spyrus_info *sinfo );
extern int spyrus_free_use_lock( struct spyrus_info *sinfo );

/* Common call sequences for the above.  They assume some standard names
 * for local variables
 */
#define SPYRUS_GET_USE_LOCK(act)                                        \
        do {                                                            \
            rc = spyrus_get_use_lock( sinfo );                          \
            if ( rc )                                                   \
            {                                                           \
                if (sinfo->debug)                                       \
                {                                                       \
                    printf("%s failed to get use lock\n", act );        \
                    printf("  Unix error %d (%s)\n", errno,             \
                                                strerror( errno ));     \
                }                                                       \
                return rc;                                              \
            }                                                           \
        } while ( 0 )

#define SPYRUS_FREE_USE_LOCK()  spyrus_free_use_lock( sinfo )


/* Another common code fragment
 */
#define SPYRUS_CHECK_INDEX( first, func )                       \
        do {                                                    \
            if ( index < first || index > SPYRUS_LAST_SLOT )    \
            {                                                   \
                if ( sinfo->debug )                             \
                    printf("Bad index for %s\n", func );        \
                return SPYRUS_ERR_INDEX;                        \
            }                                                   \
        } while ( 0 )


/* Get and release the memory access lock.
 * Since getting the memory lock requires the card to release the lock it
 * can time out.
 */
extern int spyrus_get_mem_lock( struct spyrus_info *sinfo );
extern int spyrus_free_mem_lock( struct spyrus_info *sinfo );

/* Wait for the card to signal it's ready (does not set the lock flag) */
extern int spyrus_wait( struct spyrus_info *sinfo );

/* Pass the memory lock to the card and allow it to start executing */
extern int spyrus_execute( struct spyrus_info *sinfo );


/* Setup and execute the simple command on the card */
extern int spyrus_simple_command( struct spyrus_info *sinfo, char *user_name,
        uint32_t cmd, void *in_buf, int in_size, void *out_buf, int out_size );

/* A command with a hash input buffer, the actual inbuf is filled out by the
 * function and the 12 byte header added to the hash buf.
 */
extern int spyrus_hash_command( struct spyrus_info *sinfo, char *user_name,
        uint32_t cmd, void *hash_buf, int hash_size, void *out_buf,
        int out_size );


/* Functions corresponding to single card commands
 *
 * Get_Status
 */
extern int spyrus_get_status( struct spyrus_info *sinfo,
                                        struct spyrus_status *status );

extern int spyrus_zeroize( struct spyrus_info *sinfo );

extern int spyrus_load_cert( struct spyrus_info *sinfo, int index, char *cert,
                                        int cert_len, char *cert_label );

extern int spyrus_load_cert_file( struct spyrus_info *sinfo, int index,
                                        char *file_name, char *cert_label );

extern int spyrus_check_pin( struct spyrus_info *sinfo, uint32_t type,
                                        char *pin_phrase );

extern int spyrus_get_raw_cert( struct spyrus_info *sinfo, int index,
                                uint8_t *cert, unsigned int *len );

extern int spyrus_delete_cert( struct spyrus_info *sinfo, int index );


/* Generate a new public/private key pair.
 * Key parameters can be provided in the optional .pem file or will be
 * generated afresh each time.
 */
extern int spyrus_keygen( struct spyrus_info *sinfo, int index,
                                        char *pem_name, FILE *outf );

/* Get the public key for a slot as an in memory PEM */
extern int spyrus_get_key_pem( struct spyrus_info *sinfo, int index,
                                        uint8_t *outp, unsigned int *lret );

#ifdef EVP_PK_DSA
/* and as an OpenSSL PKEY */
extern int spyrus_get_key_pkey( struct spyrus_info *sinfo, int index,
                                        EVP_PKEY **pkey_ret );

/* Get the full X509 structure from the in memory PEM */
extern int spyrus_get_cert_from_pem( struct spyrus_info *sinfo, uint8_t *cert,
                                        int len, X509 **x509_ret );

/* Test that the public key matches the private key stored for a slot */
extern int spyrus_check_key_in_slot(struct spyrus_info *sinfo, int index,
                                        EVP_PKEY *pkey );
#endif


/* Certificate request generation
 */
/* Certificate request subjects are built with key and value pairs from the
 * following structure
 */
struct req_entry {
        char *env_name;
        char *key;
        char *value;
};

extern int spyrus_request_add_entry( char *key, char *val );

extern int spyrus_gen_request( struct spyrus_info *sinfo, int index,
                                                                FILE *outf );

extern struct req_entry *spyrus_get_req_subject_list();


/* Generate signature without slot validation.
 * (used for certificate request signatures, and locating slot by key)
 */
extern int spyrus_sign_raw( struct spyrus_info *sinfo, int index,
                                const uint8_t *hash, uint8_t *signature );

#ifdef EVP_PK_DSA
extern int spyrus_verify_raw( struct spyrus_info *sinfo, int index,
                const uint8_t *hash, uint8_t *signature, EVP_PKEY *pkey );
#endif

/* Full "factory" initialisation and certificate installation
 */
extern int spyrus_full_configure_sequence( struct spyrus_info *sinfo,
        char *sso_pin, char *user_pin, char *cert, int len, char *cert_label,
        FILE *record_fp );

extern int spyrus_full_configure_sequence_file( struct spyrus_info *sinfo,
        char *sso_pin, char *user_pin, char *file_name, char *cert_label,
        FILE *record_fp );

/* Change the user PIN phrase */
extern int spyrus_change_user_pin( struct spyrus_info *sinfo, char *sso_pin,
        char *user_pin );

extern void spyrus_record_user_pin( char *user_pin );

extern void spyrus_record_default_slot( int default_slot );


/* Select the indicated card personality/slot
 */
extern int spyrus_select_slot( struct spyrus_info *sinfo, int slot, int issue );


/* Misc controls */

/* Reset the card via the soft reset bit */
extern int spyrus_reset( struct spyrus_info *sinfo );

/* PINS and certificates can need space padding.
 * Parameter order matches memcpy(), beware this conflicts with James.
 */
extern void spyrus_copy_and_pad( uint8_t *dst, char *src, int len );

/* Mark a certificate/key slot as invalid.
 * The caller must already hold the card use lock.
 */
extern int spyrus_invalidate_slot( struct spyrus_info *sinfo, int slot );

/* Set the drivers idea of which slots we are using */
extern int spyrus_ioc_set_current( struct spyrus_info *sinfo, int index,
                                                                int issue );

extern int spyrus_ioc_set_default( struct spyrus_info *sinfo, int index,
                                                                int issue );

/* Another ioctl based routine */
#ifdef SPIOC_GET_STATUS
extern int spyrus_get_state( struct spyrus_info *sinfo,
                                        struct spyrus_status_regs *status );
#endif


/* Status/info displays */

/* Return a short string for the card state */
extern char *spyrus_strstate( int state );

/* Grab and print the two state registers */
extern int spyrus_print_state( struct spyrus_info *sinfo, FILE *out );

/* Issue a Get_Status command and print the returned structure */
extern int spyrus_print_status( struct spyrus_info *sinfo, FILE *out );

/* Print the list of personality strings */
extern int spyrus_print_personality_list( struct spyrus_info *sinfo,
                                                                FILE *out );

/* Convert a serial number to a string */
extern char *spyrus_conv_serial( uint8_t *serial );

/* Dump the certificate from a slot to file */
extern int spyrus_dump_cert( struct spyrus_info *sinfo, int index,
                                                                FILE *out );

/* Dump the public key from a slot to file */
extern int spyrus_dump_key( struct spyrus_info *sinfo, int index, FILE *out );

/* Hash a file and return the result or print to file */
extern int spyrus_hash_file( struct spyrus_info *sinfo, char *file_name,
                                                uint8_t *hash, FILE *out );


/* Simple debug utility */
extern void dumphex ( char *buf, int size, FILE *out );
