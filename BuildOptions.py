from sentence_transformers import SentenceTransformer
import json
import struct
import base64
import os
import datetime
import   sys
from     snowflake.snowpark           import Session
from     snowflake.snowpark.functions import col, to_timestamp
from     snowflake.snowpark.types     import IntegerType, StringType, StructField, StructType, DateType,LongType,DoubleType

from src.lib import code_library


def main(templateFilename = './src/json/AllTemplates.json', useLocalModel = False, encode = False, truncateLoad = False, loadSnowflake = False, runQueries = False, saveStageFiles = False, production = False):

    # load template json
    print('Loading template file '+templateFilename)
    templateFile = open(templateFilename)
    templateJSON = json.load(templateFile)
    templates = templateJSON['templates']
    paramLists = templateJSON['parameterLists']
    templateFile.close()

    # load model
    baseModelName = 'all-distilroberta-v1'
    if(useLocalModel):
        modelName = './LocalModel/'
    else:
        modelName = baseModelName
    model = SentenceTransformer(modelName)

    # prepare output files
    if(truncateLoad):
        ak = open('src/csv/answerKey.csv', 'w')
        ak.write(str(datetime.datetime.now())+'\n')
        optionSummary = open('src/csv/optionSummary.csv', 'w')
        optionSummary.write('Option ID|Option Template|Combo Count|Question Count|Base Model %|Local Model %\n')
    else:
        lines = []
        if(os.path.isfile('src/csv/answerKey.csv')):
            ak = open('src/csv/answerKey.csv', 'r')
            ak.readline()
            lines = ak.readlines()
            ak.close()
        ak = open('src/csv/answerKey.csv', 'w')
        ak.write(str(datetime.datetime.now())+'\n')
        ak.writelines(lines)
        optionSummary = open('src/csv/optionSummary.csv', 'a')

    

    stageQ = None
    stageD = None
    if(loadSnowflake):
        stageQ = open('toStageQuery.csv', 'w')
        stageQ.write('DESC|BATCH|DASHBOARD|QUERY|ENCODING|ENCODING_JSON|RESULT_CACHE|RESULT_CACHE_TS\n')
        stageD = open('toStageDashboard.csv', 'w')
        stageD.write('DESC|BATCH|DASHBOARD|URL|ENCODING|ENCODING_JSON|FILTER|QUERY\n')
        session = code_library.snowconnection()    
        batch = str(datetime.datetime.now())

    count = 0
    templateID = 0

    for template in templates:
        templateID += 1
        optionSummary.write(str(templateID)+'|'+template['desc']+'|')

        paramCount = [0 for param in template['parameters']]
        paramMaxCount = [len(paramLists[param]['descriptionValues']) for param in template['parameters']]
        
        comboCount = 0
        questionCount = 0
        done = False
        while not done: # for each parameter combination

            # base options
            newDesc = template['desc']
            newQuestions = template['questions']
            newQuery = template['query']
            newURL = 'https://ipqa.armeta.com/pricechopper/analytics/'+template['urlpage']
            newURLFilter = template['urlfilter']
            newURLQuery = template['urlquery']

            # replace parameter placeholders with values
            for p in range(len(template['parameters'])):
                paramName = template['parameters'][p]
                DescParam = paramLists[paramName]['descriptionValues'][paramCount[p]]
                QuestionParam = paramLists[paramName]['questionValues'][paramCount[p]]
                queryParam = paramLists[paramName]['queryValues'][paramCount[p]]
                urlParam = paramLists[paramName]['urlValues'][paramCount[p]]

                newDesc = newDesc.replace(paramName, DescParam)
                newQuestions = [newQuestion.replace(paramName, QuestionParam) for newQuestion in newQuestions]
                newQuery = newQuery.replace('DESCRIPTION_'+paramName, DescParam).replace(paramName, queryParam)
                newURLFilter = newURLFilter.replace(paramName, urlParam)
                newURLQuery = newURLQuery.replace(paramName, urlParam)
            
            urlData = []
            if(newURLFilter != ''):
                urlData.append('filter=' + str(base64.b64encode(newURLFilter.encode("ascii")))[2:-1].replace('=', '%3D'))
            if(newURLQuery != ''):
                urlData.append('query=' + str(base64.b64encode(newURLQuery.encode("ascii")))[2:-1].replace('=', '%3D'))
            if(template['urlview'] != ''):
                urlData.append('view=' + str(base64.b64encode(template['urlview'].encode("ascii")))[2:-1].replace('=', '%3D'))
            
            if(len(urlData) > 0):
                newURL += '?'+urlData[0]
                for x in urlData[1:]:
                    newURL += '&'+x

            # output question variations with answers
            for newQuestion in newQuestions:
                ak.write(newQuestion+'|'+newDesc+'|'+str(templateID)+'\n')

            # append to stage file if loading to snowflake
            if(loadSnowflake):
                if(encode):
                    enc = model.encode(newDesc.lower()).tolist()
                    enc_json = '{"encoding": '+str(enc)+'}'
                    enc_bin = ''.join([''.join(['%02x' % (b) for b in bytearray(struct.pack('d', d))]) for d in enc])
                else:
                    enc_json = ''
                    enc_bin = ''

                query_cache = ''
                query_cache_ts = ''
                if(runQueries):
                    query_cache = session.sql(newQuery).collect()
                    query_cache_ts = str(datetime.datetime.now())
                    if(len(query_cache) == 0 or query_cache[0] == None):
                        query_cache = 'No results'
                    elif(len(query_cache[0]) == 0 or query_cache[0][0] == None):
                        query_cache = 'No results'
                    else:
                        query_cache = query_cache[0][0]
                    
                #DESC, BATCH, DASHBOARD, QUERY, ENCODING, ENCODING_JSON, RESULT_CACHE, RESULT_CACHE_TS
                stageQ.write('%s|%s|%s|%s|%s|%s|%s|%s\n' % (newDesc, batch, template['urlpage'], newQuery, enc_bin, enc_json, query_cache, query_cache_ts))
                #DESC, BATCH, DASHBOARD, URL, ENCODING, ENCODING_JSON, FILTER, QUERY
                stageD.write('%s|%s|%s|%s|%s|%s|%s|%s\n' % (newDesc, batch, template['urlpage'], newURL, enc_bin, enc_json, newURLFilter, newURLQuery))

            # get next combination of parameters
            if(len(paramCount) > 0):
                paramCount[0] += 1
                for i in range(len(paramCount)):
                    if(paramCount[i] >= paramMaxCount[i]):
                        if(i == len(paramCount)-1):
                            done = True
                        else:
                            paramCount[i+1] += 1
                            paramCount[i] = 0
            else:
                done = True

            # progress tracker
            count += 1
            if(count % 100 == 0):
                print(count)
            comboCount += 1
            questionCount += len(newQuestions)
        
        optionSummary.write(str(comboCount)+'|'+str(questionCount)+'||\n')

    # end of templates

    # finished generating options
    ak.close()
    print('Generated %d options' % (count))

    # load staged records
    if loadSnowflake:
        print('Loading Snowflake with batch %s' % (batch))
        stageQ.close()
        stageD.close()
        schema = 'PC'
        tableDashboard = 'OPTIONS_DASHBOARD_DEV'
        tableQuery = 'OPTIONS_QUERY_DEV'
        if production:
            tableDashboard = 'OPTIONS_DASHBOARD'
            tableQuery = 'OPTIONS_QUERY'
        stageDashboard = '@PC.PC_DASHBOARD_OPTION_STAGE'
        stageQuery = '@PC.PC_QUERY_OPTION_STAGE'

        print('Using tables %s, %s' % (schema+'.'+tableDashboard, schema+'.'+tableQuery))

        if truncateLoad:
            print('Truncating Existing Tables...')
            session.sql('TRUNCATE TABLE %s."%s";' % (schema, tableDashboard)).collect()
            session.sql('TRUNCATE TABLE %s."%s";' % (schema, tableQuery)).collect()

        print('Clearing Stages...')
        session.sql('REMOVE %s;' % (stageDashboard)).collect()
        session.sql('REMOVE %s;' % (stageQuery)).collect()

        print('Uploading Stages...')
        session.sql('PUT file://%s/toStageDashboard.csv %s;' % (str(os.getcwd()), stageDashboard)).collect()
        session.sql('PUT file://%s/toStageQuery.csv %s;' % (str(os.getcwd()), stageQuery)).collect()

        print('Loading Stages Into Tables...')
        session.sql('COPY INTO %s.%s (DESC, BATCH, DASHBOARD, URL, ENCODING, ENCODING_JSON, FILTER, QUERY) FROM %s file_format = (type = \'CSV\' SKIP_HEADER = 1 FIELD_DELIMITER = \'|\');' % (schema, tableDashboard, stageDashboard)).collect()
        session.sql('COPY INTO %s.%s (DESC, BATCH, DASHBOARD, QUERY, ENCODING, ENCODING_JSON, RESULT_CACHE, RESULT_CACHE_TS) FROM %s file_format = (type = \'CSV\' SKIP_HEADER = 1 FIELD_DELIMITER = \'|\');' % (schema, tableQuery, stageQuery)).collect()

        if not saveStageFiles:
            os.remove('toStageDashboard.csv')
            os.remove('toStageQuery.csv')


if __name__ == '__main__':
    if(len(sys.argv) > 1):
        flags = ''.join([arg[1:] for arg in sys.argv if arg[0] == '-' and arg[1] != '-'])
        if(sys.argv[1][0] != '-'): # included template filepath
            main(sys.argv[1]
                 , useLocalModel = '--useLocalModel' in sys.argv or 'l' in flags
                 , encode = '--encode' in sys.argv or 'e' in flags
                 , truncateLoad = '--truncateLoad' in sys.argv or 't' in flags
                 , loadSnowflake = '--loadSnowflake' in sys.argv or 's' in flags
                 , runQueries = '--runQueries' in sys.argv or 'q' in flags
                 , saveStageFiles = '--saveStageFiles' in sys.argv or 'f' in flags
                 , production = '--production' in sys.argv or 'p' in flags)
        else: # default template filepath
            main(  useLocalModel = '--useLocalModel' in sys.argv or 'l' in flags
                 , encode = '--encode' in sys.argv or 'e' in flags
                 , truncateLoad = '--truncateLoad' in sys.argv or 't' in flags
                 , loadSnowflake = '--loadSnowflake' in sys.argv or 's' in flags
                 , runQueries = '--runQueries' in sys.argv or 'q' in flags
                 , saveStageFiles = '--saveStageFiles' in sys.argv or 'f' in flags
                 , production = '--production' in sys.argv or 'p' in flags)
            
    else: #  no arguments, run from code arguments
        main(templateFilename = './src/json/AllTemplates.json', useLocalModel = False, encode = False, truncateLoad = False, loadSnowflake = False, runQueries = False, saveStageFiles=False, production=False)
