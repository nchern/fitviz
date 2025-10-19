#!/bin/sh
set -ue

# Help: syncs data on smartwatch with your local deskop via MTP

die() { echo "$(basename "$0"): fatal: $1" && exit "${2-1}"; }

check_garmin_fs() {
    # light check that we are trying to sync with Garmin and not with
    # something else mountet over MTP
    [ ! -f "$1/GarminDevice.xml" ] && return 1
    [ ! -f "$1/device.fit" ] && return 1
}


LOCAL_DATA_DIR="$HOME/Smartwatch"

REMOTE_MOUNT_DIR="$HOME/mnt"
REMOTE_DATA_DIR="$REMOTE_MOUNT_DIR/Internal Storage/GARMIN"


mkdir -p "$REMOTE_MOUNT_DIR"

jmtpfs "$REMOTE_MOUNT_DIR"

check_garmin_fs "$REMOTE_DATA_DIR" || die "[$REMOTE_DATA_DIR]: FS not look like Garmin FS. Double-check"
rsync --dry-run -aP "$REMOTE_DATA_DIR/" "$LOCAL_DATA_DIR/"

fusermount -u "$REMOTE_MOUNT_DIR"
