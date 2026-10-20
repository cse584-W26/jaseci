#!/usr/bin/env bash
set -euo pipefail
exp_root=$(cd -- "$(dirname -- "$0")" && pwd)
workspace_root=$(cd -- "$exp_root/../.." && pwd)
artifact_root="$workspace_root/webridge"
mkdir -p "$exp_root/logs"
if [ ! -d "$artifact_root/.git" ]; then
 git clone --no-checkout https://github.com/Novemser/webridge-materials.git "$artifact_root"
 git -C "$artifact_root" checkout --detach ae2e4c2642815ee8622e4af955d406859f718795
fi
test "$(git -C "$artifact_root" rev-parse HEAD)" = ae2e4c2642815ee8622e4af955d406859f718795
docker build -t jac-webridge-build:ubuntu18 -f "$exp_root/Dockerfile.build" "$exp_root"
if [ ! -d "$exp_root/upstream-jdk8u/.git" ]; then
 git clone --depth 1 --branch jdk8u312-ga --filter=blob:none --sparse https://github.com/openjdk/jdk8u.git "$exp_root/upstream-jdk8u"
fi
git -C "$exp_root/upstream-jdk8u" sparse-checkout set corba/make/tools jdk/make/src
cp -a "$exp_root/upstream-jdk8u/corba/make/tools" "$artifact_root/SourceCode/openjdk8-webridge/corba/make/"
mkdir -p "$artifact_root/SourceCode/openjdk8-webridge/jdk/make/src"
cp -a "$exp_root/upstream-jdk8u/jdk/make/src/classes" "$artifact_root/SourceCode/openjdk8-webridge/jdk/make/src/"
python3 "$exp_root/repair_upstream.py"
docker run --rm --name jac-webridge-jdk-build --user "$(id -u):$(id -g)" -v "$workspace_root:/work" -w /work/webridge/SourceCode/openjdk8-webridge jac-webridge-build:ubuntu18 bash -lc '
set -e
bash configure CC=gcc-6 CXX=g++-6 --with-boot-jdk=/usr/lib/jvm/java-8-openjdk-amd64 --with-jvm-variants=zero --with-debug-level=release --with-extra-cflags="-DENABLE_CONCOLIC -DONELINE -DCONCOLIC_JDBC -DENABLE_WEBRIDGE" --with-extra-cxxflags="-DENABLE_CONCOLIC -DONELINE -DCONCOLIC_JDBC -DENABLE_WEBRIDGE"
make all JOBS=8 CONF=linux-x86_64-normal-zero-release
bash configure CC=gcc-6 CXX=g++-6 --with-boot-jdk=/usr/lib/jvm/java-8-openjdk-amd64 --with-debug-level=release
make all JOBS=8 CONF=linux-x86_64-normal-server-release
' > "$exp_root/logs/build-jdks-scripted.log" 2>&1
mkdir -p "$exp_root/boot-jdk8" "$exp_root/native-lib"
docker run --rm jac-webridge-build:ubuntu18 tar -C /usr/lib/jvm/java-8-openjdk-amd64 -cf - . | tar -xf - -C "$exp_root/boot-jdk8"
docker run --rm jac-webridge-build:ubuntu18 cat /usr/lib/x86_64-linux-gnu/libffi.so.6 > "$exp_root/native-lib/libffi.so.6"
export JAVA_HOME="$exp_root/boot-jdk8"
cd "$artifact_root/SourceCode/webridge-common"
./gradlew --no-daemon -I "$exp_root/custom-jdk.gradle" :lib:shadowJar publishToMavenLocal -x test -x spotlessJavaApply -x javadoc > "$exp_root/logs/build-common-scripted.log" 2>&1
./gradlew --no-daemon -I "$exp_root/export-deps.gradle" :basic-components:exportExperimentDeps > "$exp_root/logs/export-deps-scripted.log" 2>&1
if [ ! -x "$exp_root/apache-maven-3.8.8/bin/mvn" ]; then
 curl -fL https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.8.8/apache-maven-3.8.8-bin.tar.gz -o "$exp_root/apache-maven-3.8.8-bin.tar.gz"
 tar -xzf "$exp_root/apache-maven-3.8.8-bin.tar.gz" -C "$exp_root"
fi
export JAVA_HOME="$artifact_root/SourceCode/openjdk8-webridge/build/linux-x86_64-normal-server-release/images/j2sdk-image"
export LD_LIBRARY_PATH="$exp_root/native-lib"
cd "$artifact_root/Application/my-blog"
"$exp_root/apache-maven-3.8.8/bin/mvn" -B package -Dmaven.test.skip=true > "$exp_root/logs/build-myblog-scripted.log" 2>&1
if [ ! -d "$exp_root/paper-driver" ]; then
 python3 "$exp_root/paper-audit/prepare_driver.py" --output "$exp_root/paper-driver" --profile paper-equal
fi
python3 "$exp_root/export_raw_samples.py"
export JAVA_HOME="$exp_root/boot-jdk8"
"$exp_root/paper-driver/gradlew" -p "$exp_root/paper-driver" --no-daemon jar -x test > "$exp_root/logs/build-paper-driver-scripted.log" 2>&1
mkdir -p "$exp_root/classes"
"$JAVA_HOME/bin/javac" -cp "$artifact_root/SourceCode/webridge-common/lib/build/libs/lib.jar:$exp_root/deps/*" -d "$exp_root/classes" "$exp_root/java/PaperCompilerServer.java" "$exp_root/java/Ic5Benchmark.java"
