UMCCR_SCHEMA_INSTALLATION=${HOME}/Documents/Biocommons/Gen3/src/umccr-dictionary
SCHEMADEV_INSTALLATION=${HOME}/PycharmProjects/biocommons-gen3-schamadev
COMPOSE_SERVICES_INSTALLATION=${HOME}/Documents/Biocommons/Gen3/src/compose-services

CURRENT_DIR=`cwd`

echo "removing old schemas"
rm ${UMCCR_SCHEMA_INSTALLATION}/dictionary/cad/gdcdictionary/schemas/*.yaml

echo "copying"
cp ${SCHEMADEV_INSTALLATION}/schema_out/*.yaml ${UMCCR_SCHEMA_INSTALLATION}/dictionary/cad/gdcdictionary/schemas/

echo "compiling"
cd ${UMCCR_SCHEMA_INSTALLATION}
make up
make compile dd=cad
make load dd=cad
make simulate dd=cad project=simulated samples=10

echo "purging old schemas"
rm ${COMPOSE_SERVICES_INSTALLATION}/datadictionary/gdcdictionary/schemas/*.yaml

echo "copying"
cp ${SCHEMADEV_INSTALLATION}/schema_out/*.yaml ${COMPOSE_SERVICES_INSTALLATION}/datadictionary/gdcdictionary/schemas/

cd ${COMPOSE_SERVICES_INSTALLATION}
docker-compose down
docker-compose up -d

echo "Now is the time to relax, and take a deep breath and checking it is all okay on your local development environment."
echo "if you press enter the ONLINE system will receive a new json"
echo "make sure it is all good!!!"
read

echo "save the current json as json.old"
aws s3 cp s3://biocommons-gen3-schema/cad/dev/cad.json s3://biocommons-gen3-schema/cad/dev/cad.json.old

echo "Put the local json online"
aws s3 cp ${UMCCR_SCHEMA_INSTALLATION}/schema/cad.json s3://biocommons-gen3-schema/cad/dev/cad.json

echo "Giving the world access to cad.json"
aws s3api put-object-acl --bucket biocommons-gen3-schema --key cad/dev/cad.json --acl public-read