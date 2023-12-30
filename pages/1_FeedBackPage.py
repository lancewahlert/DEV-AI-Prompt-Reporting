# Visualizations 
import streamlit as st
from   PIL import Image
from streamlit_extras.switch_page_button import switch_page
from src.lib import code_library

with st.form("Give Feedback: ", clear_on_submit=True):
    st.session_state.FeedbackRating = st.radio("Was this app helpful?", ["✅", "❌"], label_visibility='visible', disabled=False, horizontal=True, index = 0) 
    st.session_state.FeedbackText   = st.text_input("How could this app be improved?", "... ", disabled=False)   
    with st.spinner(text="Sending Feedback..."):                     
        submitted = st.form_submit_button("Submit")
        if submitted:
            try:
                LastPrompt = code_library.get_LastPrompt(st.session_state.number)
            except:
                LastPrompt = ''
            #code_library.write_Audit(session, st.session_state.FeedbackRating, st.session_state.FeedbackText)
            st.toast('Success! Your feedback has been recieved. ', icon='✅') 


if st.button("Return"):
    switch_page('Streamlit_App')