# Visualizations 
import streamlit as st
from   PIL import Image
from streamlit_extras.switch_page_button import switch_page
#import extra_streamlit_components as stx

# custom functions
from src.lib import dev_code_library
import json

def main():

    # Get connection string paramaters
    session = dev_code_library.snowconnection()    
    
    # gets mapping file and their encodings as well as meta data for the model being used
    model, dash_enc, dash_opts, query_enc, query_opts, BotAvatar, UserAvatar  \
    = dev_code_library.env_Setup(session                                          
                             , "Analytics Digital Assistant - Price Chopper"  
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
        number = dev_code_library.manage_Cache()
         # Give filtering options for AI results
        options = st.radio("What would you like to see?",('Both Dashboard and Query Results', 'Dashboards Only', 'Query Results Only'))

    # load chat history 
    dev_code_library.load_Cache(UserAvatar, BotAvatar)
   
    # recieve prompt from user
    prompt = st.chat_input("Send a Message")
    if prompt : 
        # Start Chat - user
        with st.chat_message("user", avatar = UserAvatar):
            st.markdown(prompt)
        
        if prompt == 'reload':
            st.cache_resource.clear()
            dash_enc, dash_opts, query_enc, query_opts = dev_code_library.get_Data(session)
        else:
            # clean the prompt before the AI recieves it
            clean_prompt = prompt.lower().replace('\'','').replace('-',' ')
                
            # run the prompt against the AI to recieve an answer And Write to session cache for user
            dash_answer, query_answer, sim_score = \
            dev_code_library.do_Get(clean_prompt, model, dash_enc, dash_opts, query_enc, query_opts)        
            dev_code_library.save_UserCache(number, prompt)

            #Start chat - assistant
            with st.chat_message("assistant", avatar = BotAvatar):
                # Show query result 
                if(query_answer != '') and (options != 'Dashboards Only'):
                    # Write results + session cache for assistant
                    query_answer = str(query_answer).replace("$", "\\$")
                    #st.markdown(query_answer + ' ('+str(sim_score)+')') 
                    st.markdown(query_answer) 
                    dev_code_library.save_AssistantCache(number, query_answer)
                elif (options != 'Dashboards Only'):
                    # Write results + session cache for assistant 
                    st.write("No query results")               
                    dev_code_library.save_AssistantCache(number, "No query results")

                # Show dashboard result  
                if(dash_answer != '') and (options != 'Query Results Only'): 
                    # Write results + session cache for assistant
                    st.markdown("Your query reminds me of this [dashboard.](%s)" % dash_answer)
                    st.session_state.number       = number         
                    dev_code_library.save_AssistantCache(number, "Your query reminds me of this [dashboard.](%s)" % dash_answer)
        # End chat - assistant
# ask user if reply was helpful
    if st.button('Give Feedback'):
        switch_page('FeedBackPage')
    
if __name__ == '__main__':
    main()
