import socket
import boto3
import time
import sys
import os
from dotenv import load_dotenv

# 1. Load environment variables from .env file
load_dotenv(override=True)

# --- Configuration ---
# We fetch variables from the environment now.
# The second argument in getenv is a default value if the key is missing.
INSTANCE_ID = os.getenv("EC2_INSTANCE_ID")
REGION = os.getenv("AWS_DEFAULT_REGION")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Convert port to integer; default to 9000 if not set
try:
    TARGET_PORT = int(os.getenv("TARGET_PORT", 9000))
except ValueError:
    print("❌ Error: TARGET_PORT in .env must be a number.")
    sys.exit(1)

# Validation: Ensure critical variables exist
if not INSTANCE_ID:
    print("❌ Error: EC2_INSTANCE_ID is missing from .env file.")
    sys.exit(1)
# ---------------------

def check_connection(ip, port, timeout=3):
    """
    Tries to open a TCP connection to ip:port. 
    Returns True if successful, False otherwise.
    """
    if not ip:
        return False
        
    print(f"Testing connection to {ip}:{port}...")
    try:
        # AF_INET = IPv4, SOCK_STREAM = TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex((ip, port))
            if result == 0:
                print(f"✅ Success! {ip}:{port} is reachable.")
                return True
            else:
                return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

def get_instance_info(ec2_client, instance_id):
    """
    Fetches the current state and Public IP of the instance.
    """
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        
        state = instance['State']['Name']
        # PublicIpAddress might not exist if instance is stopped or private
        public_ip = instance.get('PublicIpAddress', None) 
        
        return state, public_ip
    except Exception as e:
        print(f"❌ Error fetching instance info: {e}")
        sys.exit(1)

def main():
    # Initialize AWS Client
    # Boto3 automatically picks up AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY 
    # from the environment (loaded by load_dotenv)
    try:
        ec2 = boto3.client(
            'ec2',
            region_name=REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
    except Exception as e:
        print(f"❌ Failed to initialize AWS client. Check your credentials in .env.\nError: {e}")
        sys.exit(1)

    # 1. Get current IP and Status first
    print("--- Checking Status ---")
    current_state, current_ip = get_instance_info(ec2, INSTANCE_ID)
    print(f"Instance State: {current_state}")
    print(f"Current Public IP: {current_ip}")

    # 2. Check if the service is ALREADY working
    if current_state == 'running' and current_ip:
        if check_connection(current_ip, TARGET_PORT):
            print("System is already up and running. Exiting.")
            return

    print(f"⚠️  Service on {current_ip}:{TARGET_PORT} not reachable.")

    # 3. Check if EC2 needs starting
    if current_state in ['stopped', 'stopping']:
        print(f"Instance is {current_state}. Starting it now...")
        
        try:
            ec2.start_instances(InstanceIds=[INSTANCE_ID])
            
            # Wait for it to be 'running'
            print("Waiting for instance to enter 'running' state...")
            waiter = ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[INSTANCE_ID])
            print("Instance is now running!")
            
            # RE-FETCH IP because it likely changed (unless using Elastic IP)
            current_state, current_ip = get_instance_info(ec2, INSTANCE_ID)
            print(f"New Public IP assigned: {current_ip}")
            
        except Exception as e:
            print(f"❌ Failed to start instance: {e}")
            sys.exit(1)

    elif current_state == 'pending':
        print("Instance is pending. Waiting for it to run...")
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[INSTANCE_ID])
        current_state, current_ip = get_instance_info(ec2, INSTANCE_ID)

    # 4. Wait for the application to start inside the EC2
    if not current_ip:
        print("❌ Error: Instance is running but has no Public IP. Check AWS settings.")
        return

    print(f"--- Waiting for service on {current_ip}:{TARGET_PORT} to come online ---")
    print("(This might take a minute while the application boots up...)")
    
    # Try 20 times, waiting 5 seconds between tries
    for i in range(20):
        if check_connection(current_ip, TARGET_PORT):
            print("\n🎉 SUCCESS: Application is running and accessible!")
            print(f"URL: http://{current_ip}:{TARGET_PORT}")
            return
        
        time.sleep(5)
        print(".", end="", flush=True)

    print("\n❌ Timeout: EC2 is running, but port 9000 is still not open.")
    print("Check if the application crashed or if the Security Group allows traffic on port 9000.")

if __name__ == "__main__":
    main()