#!/bin/sh
# data-cd11-misc/src/scripts/cd11-spyrus-tool.sh
#
# Copyright: ©2010, Güralp Systems Ltd.
# Author: Laurence Withers <lwithers@guralp.com>
# License: GNU GPLv3
#
#  This script is a tool to manage Spyrus keypairs in the CD1.1/IMS2.0 system.
#  Run it with no arguments for usage. Refer to MAN-EAM-1100 for further
#  documentation.
#



#
# CONSTANTS
#

# Directory for Spyrus-related config files
SPYRUS_DIR="/etc/spyrus"

# Default DSA parameter file, for speeding up key generation
SPYRUS_DSAPARAM="${SPYRUS_DIR}/dsaparam.pem.local"

# Config file in which we save the active slot for this tool
CD11_SPYRUS_TOOLFILE="${SPYRUS_DIR}/cd11-spyrus-tool.local"

# PIN used when initialising the card if user doesn't provide one
DEFAULT_PIN="1234"

# The two slots this script alternates between
SLOT_A="1"
SLOT_B="2"

# usage()
#  Displays a usage prompt.
usage() {
    cat <<EOF
Usage:
    $0 <command> [params]
    
    Manages keys in slot ${SLOT_A} and slot ${SLOT_B} of the Spyrus card. Interacts with
    spyrus_util and cd11-management-tool .
    
Commands:
    help
    init_card
    generate_keypair    
    start_keypair

init_card command:
    $0 init_card [<pin>]

    Re-initialises the card, destroying any keys or certificates it may hold.
    Takes one parameter, the PIN number to use. This will default to ${DEFAULT_PIN} if
    unspecified.

generate_keypair command:
    $0 generate_keypair <csr_common_name> [<dsa_parameter_filename>]
    
    Generates a new keypair in the inactive slot, returning a CSR on stdout.
    The first parameter is the commonName field to use in the CSR, and could
    be the station's ID code. The second, optional parameter is the name of
    a file containing DSA parameters.

start_keypair command:
    $0 start_keypair <auth_key_id>
    
    Switches the active slot. The authentication key ID value to use must be
    specified as a parameter.
EOF
}



#
# INITIALISE CARD
#

# init_card()
#  Runs the card initialisation process. This will of course destroy anything
#  stored in the card. ‘spyrus_util --init’ is interactive so we pipe the string
#  “yes” to it, confirming we wish to continue.
init_card() {
    PIN="$1"

    # use default PIN if user didn't provide one
    [ -z "${PIN}" ] && PIN="${DEFAULT_PIN}"

    # perform the initialisation
    echo "yes" | spyrus_util --init --loose --sso-pin "${PIN}" --user-pin "${PIN}"
}



#
# SLOT MANAGEMENT FUNCTIONS
#

# get_inactive_slot()
#  Gets the currently-inactive slot from the configuration file. If we don't
# have an active slot, or the active slot isn't valid, we return SLOT_A.
# Otherwise, if SLOT_A is active we return SLOT_B; and if SLOT_B is active, we
# return SLOT_A. Result on stdout.
get_inactive_slot() {
    if [ -e "${CD11_SPYRUS_TOOLFILE}" ]
    then
        CUR_SLOT="`gcs_rwvar gcs_get_varcf active_slot "${CD11_SPYRUS_TOOLFILE}"`"
    fi
    
    case "${CUR_SLOT}" in
    ${SLOT_A})
        echo "${SLOT_B}"
        return 0
        ;;

    ${SLOT_B})
        echo "${SLOT_A}"
        return 0
        ;;
    esac
    
    echo "Warning: starting from slot ${SLOT_A}" >&2
    echo "${SLOT_A}"
    return 0
}

# set_active_slot()
#  Updates the configuration file with a new active slot.
set_active_slot() {
    NEW_SLOT="$1"
    
    touch "${CD11_SPYRUS_TOOLFILE}" || return 1
    gcs_rwvar gcs_set_varcf active_slot "${CD11_SPYRUS_TOOLFILE}" "${NEW_SLOT}"
}



#
# GENERATE A KEYPAIR
#

# generate_keypair()
#  Generates a fresh keypair in the currently inactive slot, then generates a
#  CSR which is printed to stdout.
generate_keypair() {
    COMMON_NAME="$1"
    DSA_PARAMS="$2"

    # test we have a common name set
    if [ -z "${COMMON_NAME}" ]
    then
        echo "Error: common name must be specified for CSR." >&2
        return 1
    fi

    # test for DSA parameter file to use
    [ -z "${DSA_PARAMS}" ] && DSA_PARAMS="${SPYRUS_DSAPARAM}"
    if [ -e "${DSA_PARAMS}" ]
    then
        DSA_PARAMS="--dsaparam ${DSA_PARAMS}"
    else
        DSA_PARAMS=""
        echo "Warning: no DSA parameter file. Key generation will be slow." >&2
    fi

    # get slot to use
    SLOT="`get_inactive_slot`"
    [ -n "${SLOT}" ] || return 1

    # generate a new keypair
    spyrus_util ${DSA_PARAMS} --keygen --index "${SLOT}" > /dev/null
    [ $? -eq 0 ] || return 1

    # generate a CSR
    spyrus_util --request --index "${SLOT}" "commonName=${COMMON_NAME}"
}



#
# SWITCH ACTIVE SLOT
#

# start_keypair()
#  Switches to the inactive slot, making it active. Updates both the tool's
#  configuration file as well as all CD1.1 modules and their configuration.
start_keypair() {
    AUTH_KEY_ID="$1"

    # test for valid auth key ID
    if [ -z "${AUTH_KEY_ID}" ]
    then
        echo "Authentication key ID must be specified." >&2
        return 1
    fi

    # find slot we are switching to
    SLOT="`get_inactive_slot`"
    [ -n "${SLOT}" ] || return 1

    # perform the switch
    set_active_slot "${SLOT}"
    cd11-management-tool --all --save-config --auth-key-id "${SLOT},${AUTH_KEY_ID}"
}



#
# MAIN OPERATIONS
#

if [ $# -eq 0 ]
then
    usage
    exit 1
fi

case "$1" in
help | --help)
    usage
    exit 0
    ;;
    
init_card)
    init_card "$2"
    exit $?
    ;;

generate_keypair)
    generate_keypair "$2" "$3"
    exit $?
    ;;

start_keypair)
    start_keypair "$2"
    exit $?
    ;;
esac

echo "Unrecognised command. Try $0 help"
exit 1



# vim: ts=4:sw=4:expandtab
