#!/usr/bin/env bash
set -euo pipefail
exp_root=$(cd -- "$(dirname -- "$0")" && pwd)
if ! docker container inspect jac-webridge-paper-mysql5725 > /dev/null 2>&1; then
 docker run -d --name jac-webridge-paper-mysql5725 --cpus=8 --cpuset-cpus=4-7,14-17 --memory=16g -p 127.0.0.1:55325:3306 -e MYSQL_ALLOW_EMPTY_PASSWORD=yes -e MYSQL_DATABASE=my_blog_db mysql:5.7.25 --performance-schema=ON --local-infile=1
else
 test "$(docker inspect -f '{{.Config.Image}}' jac-webridge-paper-mysql5725)" = mysql:5.7.25
 docker start jac-webridge-paper-mysql5725 > /dev/null
fi
for attempt in $(seq 1 120); do
 if docker exec jac-webridge-paper-mysql5725 mysqladmin -uroot ping --silent > /dev/null 2>&1; then break; fi
 sleep 1
done
test "$(docker exec jac-webridge-paper-mysql5725 mysql -uroot -N -e 'SELECT VERSION();')" = 5.7.25
docker exec jac-webridge-paper-mysql5725 mysql -uroot -e "ALTER DATABASE my_blog_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER IF NOT EXISTS 'webridge'@'%' IDENTIFIED BY 'webridge-local'; GRANT ALL PRIVILEGES ON my_blog_db.* TO 'webridge'@'%'; GRANT SELECT ON performance_schema.* TO 'webridge'@'%';"
docker update --cpuset-cpus 4-7,14-17 --cpus=8 --memory=16g jac-webridge-paper-mysql5725
mkdir -p "$exp_root/paper"
docker build -t jac-webridge-network:ubuntu22 -f "$exp_root/Dockerfile.network" "$exp_root"
docker run --rm --network container:jac-webridge-paper-mysql5725 --cap-add NET_ADMIN jac-webridge-network:ubuntu22 tc qdisc replace dev eth0 root netem delay 2100us
docker run --rm --network container:jac-webridge-paper-mysql5725 --cap-add NET_ADMIN jac-webridge-network:ubuntu22 tc -s qdisc show dev eth0 > "$exp_root/paper/netem.txt"
db_ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' jac-webridge-paper-mysql5725)
docker run --rm --network host jac-webridge-network:ubuntu22 ping -c 20 -i 0.2 "$db_ip" > "$exp_root/paper/ping-rtt.txt"
