#!/bin/bash

ssh_user='root'
ip=$1
certs=(
/etc/kafka/ssl/cert/client1.crt
/etc/kafka/ssl/key/client1.key
/etc/kafka/ssl/ca/ca-crt
)

cert_count=${#certs[@]}
count=0

function getcerts {
        while [ $count -lt $cert_count  ]; do
                echo "[info] fetching ${certs[count]} from $ip.."
                ssh $ssh_user@$ip "cat ${certs[count]}" > $(echo ${certs[count]} | awk -F '/' {'print $NF'})
                count=$(( $count + 1  ))

        done
}

function help {
        cat << EOF
[fatal] Please provide and IP address as the first arguement.

Usage:
bash getcerts.sh [IP]

Example:
bash getcerts.sh 192.0.2.21
EOF

exit
}
function main {
        getcerts
}

# main
if [ -z $1 ]; then
        help
fi

main