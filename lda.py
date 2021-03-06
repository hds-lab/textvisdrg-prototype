"""
This script extracts topics from textprizm csv files
and tweet csv files using gensim.

To run it, you must have gensim and nltk installed.
Maybe other stuff too.

Before you run, you should have the following directory structure:

some_dir/
  lda.py (this script)
  textprizm/
    data_points.csv
  tweets/
    twitter_stream_tweet.csv

Run: python lda.py

This will create a bunch of files in the
textprizm and tweets folders for processed corpora,
dictionaries, and topic models output from gensim.

Hooray.
"""

import csv
import codecs
from os import path

from gensim import corpora, models, similarities

# Get the stopwords corpus
import nltk
nltk.download('stopwords')

from nltk.corpus import stopwords

class CsvTexts(object):
    def __init__(self, filename, textfield='text', 
                 file_encoding='utf-8', target_encoding='utf-8', 
                 filter=None):
        self.filename = filename
        self.textfield = textfield
        self.file_encoding = file_encoding
        self.target_encoding = target_encoding
        self.filter = filter
        
    def __iter__(self):
        # we can read data in various encodings
        if self.file_encoding is None or self.file_encoding == 'utf-8':
            file_reader = open
        else:
            file_reader = codecs.getreader(self.file_encoding)
        
        with file_reader(self.filename, 'rb') as infile:

            cleaned = (line.replace('\0','') for line in infile)
            reader = csv.DictReader(cleaned)
            
            if self.textfield not in reader.fieldnames:
                raise RuntimeError("File %s does not include field %s" % (self.filename, self.textfield))
            
            for row in reader:
            
                if self.filter is not None:
                    row = self.filter(row)
                    if not row:
                        continue
                        
                if self.target_encoding is None or self.target_encoding == self.file_encoding:
                    # no re-coding necessary
                    yield row[self.textfield]
                else:
                    # we need to re-encode the data as some other encoding
                    yield unicode(row[self.textfield], self.target_encoding)

class Tokenizer(object):
    def __init__(self, texts, stoplist=None):
        self.texts = texts
        self.stoplist = stoplist
        if self.stoplist is None:
            self.stoplist = []
        
    def __iter__(self):
        for text in self.texts:
            yield [word for word in text.lower().split() if word not in self.stoplist]
            
class BowCorpus(object):
    def __init__(self, tokenized, dictionary):
        self.tokenized = tokenized
        self.dictionary = dictionary
        
    def __iter__(self):
        for tokens in self.tokenized:
            # assume there's one document per line, tokens separated by whitespace
            yield self.dictionary.doc2bow(tokens)


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
    distributed = False
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

    ## Hierarchical Dirichle Processes
    ## This takes forever...
    #hdp = get_hdp(hdp_name,
    #              corpus_tfidf,
    #              id2word=dictionary)
    #hdp.print_topics(topics=num_topics)
    
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
    
