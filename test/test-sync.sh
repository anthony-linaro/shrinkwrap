#!/bin/bash
# Create temporary git repositories and test shrinkwrap's synchronization feature

# Run on the host, so we don't need to deal with remote git URLs.
SHRINKWRAP="shrinkwrap -R null"

set -eu

LOG=/tmp/shrinkwrap-sync-test.log
echo > $LOG
echo "Logging to file $LOG"

set -x
exec 2>>$LOG

T=$(mktemp -d)
# paranoid check: ensure we won't remove existing files
[ -z "$T" -o -n "$(ls -A $T)" ] && exit 1
trap "rm -rf $T" EXIT

export SHRINKWRAP_BUILD=$T/build
export SHRINKWRAP_PACKAGE=$T/package

cat << EOF > $T/gitconfig
# Needed when not configured in config (e.g. on ci)
[user]
    name = Mr T. Ester
    email = mr.t.ester@test-sync.sh

# Needed so we can use local repo paths for submodules
[protocol.file]
    allow = always
EOF

export GIT_CONFIG_GLOBAL=$T/gitconfig

# Test $1 must succeed
OK () {
    local name="$1"
    shift
    $SHRINKWRAP build -v $T/base.yaml $@ >>$LOG 2>&1 ||
        { echo "FAIL  $name" && exit 1; }
    echo "PASS  $name"
}

# Test $1 must fail
FAIL () {
    local name="$1"
    shift
    $SHRINKWRAP build -v $T/base.yaml $@ >>$LOG 2>&1 &&
        echo "FAIL  $name" && exit 1
    echo "PASS  $name"
}

# File $1 content must be equal to $2
CONTENT () {
    local file="$1"
    local nice="${file##$T}" # remove prefix
    local content="$2"

    if [ -e "$file" ] && [ "$(cat $file)" = "$content" ]; then
        echo "PASS    $nice"
    else
        echo "FAIL    $nice"
        exit 1
    fi
}

TESTS () {
    echo "$@"
    echo "#### $@" >> $LOG
}


# Create the initial repos and config
{
    git init $T/repo1 -b main
    git init $T/module1 -b main

    pushd $T/module1
    echo -n "module 1 commit 0" > README
    git add README
    git commit -m "commit 0"
    popd

    pushd $T/repo1
    echo -n "repo 1 commit 0" > README
    git add README
    git commit -m "commit 0"

    git submodule add file://$T/module1 module
    git commit -a -m "Add module 1"
    popd
} >> $LOG

cat << EOF > $T/base.yaml
%YAML 1.2
---
concrete: true

build:
  test1:
    repo:
      remote: file://$T/repo1
      revision: main
    build:
      - cat module/README
EOF


################################################################################
TESTS   Basic clone and update

OK "initial clone"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 0"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/README "module 1 commit 0"

OK "second sync is nop"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 0"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/README "module 1 commit 0"

# Update the repo1 README
{
    pushd $T/repo1
    echo -n "repo 1 commit 1" > README
    git commit -a -m "commit 1"
    popd
} >> $LOG

OK "sync=on does not update"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 0"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/README "module 1 commit 0"

OK "sync=force updates" --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 1"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/README "module 1 commit 0"


################################################################################
TESTS   Module update

# Update the module1 README
{
    pushd $T/module1
    echo -n "module 1 commit 1" > README
    git commit -a -m "commit 1"
    popd

    pushd $T/repo1
    git submodule update --remote
    git commit -a -m "Update submodule 1"
    popd
} >> $LOG

OK "sync=on does not update"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 1"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/README "module 1 commit 0"

OK "sync=force updates module" --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 1"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/README "module 1 commit 1"


################################################################################
TESTS   Tag and branch update

# Update repo1 with a tag
{
    pushd $T/repo1
    echo -n "repo 1 commit 2" > README
    git commit -a -m "commit 2"
    git tag v0.1
    popd
} >> $LOG

# Update revision with an overlay
cat << EOF > $T/overlay.yaml
build:
  test1:
    repo:
      revision: v0.1
EOF

OK "update new tag" -o $T/overlay.yaml
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 2"

OK "rollback to main without overlay"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 1"

# Update repo1 with a branch
{
    pushd $T/repo1
    git checkout -b topic1
    echo -n "repo 1 commit topic.1" > README
    git commit -a -m "commit 1 on topic"
    git checkout -
    popd
} >> $LOG

# Update revision with an overlay
cat << EOF > $T/overlay.yaml
build:
  test1:
    repo:
      revision: topic1
EOF


OK "update new branch" -o $T/overlay.yaml
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit topic.1"

OK "rollback to main without overlay"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 1"

OK "force update" --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 2"


################################################################################
TESTS   Tagged module update

# Update the module1 README
{
    pushd $T/module1
    echo -n "module 1 commit 2" > README
    git commit -a -m "commit 2"
    popd

    pushd $T/repo1
    git submodule update --remote
    git commit -a -m "Update submodule 1"
    git tag v0.1.1
    popd
} >> $LOG

# Update revision with an overlay
cat << EOF > $T/overlay.yaml
build:
  test1:
    repo:
      revision: v0.1.1
EOF

OK "tagged module update" -o $T/overlay.yaml
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 2"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/README "module 1 commit 2"


################################################################################
TESTS   Tag and branch udpates with --force-sync

# Update repo1 with a tag
{
    pushd $T/repo1
    echo -n "repo 1 commit 3" > README
    git commit -a -m "commit 3"
    git tag v0.2
    popd
} >> $LOG

# Update revision with an overlay
cat << EOF > $T/overlay.yaml
build:
  test1:
    repo:
      revision: v0.2
EOF

OK "tag update with sync=force" -o $T/overlay.yaml --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 3"

OK "back to main (overriden by force)"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 2"

# Update repo1 with a branch
{
    pushd $T/repo1
    git checkout -b topic2
    echo -n "repo 1 commit topic.2" > README
    git commit -a -m "commit 1 on topic 2"
    git checkout -
    popd
} >> $LOG

# Update revision with an overlay
cat << EOF > $T/overlay.yaml
build:
  test1:
    repo:
      revision: topic2
EOF

OK "branch update with sync=force" -o $T/overlay.yaml --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit topic.2"

OK "back to main"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 2"



################################################################################
TESTS   Overwrite file

# Add a file to repo1
{
    pushd $T/repo1
    echo "int main() {}" > main.c
    git add main.c
    git commit -a -m "add main"
    git tag v0.3
    popd
} >> $LOG

# Update revision with an overlay
cat << EOF > $T/overlay.yaml
build:
  test1:
    repo:
      revision: v0.3
EOF

# Also create the file locally
{
    echo "int foo() {}" > $SHRINKWRAP_BUILD/source/base/test1/main.c
} >> $LOG

FAIL "refusing to overwrite" -o $T/overlay.yaml
CONTENT $SHRINKWRAP_BUILD/source/base/test1/main.c "int foo() {}"

OK "force overwrite" -o $T/overlay.yaml --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/main.c "int main() {}"


################################################################################
TESTS   Overwrite module file

# Add a file to module1, in a new branch
{
    pushd $T/module1
    echo "int main() {}" > main.c
    git add main.c
    git commit -a -m "add main"
    popd

    pushd $T/repo1
    git submodule update --remote --merge
    git commit -a -m "Update submodule 2"
    git tag v0.4
    popd
} >> $LOG

# Update revision with an overlay
cat << EOF > $T/overlay.yaml
build:
  test1:
    repo:
      revision: v0.4
EOF

# Also create the file locally
{
    echo "int foo() {}" > $SHRINKWRAP_BUILD/source/base/test1/module/main.c
} >> $LOG

FAIL "refusing to overwrite submodule" -o $T/overlay.yaml
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/main.c "int foo() {}"

OK "force overwrite submodule" -o $T/overlay.yaml --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/main.c "int main() {}"


################################################################################
TESTS   User source dir

# Use a local source directory
cat << EOF > $T/overlay.yaml
build:
  test1:
    sourcedir: $T/my-source/
EOF

OK "create local sourcedir" -o $T/overlay.yaml
CONTENT $T/my-source/README "repo 1 commit 3"

rm -rf $T/my-source/
mkdir $T/my-source/

OK "use empty local sourcedir" -o $T/overlay.yaml
CONTENT $T/my-source/README "repo 1 commit 3"

rm -rf $T/my-source/
mkdir $T/my-source/
echo GPL > $T/my-source/LICENSE

# fatal: destination path '.' already exists and is not an empty directory.
# --force-sync won't work in this case because it's the clone that fails
FAIL "clone fail in non-empty sourcedir" -o $T/overlay.yaml
CONTENT $T/my-source/LICENSE "GPL"

rm -rf $T/my-source/


################################################################################
TESTS   Override branch

# Reuse an existing branch name in a different repo
{
    git init $T/repo2 -b main
    git init $T/module2 -b main

    pushd $T/module2
    echo -n "module 2 commit 0" > README
    git add README
    git commit -m "commit 0"
    popd

    pushd $T/repo2
    echo repo 2 commit 0 > README
    git add README
    git commit -a -m "commit 0"

    git submodule add file://$T/module2 module
    git commit -a -m "Add module 2"
    popd
} >> $LOG

cat << EOF > $T/overlay.yaml
build:
  test1:
    repo:
      remote: file://$T/repo2
EOF

OK "sync=on use old main branch" -o $T/overlay.yaml
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 2"

OK "sync=force use new main branch" -o $T/overlay.yaml --force-sync-all
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 2 commit 0"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/README "module 2 commit 0"


################################################################################
TESTS   Update module branch

# Update repo2 module branch
{
    pushd $T/module2
    git checkout -b branch2
    echo -n "module 2 commit 1" > README
    git commit -a -m "commit 1"
    popd

    pushd $T/repo2
    git submodule set-branch -b branch2 module
    git submodule update --remote
    git commit -a -m "Update module branch"
    popd
} >> $LOG

OK "sync=force update module branch" -o $T/overlay.yaml --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/README "module 2 commit 1"


################################################################################
TESTS   Update module URL

# Update repo2 module URL
{
    pushd $T/repo2
    git submodule set-branch -b main module
    git submodule set-url module file://$T/module1
    git submodule update --remote
    git commit -a -m "Update module URL"
    popd
} >> $LOG

cat << EOF > $T/overlay.yaml
build:
  test1:
    repo:
      remote: file://$T/repo2
EOF

OK "sync=true doesn't update module URL" -o $T/overlay.yaml
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 2 commit 0"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/README "module 2 commit 1"

OK "sync=force updates module URL" -o $T/overlay.yaml --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 2 commit 0"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/module/README "module 1 commit 2"


OK "rollback to repo1" --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 3"


################################################################################
TESTS   nosync config

# Update the repo1 README
{
    pushd $T/repo1
    echo -n "repo 1 commit 4" > README
    git commit -a -m "commit 4"
    git tag v0.5
    popd
} >> $LOG

cat << EOF > $T/overlay.yaml
build:
  test1:
    repo:
      revision: v0.5
    sync: false
EOF

OK "config sync=false does not update" -o $T/overlay.yaml
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 3"

OK "config sync=false updates with --force-sync-all" -o $T/overlay.yaml --force-sync-all
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 4"

cat << EOF > $T/overlay.yaml
build:
  test1:
    sync: hello
EOF

FAIL "invalid config" -o $T/overlay.yaml

# Update the repo1 README
{
    pushd $T/repo1
    echo -n "repo 1 commit 5" > README
    git commit -a -m "commit 5"
    popd
} >> $LOG

cat << EOF > $T/overlay.yaml
build:
  test1:
    sync: force
EOF

OK "config sync=force does not update with --no-sync" -o $T/overlay.yaml --no-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 4"

OK "config sync=force does not update with --no-sync-all" -o $T/overlay.yaml --no-sync-all
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 4"

OK "config sync=force updates" -o $T/overlay.yaml
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 5"


################################################################################
TESTS   hash sync

# Obtain hash of a specific commit
old_hash=$(git -C $T/repo1 show-ref --hash v0.1)

cat << EOF > $T/overlay.yaml
build:
  test1:
    repo:
      revision: $old_hash
EOF

OK "switch to old git hash" -o $T/overlay.yaml
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 2"
OK "switch to main"
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 5"

OK "switch to old git hash with --force-sync" -o $T/overlay.yaml --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 2"
OK "switch to main with --force-sync" --force-sync=test1
CONTENT $SHRINKWRAP_BUILD/source/base/test1/README "repo 1 commit 5"

echo ALL TESTS PASS
