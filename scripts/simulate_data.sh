UMCCR_SCHEMA_INSTALLATION=${HOME}/Documents/Biocommons/Gen3/src/umccr-dictionary
DATA_SIMULATOR_INSTALLATION=${HOME}/Documents/Biocommons/Gen3/src/plausible_data_gen
projects="AusDiab FIELD BioHEART-CT"

CURRENT_DIR=`pwd`

cd $UMCCR_SCHEMA_INSTALLATION

make up

for i in $projects; do
	echo make dd=cad project=$i samples=1000
	make simulate dd=cad project=$i samples=1000
	cd data/cad/$i
	python3 ${DATA_SIMULATOR_INSTALLATION}/main.py --gurl https://docs.google.com/spreadsheets/d/1AX9HLzIV6wtkVylLkwOr3kdKDaZf4ukeYACTJ7lYngk/edit#gid=1400179124 --path .
	cd ../../..

done 

cd $CURRENT_DIR

