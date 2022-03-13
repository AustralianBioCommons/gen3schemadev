# generate a smallish simulated dataset and upload using the ec2
# assumes appropriate aws credentials are configured as the 'default' profile
CURRENT_DIR=`pwd`
UMCCR_SCHEMA_INSTALLATION=${HOME}/Documents/GitHub/umccr-dictionary
SCHEMADEV_INSTALLATION=${HOME}/Documents/GitHub/gen3schemadev
COMPOSE_SERVICES_INSTALLATION=${HOME}/Documents/GitHub/uwe-compose-services/compose-services
projects=("test1")
num_samples=10
gen3_profile=marion_acva

echo "removing old schemas"
rm ${UMCCR_SCHEMA_INSTALLATION}/dictionary/cad/gdcdictionary/schemas/*.yaml

echo "generating new schemas from google sheets"
cd ${SCHEMADEV_INSTALLATION}
source venv/bin/activate
python sheet2yaml.py
deactivate

echo "Schema generation complete."
echo "copying"
cp ${SCHEMADEV_INSTALLATION}/schema_out/*.yaml ${UMCCR_SCHEMA_INSTALLATION}/dictionary/cad/gdcdictionary/schemas/

echo "compiling"
cd ${UMCCR_SCHEMA_INSTALLATION}
make up
make test dd=cad project=sim samples=10
make validate dd=cad project=sim samples=10
make compile dd=cad project=sim samples=10
# make a small project for testing local setup
#make simulate dd=cad project=jenkins samples=10

for i in "${projects[@]}"; do
  echo $i
  make simulate dd=cad project=$i samples=$num_samples
done

cd ${UMCCR_SCHEMA_INSTALLATION}
make down

cd $CURRENT_DIR

echo "purging old schemas"
rm ${COMPOSE_SERVICES_INSTALLATION}/datadictionary/gdcdictionary/schemas/*.yaml

echo "copying"
cp ${SCHEMADEV_INSTALLATION}/schema_out/*.yaml ${COMPOSE_SERVICES_INSTALLATION}/datadictionary/gdcdictionary/schemas/

echo "Put the local json online in test directory"
aws s3 cp s3://biocommons-gen3-schema/marion-testing/cad.json s3://biocommons-gen3-schema/marion-testing/cad.json.old
aws s3 cp ${UMCCR_SCHEMA_INSTALLATION}/schema/cad.json s3://biocommons-gen3-schema/marion-testing/cad.json

echo "Making the schema.json public"
aws s3api put-object-acl --bucket biocommons-gen3-schema --key marion-testing/cad.json --acl public-read

echo "Restarting local instance"
cd ${COMPOSE_SERVICES_INSTALLATION}
docker-compose down
docker volume rm compose-services_psqldata
docker-compose up -d

echo "Now is the time to relax, and take a deep breath and checking it is all okay on your local development environment."
echo "if you press enter the ONLINE system will receive a new json"
echo "make sure it is all good!!!"
read

echo "save the current json as json.old"
aws s3 cp s3://biocommons-gen3-schema/cad/dev/cad.json s3://biocommons-gen3-schema/cad/dev/cad.json.old

echo "Put the local json online"
aws s3 cp ${UMCCR_SCHEMA_INSTALLATION}/schema/cad.json s3://biocommons-gen3-schema/cad/dev/cad.json

echo "Making the schema.json public"
aws s3api put-object-acl --bucket biocommons-gen3-schema --key cad/dev/cad.json --acl public-read

echo "Now login to management ec2, reset the deployment, get new credentials, re-configure the client on the data simulation ec2, come back and continue when you are ready to run the datas_submittor.py."
read

echo "starting up the ec2"
aws ec2 start-instances --instance-ids i-001632cdd600d853d
while [ "$(aws ec2 describe-instances --instance-ids i-001632cdd600d853d | jq -r '.Reservations[].Instances[].State.Name')" != "running" ]; do
	echo "Waiting for machine to start"
	sleep 1
done

#ec2_home=`aws ec2 describe-instances --instance-ids i-001632cdd600d853d | jq -r ".Reservations[].Instances[].PublicDnsName"`

ec2_home="ec2-13-210-31-82.ap-southeast-2.compute.amazonaws.com"

for i in "${projects[@]}"; do
  echo "copying metadata jsons to ec2 for project "$i
  scp -r -i ${HOME}/.ssh/gen3-management.pem ${UMCCR_SCHEMA_INSTALLATION}/data/cad/$i ubuntu@$ec2_home:~/data/cad
done

for project in "${projects[@]}"; do
  echo "Substituting metadata values and uploading metadata and files to the portal for project "$project
  export this_project=$project
	ssh -i ${HOME}/.ssh/gen3-management.pem ubuntu@$ec2_home "source ~/.bash_profile; cd ~/data/cad/$this_project; python3 ~/gen3schemadev/plausible_data_gen.py --gurl https://docs.google.com/spreadsheets/d/1AX9HLzIV6wtkVylLkwOr3kdKDaZf4ukeYACTJ7lYngk/edit#gid=1400179124 --path . --dummy-seq-files --dummy-lipid-files ; python3 ~/gen3schemadev/datas_submittor.py --folder ~/data/cad --projects $this_project --profile $gen3_profile ; rm -r ~/data/cad/$this_project/dummy_files"
done

echo "data and metadata uploaded."

echo "shutting down ec2"
aws ec2 stop-instances --instance-ids i-001632cdd600d853d
while [ "$(aws ec2 describe-instances --instance-ids i-001632cdd600d853d | jq -r '.Reservations[].Instances[].State.Name')" != "stopped" ]; do
	echo "Waiting for shutdown"
	sleep 1
done

echo "ec2 shutdown completed."
