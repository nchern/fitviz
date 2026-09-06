#!/bin/sh

. tests/lib.sh


fitparse() {
    _cmd="$1"; shift
    ./fitparse.py -c "$_cmd" "$@"
}

begin "Test dump command"
./fitparse.py -c dump testdata/Monitor/MAD00000.FIT | diff testdata/MAD00000.FIT.dump.txt -
end 0 "expected no diff"

begin "Test sleep command"
./fitparse.py -c sleep testdata/Sleep/* | diff testdata/sleep.txt -
end 0 "expected no diff"

begin "Test stress command"
./fitparse.py -c stress testdata/Monitor/MAD00000.FIT | diff testdata/MAD00000.FIT.stress.txt -
end 0 "expected no diff"

begin "Test pulse command"
./fitparse.py -c pulse testdata/Monitor/MAD00000.FIT | diff testdata/MAD00000.FIT.pulse.txt -
end 0 "expected no diff"

begin "Test steps command"
./fitparse.py -c steps testdata/Monitor/* | diff testdata/expected.steps.txt -
end 0 "expected no diff"
