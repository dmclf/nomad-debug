#!/bin/bash
# https://github.com/hashicorp/nomad/issues/26693
cat << EOF > nomad-hello-world.hcl
job "helloworld" {
  datacenters = ["*"]
  type = "batch"
  group "example" {
    task "alpine" {
      driver = "docker"
      config {
        image = "alpine"
        args = [
          "echo",
          "hello_world",
        ]
      }
    }
  }
}
EOF

nomad job plan nomad-hello-world.hcl
nomad job run -check-index 0 nomad-hello-world.hcl

export MAX_TRIES=20 TRY=0 ALLOC_ID=""

#loop until alloc done downloading image.
while [[ -z "$ALLOC_ID" && $TRY -lt $MAX_TRIES ]]; do
  ALLOC_ID=$(nomad job status helloworld | awk '/run.*(running|complete).*ago/ {getline; print $1}')
  if [[ -z "$ALLOC_ID" ]]; then
    sleep 2
    ((TRY++))
    echo "Waiting... ($TRY/$MAX_TRIES)"
  fi
done

#show alloc status -short
nomad alloc status -short $ALLOC_ID

#echo hello_world should be quick, timeout with 60 seconds.
timeout 60 nomad alloc logs -f $ALLOC_ID

ALLOC_EXITCODE=$?
if test $ALLOC_EXITCODE -eq 0
then 
    echo "ALLOC_EXITCODE:$ALLOC_EXITCODE = OK -> PASS .. logs -f terminated properly"
else
    nomad alloc status $ALLOC_ID
    echo "ERROR ALLOC_EXITCODE=$ALLOC_EXITCODE timeout reached, logs -f was not closing after task dead/terminated/exit (0)"
fi

function workaround_logic() {
    while true
    do
        nomad alloc status -short $ALLOC_ID | grep Terminated && break
        sleep 2
    done

}

nomad alloc logs -f $ALLOC_ID &
loop_until_done

echo "Waiting .. killing leftovers"
jobs -p
kill $(jobs -p)
