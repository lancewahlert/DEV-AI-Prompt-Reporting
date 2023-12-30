import os
import sys

# data manipulation 
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

#data types
import json
import struct
import datetime
import pandas

#snowpark
import   sys
from     snowflake.snowpark           import Session
from     snowflake.snowpark.functions import col, to_timestamp
from     snowflake.snowpark.types     import IntegerType, StringType, StructField, StructType, DateType,LongType,DoubleType

# add src to system path
sys.path.append('src')

from lib import code_library

modelname = 'all-distilroberta-v1'
#modelname = './LocalModel/'

def parseBinaryEncoding(bin_enc):
    return [struct.unpack('d', bytearray(bin_enc[i:i+8]))[0] for i in range(0, len(bin_enc), 8)]

def env_Setup():

    starttime = datetime.datetime.now()
    
    # model selection
    model = SentenceTransformer(modelname)

    # ak = open('src/csv/answerKey.csv', 'r')
    # ak.readline()
    # ops = [line.split('|')[1].replace('\n', '').replace('\r', '') for line in ak]
    # ops = list(set(ops)) # removes duplicates
    # ak.close()
    # dash_opts  = [desc for desc in ops]
    # query_opts = [desc for desc in ops]
    # dash_enc   = [model.encode(desc) for desc in ops]
    # query_enc  = [model.encode(desc) for desc in ops]

    # dash_desc  = [desc for desc in ops]
    # query_desc = [desc for desc in ops]

    
    # Get session tables
    session = code_library.snowconnection() 
    options_dash  = session.table("OPTIONS_DASHBOARD")
    options_query = session.table("OPTIONS_QUERY")

    #recieve options and their encodings and return
    dash_rows = options_dash.filter('BATCH = \'2023-09-26 14:43:05.465437\'').select(['URL', 'ENCODING', 'DESC']).to_pandas().values.tolist()
    query_rows = options_query.filter('BATCH = \'2023-09-26 14:43:05.465437\'').select(['RESULT_CACHE', 'ENCODING', 'DESC']).to_pandas().values.tolist()

    dash_opts  = [row[2] for row in dash_rows]
    query_opts = [row[2] for row in query_rows]
    dash_enc   = [parseBinaryEncoding(row[1]) for row in dash_rows]
    query_enc  = [parseBinaryEncoding(row[1]) for row in query_rows]

    dash_desc  = [row[2] for row in dash_rows]
    query_desc = [row[2] for row in query_rows]

    return model, dash_enc, dash_opts, query_enc, query_opts, dash_desc, query_desc


# run the prompt against the AI to recieve an answer
def do_GET(prompt, model, dash_enc, dash_opts, query_enc, query_opts, dash_desc, query_desc):   
    #init 
    encoding = None
    dash_answer = ''
    query_answer = ''
    dash_answer_desc = ''
    query_answer_desc = ''

    # Encode prompt based off which model is being used
    if(prompt != ''):
        clean_prompt = prompt.replace('\'', '').replace('-', '')
        encoding = model.encode(clean_prompt)
    
        # pick and return a dashboard answer based off options.json
        sim = cosine_similarity([encoding], dash_enc)
        dash_answer = dash_opts[sim[0].tolist().index(max(sim[0]))]
        dash_answer_desc = dash_desc[sim[0].tolist().index(max(sim[0]))]

        # pick and return a query answer
        sim = cosine_similarity([encoding], query_enc)
        query_answer = query_opts[sim[0].tolist().index(max(sim[0]))]
        query_answer_desc = query_desc[sim[0].tolist().index(max(sim[0]))]
    
    return dash_answer, query_answer, dash_answer_desc, query_answer_desc

def main(useLocalModel = False):

    starttime = datetime.datetime.now()

    if(useLocalModel):
        modelname = './LocalModel/'
    else:
        modelname = 'all-distilroberta-v1'

    # gets mapping file and their encodings as well as meta data for the model being used
    model, dash_enc, dash_opts, query_enc, query_opts, dash_desc, query_desc = env_Setup()

    print('Env setup (%d options) in %d secs' % (len(dash_opts), (datetime.datetime.now() - starttime).seconds))

    totalDash = 0
    countDash = 0
    totalQuery = 0
    countQuery = 0
    totalBoth = 0
    countBoth = 0

    total = -1
    ak = open('src/csv/answerKey.csv', 'r')
    for line in ak:
        total += 1
    ak.close()

    ak = open('src/csv/answerKey.csv', 'r')
    ak_timestamp = ak.readline().replace('\n', '').replace('\r', '')

    optionSummary = pandas.read_csv('src/csv/optionSummary.csv',sep='|')

    outputpath = 'src/csv/all-distilroberta-v1/'
    if(useLocalModel):
        outputpath = 'src/csv/LocalModel/'
    good = open(outputpath+'Questions_good.csv', 'w')
    bad = open(outputpath+'Questions_bad.csv', 'w')
    bad_debug = open(outputpath+'Questions_bad_debug.csv', 'w')
    bad_debug.write('Question | Wrong Answer | Expected Answer | Option ID\n')

    goodPerOption = {}
    badPerOption = {}
    countPerOption = {}

    currentCount = 0
    starttime = datetime.datetime.now()
    for line in ak.readlines():
        if(line == ''):
            continue
        split = line.replace('\n', '').replace('\r', '').split('|')
        prompt = split[0]
        ans = split[1]
        id = split[2]

        dash_answer, query_answer, dash_answer_desc, query_answer_desc = do_GET(prompt, model, dash_enc, dash_opts, query_enc, query_opts, dash_desc, query_desc)

        totalDash += 1
        totalQuery += 1
        totalBoth += 1
        if(dash_answer_desc == ans):
            countDash += 1
        if(query_answer_desc == ans):
            countQuery += 1
        if(dash_answer_desc == ans and query_answer_desc == ans):
            good.write(prompt+'\n')
            countBoth += 1
        if(dash_answer_desc != ans and query_answer_desc != ans):
            bad.write(prompt+'\n')
            bad_debug.write(prompt + ' | ' + query_answer_desc + ' | ' + ans + ' | ' + str(id) + '\n')

        if(id not in countPerOption):
            countPerOption[id] = 0
            goodPerOption[id] = 0
            badPerOption[id] = 0

        goodPerOption[id] += 1 if dash_answer_desc == ans and query_answer_desc == ans else 0
        badPerOption[id] += 1 if (dash_answer_desc != ans and query_answer_desc != ans) else 0
        countPerOption[id] += 1 

        currentCount += 1
        if(currentCount % 100 == 0):
            endtime = datetime.datetime.now()
            dur_s = (endtime - starttime).seconds
            left_s = int(dur_s/currentCount * (total-currentCount))
            dur_m = int(dur_s / 60)
            dur_s = dur_s % 60
            left_m = int(left_s / 60)
            left_s = left_s % 60
            print('Evaluated %5d entries (%d%%) in %2dm %02ds. Estimated time remaining: %2dm %02ds' % (currentCount, currentCount*100.0/total, dur_m, dur_s, left_m, left_s))
        
    endtime = datetime.datetime.now()
    dur_s = (endtime - starttime).seconds
    dur_m = int(dur_s / 60)
    dur_s = dur_s % 60
    print('Evaluated %5d total entries in %2dm %02ds.' % (currentCount, dur_m, dur_s))
    print( '%s model on %d entries from answerKey %s' % ('Tuned' if modelname == './LocalModel/' else 'Base' , currentCount, ak_timestamp) )
    print('Dashboards : %02.1f%%' % (countDash*100.0/totalDash))
    print('Queries    : %02.1f%%' % (countQuery*100.0/totalQuery))
    print('Both       : %02.1f%%' % (countBoth*100.0/totalBoth))

    good.close()
    bad.close()
    bad_debug.close()

    for id in countPerOption:
        optionSummary.at[int(id)-1, 'Base Model %'] = (goodPerOption[id] * 1.0 / countPerOption[id])
        

    optionSummary.to_csv('src/csv/optionSummary.csv',sep='|',index=False)

if __name__ == '__main__':
    
    if(len(sys.argv) > 1):
        flags = ''.join([arg[1:] for arg in sys.argv if arg[0] == '-' and arg[1] != '-'])
        main(useLocalModel = '--useLocalModel' in sys.argv or 'l' in flags)
    else:
        main(useLocalModel = False)
