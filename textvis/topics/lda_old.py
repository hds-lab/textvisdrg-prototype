import csv
import codecs
from os import path

from gensim import corpora, models, similarities
from nltk.corpus import stopwords


class DbTexts(object):
    def __init__(self, model, textfield='text', filter=None):
        self.model = model
        self.textfield = textfield
        self.filter = filter
        
    def __iter__(self):
        for obj in self.model.objects.all().iterator():
            
            if self.filter is not None:
                obj = self.filter(obj)
                if not obj:
                    continue
            
            yield getattr(obj, self.textfield)

class Tokenizer(object):
    def __init__(self, texts, stoplist=None):
        self.texts = texts
        self.stoplist = stoplist
        if self.stoplist is None:
            self.stoplist = []
        
    def __iter__(self):
        from models import Word
        max_length = Word._meta.get_field('text').max_length 
        
        for text in self.texts:
            words = []
            for word in text.lower().split():
                if word not in self.stoplist:
                    if len(word) >= max_length:
                        word = word[:max_length-1]
                    words.append(word)
            yield words
            
class BowCorpus(object):
    def __init__(self, tokenized, dictionary):
        self.tokenized = tokenized
        self.dictionary = dictionary
        
    def __iter__(self):
        for tokens in self.tokenized:
            # assume there's one document per line, tokens separated by whitespace
            yield self.dictionary.doc2bow(tokens)

def build_tweet_dictionary():
    import logging
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)
    
    from twitter_stream.models import Tweet
    
    stoplist = stopwords.words('english')
    
    texts = DbTexts(Tweet)
    tokenized = Tokenizer(texts, stoplist=stoplist)
    
    # build a dictionary
    print "Building a dictionary"
    dictionary = corpora.Dictionary(tokenized)
    
    # Remove extremely rare words
    dictionary.filter_extremes(no_below=2, no_above=0.5, keep_n=None)
    dictionary.compactify()
    
    # Save it in the database
    print "Saving the tweet dict"
    
    from models import Dictionary
    return Dictionary.create_from_gensim_dictionary(dictionary, "tweets dictionary")

    
def cacheable(obj_class):
    """
    Get from cache for any class that extends
    gensim.corpora.indexedcorpus.IndexedCorpus
    or gensim.utils.SaveLoad.
    
    Apply the decorator to a function that constructs
    a new instance of the object.
    
    Supply the class used to build objects as an argument to the decorator.
    """
    
    from gensim.corpora.indexedcorpus import IndexedCorpus
    from gensim.utils import SaveLoad
    
    if issubclass(obj_class, IndexedCorpus):
        def save(fname, obj):
            obj_class.serialize(fname, obj)
        load = obj_class
    
    elif issubclass(obj_class, SaveLoad):
        def save(fname, obj):
            obj.save(fname)
        def load(fname):
            return obj_class.load(fname)

    def wrap(constructor):
            
        def inner(cache_filename, *args, **kwargs):
            if not path.isfile(cache_filename):
                obj = constructor(*args, **kwargs)
                save(cache_filename, obj)
            else:
                obj = load(cache_filename)
                
            return obj
            
        return inner
        
    return wrap

@cacheable(corpora.Dictionary)
def get_dictionary(tokenized):
    dictionary = corpora.Dictionary(tokenized)
    # Remove extremely rare words
    dictionary.filter_extremes(no_below=2, no_above=0.5, keep_n=None)
    dictionary.compactify()
    return dictionary
    
@cacheable(corpora.MmCorpus)
def get_corpus(tokenized, dictionary):
    return BowCorpus(tokenized, dictionary)
    
@cacheable(models.TfidfModel)
def get_tfidf(*args, **kwargs):
    return models.TfidfModel(*args, **kwargs)

@cacheable(models.LsiModel)
def get_lsi(*args, **kwargs):
    return models.LsiModel(*args, **kwargs)

@cacheable(models.LdaModel)
def get_lda(*args, **kwargs):
    return models.LdaModel(*args, **kwargs)

@cacheable(models.LdaMulticore)
def get_lda_multi(*args, **kwargs):
    return models.LdaMulticore(*args, **kwargs)

@cacheable(models.HdpModel)
def get_hdp(*args, **kwargs):
    return models.HdpModel(*args, **kwargs)

def analyze_text(texts, targetdir='', file_prefix=None, stoplist=None):
    tokenized = Tokenizer(texts, stoplist=stoplist)
    
    if file_prefix is not None:
        file_prefix = '%s.' % file_prefix
    else:
        file_prefix = ''

    num_topics = 50
    distributed = True
    workers = 3
        
    dictionary_name = path.join(targetdir, '%sdictionary.dict' % file_prefix)
    corpus_name = path.join(targetdir, '%scorpus.mm' % file_prefix)
    tfidf_name = path.join(targetdir, '%smodel.tfidf' % file_prefix)
    lsi_name = path.join(targetdir, '%smodel.%s.lsi' % (file_prefix, num_topics))
    lda_name = path.join(targetdir, '%smodel.%s.lda' % (file_prefix, num_topics))
    lda_multi_name = path.join(targetdir, '%smodel.%s.lda_multi' % (file_prefix, num_topics))
    hdp_name = path.join(targetdir, '%smodel.hdp' % file_prefix)
    
    dictionary = get_dictionary(dictionary_name, tokenized)
    corpus = get_corpus(corpus_name, tokenized, dictionary)

    tfidf = get_tfidf(tfidf_name, corpus)
    corpus_tfidf = tfidf[corpus]

    lsi = get_lsi(lsi_name,
                  corpus_tfidf, 
                  num_topics=num_topics,
                  distributed=distributed,
                  id2word=dictionary)
    lsi.print_topics(num_topics=num_topics)

    lda = get_lda(lda_name,
                  corpus_tfidf, 
                  num_topics=num_topics, 
                  id2word=dictionary, 
                  distributed=distributed)
    lda.print_topics(num_topics=num_topics)

    lda_multi = get_lda_multi(lda_multi_name,
                              corpus_tfidf,
                              num_topics=num_topics,
                              workers=workers,
                              id2word=dictionary)
    lda_multi.print_topics(num_topics=num_topics)

    hdp = get_hdp(hdp_name,
                  corpus_tfidf,
                  id2word=dictionary)
    hdp.print_topics(topics=num_topics)
    
def main():
    
    import logging
    logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG)
    
    stoplist = stopwords.words('english')
    
    tweets = CsvTexts("tweets/twitter_stream_tweet.csv")
    analyze_text(tweets, targetdir='tweets', file_prefix="nostop", stoplist=stoplist)
    
    def chatfilter(row):
        if str(row['type']) != '0':
            return None
        return row
    
    chats = CsvTexts("textprizm/data_points.csv", textfield="message", filter=chatfilter)
    analyze_text(chats, targetdir='textprizm', file_prefix="nostop", stoplist=stoplist)
    
if __name__ == '__main__':
    main()
    
