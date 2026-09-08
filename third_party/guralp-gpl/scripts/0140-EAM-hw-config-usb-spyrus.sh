#!/bin/sh
# /usr/lib/upgrade/0140-EAM-hw-config-usb-spyrus.sh
# 
#  Copyright: ©2011–2012, Güralp Systems Ltd.
#  Author: Laurence Withers <lwithers@guralp.com>
#  License: GPLv3
#

SPYDIR="/etc/spyrus"
SPYCFG="${SPYDIR}/spyrus.local"

# Test for existence of the Spyrus directory and exit if it's already prepared
[ -d "${SPYDIR}" ] && exit 0

# Check if USB Spyrus is recorded in the configuration file; exit if not
. "/etc/conf.local/hw_config"
[ -z "${SPYRUS_USB_PRESENT}" ] && exit 0
gcs_truefalse "${SPYRUS_USB_PRESENT}" || exit 0

# Create fresh state directory
echo " * Creating USB Spyrus configuration files"

mkdir -m 02770 "${SPYDIR}"
chgrp spyrus "${SPYDIR}"

echo "SPYENABLE=1" > "${SPYCFG}"
[ -n "${SPYRUS_USB_POWER_LINE}" ] && echo "SPY_POWER_LINE=${SPYRUS_USB_POWER_LINE}" >> "${SPYCFG}"
[ -n "${SPYRUS_USB_POWER_DELAY}" ] && echo "SPY_POWER_DELAY=${SPYRUS_USB_POWER_DELAY}" >> "${SPYCFG}"

openssl dsaparam -outform pem 1024 > "${SPYDIR}/dsaparam.pem.local"
