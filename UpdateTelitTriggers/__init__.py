import logging
import json
import requests
import re
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    requestJson = json.loads(req.get_json())
    telitApiEndpoint = "https://api.devicewise.com/api"
    triggerNameRegexPattern = "^TEMEDA_.*_FORWARD$"
    telitUsername = requestJson["telitUsername"]
    telitPassword = requestJson["telitPassword"]
    try:
        if requestJson.has_key("actions"):
            if requestJson.has_key("propertyKey"):
                propertyKey = requestJson["propertyKey"]
                if type(propertyKey) == type('a'):
                    
                        authObject = {}
                        authObject.update({ "auth" : { "command" : "api.authenticate", "params": { "username" : telitUsername, "password" : telitPassword }}})

                        authJson = json.dumps(authObject)
                        authResponse = requests.post(url=telitApiEndpoint,data=authJson)

                        if authResponse.ok:
                            
                                lookupObject = {}
                                lookupObject.update({ "auth" : { "sessionId" : authResponse.json()["auth"]["params"]["sessionId"] }})
                                lookupObject.update({ "cmd" : { "command" : "trigger.find", "params" : { "name" : f"TEMEDA_{propertyKey}_FORWARD" }}})

                                lookupJson = json.dumps(lookupObject)
                                lookupResponse = requests.post(url=telitApiEndpoint,data=lookupJson)

                                if lookupResponse.ok:

                                        updateObject = {}
                                        updateObject.update({ "auth" : { "sessionId" : authResponse.json()["auth"]["params"]["sessionId"] }})
                                        updateObject.update({ "cmd" : { "command" : "trigger.update", "params" : { "id" : lookupResponse.json()["cmd"]["params"]["id"], "actions" : requestJson["actions"] }}})

                                        updateJson = json.dumps(updateObject)
                                        updateResponse = requests.post(url=telitApiEndpoint,data=updateJson)
                                        
                                        if updateResponse.ok:
                                            return func.HttpResponse(body = f"Telit trigger TEMEDA_{propertyKey}_FORWARD updated successfuly. (id={lookupResponse.json()['cmd']['params']['id']})",status_code = 200)
                                        
                                        else:
                                            return func.HttpResponse(body = f"{json.dumps(updateResponse.json())}",status_code = 400)
                                
                                else:
                                    return func.HttpResponse(body = f"{json.dumps(updateResponse.json())}",status_code = 400)

                        else:
                            return func.HttpResponse(body = f"{json.dumps(updateResponse.json())}",status_code = 401)
                
                else:
                    return func.HttpResponse(body = "Property key must be a valid string.",status_code = 400)

            else:
                authObject = {}
                authObject.update({ "auth" : { "command" : "api.authenticate", "params": { "username" : telitUsername, "password" : telitPassword }}})

                authJson = json.dumps(authObject)
                authResponse = requests.post(url=telitApiEndpoint,data=authJson)

                if authResponse.ok:
                        lookupObject = {}
                        lookupObject.update({ "auth" : { "sessionId" : authResponse.json()["auth"]["params"]["sessionId"] }})
                        lookupObject.update({ "cmd" : { "command" : "trigger.list" }})

                        lookupJson = json.dumps(lookupObject)
                        lookupResponse = requests.post(url=telitApiEndpoint,data=lookupJson)

                        if lookupResponse.ok:
                            responseBody = ""
                            for trigger in lookupResponse.json()["cmd"]["params"]["result"]:
                                if re.match(pattern=triggerNameRegexPattern,string=trigger["name"]) != None:
                                        updateObject = {}
                                        updateObject.update({ "auth" : { "sessionId" : authResponse.json()["auth"]["params"]["sessionId"] }})
                                        updateObject.update({ "cmd" : { "command" : "trigger.update", "params" : { "id" : trigger["id"], "actions" : requestJson["actions"] }}})

                                        updateJson = json.dumps(updateObject)
                                        updateResponse = requests.post(url=telitApiEndpoint,data=updateJson)
                                        
                                        if updateResponse.ok:
                                            responseBody += f"Telit trigger {trigger['name']} updated successfuly. (id={trigger['id']})\n"
                                        
                                        else:
                                            return func.HttpResponse(body = f"{json.dumps(updateResponse.json())}",status_code = 400)

                            return func.HttpResponse(body=responseBody,status_code=200)

                        else:
                            return func.HttpResponse(body = f"{json.dumps(updateResponse.json())}",status_code = 400)

                else:
                    return func.HttpResponse(body = f"{json.dumps(updateResponse.json())}",status_code = 401)
    except ValueError as exception:
        return func.HttpResponse(body = f"{exception}",status_code = 500)