
import requests

class MAPI_BASEURL:
    baseURL = "https://moa-engineers.midasit.com:443/civil"
    
    def __init__(self, baseURL:str = "https://moa-engineers.midasit.com:443/civil"):
        ''' Define the Base URL for API connection.
        ```
        MAPI_BASEURL('https://moa-engineers.midasit.com:443/civil')
        ```
        '''
        MAPI_BASEURL.baseURL = baseURL
        

  
class MAPI_KEY:
    """MAPI key from Civil NX.\n\nEg: MAPI_Key("eadsfjaks568wqehhf.ajkgj345qfhh")"""
    data = ""
    
    def __init__(self, mapi_key:str):
        MAPI_KEY.data = mapi_key
        
#---------------------------------------------------------------------------------------------------------------

#2 midas API link code:
def MidasAPI(method:str, command:str, body:dict={})->dict:
    f"""Sends HTTP Request to MIDAS Civil NX
            Parameters:
                Method: "PUT" , "POST" , "GET" or "DELETE"
                Command: eg. "/db/NODE"
                Body: {{"Assign":{{1{{'X':0, 'Y':0, 'Z':0}}}}}}            
            Examples:
                ```python
                # Create a node
                MidasAPI("PUT","/db/NODE",{{"Assign":{{"1":{{'X':0, 'Y':0, 'Z':0}}}}}})"""
    
    base_url = MAPI_BASEURL.baseURL
    mapi_key = MAPI_KEY.data

    url = base_url + command
    headers = {
        "Content-Type": "application/json",
        "MAPI-Key": mapi_key
    }

    if method == "POST":
        response = requests.post(url=url, headers=headers, json=body)
    elif method == "PUT":
        response = requests.put(url=url, headers=headers, json=body)
    elif method == "GET":
        response = requests.get(url=url, headers=headers)
    elif method == "DELETE":
        response = requests.delete(url=url, headers=headers)


    return response.json()


#--------------------------------------------------------------------

def _getUNIT():
    return MidasAPI('GET','/db/UNIT',{})['UNIT']['1']

def _setUNIT(unitJS):
    js = {
        "Assign" : {
            "1" : unitJS
        }
    }
    MidasAPI('PUT','/db/UNIT',js)
