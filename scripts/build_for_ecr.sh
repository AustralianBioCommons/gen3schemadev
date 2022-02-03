NAME=`echo $1 | cut -d":" -f 1`
TAG=`echo $1 | cut -d":" -f 2`


if [[ "NAME" == ""  || "$TAG" == "" ]]; then
	echo "Usage: ${0} image-name:tag-name"
	exit
fi

docker build --platform linux/amd64 -t 145193863738.dkr.ecr.ap-southeast-2.amazonaws.com/${NAME}:${TAG}-amd64 . && \
docker build --platform linux/arm64 -t 145193863738.dkr.ecr.ap-southeast-2.amazonaws.com/${NAME}:${TAG}-arm64 . && \
docker push 145193863738.dkr.ecr.ap-southeast-2.amazonaws.com/${NAME}:${TAG}-amd64 && \
docker push 145193863738.dkr.ecr.ap-southeast-2.amazonaws.com/${NAME}:${TAG}-arm64 && \
docker manifest create --amend 145193863738.dkr.ecr.ap-southeast-2.amazonaws.com/${NAME}:${TAG} 145193863738.dkr.ecr.ap-southeast-2.amazonaws.com/${NAME}:${TAG}-amd64 145193863738.dkr.ecr.ap-southeast-2.amazonaws.com/${NAME}:${TAG}-arm64 && \
docker manifest push 145193863738.dkr.ecr.ap-southeast-2.amazonaws.com/${NAME}:${TAG}