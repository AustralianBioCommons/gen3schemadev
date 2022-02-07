aws ec2 stop-instances --instance-ids i-001632cdd600d853d
while [ "$(aws ec2 describe-instances --instance-ids i-001632cdd600d853d | jq -r '.Reservations[].Instances[].PublicIpAddress')" != "null" ]; do 
	echo "Waiting for shutdown"
done
