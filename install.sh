#!/bin/sh
export LANG="en_US.UTF-8"
echo '1.删除历史串口映射'
killall -9 socat
echo '2.映射串口/dev/ttyS11'
socat PTY,link=/dev/ttyS10 PTY,link=/dev/ttyS11 &

echo '3.获取镜像'

echo '4.删除历史docker 镜像'
docker rmi serialserver_code
echo '5. 查找并且删除历史 docker 镜像和容器'
docker images|grep none|awk '{print $3 }'|xargs docker rmi
docker ps -a | grep serialserver_code | awk  '{print $1 }' |xargs docker rm -f
echo '6.读取用户ID 和镜像名称'
parse_json(){
echo "${1//\"/}" | sed "s/.*$2:\([^,}]*\).*/\1/"
}
userid=$(parse_json $docEnv "userId")
echo $userid
echo $HOSTNAME

echo '7.把用户ID 和 镜像名称 写入docker 环境变量中'
path=/serialServer/Dockerfile
cd /serialServer
git checkout ./
sed -i "s/container_id/$HOSTNAME/" /serialServer/Dockerfile
sed -i "s/user_id/$userid/" /serialServer/Dockerfile
echo '8.启动docker'

cd /serialServer && docker-compose -f docker-compose.yml up --build -d