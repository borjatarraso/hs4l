# hs4l -- helpers shared by bin/spy.sh and bin/spy-native.sh (sourced, POSIX sh)

# Print the /dev/bus/usb node of the first SPYRUS LYNKS (08df:0a00) found.
hs4l_usb_node() {
  for d in /sys/bus/usb/devices/*; do
    [ -r "$d/idVendor" ] && [ -r "$d/idProduct" ] || continue
    read -r v < "$d/idVendor"
    read -r p < "$d/idProduct"
    [ "$v" = 08df ] && [ "$p" = 0a00 ] || continue
    read -r bus < "$d/busnum"
    read -r dev < "$d/devnum"
    printf '/dev/bus/usb/%03d/%03d\n' "$bus" "$dev"
    return 0
  done
  return 1
}

# Print "sudo" when the vendor tool must be run as root, nothing otherwise.
#   HS4L_SUDO=1  always sudo        HS4L_SUDO=0  never sudo
# Default: run unprivileged when the token node, libspyrus' use-lock
# (/var/lock/spyrus.lck) and its config dir (/etc/spyrus) are all writable by
# this user -- which is what scripts/setup-udev.sh arranges. Otherwise fall
# back to sudo and say so once.
hs4l_sudo() {
  case "${HS4L_SUDO:-}" in
    1) echo sudo; return 0 ;;
    0) return 0 ;;
  esac
  [ "$(id -u)" = 0 ] && return 0
  node=$(hs4l_usb_node) || {
    echo "hs4l: no SPYRUS LYNKS (08df:0a00) on USB; running anyway" >&2
    return 0
  }
  if [ -w "$node" ] && [ -w /var/lock/spyrus.lck ] && [ -w /etc/spyrus ]; then
    return 0
  fi
  echo "hs4l: $node, /var/lock/spyrus.lck or /etc/spyrus not writable by $(id -un); using sudo" >&2
  echo "hs4l: (run scripts/setup-udev.sh once to work without sudo, or set HS4L_SUDO=0)" >&2
  echo sudo
}

# Print the wrapper's own knobs (spyrus_util's help follows when it is there).
#   $1  wrapper name    $2  runtime-location variable    $3  fetch-source variable
hs4l_help() {
  cat <<EOT
$1 -- hs4l wrapper around the vendor's spyrus_util; every flag passes through.

Environment:
  $2
  $3
  HS4L_SUDO=1     always run the vendor tool under sudo
  HS4L_SUDO=0     never sudo (fails if the token node, /var/lock/spyrus.lck or
                  /etc/spyrus are not writable; scripts/setup-udev.sh fixes that)

Verify a signature off-card:  python3 scripts/verify.py PUBKEY MESSAGE SIGNATURE
Docs: README.md, docs/REINITIALIZE.md, docs/TROUBLESHOOTING.md

EOT
}

# True when -h or --help is among the arguments.
hs4l_wants_help() {
  for a in "$@"; do
    case "$a" in -h|--help) return 0 ;; esac
  done
  return 1
}
