#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

import streamlit as st
import json
import logging
import os
import sys
import time
import requests
import dotenv
import time
import uuid

from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential
import requests

dotenv.load_dotenv()


st.set_page_config(page_title="Text to Speech Avatar Demo",layout="wide")
st.title("HR Assistant - RAG with Azure Text to Speech Avatar")
st.info("The HR Assistant will help answer HR policy and employee benefit queries from employees. "+
        "This demo application leverages Azure Text-to-Speech Avatar in RAG based application")
response_msg = ''

# Add Session State to refer response_message later
if 'response_msg' not in st.session_state:
    st.session_state['response_msg'] = response_msg

# Header Section
col1, col2, col3 = st.columns([1,1,1])

with col1:
    st.image("Designer.jpeg")

with col2:
    st.header("User Query")
    user_message=st.text_input("Type your query here")
    submit_button = st.button('Submit Query')
    llm_output_message = st.empty()
    llm_output_message.text_area(label ="Search Response (using GPT-4o)",value='', height =300)

    
    if submit_button:
        
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("DEPLOYMENT_NAME")
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        search_key = os.getenv("AZURE_SEARCH_KEY")
        search_index = os.getenv("AZURE_SEARCH_INDEX")
        subscription_key = os.getenv("AZURE_OPENAI_API_KEY")

        # Initialize Azure OpenAI client with key-based authentication
        client = AzureOpenAI(
        azure_endpoint = endpoint,
        api_key = subscription_key,
        api_version = "2024-05-01-preview")

        llm_output_message.text_area(label ="Search Response (using GPT-4o)",value='Output is being generated...', height =300)

        message_text = [{"role":"system","content":"You are an AI assistant who responds to user queries based the data provided. Make the response easy to be narrated in a natural language. Please don't mention the citation or document reference in your response"},{"role": "user", "content": user_message}]

        completion = client.chat.completions.create(
            model=deployment,
            messages= message_text,
            max_tokens=800,
            temperature=0.3,
            top_p=0.95,
            stream=False
        ,
            extra_body={
            "data_sources": [{
                "type": "azure_search",
                "parameters": {
                  "endpoint": f"{search_endpoint}",
                  "index_name": "gptkbindex",
                  "semantic_configuration": "default",
                  "query_type": "vector_semantic_hybrid",
                  "fields_mapping": {},
                  "in_scope": True,
                  "role_information": "You are an AI assistant that helps people find information.",
                  "filter": None,
                  "strictness": 3,
                  "top_n_documents": 5,
                  "authentication": {
                    "type": "api_key",
                    "key": f"{search_key}"
                  },
                  "embedding_dependency": {
                    "type": "deployment_name",
                    "deployment_name": "embedding"
                  }
                }
              }]
            })
   
        response_msg= completion.choices[0].message.content
        llm_output_message.text_area(label ="Search Response (using GPT-4o)",value=response_msg, height =300)

        # Store ChatGPT response in session_state variable
        st.session_state.response_msg = response_msg

with col3:
   
   st.header("Generated Video Avatar")
   avatar_message = st.empty()
   avatar_message.text_area(label ="HR Avatar Response",value='', height =50)
   
   logging.basicConfig(stream=sys.stdout, level=logging.INFO,  # set to logging.DEBUG for verbose output
       format="[%(asctime)s] %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p %Z")
   logger = logging.getLogger(__name__)

   # The endpoint (and key) could be gotten from the Keys and Endpoint page in the Speech service resource.
   # The endpoint would be like: https://<region>.api.cognitive.microsoft.com or https://<custom_domain>.cognitiveservices.azure.com
   # If you want to use passwordless authentication, custom domain is required.
   SPEECH_ENDPOINT = os.getenv("AZURE_SPEECH_ENDPOINT")
   # We recommend to use passwordless authentication with Azure Identity here; meanwhile, you can also use a subscription key instead
   PASSWORDLESS_AUTHENTICATION = False
   API_VERSION = "2024-04-15-preview"

   llm_reponse=st.session_state.response_msg

   def _create_job_id():
       # the job ID must be unique in current speech resource
       # you can use a GUID or a self-increasing number
       return uuid.uuid4()


   def _authenticate():
       if PASSWORDLESS_AUTHENTICATION:
           # Refer to https://learn.microsoft.com/python/api/overview/azure/identity-readme?view=azure-python#defaultazurecredential
           # for more information about Azure Identity
           # For example, your app can authenticate using your Azure CLI sign-in credentials with when developing locally.
           # Your app can then use a managed identity once it has been deployed to Azure. No code changes are required for this transition.

           # When developing locally, make sure that the user account that is accessing batch avatar synthesis has the right permission.
           # You'll need Cognitive Services User or Cognitive Services Speech User role to submit batch avatar synthesis jobs.
           credential = DefaultAzureCredential()
           token = credential.get_token('https://cognitiveservices.azure.com/.default')
           return {'Authorization': f'Bearer {token.token}'}
       else:
           SUBSCRIPTION_KEY = os.getenv("AZURE_SPEECH_KEY")
           return {'Ocp-Apim-Subscription-Key': SUBSCRIPTION_KEY}


   def submit_synthesis(job_id: str):
       url = f'{SPEECH_ENDPOINT}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}'
       header = {
           'Content-Type': 'application/json'
       }
       header.update(_authenticate())
       isCustomized = False

       payload = {
           'synthesisConfig': {
               "voice": 'en-US-JennyMultilingualNeural',
           },
           # Replace with your custom voice name and deployment ID if you want to use custom voice.
           # Multiple voices are supported, the mixture of custom voices and platform voices is allowed.
           # Invalid voice name or deployment ID will be rejected.
           'customVoices': {
               # "YOUR_CUSTOM_VOICE_NAME": "YOUR_CUSTOM_VOICE_ID"
           },
           "inputKind": "plainText",
           "inputs": [
               {
                   "content": llm_reponse,
               },
           ],
           "avatarConfig":
            {
               "customized": isCustomized, # set to True if you want to use customized avatar
               "talkingAvatarCharacter": 'Lisa-casual-sitting',  # talking avatar character
               "videoFormat": "mp4",  # mp4 or webm, webm is required for transparent background
               "videoCodec": "h264",  # hevc, h264 or vp9, vp9 is required for transparent background; default is hevc
               "subtitleType": "soft_embedded",
               "backgroundColor": "#FFFFFFFF", # background color in RGBA format, default is white; can be set to 'transparent' for transparent background
               # "backgroundImage": "https://samples-files.com/samples/Images/jpg/1920-1080-sample.jpg", # background image URL, only support https, either backgroundImage or backgroundColor can be set
           }
           if isCustomized
           else 
           {
             "customized": isCustomized, # set to True if you want to use customized avatar
             "talkingAvatarCharacter": 'Lisa',  # talking avatar character
             "talkingAvatarStyle": 'casual-sitting',  # talking avatar style, required for prebuilt avatar, optional for custom avatar
             "videoFormat": "mp4",  # mp4 or webm, webm is required for transparent background
             "videoCodec": "h264",  # hevc, h264 or vp9, vp9 is required for transparent background; default is hevc
             "subtitleType": "soft_embedded",
             "backgroundColor": "#FFFFFFFF", # background color in RGBA format, default is white; can be set to 'transparent' for transparent background
             # "backgroundImage": "https://samples-files.com/samples/Images/jpg/1920-1080-sample.jpg", # background image URL, only support https, either backgroundImage or backgroundColor can be set
         }  
       }

       response = requests.put(url, json.dumps(payload), headers=header)
       if response.status_code < 400:
           logger.info('Batch avatar synthesis job submitted successfully')
           logger.info(f'Job ID: {response.json()["id"]}')
           avatar_message.text_area(label ="HR Avatar Response",value='HR Avatar is being generated...', height =50)
           return True
       else:
           logger.error(f'Failed to submit batch avatar synthesis job: [{response.status_code}], {response.text}')


   def get_synthesis(job_id):
       url = f'{SPEECH_ENDPOINT}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}'
       header = _authenticate()

       response = requests.get(url, headers=header)
       
       if response.status_code < 400:
           logger.debug('Get batch synthesis job successfully')
           logger.debug(response.json())
           if response.json()['status'] == 'Succeeded':
               logger.info(f'Batch synthesis job succeeded, download URL: {response.json()["outputs"]["result"]}')
               avatar_message.empty()
               st.video(response.json()["outputs"]["result"]) 
           return response.json()['status']
       else:
           logger.error(f'Failed to get batch synthesis job: {response.text}')


   def list_synthesis_jobs(skip: int = 0, max_page_size: int = 100):
       """List all batch synthesis jobs in the subscription"""
       url = f'{SPEECH_ENDPOINT}/avatar/batchsyntheses?api-version={API_VERSION}&skip={skip}&maxpagesize={max_page_size}'
       header = _authenticate()

       response = requests.get(url, headers=header)
       if response.status_code < 400:
           logger.info(f'List batch synthesis jobs successfully, got {len(response.json()["values"])} jobs')
           logger.info(response.json())
       else:
           logger.error(f'Failed to list batch synthesis jobs: {response.text}')


   if __name__ == '__main__':
       job_id = _create_job_id()
       if submit_synthesis(job_id):
           while True:
               status = get_synthesis(job_id)
               if status == 'Succeeded':
                   logger.info('batch avatar synthesis job succeeded')
                   break
               elif status == 'Failed':
                   logger.error('batch avatar synthesis job failed')
                   break
               else:
                   logger.info(f'batch avatar synthesis job is still running, status [{status}]')
                   time.sleep(5)