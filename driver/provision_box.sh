#!/bin/bash
set -e
NAME="$1"
REGION=us-west-2; AMI=ami-00563078bca04e287; ITYPE=m7i.xlarge; VPC=vpc-02c2ac734b774000f
TS=$(date +%s%N | tail -c 7); KEY=sweb-$NAME-$TS; SG_NAME=sweb-$NAME-$TS; PEM=/tmp/${KEY}.pem
ENVF=/tmp/${NAME}.env
aws ec2 create-key-pair --key-name $KEY --query KeyMaterial --output text --region $REGION > $PEM
chmod 400 $PEM
MYIP=$(curl -s https://checkip.amazonaws.com)
SG=$(aws ec2 create-security-group --group-name $SG_NAME --description "$NAME" --vpc-id $VPC --query GroupId --output text --region $REGION)
aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 22 --cidr ${MYIP}/32 --region $REGION >/dev/null
IID=$(aws ec2 run-instances --image-id $AMI --instance-type $ITYPE --key-name $KEY \
  --security-group-ids $SG --count 1 --instance-initiated-shutdown-behavior terminate \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":50,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME}]" \
  --query "Instances[0].InstanceId" --output text --region $REGION)
aws ec2 wait instance-running --instance-ids $IID --region $REGION
IP=$(aws ec2 describe-instances --instance-ids $IID --query "Reservations[0].Instances[0].PublicIpAddress" --output text --region $REGION)
printf "KEY=%s\nPUBIP=%s\nIID=%s\nSG=%s\nREGION=%s\n" "$KEY" "$IP" "$IID" "$SG" "$REGION" > $ENVF
ssh_cmd() { ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i $PEM ec2-user@$IP "$@"; }
for i in $(seq 40); do ssh_cmd "echo up" 2>/dev/null && break || sleep 5; done
ssh_cmd "sudo shutdown -h +180 || true; sudo dnf install -y -q docker 2>/dev/null; sudo systemctl enable --now docker 2>/dev/null; sudo usermod -aG docker ec2-user; echo BOOTSTRAPPED $NAME" >/dev/null 2>&1
echo "READY $NAME $IP"
