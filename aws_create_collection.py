import boto3
boto3.setup_default_session(profile_name='face')

def create_collection(collection_id):
    client = boto3.client('rekognition')

    # Create a collection
    print('Creating collection:' + collection_id)
    response = client.create_collection(CollectionId=collection_id)
    print('Collection ARN: ' + response['CollectionArn'])
    print('Status code: ' + str(response['StatusCode']))
    print('Done...')


def main():
    collection_id = 'collection_test'
    create_collection(collection_id)


if __name__ == "__main__":
    main()
