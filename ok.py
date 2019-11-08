"""
I use twitter Streamer to get tweets.For every tweet whic h is recieved in ondata function of StdOutListener Class .then I demojezise the function ,remove the hashtags,'@'marks
and urls from it. Then I put it into json file and mongodb  parallely.After that we try to split the sentence subject wise in findSVAOs function,then we use subjectfunc to find different subjects 
we make a list sentences and their subject.In firebase we store the the 2 documents one named volumetric and other sentiment.In the volumetric we find the no of tweets with certain party as their subject
The subject we find in the findsub function are use to increase the value of that subject by 1.Then we get the sentiment of that subject.if the sentiment is >0 then it is stored as positve.
eg- lets suppose the sentence is 'Congress is doing bad but NCP is leading'.If this has hastags,'@',etc we remove it.Give this to findSVAO function which would give [('Congress','doing','bad'),('NCP','doing','good')]
the we give this to subject function which would give 2 subjects namely ['congress','ncp'].We find the sentiment with respect to each sentenc. and in volumetric we do dict['congress']+=1 and same  for NCP.
In sentiment we do dict['congress_negative']+=1(as sentiment will come negative) and dic['ncp_positive']+=1 (as sentiment is positive).Then update the document in firebase
"""

from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
import pandas as pd
import ast
import re
import json
from googletrans import Translator
import spacy
import emoji
from pymongo import MongoClient
import twitter_credentials
from datetime import date
import textblob
from nltk.stem.wordnet import WordNetLemmatizer
from spacy.lang.en import English
import firebase_admin
from firebase_admin import credentials,firestore

SUBJECTS = ["nsubj", "nsubjpass", "csubj", "csubjpass", "agent", "expl"]
OBJECTS = ["dobj", "dative", "attr", "oprd"]
ADJECTIVES = ["acomp", "advcl", "advmod", "amod", "appos", "nn", "nmod", "ccomp", "complm",
              "hmod", "infmod", "xcomp", "rcmod", "poss"," possessive"]
COMPOUNDS = ["compound"]
PREPOSITIONS = ["prep"]

def getSubsFromConjunctions(subs):
    moreSubs = []
    for sub in subs:
        # rights is a generator
        rights = list(sub.rights)
        rightDeps = {tok.lower_ for tok in rights}
        if "and" in rightDeps:
            moreSubs.extend([tok for tok in rights if tok.dep_ in SUBJECTS or tok.pos_ == "NOUN"])
            if len(moreSubs) > 0:
                moreSubs.extend(getSubsFromConjunctions(moreSubs))
    return moreSubs

def getObjsFromConjunctions(objs):
    moreObjs = []
    for obj in objs:
        # rights is a generator
        rights = list(obj.rights)
        rightDeps = {tok.lower_ for tok in rights}
        if "and" in rightDeps:
            moreObjs.extend([tok for tok in rights if tok.dep_ in OBJECTS or tok.pos_ == "NOUN"])
            if len(moreObjs) > 0:
                moreObjs.extend(getObjsFromConjunctions(moreObjs))
    return moreObjs

def getVerbsFromConjunctions(verbs):
    moreVerbs = []
    for verb in verbs:
        rightDeps = {tok.lower_ for tok in verb.rights}
        if "and" in rightDeps:
            moreVerbs.extend([tok for tok in verb.rights if tok.pos_ == "VERB"])
            if len(moreVerbs) > 0:
                moreVerbs.extend(getVerbsFromConjunctions(moreVerbs))
    return moreVerbs

def findSubs(tok):
    head = tok.head
    while head.pos_ != "VERB" and head.pos_ != "NOUN" and head.head != head:
        head = head.head
    if head.pos_ == "VERB":
        subs = [tok for tok in head.lefts if tok.dep_ == "SUB"]
        if len(subs) > 0:
            verbNegated = isNegated(head)
            subs.extend(getSubsFromConjunctions(subs))
            return subs, verbNegated
        elif head.head != head:
            return findSubs(head)
    elif head.pos_ == "NOUN":
        return [head], isNegated(tok)
    return [], False

def isNegated(tok):
    negations = {"no", "not", "n't", "never", "none"}
    for dep in list(tok.lefts) + list(tok.rights):
        if dep.lower_ in negations:
            return True
    return False

def findSVs(tokens):
    svs = []
    verbs = [tok for tok in tokens if tok.pos_ == "VERB"]
    for v in verbs:
        subs, verbNegated = getAllSubs(v)
        if len(subs) > 0:
            for sub in subs:
                svs.append((sub.orth_, "!" + v.orth_ if verbNegated else v.orth_))
    return svs

def getObjsFromPrepositions(deps):
    objs = []
    for dep in deps:
        if dep.pos_ == "ADP" and dep.dep_ == "prep":
            objs.extend([tok for tok in dep.rights if tok.dep_  in OBJECTS or (tok.pos_ == "PRON" and tok.lower_ == "me")])
    return objs

def getAdjectives(toks):
    toks_with_adjectives = []
    for tok in toks:
        adjs = [left for left in tok.lefts if left.dep_ in ADJECTIVES]
        adjs.append(tok)
        adjs.extend([right for right in tok.rights if tok.dep_ in ADJECTIVES])
        tok_with_adj = " ".join([adj.lower_ for adj in adjs])
        toks_with_adjectives.extend(adjs)

    return toks_with_adjectives

def getObjsFromAttrs(deps):
    for dep in deps:
        if dep.pos_ == "NOUN" and dep.dep_ == "attr":
            verbs = [tok for tok in dep.rights if tok.pos_ == "VERB"]
            if len(verbs) > 0:
                for v in verbs:
                    rights = list(v.rights)
                    objs = [tok for tok in rights if tok.dep_ in OBJECTS]
                    objs.extend(getObjsFromPrepositions(rights))
                    if len(objs) > 0:
                        return v, objs
    return None, None

def getObjFromXComp(deps):
    for dep in deps:
        if dep.pos_ == "VERB" and dep.dep_ == "xcomp":
            v = dep
            rights = list(v.rights)
            objs = [tok for tok in rights if tok.dep_ in OBJECTS]
            objs.extend(getObjsFromPrepositions(rights))
            if len(objs) > 0:
                return v, objs
    return None, None

def getAllSubs(v):
    verbNegated = isNegated(v)
    subs = [tok for tok in v.lefts if tok.dep_ in SUBJECTS and tok.pos_ != "DET"]
    if len(subs) > 0:
        subs.extend(getSubsFromConjunctions(subs))
    else:
        foundSubs, verbNegated = findSubs(v)
        subs.extend(foundSubs)
    return subs, verbNegated

def getAllObjs(v):
    # rights is a generator
    rights = list(v.rights)
    objs = [tok for tok in rights if tok.dep_ in OBJECTS]
    objs.extend(getObjsFromPrepositions(rights))

    potentialNewVerb, potentialNewObjs = getObjFromXComp(rights)
    if potentialNewVerb is not None and potentialNewObjs is not None and len(potentialNewObjs) > 0:
        objs.extend(potentialNewObjs)
        v = potentialNewVerb
    if len(objs) > 0:
        objs.extend(getObjsFromConjunctions(objs))
    return v, objs

def getAllObjsWithAdjectives(v):
    # rights is a generator
    rights = list(v.rights)
    objs = [tok for tok in rights if tok.dep_ in OBJECTS]

    if len(objs)== 0:
        objs = [tok for tok in rights if tok.dep_ in ADJECTIVES]

    objs.extend(getObjsFromPrepositions(rights))

    potentialNewVerb, potentialNewObjs = getObjFromXComp(rights)
    if potentialNewVerb is not None and potentialNewObjs is not None and len(potentialNewObjs) > 0:
        objs.extend(potentialNewObjs)
        v = potentialNewVerb
    if len(objs) > 0:
        objs.extend(getObjsFromConjunctions(objs))
    return v, objs

def findSVOs(tokens):
    svos = []
    verbs = [tok for tok in tokens if tok.pos_ == "VERB" and tok.dep_ != "aux"]
    for v in verbs:
        subs, verbNegated = getAllSubs(v)
        # hopefully there are subs, if not, don't examine this verb any longer
        if len(subs) > 0:
            v, objs = getAllObjs(v)
            for sub in subs:
                for obj in objs:
                    objNegated = isNegated(obj)
                    svos.append((sub.lower_, "!" + v.lower_ if verbNegated or objNegated else v.lower_, obj.lower_))
    return svos

def findSVAOs(tokens):
    svos = []
    verbs = [tok for tok in tokens if tok.pos_ == "VERB" and tok.dep_ != "aux"]
    for v in verbs:
        subs, verbNegated = getAllSubs(v)
        # hopefully there are subs, if not, don't examine this verb any longer
        if len(subs) > 0:
            v, objs = getAllObjsWithAdjectives(v)
            for sub in subs:
                for obj in objs:
                    objNegated = isNegated(obj)
                    obj_desc_tokens = generate_left_right_adjectives(obj)
                    sub_compound = generate_sub_compound(sub)
                    svos.append((" ".join(tok.lower_ for tok in sub_compound), "!" + v.lower_ if verbNegated or objNegated else v.lower_, " ".join(tok.lower_ for tok in obj_desc_tokens)))
    return svos

def generate_sub_compound(sub):
    sub_compunds = []
    for tok in sub.lefts:
        if tok.dep_ in COMPOUNDS:
            sub_compunds.extend(generate_sub_compound(tok))
    sub_compunds.append(sub)
    for tok in sub.rights:
        if tok.dep_ in COMPOUNDS:
            sub_compunds.extend(generate_sub_compound(tok))
    return sub_compunds

def generate_left_right_adjectives(obj):
    obj_desc_tokens = []
    for tok in obj.lefts:
        if tok.dep_ in ADJECTIVES:
            obj_desc_tokens.extend(generate_left_right_adjectives(tok))
    obj_desc_tokens.append(obj)

    for tok in obj.rights:
        if tok.dep_ in ADJECTIVES:
            obj_desc_tokens.extend(generate_left_right_adjectives(tok))

    return obj_desc_tokens

def punetweets(tweet,y):
    
    sub='' 
    if('sangram' in tweet or 'sanjay' in tweet or 'ramesh' in tweet or ('pune' in tweet and 'congress' in tweet)):
        sub='congress'
    elif('bankhele' in tweet or 'sharaddada' in tweet or 'gore' in tweet or'vijaybapu' in tweet or 'kuldip' in tweet or 'chabukswar' in tweet or('pune' in tweet and 'shivsena' in tweet)):
        sub='shivsena'
    elif('baburao' in tweet or 'harshwardhan' in tweet or 'laxman' in tweet or 'mahesh' in tweet or 'jagdish' in tweet or 'sidharth' in tweet or 'bhimarao' in tweet or 'madhuri' in tweet or 'sunil' in tweet or 'yogesh' in tweet or 'chabukswar' in tweet or ('pune' in tweet and 'bjp' in tweet)):
        sub='bjp'
    elif('kailas' in tweet or 'anil' in tweet or 'nimhan' in tweet or 'kishor' in tweet or 'vasant' in tweet or 'manisha' in tweet or 'ajay' in tweet or('pune' in tweet and 'mns' in tweet)):
        sub='mns'
    elif('atul' in tweet or 'dilip dattatray' in tweet or 'ashok raosaheb' in tweet or 'rameshappa' in tweet or 'dattatray' in tweet or 'ajit' in tweet or 'sunil' in tweet or 'sunil vijay' in tweet or 'dodke' in tweet or 'ashwini' in tweet or 'chetan' in tweet or ('pune' in tweet and 'ncp' in tweet)):
        sub='ncp'
    else:
        sub='other'
    return sub


def tweetsub(tweet):
    sub=''
    print("goes to tweetsub")
    tweet=tweet.lower()
    try:
        t=Translator()
        tweet=t.translate(tweet).text
    except Exception as e:
        print("error in Translator")
    
    i=tweet

    if('mns' in str(i) or 'raj ' in str(i)):
        sub='mns'

    elif('congress' in str(i) or 'inc' in str(i) or 'rahul' in str(i) or 'gandhi' in str(i) or 'cong' in str(i) or 'upa' in str(i)):
        sub='congress'
    elif('shivsena' in str(i)or 'thackeray' in str(i) or'bmc' in str(i) or 'uddhav' in str(i) or 'aditya' in str(i) or 'nda' in str(i)):
        sub='shivsena'
    elif('ncp' in str(i) or 'sharad' in str(i) or 'pawar' in str(i)):
        sub='ncp'
    elif('bjp' in str(i) or'government' in str(i) or'govt' in str(i) or 'fadnavis' in str(i)or 'BJP4India' in tweet or 'BJP4Maharashtra' in str(i) or 'amit' in str(i) or 'bmc'in str(i) or 'modi' in str(i)):
        sub='bjp'    
    else:
        sub='other'

    return sub


def findsub(a,tweet,y):
    coff=0
    lst=[]
    sb_lst=[]
    co_sub=0
    sentence=''
    temp=''
    sub=''
    for i in a:
        print(i)
        if(i is None):
            continue
        if('mns' in str(i) or 'raj' in str(i)):
           
            if(coff==0):
               
                sub='mns'
                co_sub=1
                temp=''
                for j in i:
                    print(j)
                    temp=temp+" "+j
                sentence=sentence+" "+temp
                coff=1
            elif(coff==1):
                print('Comes here')
                if(sub=='mns'):
                    temp=''
                    for j in i:
                        temp=temp+" "+j
                    sentence=sentence+" "+temp
                else:
                    lst.append(sentence)
                    sb_lst.append(sub)
                    sentence=''
                    sub='mns'
                    temp=''
                    for j in i:
                        temp=temp+" "+j
                    sentence=sentence+" "+temp

        elif('congress' in str(i) or 'inc' in str(i) or 'rahul' in str(i) or 'gandhi' in str(i)or 'upa' in str(i)):
           
            if(coff==0):
                co_sub=1
                sub='congress'
                temp=''
                for j in i:
                    temp=temp+" "+j
                sentence=sentence+" "+temp
                coff=1
            elif(coff==1):
                if(sub=='congress'):
                    temp=''
                    for j in i:
                        temp=temp+" "+j
                    sentence=sentence+" "+temp
                else:
                    lst.append(sentence)
                    sb_lst.append(sub)
                    sentence=''
                    sub='congress'
                    temp=''
                    for j in i:
                        temp=temp+" "+j
                    sentence=sentence+" "+temp
        elif('shivsena' in str(i)or 'thackeray' in str(i) or'bmc' in str(i) or 'uddhav' in str(i) or 'aditya' in str(i) or 'nda' in str(i)):
            if(coff==0):
                co_sub=1
                sub='shivsena'
                temp=''
                for j in i:
                    temp=temp+" "+j
                sentence=sentence+" "+temp
                coff=1
            elif(coff==1):
                if(sub=='shivsena'):
                    temp=''
                    for j in i:
                        temp=temp+" "+j
                    sentence=sentence+" "+temp
                else:
                    lst.append(sentence)
                    sb_lst.append(sub)
                    sentence=''
                    sub='shivsena'
                    temp=''
                    for j in i:
                        temp=temp+" "+j
                    sentence=sentence+" "+temp
        elif('ncp' in str(i) or 'sharad' in str(i) or 'pawar' in str(i)):
           
            if(coff==0):
                co_sub=1
                sub='ncp'
                temp=''
                for j in i:
                    temp=temp+" "+j
                sentence=sentence+" "+temp
                coff=1
            elif(coff==1):
                if(sub=='ncp'):
                    temp=''
                    for j in i:
                        temp=temp+" "+j
                    sentence=sentence+" "+temp
                else:
                    lst.append(sentence)
                    sb_lst.append(sub)
                    sentence=''
                    sub='ncp'
                    temp=''
                    for j in i:
                        temp=temp+" "+j
                    sentence=sentence+" "+temp
        elif('bjp' in str(i) or'government' in str(i) or'govt' in str(i) or 'fadnavis' in str(i) or 'bmc'in str(i) or 'modi' in str(i)):
           
            if(coff==0):
                co_sub=1
                sub='bjp'
                temp=''
                for j in i:
                    temp=temp+" "+j
                sentence=sentence+" "+temp
                coff=1
            elif(coff==1):
                if(sub=='bjp'):
                    temp=''
                    for j in i:
                        temp=temp+" "+j
                    sentence=sentence+" "+temp
                else:
                    lst.append(sentence)
                    sb_lst.append(sub)
                    sentence=''
                    sub='bjp'
                    temp=''
                    for j in i:
                        temp=temp+" "+j
                    sentence=sentence+" "+temp                    
        else:
           
            temp=''
            for j in i:
                temp=temp+" "+j
            sentence=sentence+" "+temp
            if(co_sub==0):
                co_sub==1
                sub='other'
    lst.append(sentence)
    #print(lst)
    
    final_lst=[]
    print(sub)
    #punetweets(tweet,y)
    if(sub=='other'):
        sub=tweetsub(tweet)
        lst=[]
        lst.append(tweet.lower())
    sb_lst.append(sub)
    if(len(sb_lst)==1):
        lst=[]
        y=re.sub(r'#\w+','',y)
        y=re.sub(r'@\w+', '', y)
        y=re.sub(r'http.?://[^\s]+[\s]?', '', y)
        y=re.sub(r'_dark_skin_tone','',y)
        y=re.sub(r'\n','',y)
        y=re.sub(r'_light_skin_tone','',y)
        y=re.sub(r'_medium-dark_tone','',y)
        y=re.sub(r'_medium-light_tone','',y)
        y=re.sub(r'_medium_tone','',y)
        try:
            t=Translator()
            y=t.translate(str(y)).text
        except Exception as e:
            print("error in Translator")
        
        print("comes here after Translator")
        lst.append(y.lower())
    #print(sb_lst)
    final_lst.append(lst)
    final_lst.append(sb_lst)
    return final_lst


# # # # TWITTER STREAMER # # # #
class TwitterStreamer():
    """
    Class for streaming and processing live tweets.
    """
    def __init__(self):
        pass

    def stream_tweets(self, fetched_tweets_filename, hash_tag_list,db1):
        # This handles Twitter authetification and the connection to Twitter Streaming API
        listener = StdOutListener(fetched_tweets_filename,db1)
        auth = OAuthHandler(twitter_credentials.CONSUMER_KEY, twitter_credentials.CONSUMER_SECRET)
        auth.set_access_token(twitter_credentials.ACCESS_TOKEN, twitter_credentials.ACCESS_TOKEN_SECRET)
        stream = Stream(auth, listener)

        # This line filter Twitter Streams to capture data by the keywords: 
        stream.filter(track=hash_tag_list)
        #stream.filer(locations=[72.805557,18.888376, 72.792638 ,19.308999, 73.145248,19.239641,73.110421,18.978596]) 


# # # # TWITTER STREAM LISTENER # # # #
class StdOutListener(StreamListener):
    """
    This is a basic listener that just prints received tweets to stdout.
    """
    df=pd.DataFrame()
    def __init__(self, fetched_tweets_filename,db1):
        self.fetched_tweets_filename = fetched_tweets_filename
        self.db1=db1

    def on_data(self, data):
        try:            
            #This is where we start getting tweets
            client=MongoClient(MONGO_HOST)

            db=client.twitterdb
            print(type(data))
            ok=json.loads(data)
            print(type(ok))
            db.tweets.insert(ok)
            i=ok
            if (u'retweeted_status' in i.keys()):
                    try:
                        tweet = i['retweeted_status']['extended_tweet']["full_text"]
                    except:
                        tweet = i['retweeted_status']['text']
                    #print("new tweet"+ tweet)
            else:
                if(u'extended_tweet' in i.keys()):
                    tweet=i['extended_tweet']['full_text']
                else:
                    tweet=i['text']
            tweet=emoji.demojize(tweet)
            y=tweet
            #demojise emoji and remove hashtags and'@'
            tweet=re.sub(r'_dark_skin_tone','',tweet)
            tweet=re.sub(r'\n','',tweet)
            tweet=re.sub(r'_light_skin_tone','',tweet)
            tweet=re.sub(r'_medium-dark_tone','',tweet)
            tweet=re.sub(r'_medium-light_tone','',tweet)
            tweet=re.sub(r'_medium_tone','',tweet)
            tweet=re.sub(r'#','',tweet)
            tweet=re.sub(r'@', '', tweet)
            tweet=re.sub(r"'s", '', tweet)
            tweet=re.sub(r'http.?://[^\s]+[\s]?', '', tweet)
            tweet=re.sub(r':','',tweet)
            parser = spacy.load('en', disable=['ner','textcat'])
            parse = parser(str(tweet))
            #findSVAOS function to get split sentences
            ans=(findSVAOs(parse))
            print("tweet is "+tweet)
            #print(ans)
            if(not ans):
                ans=list(tweet)
                ans.append('')
            final_list=[]
            final_list=findsub(ans,tweet,y)
            print(final_list)
            #the next 7-8 line were to find and predict seats for pune.This is  an extra thing,You can ignore it
            pune_sub=''
            pune_sub=punetweets(tweet,y)
            pune_dict=db.pune.find_one({"_id":10})
            db.pune.update_one({
              "_id": 10
            },{
              '$inc': {
                str(pune_sub): 1
              }
            }, upsert=False)
            #write json for each day
            date_today=date.today()
            with open(self.fetched_tweets_filename+str(date_today)+".json", 'a') as tf:
                tf.write(data+",")
            #get documents from firebase
            doc_ref = db1.collection(u'data').document(u'volume')
            try:
                doc = doc_ref.get()
                print(u'Document data: {}'.format(doc.to_dict()))
            except google.cloud.exceptions.NotFound:
                print(u'No such document!')
            doc2=doc.to_dict()
            #print(type(doc2))

            doc_ref = db1.collection(u'data').document(u'sentiment')
            try:
                doc = doc_ref.get()
                print(u'Document data: {}'.format(doc.to_dict()))
            except google.cloud.exceptions.NotFound:
                print(u'No such document!')
            doc1=doc.to_dict()
            #to do the updation of documents to firebase
            for j in range(len(final_list[1])):
                doc2[final_list[1][j]]+=1;
                c=textblob.Sentence(final_list[0][j])
                senti=c.sentiment.polarity
                print(senti)
                if(senti>0.2):
                    doc1[final_list[1][j]+"_positive"]+=1
                elif(senti==0):
                    continue
                elif(senti<0.2):
                    doc1[final_list[1][j]+"_negative"]+=1
                else:
                    continue
                 
            db1.collection(u'data').document(u'volume').set(doc2)
            db1.collection(u'data').document(u'sentiment').set(doc1) 


            
            return True
        except BaseException as e:
            print("Error on_data %s" % str(e))
        return True
          

    def on_error(self, status):
        print(status)

 
if __name__ == '__main__':
 	
    MONGO_HOST='mongodb://localhost/twitterdb'
    # Authenticate using config.py and connect to Twitter Streaming API.
    #Hashtag list gives the list of hashtags you want to search by
    hash_tag_list = ["maharashtra elections","bjp elections","congress elections","mh elections","maharashtra","shivsena","mns","shivsena elections","mns elections","ncp","sharad pawar","bal thackeray","devendra fadnavis"]
    date_today=date.today()
    cred = credentials.Certificate("ServiceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db1=firestore.client()
    fetched_tweets_filename = "tweets-"
    #df=pd.DataFrame()
    twitter_streamer = TwitterStreamer()
    twitter_streamer.stream_tweets(fetched_tweets_filename, hash_tag_list,db1)
