import logging
import json
import io
import re
import requests
import numpy as np
import azure.functions as func
from io import BytesIO
from uuid import uuid1
from PIL import Image
from azure.storage.blob import BlockBlobService
from azure.keyvault import KeyVaultClient
from azure.cosmos.cosmos_client import CosmosClient
from azure.mgmt.resource import ResourceManagementClient
from msrestazure.azure_active_directory import MSIAuthentication

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    # Establish some static values and placeholders:
    repositoryUrl = "https://github.com/gah112/25DaysOfServerless/master"
    keyVaultUrl = "https://examplekeyvault.vault.azure.net/"
    azureSubscriptionId = "166427d0-d7e5-4c8b-9ff5-1217190cb845"
    azureStorageContainerName = "github-commit-images"
    azureCosmosDatabaseName = "ServerlessExamples"
    azureCosmosCollectionName = "collection01"
    filePathPattern = "^.*\.png$"
    authenticatedFlag = False

    try:
        # Create a placeholder dictionary for the output object:
        databaseObject = {}

        # Deserialize the request body:
        requestBody = json.loads(req.get_json())

        for commit in requestBody["commits"]:
            for committedFile in commit["files"]:
                
                # Check to see if the file has a .png extension using regex:
                if re.match(filePathPattern,committedFile["filename"]):
                    
                    # Get some data from the commit:
                    databaseObject.update({"githubCommitSha" : commit["sha"]})
                    databaseObject.update({"githubCommitUrl" : commit["url"]})
                    databaseObject.update({"githubNodeId" : commit["node_id"]})
                    databaseObject.update({"githubCommitDate" : commit["committer"]["date"]})
                    databaseObject.update({"githubCommitterName" : commit["committer"]["name"]})
                    databaseObject.update({"githubCommitterEmailAddress" : commit["committer"]["email"]})
                    databaseObject.update({"githubCommitMessage" : commit["message"]})

                    # Get some data from the file:
                    databaseObject.update({"githubFileName" : committedFile["filename"]})
                    databaseObject.update({"githubFileStatus" : committedFile["status"]})
                    databaseObject.update({"githubFileAdditionsCount" : committedFile["additions"]})
                    databaseObject.update({"githubFileDeltionsCount" : committedFile["deletions"]})
                    databaseObject.update({"githubFileChangesCount" : committedFile["changes"]})
                    databaseObject.update({"githubFileRawUrl" : committedFile["raw_url"]})

                    # Parse the image into a pixel array:
                    imageRequest = requests.get(githubFileRawUrl)
                    imageContent = Image.open(BytesIO(imageRequest.content))
                    imageArray = np.array(imageContent)

                    # Store the pixel values in arrays in a dictionary:
                    pixelValues = {}
                    if imageArray.shape[2] > 2:
                        pixelValues.update({"r" : imageArray[:,:,0] })
                        pixelValues.update({"g" : imageArray[:,:,1] })
                        pixelValues.update({"b" : imageArray[:,:,2] })
                        
                        if imageArray.shape[2] > 3:
                            pixelValues.update({"a" : imageArray[:,:,3] })

                    # Add the dictionary to the output object:
                    databaseObject.update({"pixelValues" : pixelValues})

                    if not(authenticatedFlag):

                        # Create the MSI Authentication:
                        msiAuthenticationCredentials = MSIAuthentication()

                        # Create the Key Vault Client:
                        keyVaultClient = KeyVaultClient(msiAuthenticationCredentials)

                        # Set the authenticated flag:
                        authenticatedFlag = True
                    
                    # Get the connection string for the Azure Storage Account:
                    blobConnectionStringSecretBundle = keyVaultClient.get_secret(keyVaultUrl,"serverlessexamples-azure-storage-connection-string")
                    
                    # Create the Block Blob Service:
                    blockBlobService = BlockBlobService(connection_string = blobConnectionStringSecretBundle.value)

                    # Write the image from github to Azure Storage:
                    blobPath = f"images/{uuid1()}.png"
                    blockBlobService.copy_blob(azureStorageContainerName,blobPath,githubFileRawUrl)

                    # Get the URL of the image in Azure Storage:
                    blobUrl = blockBlobService.make_blob_url(azureStorageContainerName,blobPath)

                    # Add the Azure Storage URL to the output object:
                    databaseObject.update({"azureStorageUrl" : blobUrl})

                    # Add some other fields to the output object:
                    databaseObject.update({"documentType" : "GithubCommitImage"})
                    databaseObject.update({"partitionKey" : "GithubCommitImages"})

                    # Create the Cosmos DB Client:
                    cosmosUrlSecretBundle = keyVaultClient.get_secret(keyVaultUrl,"serverlessexamples-azure-cosmosdb-url")
                    cosmosUrl = secretBundle.value
                    cosmosKeySecretBundle = keyVaultClient.get_secret(keyVaultUrl,"serverlessexamples-azure-cosmosdb-key")
                    cosmosKey = secretBundle.value
                    cosmosClient = cosmos_client.CosmosClient(url_connection = cosmosUrl,auth = { 'masterKey': cosmosKey })

                    # Write the JSON to Azure Cosmos DB:
                    cosmosClient.CreateItem(f"dbs/{azureCosmosDatabaseName}/colls/{azureCosmosCollectionName}/",document = databaseObject)

        return func.HttpResponse(body = "Successfully processed request!",status_code = 200)

    except Exception as error:
        return func.HttpResponse(body = f"{error}",status_code = 500)