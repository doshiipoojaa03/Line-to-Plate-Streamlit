import streamlit as st
from backend.finalUIfunc import SS_create
from backend.midas_civil_lib import *

if "api_key_entered" not in st.session_state:
    st.session_state.api_key_entered = False

# Function to set API key
def set_api_key():
    if st.session_state.mapi_input:
        MAPI_KEY(st.session_state.mapi_input)
        st.session_state.api_key_entered = True

# If API key not yet entered, show input card
if not st.session_state.api_key_entered:
    st.markdown("## Enter MAPI_KEY to continue")
    st.text_input("MAPI_KEY", key="mapi_input", type="password")
    st.button("Submit", on_click=set_api_key)
else:

  st.set_page_config(page_title="Line to Plate Converter", layout="wide")

  st.title("Line to Plate Converter")

  # Meshing option
  switch_chngMesh = st.checkbox("Meshing option - Size or division", value=True)

  # Mesh input
  mesh_label = "No. of division" if switch_chngMesh else "Mesh Size (length)"
  txt_mesh = st.number_input(mesh_label, min_value=0, value=20, step=1)

  # Rigid link option
  chk_RigdLnk = st.checkbox("Rigid Link", value=True)

  # Run button
  if st.button("Create Mesh"):
      try:
          nSeg = txt_mesh
          mSize = 0
          if not switch_chngMesh:
              mSize = txt_mesh
              nSeg = 0

          SS_create(int(nSeg), float(mSize), bool(chk_RigdLnk))

          Thickness.create()
          Node.create()
          Element.create()
          if chk_RigdLnk:
              Boundary.RigidLink.create()

          st.success("Plates created successfully!")
      except Exception as e:
          st.error(f"An error occurred: {str(e)}")
