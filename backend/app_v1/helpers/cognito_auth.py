from cognito_identity_sdk import AWSCognitoIdentityProvider

# Configure AWS Cognito
region = 'us-east-1'  # Specify your region
client_id = 'your-client-id'  # Replace with your App Client ID
user_pool_id = 'your-user-pool-id'  # Replace with your User Pool ID

provider = AWSCognitoIdentityProvider(
    client_id=client_id,
    user_pool_id=user_pool_id,
    region_name=region
)

# Function to sign up a new user
def sign_up(email, password):
    attributes_data = {
        'email': email
    }
    response = provider.sign_up(
        Username=email,
        Password=password,
        UserAttributes=[{'Name': key, 'Value': value} for key, value in attributes_data.items()]
    )
    return response

# Example usage
sign_up_response = sign_up('example@example.com', 'SecurePassword123!')
print(sign_up_response)