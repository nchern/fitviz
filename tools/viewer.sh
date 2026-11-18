#!/bin/sh
set -ue

NAME=fitviz

{ sleep 3; "$BROWSER" "http://localhost:3000/dashboards" ; } &

# start if exists
if docker ps -a | grep -q "$NAME" ; then
    exec docker start -i "$NAME"
fi

# create and run
exec docker run -t --rm                             \
    -p 3000:3000                                    \
    --name "$NAME"                                  \
    -e GF_AUTH_ANONYMOUS_ENABLED=true               \
    -e GF_AUTH_DISABLE_LOGIN_FORM=true              \
    -e GF_AUTH_ANONYMOUS_ORG_ROLE=Admin             \
    -e GF_INSTALL_PLUGINS=frser-sqlite-datasource   \
    -v fitviz-data:/var/lib/grafana                 \
    -v "$HOME/fit.db:/var/data/fit.db"              \
    --user "$(id -u):$(id -g)"                      \
    grafana/grafana:latest
