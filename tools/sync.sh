#!/bin/sh
set -ue

# Help: syncs data on smartwatch with your local deskop via MTP

LOCAL_DATA_DIR="$HOME/Smartwatch"

REMOTE_MOUNT_DIR="$HOME/mnt"
REMOTE_DATA_DIR="$REMOTE_MOUNT_DIR/Internal Storage/GARMIN"

die() { echo "$(basename "$0"): fatal: $1" && exit "${2-1}"; }

assert_garmin_fs() {
    # light check that we are trying to sync with Garmin and not with
    # something else mountet over MTP
    _err_msg="[$REMOTE_DATA_DIR]: FS not look like Garmin FS. Double-check"
    set +e
    [ ! -f "$1/GarminDevice.xml" ] && die "$_err_msg"
    [ ! -f "$1/device.fit" ] && die "$_err_msg"
    set -e
}

mount_garmin() {
    jmtpfs "$REMOTE_MOUNT_DIR" || _err_code=$?
    if [ "$_err_code" -gt 0 ]; then
        if [ "$_err_code" = 134 ]; then
            echo "$REMOTE_MOUNT_DIR: already mounted; continue"
            exit
        fi
        exit "$_err_code"
    fi
}

unmount_garmin() {
    fusermount -u "$REMOTE_MOUNT_DIR"
    echo "$REMOTE_MOUNT_DIR: successfully unmounted"
}


mkdir -p "$REMOTE_MOUNT_DIR"

mount_garmin

assert_garmin_fs "$REMOTE_DATA_DIR"

rsync -aP "$REMOTE_DATA_DIR/" "$LOCAL_DATA_DIR/"

unmount_garmin
