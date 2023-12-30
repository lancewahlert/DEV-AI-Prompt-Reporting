# Visualizations 
import streamlit as st
from   PIL import Image
from streamlit_extras.switch_page_button import switch_page
#import extra_streamlit_components as stx

# custom functions
from src.lib import cq_code_library
import json

def main():

    # Get connection string paramaters
    session = cq_code_library.snowconnection()    
    
    # gets mapping file and their encodings as well as meta data for the model being used
    model, query_enc, query_opts, BotAvatar, UserAvatar  \
    = cq_code_library.env_Setup(session                                          
                             , "Analytics Digital Assistant - Complex Queries"  
                             , "wide"                                         
                             , "collapsed"                                     
                             , {'About': "This is a webpage with a user input box where to input natural language and recieve real information along with links to a dashboard to help satisfy your query"} 
                             , './src/media/Title.png' 
                            )

    with st.chat_message("assistant", avatar = BotAvatar):
         st.write("How can I help you?")  

    # sidebar options
    with st.sidebar:
         # caching for chat
        number = cq_code_library.manage_Cache()
         # Give filtering options for AI results
         
    # load chat history 
    cq_code_library.load_Cache(UserAvatar, BotAvatar)
   
    # recieve prompt from user
    prompt = st.chat_input("Send a Message")
    if prompt : 
        # Start Chat - user
        with st.chat_message("user", avatar = UserAvatar):
            st.markdown(prompt)
        
        if prompt == 'reload':
            st.cache_resource.clear()
            query_enc, query_opts = cq_code_library.get_Data(session)
        else:
            # clean the prompt before the AI recieves it
            clean_prompt = prompt.lower().replace('\'','').replace('-',' ')
                
            # run the prompt against the AI to recieve an answer And Write to session cache for user
            query_answer, sim_score = \
            cq_code_library.do_Get(clean_prompt, model, query_enc, query_opts)        
            cq_code_library.save_UserCache(number, prompt)

            #Start chat - assistant
            with st.chat_message("assistant", avatar = BotAvatar):
                # Show query result 
                if(query_answer != ''):
                    # Write results + session cache for assistant
                    query_answer = str(query_answer).replace("$", "\\$") # + ' ('+str(sim_score)+')'
                    st.markdown(query_answer) 
                    cq_code_library.save_AssistantCache(number, query_answer)
                else:
                    # Write results + session cache for assistant 
                    st.write("No query results")               
                    cq_code_library.save_AssistantCache(number, "No query results")

        # End chat - assistant
# ask user if reply was helpful
    if st.button('Give Feedback'):
        switch_page('FeedBackPage')
    
if __name__ == '__main__':
    main()
