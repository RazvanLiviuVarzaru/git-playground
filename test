# User config
BUILD_IMAGE=quay.io/mariadb-foundation/bb-worker:rhel10
GIT_REPO=https://github.com/MariaDB-Corporation/mariadb-connector-odbc.git
GIT_BRANCH=odbc-3.1
GIT_COMMIT=3d62dc272b682247191730ba88a4a39d756fe39a
MAKE_PARALLEL=24
# Save tar / rpm artifacts to host
SAVE_TO_HOST_ARTIFACTS_DIR="/home/razvan/tmp/odbc-artifacts"
SAVE_ARTIFACTS=1 # 1 to save, 0 to skip saving

# Sidecar config
SIDECAR=mariadb:latest
SIDECAR_NAME=sidecar-mariadb-server

# Test config
TEST_UID=root
TEST_PASSWORD=
TEST_PORT=3306
TEST_SERVER=$SIDECAR_NAME
TEST_SCHEMA=test
TEST_VERBOSE=true
TEST_DRIVER=maodbc_test
TEST_DSN=maodbc_test

# System config
NETWORK_NAME=mariadb-connector-odbc
VOLUME_NAME=mariadb-connector-odbc
CONTAINER_NAME=mariadb-connector-odbc
VOLUME_MOUNT_POINT=/home/buildbot
BASE_DIR="$VOLUME_MOUNT_POINT/odbc_build"
SOURCE_DIR="$BASE_DIR/source"
BUILD_DIR="$BASE_DIR/build"
BINTAR_DIR="$BUILD_DIR/bintar"
RPM_DIR="$BUILD_DIR/rpm"

cleanup_resource () {
  # Docker volume
  docker ps -a --filter "volume=$VOLUME_NAME" --format "{{.ID}}" | xargs -r docker rm -f
  docker volume rm $VOLUME_NAME || true 2> /dev/null
  # Docker network
  docker ps -a --filter "network=$NETWORK_NAME" --format "{{.ID}}" | xargs -r docker rm -f
  docker network rm $NETWORK_NAME || true 2> /dev/null
}

# Precleanup
cleanup_resource > /dev/null 2>&1 || true
# Docker volume
echo "Creating docker volume $VOLUME_NAME"
docker volume create $VOLUME_NAME
# Docker network
echo "Creating docker network $NETWORK_NAME"
docker network create $NETWORK_NAME

# Sidecar
docker run \
  -e MARIADB_ALLOW_EMPTY_ROOT_PASSWORD=1 \
  -e MARIADB_DATABASE=test \
  --network $NETWORK_NAME \
  --rm \
  --name $SIDECAR_NAME \
  -d \
  $SIDECAR

# sleep 10 # Wait for the server to be up and running

echo "--------------------------------------------------------------"
echo "Get source"
echo "--------------------------------------------------------------"
docker run \
  -e GIT_REPO=$GIT_REPO \
  -e GIT_COMMIT=$GIT_COMMIT \
  -e GIT_BRANCH=$GIT_BRANCH \
  -e SOURCE_DIR=$SOURCE_DIR \
  -v $VOLUME_NAME:$VOLUME_MOUNT_POINT \
  -w $VOLUME_MOUNT_POINT \
  --network $NETWORK_NAME \
  --rm \
  --name $CONTAINER_NAME \
  $BUILD_IMAGE \
  bash -c '
    mkdir -p $SOURCE_DIR
    cd $SOURCE_DIR
    git clone -b $GIT_BRANCH $GIT_REPO .
    git reset --hard $GIT_COMMIT
  '

echo "--------------------------------------------------------------"
echo "Build bintar"
echo "--------------------------------------------------------------"
docker run \
  -e MAKE_PARALLEL=$MAKE_PARALLEL \
  -e BINTAR_DIR=$BINTAR_DIR \
  -e SOURCE_DIR=$SOURCE_DIR \
  -v $VOLUME_NAME:$VOLUME_MOUNT_POINT \
  -w $VOLUME_MOUNT_POINT \
  --network $NETWORK_NAME \
  --rm \
  --name $CONTAINER_NAME \
  $BUILD_IMAGE \
  bash -c '
    mkdir -p $BINTAR_DIR
    cd $BINTAR_DIR
    cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCONC_WITH_UNIT_TESTS=Off -DPACKAGE_PLATFORM_SUFFIX=$HOSTNAME -DWITH_SSL=OPENSSL -DWITH_OPENSSL=ON $SOURCE_DIR
    cmake --build . --config RelWithDebInfo --target package --parallel $MAKE_PARALLEL
    ls -l *.tar.gz
  '

echo "--------------------------------------------------------------"
echo "Build rpm"
echo "--------------------------------------------------------------"
docker run \
  -e MAKE_PARALLEL=$MAKE_PARALLEL \
  -e RPM_DIR=$RPM_DIR \
  -e SOURCE_DIR=$SOURCE_DIR \
  -v $VOLUME_NAME:$VOLUME_MOUNT_POINT \
  -w $VOLUME_MOUNT_POINT \
  --network $NETWORK_NAME \
  --rm \
  --name $CONTAINER_NAME \
  $BUILD_IMAGE \
  bash -c '
    mkdir -p $RPM_DIR
    cd $RPM_DIR
    cmake -DRPM=On -DCPACK_GENERATOR=RPM -DCMAKE_BUILD_TYPE=RelWithDebInfo -DMARIADB_LINK_DYNAMIC=On -DPACKAGE_PLATFORM_SUFFIX=$HOSTNAME -DWITH_SSL=OPENSSL $SOURCE_DIR
    cmake --build . --config RelWithDebInfo --target package --parallel $MAKE_PARALLEL
    ls -l *rpm
  '

echo "--------------------------------------------------------------"
echo "Test bintar"
echo "--------------------------------------------------------------"
docker run \
  -e BINTAR_DIR=$BINTAR_DIR \
  -e TEST_UID=$TEST_UID \
  -e TEST_PASSWORD=$TEST_PASSWORD \
  -e TEST_PORT=$TEST_PORT \
  -e TEST_SERVER=$TEST_SERVER \
  -e TEST_SCHEMA=$TEST_SCHEMA \
  -e TEST_VERBOSE=$TEST_VERBOSE \
  -e TEST_DRIVER=$TEST_DRIVER \
  -e TEST_DSN=$TEST_DSN \
  -e SIDECAR_NAME=$SIDECAR_NAME \
  -v $VOLUME_NAME:$VOLUME_MOUNT_POINT \
  -w $VOLUME_MOUNT_POINT \
  --network $NETWORK_NAME \
  --rm \
  --name $CONTAINER_NAME \
  $BUILD_IMAGE \
  bash -c '
    cd $BINTAR_DIR/test
    export ODBCINI="$PWD/odbc.ini"
    export ODBCSYSINI=$PWD
    export TEST_SKIP_UNSTABLE_TEST=1
    sed -i "s/localhost/$SIDECAR_NAME/" odbc.ini
    ./odbc_basic
    ctest --output-on-failure
  '

echo "--------------------------------------------------------------"
echo "Test rpm"
echo "--------------------------------------------------------------"

# Here I am doing some tricks to make it work;
# 1. In the absence of a system-level install of libmariadb.so.3, I am installling the C/ODBC RPM with --nodeps
# 2. /usr/lib64/libmaodbc.so still needs libmariadb.so.3 so I am setting LD_LIBRARY_PATH to point to the lib in the bintar directory where libmariadb.so.3 is built

docker run \
  -e RPM_DIR=$RPM_DIR \
  -e BINTAR_DIR=$BINTAR_DIR \
  -e TEST_UID=$TEST_UID \
  -e TEST_PASSWORD=$TEST_PASSWORD \
  -e TEST_PORT=$TEST_PORT \
  -e TEST_SERVER=$TEST_SERVER \
  -e TEST_SCHEMA=$TEST_SCHEMA \
  -e TEST_VERBOSE=$TEST_VERBOSE \
  -e TEST_DRIVER=$TEST_DRIVER \
  -e TEST_DSN=$TEST_DSN \
  -e SIDECAR_NAME=$SIDECAR_NAME \
  -v $VOLUME_NAME:$VOLUME_MOUNT_POINT \
  -w $VOLUME_MOUNT_POINT \
  --network $NETWORK_NAME \
  --rm \
  --name $CONTAINER_NAME \
  -u root \
  $BUILD_IMAGE \
  bash -c '
    cd $RPM_DIR
    rpm -Uvh --nodeps $RPM_DIR/*rpm
    cd $RPM_DIR/test
    export ODBCINI="$PWD/odbc.ini"
    export ODBCSYSINI=$PWD
    export TEST_SKIP_UNSTABLE_TEST=1
    sed -i "s/localhost/$SIDECAR_NAME/" odbc.ini
    export LD_LIBRARY_PATH=$BINTAR_DIR/libmariadb/libmariadb${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
    ./odbc_basic
  '

if [ "$SAVE_ARTIFACTS" -eq 1 ]; then
    echo "--------------------------------------------------------------"
    echo "Copy artifacts to docker host"
    echo "--------------------------------------------------------------"

    mkdir -p "$SAVE_TO_HOST_ARTIFACTS_DIR"
    docker run --rm \
    -v "$VOLUME_NAME:$VOLUME_MOUNT_POINT:ro" \
    -v "$SAVE_TO_HOST_ARTIFACTS_DIR:/out" \
    $BUILD_IMAGE \
    bash -c "
        set -euo pipefail
        mkdir -p /out/bintar /out/rpm
        cp -av $BINTAR_DIR/*.tar.gz /out/bintar/ 2>/dev/null || true
        cp -av $RPM_DIR/*rpm /out/rpm/ 2>/dev/null || true
        echo 'Copied artifacts to /out:'
        ls -lah /out/bintar /out/rpm || true
    "
fi

# Post cleanup
cleanup_resource > /dev/null 2>&1 || true
