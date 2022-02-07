aws ec2 start-instances --instance-ids i-001632cdd600d853d
while [ "$(aws ec2 describe-instances --instance-ids i-001632cdd600d853d | jq -r '.Reservations[].Instances[].PublicIpAddress')" = "null" ]; do 
	echo "Waiting for machine to start"
	sleep 1
done

aws ec2 describe-instances --instance-ids i-001632cdd600d853d | jq -r ".Reservations[].Instances[].PublicIpAddress"
