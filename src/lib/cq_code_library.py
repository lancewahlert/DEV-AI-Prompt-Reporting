from snowflake.snowpark import Session
from snowflake.snowpark.functions import col
# Visualizations 
import streamlit as st
import time
import toml

# data manipulation 
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

#data types
import json
import struct

# setup connection with snowflake
def snowconnection():
    f = open('./.streamlit/secrets.toml', 'r')
    connection_config = toml.load(f)
    f.close()
    session = Session.builder.configs(connection_config).create()

    return session

def save_UserCache(i, content):
    # set indice
    name = 'messages' + str(i) 
    st.session_state[name].append({"role": "user", "content": content})

def get_LastPrompt(i):
    name     = 'messages' + str(i) 
    thislist = []
    prompt = ''
    for strings in st.session_state[name]:
        if str(strings).find('user') > 0:
            thislist.append(strings)
    size = len(thislist)
    prompt = str(thislist[size-1]).replace('\'','"')
    prompt = json.loads(prompt)
    return prompt["content"]

def save_AssistantCache(i, content):
    # set indice
    name = 'messages' + str(i) 
    st.session_state[name].append({"role": "assistant", "content": content})

def load_Cache(UserAvatar, BotAvatar):
    # load session cache or reset if none
    for message in st.session_state.messages:
        if(message["role"] == "user"):
            with st.chat_message("user", avatar = UserAvatar):
                st.markdown(message["content"])
        else:       
            with st.chat_message("assistant", avatar = BotAvatar):
                st.markdown(message["content"])

def parseBinaryEncoding(bin_enc):
    return [struct.unpack('d', bytearray(bin_enc[i:i+8]))[0] for i in range(0, len(bin_enc), 8)]

# write session meta data
def write_Audit(session, prompt, FeedbackRating, FeedbackText):
    s=time.gmtime(time.time())
    session_details = session.create_dataframe(
            [
               [
                  session._session_id
                , str(prompt).replace('"','')
                , FeedbackRating
                , str(FeedbackText).replace('"','')
                , time.strftime("%Y-%m-%d %H:%M:%S", s)
                ]
            ]
            , schema=["session_id" , "input", "FeedbackRating", "FeedbackText", "TimeStamp"]
         )
    # This logs write meta data to a table in snowflake
    session_details.write.mode("append").save_as_table("session_messages_feedback")    

# caching for chats  
def manage_Cache():
    # caching for chats  
    number = st.number_input('Insert chat index number', min_value=0, max_value=None, value=0, step=1)
    # create new cache
    name = 'messages' + str(number) 
    
    # initialize session cache    
    if name not in st.session_state:
        st.session_state[name] = []

        # remove data from current session cache # reinitialize current session cache
        del st.session_state['messages']                          
        st.session_state['messages'] = []                
    else:                
        # if the name exists then we just swap out the cache
        st.session_state['messages'] = st.session_state[name]    
    
    return number

# load options file and set up model
@st.cache_resource()
def get_Model():
    # load largemodel bin file
    # model_bin = open('./LocalModel/pytorch_model.bin', 'wb')
    # shard = open('./LocalModel/shards/01_shard_pytorch_model.bin', 'rb')
    # model_bin.write(shard.read())
    # shard.close()
    # shard = open('./LocalModel/shards/02_shard_pytorch_model.bin', 'rb')
    # model_bin.write(shard.read())
    # shard.close()
    # shard = open('./LocalModel/shards/03_shard_pytorch_model.bin', 'rb')
    # model_bin.write(shard.read())
    # shard.close()
    # shard = open('./LocalModel/shards/04_shard_pytorch_model.bin', 'rb')
    # model_bin.write(shard.read())
    # shard.close()
    # model_bin.close()
    
    # model selection
    modelName = 'all-distilroberta-v1'
    #modelName = './LocalModel/'
    model = SentenceTransformer(modelName)    
    return model

@st.cache_resource()
def get_Data(_session):
    # # Open and collect options
    options_query = _session.table("OPTIONS_QUERY_COMPLEX")
        
    #recieve options and their encodings and return
    query_rows = options_query.select(['RESULT_CACHE', 'ENCODING']).filter(col('RESULT_CACHE').isNotNull() & col('ENCODING').isNotNull()).to_pandas().values.tolist()
    query_opts = [row[0] for row in query_rows]
    query_enc  = [parseBinaryEncoding(bytearray(row[1])) for row in query_rows]

    return query_enc, query_opts

def env_Setup(_session, Title, Layout, SideBarState, Menu_Items, Title_Image_Path):
    # PC Icon
    with open('src/txt/price-chopper-base64.txt') as f:
        UserAvatar = f.read()
    f.close()

    # User Avatar Icon
    with open('src/txt/bot-icon.txt') as f:
        BotAvatar = f.read()
    f.close()

    # Page Config
    st.set_page_config(
        page_title            = Title,
        page_icon             = UserAvatar,
        layout                = Layout,
        initial_sidebar_state = SideBarState,
        menu_items            = Menu_Items
    )

    # Page Header/Subheader
    if(len(Title_Image_Path) > 0):
        st.image(Title_Image_Path)

    if(len(Title) > 0):
        st.subheader(Title, divider='rainbow')

    # Open CSS file
    with open('src/css/style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    f.close()

    model = get_Model()
    query_enc, query_opts = get_Data(_session)
    
        # (re)-initialize current chat 
    if 'messages' not in st.session_state:
        st.session_state['messages'] = []
    if 'number' not in st.session_state:
        st.session_state.number = 0
    if 'FeedbackRating' not in st.session_state:
        st.session_state.FeedbackRating = ''
    if 'FeedbackText' not in st.session_state:
            st.session_state.FeedbackText = ''

    return model, query_enc, query_opts, BotAvatar, UserAvatar


# run the prompt against the AI to recieve an answer
def do_Get(prompt, _model, query_enc, query_opts):   
    #init 
    encoding = None
    
    # Encode prompt based off which model is being used
    if(prompt != ''):
        encoding = _model.encode(prompt)
    

    # pick and return a query answer
    sim = cosine_similarity([encoding], query_enc)
    query_answer = query_opts[sim[0].tolist().index(max(sim[0]))]
    return query_answer, max(sim[0])
