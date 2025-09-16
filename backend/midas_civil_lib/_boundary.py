from ._mapi import *
from ._node import *
from ._group import *

def convList(item):
        if type(item)!=list:
            return [item]
        else:
            return item


# -----  Extend for list of nodes/elems -----

def _ADD_Support(self):
    if isinstance(self.NODE,int):
        Boundary.Support.sups.append(self)
    elif isinstance(self.NODE,list):
        for nID in self.NODE:
            Boundary.Support(nID,self.CONST,self.GROUP)


class Boundary:

    @classmethod
    def create(cls):
        """Creates Boundary elements in MIDAS Civil NX"""
        if cls.RigidLink.links!=[]: cls.RigidLink.create()

    
    @classmethod
    def delete(cls):
        """Delets Boundary elements from MIDAS Civil NX and Python"""

        cls.RigidLink.delete()

    @classmethod
    def sync(cls):
        """Sync Boundary elements from MIDAS Civil NX to Python"""

        cls.RigidLink.sync()


    #Class to define Rigid  Links:
    class RigidLink:

        links = []
        
        def __init__(self, 
                    master_node: int, 
                    slave_nodes: list, 
                    group: str = "", 
                    id: int = None, 
                    dof: int = 111111,):
            """
            Rigid link. 
            Parameters:
                master_node: The first node ID
                slave_nodes: The second node ID
                group: The group name (default "")
                id: The link ID (optional)
                dof: Fixity of link (default 111111)
            
            Examples:
                ```python
                # General link with all stiffness parameters
                RigidLink(1, [2,3], "Group1", 1, 111000)
                ```
            """

            # Check if group exists, create if not
            if group != "":
                chk = 0
                a = [v['NAME'] for v in Group.Boundary.json()["Assign"].values()]
                if group in a:
                    chk = 1
                if chk == 0:
                    Group.Boundary(group)
                    
            
            self.M_NODE = master_node
            self.S_NODE = convList(slave_nodes)
            self.GROUP_NAME = group
            self.DOF = dof

            # Auto-assign ID if not provided
            if id is None:
                self.ID = len(Boundary.RigidLink.links) + 1
            else:
                self.ID = id
                
            # Add to static list
            Boundary.RigidLink.links.append(self)
        

        @classmethod
        def json(cls):
            """
            Converts RigidLink data to JSON format for API submission.
            Example:
                # Get the JSON data for all links
                json_data = RigidLink.json()
                print(json_data)
            """
            json = {"Assign": {}}
            for link in cls.links:
                if link.M_NODE not in list(json["Assign"].keys()):
                    json["Assign"][link.M_NODE] = {"ITEMS": []}

                json["Assign"][link.M_NODE]["ITEMS"].append({
                    "ID": link.ID,
                    "GROUP_NAME": link.GROUP_NAME,
                    "DOF": link.DOF,
                    "S_NODE": convList(link.S_NODE),
                })
            return json
        
        @classmethod
        def create(cls):
            """
            Sends all RigidLink data to Midas API.
            Example:
                RigidLink(1, 2, "Group1", 1, "GEN", 1000, 1000, 1000, 100, 100, 100)
                # Send to the API
                RigidLink.create()
            """
            MidasAPI("PUT", "/db/RIGD", cls.json())
        
        @classmethod
        def get(cls):
            """
            Retrieves Rigid Link data from Midas API.
            Example:
                api_data = RigidLink.get()
                print(api_data)
            """
            return MidasAPI("GET", "/db/RIGD")
        
        @classmethod
        def sync(cls):
            """
            Updates the RigidLink class with data from the Midas API.
            Example:
                RigidLink.sync()
            """
            cls.links = []
            a = cls.get()
            if a != {'message': ''}:
                for i in a['RIGD'].keys():
                    for j in range(len(a['RIGD'][i]['ITEMS'])):
                        itm = a['RIGD'][i]['ITEMS'][j]
                        Boundary.RigidLink(int(i),itm['S_NODE'],itm['GROUP_NAME'],itm['ID'],itm['DOF'])
        
        @classmethod
        def delete(cls):
            """
            Deletes all rigid links from the database and resets the class.
            Example:
                ElasticLink.delete()
            """
            cls.links = []
            return MidasAPI("DELETE", "/db/RIGD")
    #---------------------------------------------------------------------------------------------------------------