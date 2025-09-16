import numpy as np
from .midas_civil_lib import *
import math
from scipy.interpolate import splev, splprep
from math import hypot


class L2P:
    mesh_size = 0.1

# 1. -------------     Getting selected elements, sorting the nodes, deleting the middle node    -------------------

# Takes in [[1,2] , [3,4] ,[2,3]] returns [1,2,3,4]
def arrangeNodeList(n_list,elm_list):
    ''' Return arranged Nodes list (1D) and Element list (1D)'''

    n_list_2 = n_list[1:]
    ord_list=[n_list[0]]

    e_list2 = elm_list[1:]
    e_ord_list=[elm_list[0]]


    add_pos = 1 # 1 => Last  | -1 => first
    flip_count=0

    def arrangeNode(ordList,n_list,add_pos,flip_count,elm_list,e_ord_list):
        
        for i in range(len(n_list)):
            if add_pos == 1:
                if ordList[-1][1] == n_list[i][0]:
                    ordList.append(n_list[i])
                    e_ord_list.append(elm_list[i])
                    del elm_list[i]
                    del n_list[i]
                    # print(f'Last add  | {ordList}')
                    return
            elif add_pos == -1:
                if ordList[0][0] == n_list[i][1]:
                    ordList.insert(0,n_list[i])
                    e_ord_list.insert(0,elm_list[i])
                    del n_list[i]
                    del elm_list[i]
                    # print(f'First add  | {ordList}')
                    return
                
        add_pos = add_pos*-1
        flip_count += 1
        # print(f'Flipped | {ordList} | {n_list} | {add_pos}')
        if flip_count == 1 : arrangeNode(ordList,n_list,add_pos,flip_count,elm_list,e_ord_list)
        


    for _ in range(len(n_list_2)):
        arrangeNode(ord_list,n_list_2,add_pos,flip_count,e_list2,e_ord_list)

    if len(ord_list) < len(n_list):
        print('⚠️  Element not in a single continuous line | Smaller segment is returned')
    
    simple_ord_list = [ord_list[0][0],ord_list[0][1]]
    for i in range(len(ord_list)-1):
        simple_ord_list.append(ord_list[i+1][1])

    return simple_ord_list, e_ord_list


# Returns sorted nodes and alignment coordinates for the selected elements
def delSelectElements():
    ''' 
        Deletes the middle nodes
        Returns sorted nodes and alignment coordinates for the selected elements
        Returns material ID of first element
        Returns sectID of each beam element
    '''


    node_json = MidasAPI('GET','/view/SELECT')
    align_elem_list = node_json['SELECT']['ELEM_LIST']

    if align_elem_list == []:
        raise Exception("No elements selected ☹️")
        return 0

    # print(f'{align_elem_list}')


    align_elem_list_url = ",".join(map(str, align_elem_list))
    align_elem_json = MidasAPI('GET',f'/db/ELEM/{align_elem_list_url}')

    align_nodes_list =[]
    align_elem_list=[]


    for elmID in align_elem_json['ELEM']:
        nodes = align_elem_json['ELEM'][elmID]['NODE']
        align_nodes_list.append([nodes[0],nodes[1]])
        align_elem_list.append(elmID)

    arrangeLIST, arrangeLIST_ELM = arrangeNodeList(align_nodes_list,align_elem_list)
    # print(arrangeLIST)


    matID = align_elem_json['ELEM'][arrangeLIST_ELM[0]]['MATL']

    sec_ID_list_arranged = []
    for elmID in arrangeLIST_ELM:
        sec_ID_list_arranged.append(align_elem_json['ELEM'][elmID]['SECT'])

    # align_nodes_list = sorted(align_nodes_list)
    align_nodes_list = arrangeLIST

    align_nodes_list_url = ",".join(map(str, align_nodes_list))
    node_json = MidasAPI('GET',f'/db/NODE/{align_nodes_list_url}')


    align_coordinates_list = [] 

    for nd in align_nodes_list:
        align_coordinates_list.append([ node_json['NODE'][str(nd)]['X'] , node_json['NODE'][str(nd)]['Y'] , node_json['NODE'][str(nd)]['Z'] ])

    k=3

    if len(align_nodes_list)==2:
        MidasAPI('DELETE',f'/db/ELEM/{arrangeLIST_ELM[0]}')
        k=1

    else:
        align_nodes_list_url = ",".join(map(str, align_nodes_list[1:-1]))
        MidasAPI('DELETE',f'/db/NODE/{align_nodes_list_url}')
        k=min(3,len(align_nodes_list)-1)


    beta_angle = [align_elem_json['ELEM'][str(arrangeLIST_ELM[0])]['ANGLE']*3.141/180]
    for i in range(len(align_nodes_list)-2):
        ba1 = align_elem_json['ELEM'][str(arrangeLIST_ELM[i])]['ANGLE']*3.141/180
        ba2 = align_elem_json['ELEM'][str(arrangeLIST_ELM[i+1])]['ANGLE']*3.141/180
        beta_angle.append(0.5*ba1+0.5*ba2)
    beta_angle.append(align_elem_json['ELEM'][str(arrangeLIST_ELM[-1])]['ANGLE']*3.141/180)





    return align_nodes_list, align_coordinates_list,  beta_angle , arrangeLIST_ELM , matID , sec_ID_list_arranged,k






# 2. -------------     PLATE SECTION DEFINITION - Creating a uniform section (beta angle)   -------------------




# Orient section as per plane
def _orientPoint(plane_ax,plane_og,coord):
    #Plane orient

    Y_new = np.array(plane_ax[1])
    Z_new = np.array(plane_ax[0])
    X_new = np.cross(Y_new, Z_new)

    Y_new = np.cross(Z_new, X_new) # Recomputing

    X_new = X_new / np.linalg.norm(X_new)
    Y_new = Y_new / np.linalg.norm(Y_new)
    Z_new = Z_new / np.linalg.norm(Z_new)

    # Rotation matrix: columns are new basis vectors in original system
    R = np.vstack((X_new, Y_new, Z_new))

    # Original coordinate
    n_3dCord = coord.copy()
    n_3dCord.append(0)
    v = np.array(n_3dCord)
    # Transform the vector to the new coordinate system
    p_rot = np.dot(R.T, v)


    # Origin transform
    new_cord = [ p_rot[0]+plane_og[0] , p_rot[1]+plane_og[1] , p_rot[2]+plane_og[2] ]
    return new_cord

# Create nodes
def _createSectNodes(section_cordinates,plane_axis,plane_origin,beta_ang=0):
    node_ids = []

    for cord in section_cordinates:

        X = cord[0]*math.cos(beta_ang) - cord[1]*math.sin(beta_ang)
        Y = cord[1]*math.cos(beta_ang) + cord[0]*math.sin(beta_ang)

        ord = _orientPoint(plane_axis,plane_origin,[X,Y])    # Cord is 2D ; ord is 3D
        node_ids.append(Node(ord[0],ord[1],ord[2]).ID)

    return node_ids


def _createTapSectPlate(section_cordinates1,section_cordinates2,sect_lineCon,thk_plate,thk_plate_off,start_plane_axis,start_plane_origin,start_beta_angle,end_plane_axis,end_plane_origin,end_beta_angle,matID):

    s_nodes = _createSectNodes(section_cordinates1,start_plane_axis,start_plane_origin,start_beta_angle)
    e_nodes = _createSectNodes(section_cordinates2,end_plane_axis,end_plane_origin,end_beta_angle)

    for i in range(len(sect_lineCon)):

        thick_id=isCreateThick(int(thk_plate[i]*40)/40,int(thk_plate_off[i]*100)/100)

        p_node = sect_lineCon[i][0]-1
        q_node = sect_lineCon[i][1]-1

        Element.Plate([s_nodes[p_node] , e_nodes[p_node] , e_nodes[q_node] , s_nodes[q_node]],3,int(matID),thick_id)

    return s_nodes, e_nodes



def createTapPlateAlign(align_points,t_param,beta_angle,Section4Plate,rigid_LNK = False,matID=99):
    ''' Alignment points = [ [0,0,0] , [10,1,0]  , [20,0,0], [30,1,0]],
    t_param = [0,0.1,0.2,0.3,0.5...] list used for tap section
     Local Z vector of section is assumed [0,0,1]
      Direction is assumed  '''
    
    align_num_points = len(align_points)

    align_x_vec = [np.subtract(align_points[1],align_points[0])]

    for i in range(align_num_points-2):
        align_x_vec.append(np.add(np.subtract(align_points[i+2],align_points[i+1]), np.subtract(align_points[i+1],align_points[i])))
    align_x_vec.append(np.subtract(align_points[-1],align_points[-2]))

    align_plane = [ [p, [0.0001,0,1]] for p in align_x_vec]


    for i in range(align_num_points-1):
        ti = t_param[i]
        tf = t_param[i+1]
        shp1 , thk1 , thk_off1= getTapShape(ti,Section4Plate)
        shp2, thk2, thk_off2 = getTapShape(tf,Section4Plate)

        thk_avg = np.multiply(np.add(thk1,thk2),0.5)
        thk_off_avg = np.multiply(np.add(thk_off1,thk_off2),0.5)
        snode,enode = _createTapSectPlate(shp1,shp2,Section4Plate.LINE,thk_avg,thk_off_avg,align_plane[i],align_points[i],beta_angle[i],align_plane[i+1],align_points[i+1],beta_angle[i+1],matID)

        if rigid_LNK:
            if i == 0 :
                beamnode = Node(align_points[0][0],align_points[0][1],align_points[0][2]).ID
                Boundary.RigidLink(beamnode,snode)
            elif i == align_num_points-2:
                beamnode = Node(align_points[-1][0],align_points[-1][1],align_points[-1][2]).ID
                Boundary.RigidLink(beamnode,enode)








# 3 . ------------------  Smooth Alignment creation ------------------

def interpolateAlignment(pointsArray,betaAngle,n_seg=10,deg=3,mSize=0):
    ''' Returns point list and beta angle list'''
    pointsArray = np.array(pointsArray)
    x_p, y_p , z_p  = pointsArray[:,0] , pointsArray[:,1] , pointsArray[:,2]
    ang_p = betaAngle


    #-- Actual length ----
    dxq = np.diff(x_p)
    dyq = np.diff(y_p)
    dzq = np.diff(z_p)
    dlq=[0]
    for i in range(len(dxq)):
        dlq.append(hypot(dxq[i],dyq[i],dzq[i]))

    tck, u = splprep([x_p, y_p, z_p, ang_p], s=0, k=deg)

    u_fine = np.linspace(0, 1, 500)
    x_den, y_den, z_den, ang_den = splev(u_fine, tck)

    dx = np.diff(x_den)
    dy = np.diff(y_den)
    dz = np.diff(z_den)
    dl=[]
    for i in range(len(dx)):
        dl.append(hypot(dx[i],dy[i],dz[i]))

    cum_l = np.insert(np.cumsum(dl),0,0)
    total_l = cum_l[-1]


    if n_seg==0 or mSize!=0:
        n_seg=int(total_l/mSize)

    eq_len = np.linspace(0,total_l,n_seg+1)

    interp_u = np.interp(eq_len,cum_l,u_fine)
    interp_x, interp_y , interp_z, iterp_ang = splev(interp_u, tck)

    align_fine_points  = [ [x, y, z] for x, y, z in zip(interp_x, interp_y , interp_z) ]

    return align_fine_points,iterp_ang, interp_u , u




class plateTapSection:

    def __init__(self,SecPoint_arr, cg_arr, t_param_arr, line_conn_arr,thk_arr,thk_off_arr):
        ''' SecPoint_arr = [SP1, SP2, SP3] |  cg_arr = [[0,0],[0,0]] | t_param_arr = [0,0.5,1]  | thk_arr = [[0.25],[0.3]] '''

        for q,shape in enumerate(SecPoint_arr):
            for i in range(len(shape)):
                shape[i] = [shape[i][0]-cg_arr[q][0] , shape[i][1]-cg_arr[q][1]]


        self.POINTS = SecPoint_arr
        self.T = t_param_arr
        self.THICK = thk_arr
        self.THICK_OFF = thk_off_arr
        self.LINE = line_conn_arr
        self.TYPE = 'TAP'


def intpolatePOINTS(t,S1,t1,S2,t2):
    t_diff = t2-t1

    S1_scaled = np.multiply(S1,((t2-t)/t_diff))
    S2_scaled = np.multiply(S2,((t-t1)/t_diff))

    S_t = np.add(S1_scaled,S2_scaled)

    return S_t

def intpolateScalar(t,S1,t1,S2,t2):
    t_diff = t2-t1

    S1_scaled = S1*(t2-t)/t_diff
    S2_scaled = S2*(t-t1)/t_diff

    S_t = S1_scaled+S2_scaled

    return S_t

def getTapShape(t,plateTapSect):
    eq_chk = 0
    i_c = 0
    for i in range(len(plateTapSect.T)):
        if t == plateTapSect.T[i_c] :
            eq_chk=1
            break
        elif t > plateTapSect.T[i_c] and t < plateTapSect.T[i_c+1]:
            break
        i_c+=1
    
    thick_curr = plateTapSect.THICK[i_c] 
    thick_off_curr = plateTapSect.THICK_OFF[i_c] 

    if eq_chk:
        return plateTapSect.POINTS[i_c] , thick_curr, thick_off_curr
    else:
        ti = plateTapSect.T[i_c]
        tf = plateTapSect.T[i_c+1]

        Si = plateTapSect.POINTS[i_c]
        Sf = plateTapSect.POINTS[i_c+1]

        thi=plateTapSect.THICK[i_c]
        thf=plateTapSect.THICK[i_c+1]

        th_off_i=plateTapSect.THICK_OFF[i_c]
        th_off_f=plateTapSect.THICK_OFF[i_c+1]
    
    
        return intpolatePOINTS(t,Si,ti,Sf,tf) , intpolatePOINTS(t,thi,ti,thf,tf), intpolatePOINTS(t,th_off_i,ti,th_off_f,tf)





glob_thick_json = {}
def isCreateThick(thick,thick_off):
    if f'{thick}+{thick_off}' in glob_thick_json:
        return glob_thick_json[f'{thick}+{thick_off}']
    else:
        tid= Thickness(thick,offset=thick_off,off_type='val').ID
        glob_thick_json[f'{thick}+{thick_off}']=tid
        return tid




#----------------------------------------------------------------
def Mesh_SHAPE(shape,meshSize=1):
    ''' Shape is a object from midas library
    Retrurns Section points (SHAPE), Thickness, CG , Line connection of plates
    
    '''
    if shape.SHAPE == 'SB':
        H = shape.PARAMS[0]
        B = shape.PARAMS[1]
        sect_lin_con = [[1,4],[1,5],[4,2],[5,3]]

        sect_cg = [0,0]

        if H > B :
            sect_shape = [[0,0],[0,H/2],[0,-H/2],[0,H/4],[0,-H/4]]
            sect_thk = [B,B,B,B]
            sect_thk_off = [0,0,0,0]
        else : 
            sect_shape = [[0,0],[B/2,0],[-B/2,0],[B/4,0],[-B/4,0]]
            sect_thk = [H,H,H,H]
            sect_thk_off = [0,0,0,0]
    
    elif shape.SHAPE == 'L':
        H = shape.PARAMS[0]
        B = shape.PARAMS[1]
        tw = shape.PARAMS[2]
        tf = shape.PARAMS[3]

        sect_lin_con = [[1,2],[3,1]]

        sect_cg = [0,0]

        sect_shape = [[0,0],[B,0],[0,-H]]
        sect_thk = [tf,tw]
        sect_thk_off = [-tf/2,-tw/2]



    # ----------------- MESH SIZER --------------------------
    m_size = meshSize

    n_nodes = len(sect_shape)
    for i in (range(len(sect_lin_con))):
        p1 = sect_shape[sect_lin_con[i][0]-1]
        p2 = sect_shape[sect_lin_con[i][1]-1]
        dis = hypot(p1[0]-p2[0],p1[1]-p2[1])
        n_div = max(int(dis/m_size),1)
        if n_div > 1 :
            i_loc = np.linspace(p1,p2,n_div+1)
            for q in range(n_div-1):
                sect_shape.append(i_loc[q+1])

            sect_lin_con.append([n_nodes+n_div-1,int(sect_lin_con[i][1])])
            sect_thk.append(float(sect_thk[i]))
            sect_thk_off.append(float(sect_thk_off[i]))
            sect_lin_con[i][1] = n_nodes+1

            for q in range(n_div-2):
                sect_lin_con.append([n_nodes+q+1,n_nodes+q+2])
                sect_thk.append(float(sect_thk[i]))
                sect_thk_off.append(float(sect_thk_off[i]))
                
        n_nodes+=n_div-1



    return sect_shape, sect_thk ,sect_thk_off, sect_cg , sect_lin_con




def SS_create(nSeg , mSize , bRigdLnk):
    # ORIGINAL ALIGNMENT

    node_list , align_points, align_beta_angle , elm_list, matID , align_sectID_list_sorted,k = delSelectElements() # Select elements


    # NEW SMOOTH ALIGNMENT
    fine_align_points = align_points
    fine_beta_angle = align_beta_angle

    fine_align_points, fine_beta_angle, fine_t_param, align_t_param = interpolateAlignment(align_points,align_beta_angle,nSeg,2,mSize)



    Section.sync()

    sect_shape_arr = []
    sect_points_arr =[]
    cg_arr = []
    thk_arr =[]
    thk_off_arr =[]
    lin =[]
    

    align_sectID_list_sorted.insert(0, align_sectID_list_sorted[0])  # ADD first section again to match node count

    for Sid in align_sectID_list_sorted:
        for sect in Section.sect:
            if sect.ID == Sid:
                sect_shape_arr.append(sect)

    for shape in sect_shape_arr:
        sect_shape, sect_thk , sect_thk_off, sect_cg , sect_lin_con = Mesh_SHAPE(shape)
        sect_points_arr.append(sect_shape)
        thk_arr.append(sect_thk)
        thk_off_arr.append(sect_thk_off)
        cg_arr.append(sect_cg)
        lin = sect_lin_con

        
    Node.sync()
    Element.sync()
    Thickness.sync()
    Boundary.RigidLink.sync()

    myTapShape = plateTapSection(sect_points_arr,cg_arr,align_t_param,lin,thk_arr,thk_off_arr)

    createTapPlateAlign(fine_align_points,fine_t_param,fine_beta_angle,myTapShape,bRigdLnk,matID)

    Node.create()
    Element.create()
    Thickness.create()
    Boundary.RigidLink.create()


# SS_create(0,0.5,False)

# bInterp is Removed [ First toggle is removed from UI]
# SS_create(0,0.5,True)  -> No. of div = 0 => Mesh size is used
# SS_create(20,0,True)  -> Mesh size = 0 => No of division is used
# SS_create(20,0,False)  -> bLink = False => No rigid link is created