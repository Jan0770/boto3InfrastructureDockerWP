# This boto3 code sets up the required infrastructure and resources for hosting a wordpress Docker image
# Resources include VPC, IGW, security groups and an EC2
# The shell script runs the wordpress image on the provided instance


import boto3

# create_infrastructure() makes use of a try/except block for error handling

def create_infrastructure():

    try:    
        region = 'us-west-2'

        # For more control during resource definition, boto3.client is used.
        ec2 = boto3.client('ec2', region_name=region) 

        # Setting up a VPC, one subnet, IGW, and a route table with the required association
        vpc = ec2.create_vpc(
            CidrBlock='10.0.0.0/16',
            TagSpecifications=[{
                "ResourceType": "vpc",
                "Tags": [{'Key': 'Name', 'Value': 'dockerVPC'}]
            }]
        )
        vpc_id = vpc['Vpc']['VpcId']

        subnet = ec2.create_subnet(
            CidrBlock='10.0.1.0/24', 
            AvailabilityZone=region + "a", 
            VpcId=vpc_id,
            TagSpecifications=[{
                'ResourceType': 'subnet', 
                'Tags': [{'Key': 'Name', 'Value': 'dockersubnet'}]
            }]
        )
        subnet_id = subnet['Subnet']['SubnetId']

        igw = ec2.create_internet_gateway(
            TagSpecifications=[{
                 "ResourceType": "internet-gateway",
                 "Tags": [{'Key': 'Name', 'Value': 'dockerIGW'}]
            }]
        )
        igw_id = igw['InternetGateway']['InternetGatewayId']

        ec2.attach_internet_gateway(
            InternetGatewayId=igw_id, 
            VpcId=vpc_id,
        )

        route_table = ec2.create_route_table(VpcId=vpc_id)
        route_table_id = route_table["RouteTable"]["RouteTableId"]
     
        ec2.create_route(
            DestinationCidrBlock="0.0.0.0/0",
            GatewayId=igw_id,
            RouteTableId=route_table_id
        )

        ec2.associate_route_table(
            SubnetId=subnet_id,
            RouteTableId=route_table_id
        )

        # Creating two security groups, one for SSH ingress, one for HTTP traffic
        sg_ssh_inbound = ec2.create_security_group(
            Description='Allow inbound SSH traffic', 
            GroupName='ssh-ingress', 
            VpcId=vpc_id,
            TagSpecifications=[{
                "ResourceType": "security-group",
                "Tags": [{'Key': 'Name', 'Value': 'ssh_inbound'}]
            }]
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

        sg_http_traffic = ec2.create_security_group(
            Description='Allow HTTP traffic',
            GroupName='allow-http-traffic',
            VpcId=vpc_id,
            TagSpecifications=[{
                "ResourceType": "security-group",
                "Tags": [{'Key': 'Name', 'Value': 'allow_http_traffic'}]
            }]
        )

        ec2.authorize_security_group_egress(
            GroupId=sg_http_traffic['GroupId'],
            IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }]
        )

        ec2.authorize_security_group_ingress(
            GroupId=sg_http_traffic['GroupId'],
            IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }]
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
            KeyName="vockey",
            NetworkInterfaces=[{
                "DeviceIndex": 0,
                "AssociatePublicIpAddress": True,
                "SubnetId": subnet_id,
                "Groups": [sg_ssh_inbound['GroupId'], sg_http_traffic['GroupId']],
                "DeleteOnTermination": True 
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
        instance[0].wait_until_running()
        instance[0].reload()

        # A conformation that the script ran successfully
        print("Successfully build the infrastructure.")

    # If the try block throws an error, the following code will catch that and print the error message to the console
    # Additionally, resources set up during the failed build attempt will be terminated
    # Termination might throw errors itself, beware
    except Exception as e:
        print("Infrastructure build failed: \n\n" + str(e) + "\n\n"
            "Terminating resources..."      
        )
    
        instance[0].terminate()
        instance[0].wait_until_terminated()

        igw.detach_from_vpc(VpcId=vpc_id)
        igw.delete()
        ec2.delete_vpc(VpcId=vpc_id)
        
        print("Termination complete.")

create_infrastructure()