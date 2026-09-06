# Credit to DrewDevault: https://git.sr.ht/~sircmpwn/scdoc/tree/master/item/test/lib.sh

printf '=== %s\n' "$0"
trap "printf '\n'" EXIT

begin() {
	printf '%-50s' "$1"
}

end() {
	if [ $? -ne "$1" ]
	then
        _fail_msg="$2"
		printf 'FAIL: %s\n' "$_fail_msg"
	else
		printf 'OK\n'
	fi
}
