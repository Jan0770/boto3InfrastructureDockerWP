# This boto3 code sets up the required infrastructure and resources for hosting a wordpress Docker image
# Resources include VPC, IGW, security groups and an EC2
# The shell script runs the wordpress image on the provided instance

# import of boto3 SDK
import boto3

# create_infrastructure() makes use of a try/except block for error handling

def create_infrastructure():
        
    try:    
        region = 'us-west-2'

        # For more control during resource definition, boto3.client is used.
        ec2 = boto3.client('ec2', region_name=region) 

        vpc = ec2.create_vpc(
            CidrBlock='10.0.0.0/16'
        )

        vpc_id = vpc['Vpc']['VpcId']

        ec2.create_tags(
            Resources=[vpc['Vpc']['VpcId']], 
            Tags=[{'Key': 'Name', 'Value': 'dockerVPC'}]
        )

        ig = ec2.create_internet_gateway()

        ec2.attach_internet_gateway(
            InternetGatewayId=ig['InternetGateway']['InternetGatewayId'], 
            VpcId=vpc_id
        )

        # Creating two security groups, one for SSH ingress, one for HTTP egress
        sg_ssh_inbound = ec2.create_security_group(
            Description='Allow inbound SSH traffic', 
            GroupName='ssh-ingress', 
            VpcId=vpc_id
        )

        ec2.authorize_security_group_ingress(
            GroupId=sg_ssh_inbound['GroupId'], 
            IpPermissions=[{
                'FromPort': 22, 
                'IpProtocol': 'tcp', 
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}], 
                'ToPort': 22
            }]
        )

        sg_http_outbound = ec2.create_security_group(
            Description='Allow outbound HTTP traffic',
            GroupName='http-egress',
            VpcId=vpc_id
        )

        ec2.authorize_security_group_egress(
            GroupId=sg_http_outbound['GroupId'],
            IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }]
        )

        subnet = ec2.create_subnet(
            TagSpecifications=[{
                'ResourceType': 'subnet', 
                'Tags': [{'Key': 'Name', 'Value': 'dockersubnet'}]
            }], 
            CidrBlock='10.0.1.0/24', 
            AvailabilityZone=region + "a", 
            VpcId=vpc_id
        )

        # Switching to boto3.resource for simple setup of the EC2
        ec2resource = boto3.resource('ec2', region_name=region)

        # Opening and reading the shell script, provided as variable for further usage
        # The shell script needs to be available in the same directory
        # Elsewise, refactor the filepath as needed
        with open("dockerWPuserdata.sh", "r") as f:
            dockerWPuserdata = f.read()

        # The attributes for the instace are configured to provide a public IP on launch. See NetworkInterfaces
        instance = ec2resource.create_instances(
            ImageId="ami-0747e613a2a1ff483", 
            InstanceType="t2.micro", 
            SubnetId=subnet['Subnet']['SubnetId'], 
            SecurityGroupIds=[sg_ssh_inbound['GroupId'], sg_http_outbound['GroupId']], 
            KeyName="vockey",
            NetworkInterfaces=[{
                "SubnetId": subnet['Subnet']['SubnetId'], 
                "AssociatePublicIpAddress": True,
                "DeviceIndex": 0
            }],
            MinCount=1, 
            MaxCount=1, 
            TagSpecifications=[{
                'ResourceType': 'instance', 
                'Tags': [{'Key': 'Name', 'Value': 'wp-instance'}]
            }],
            UserData=dockerWPuserdata
        )

        # The following code waits for the instance to run and reloads the instance object returned by create_instance()
        # The public IP is then assigned to a variable for further use
        instance[0].wait_until_running()
        instance[0].reload()
        public_ip = instance[0].public_ip_address


        # A conformation that the script ran successfully, an overview of the EC2 and VPC
        print("Successfully build the infrastructure.\n"
              "Public IP: " + public_ip + "\n"
              "Instance: \n" + instance + "\n"
              "VPC: \n" + vpc + "\n"
        )

    # If the try block throws an error, the following code will catch that and print it to the console
    # Additionally, if a VPC or instance was set up during the failed build attempt, those will be deleted
    except Exception as e:
        print("Infrastructure build failed: \n\n" + str(e) + "\n\n"
            "Already created VPC and instance within the failed build will be deleted"      
        )

        ec2.delete_vpc(
            VpcId=vpc_id
        )
        
        instance[0].terminate()

create_infrastructure()