from sentence_transformers import SentenceTransformer, losses, InputExample
from torch.utils.data import DataLoader
import json
import datetime

starttime = datetime.datetime.now()

baseModelName  = 'all-distilroberta-v1'

ak = open('src/outputs/answerKey.csv','r')
ak.readline()


pairs = [line.replace('\n','').replace('\r','').split('|') for line in ak] # question|answer
sets = [{'qs':[],'as':[]}]

for pair in pairs:
    placed = False
    for i in range(len(sets)):
        if not placed and pair[1] not in sets[i]['as']:
            sets[i]['qs'].append(pair[0])
            sets[i]['as'].append(pair[1])
            placed = True
            break
    if not placed:
        sets.append({'qs':[pair[0]],'as':[pair[1]]})

set_len = [ len(set['qs']) for set in sets]
print(str(len(set_len)) + ' training sets with sizes: '+str(set_len))



baseModel = SentenceTransformer(baseModelName)

for set in sets:
    train_examples = [InputExample(texts=[pair[0], pair[1]]) for pair in zip(set['qs'], set['as'])]
    train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=16)
    train_loss = losses.MultipleNegativesRankingLoss(model=baseModel)
    baseModel.fit(train_objectives=[(train_dataloader, train_loss)], epochs=3)


baseModel.save('./LocalModel/')

endtime = datetime.datetime.now()
dur = (endtime-starttime).seconds
print('Total time to tune new model: %dm %ss (%d sec)' % (int(dur/60), dur%60, dur))