from django.db import models
from django.conf import settings
from django.apps import apps as django_apps

from twitter_stream.fields import PositiveBigAutoForeignKey, PositiveBigIntegerField

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

_stoplist = None
def stoplist():
    global _stoplist
    if not _stoplist:
        from nltk.corpus import stopwords
        _stoplist = stopwords.words('english')
    return _stoplist
    
class Dictionary(models.Model):
    name = models.CharField(max_length=100)
    time = models.DateTimeField(auto_now_add=True)
    
    num_docs = PositiveBigIntegerField(default=0)
    num_pos = PositiveBigIntegerField(default=0)
    num_nnz = PositiveBigIntegerField(default=0)
    
    @property
    def gensim_dictionary(self):
        if not hasattr(self, '_gensim_dict'):
            setattr(self, '_gensim_dict', self._make_gensim_dictionary())
        return getattr(self, '_gensim_dict')
    
    def get_word_id(self, bow_index):
        if not hasattr(self, '_index2id'):
            g = self.gensim_dictionary
        try:
            return self._index2id[bow_index]
        except KeyError:
            return None
    
    def _make_gensim_dictionary(self):
        
        logger.info("Building gensim dictionary from database")
        
        setattr(self, '_index2id', {})
        
        from gensim import corpora
        gensim_dict = corpora.Dictionary()
        gensim_dict.num_docs = self.num_docs
        gensim_dict.num_pos = self.num_pos
        gensim_dict.num_nnz = self.num_nnz
        
        for word in self.words.all():
            self._index2id[word.index] = word.id
            gensim_dict.token2id[word.text] = word.index
            gensim_dict.dfs[word.index] = word.document_frequency
        
        logger.info("Dictionary contains %d words" % len(gensim_dict.token2id))
        
        return gensim_dict
    
    @classmethod
    def _create_from_gensim_dictionary(cls, gensim_dict, name="default dictionary"):
        
        logger.info("Saving gensim dictionary '%s' in the database" % name)
        
        dict_model = cls(name=name)
        dict_model.num_docs = gensim_dict.num_docs
        dict_model.num_pos = gensim_dict.num_pos
        dict_model.num_nnz = gensim_dict.num_nnz
        dict_model.save()
        
        batch = []
        count = 0
        print_freq = 10000
        batch_size = 1000
        total_words = len(gensim_dict.token2id)
        
        for token, id in gensim_dict.token2id.iteritems():
            word = Word(dictionary=dict_model,
                        text=token,
                        index=id,
                        document_frequency=gensim_dict.dfs[id])
            batch.append(word)
            count += 1
            
            if len(batch) > batch_size:
                Word.objects.bulk_create(batch)
                batch = []
                
                if settings.DEBUG:
                    # prevent memory leaks
                    from django.db import connection
                    connection.queries = []
            
            if count % print_freq == 0:
                logger.info("Saved %d / %d words in the database dictionary" % (count, total_words))
                
        if len(batch):
            Word.objects.bulk_create(batch)
            count += len(batch)
            
            logger.info("Saved %d / %d words in the database dictionary" % (count, total_words))
        
        return dict_model
        
    @classmethod
    def _create_from_texts(cls, tokenized_texts, name="default dictionary"):
        from gensim.corpora import Dictionary as GensimDictionary
        
        # build a dictionary
        logger.info("Building a dictionary from texts")
        dictionary = GensimDictionary(tokenized_texts)
        
        # Remove extremely rare words
        logger.info("Dictionary contains %d words. Filtering..." % len(dictionary.token2id))
        dictionary.filter_extremes(no_below=2, no_above=0.5, keep_n=None)
        dictionary.compactify()
        logger.info("Dictionary contains %d words." % len(dictionary.token2id))
        
        return cls._create_from_gensim_dictionary(dictionary, name=name)
    
    @classmethod
    def create_from_tweets(cls, name="tweet dictionary"):
        Tweet = django_apps.get_model(settings.TWITTER_STREAM_TWEET_MODEL)
        queryset = Tweet.objects.all()
        
        texts = DbTextIterator(queryset, textfield="text")
        tokenized_texts = Tokenizer(texts, stoplist=stoplist())
        
        dictionary = cls._create_from_texts(tokenized_texts, name=name)
        dictionary._vectorize_corpus(queryset, tokenized_texts, TweetWord, textfield='text')
        
        return dictionary
    
    @classmethod
    def create_from_chats(cls, name="chat dictionary"):
        Message = django_apps.get_model('textprizm.Message')
        queryset = Message.objects.filter(type=0)
        
        texts = DbTextIterator(queryset, textfield="message")
        tokenized_texts = Tokenizer(texts, stoplist=stoplist())
        
        dictionary = cls._create_from_texts(tokenized_texts, name=name)
        dictionary._vectorize_corpus(queryset, tokenized_texts, TextPrizmWord, textfield='message')
        
    def _vectorize_corpus(self, queryset, tokenizer, wv_class, textfield='text'):
        
        logger.info("Saving document word vectors in corpus.")
        
        gdict = self.gensim_dictionary
        count = 0
        total_count = queryset.count()
        batch = []
        batch_size = 1000
        print_freq = 10000
        
        for obj in queryset.iterator():
            text = getattr(obj, textfield)
            bow = gdict.doc2bow(tokenizer.tokenize(text))
            
            for word_index, word_freq in bow:
                word_id = self.get_word_id(word_index)
                batch.append(wv_class.create(word_id=word_id,
                                             weight=word_freq,
                                             source_obj=obj))
            count += 1
            
            if len(batch) > batch_size:
                wv_class.objects.bulk_create(batch)
                batch = []
                
                if settings.DEBUG:
                    # prevent memory leaks
                    from django.db import connection
                    connection.queries = []
            
            if count % print_freq == 0:
                logger.info("Saved word-elements for %d / %d documents" % (count, total_count))
                
        if len(batch):
            wv_class.objects.bulk_create(batch)
            logger.info("Saved word-elements for %d / %d documents" % (count, total_count))
        
        logger.info("Created %d word vector entries" % count)
        
            
class Word(models.Model):
    dictionary = models.ForeignKey(Dictionary, related_name='words')
    index = models.IntegerField()
    text = models.CharField(max_length=100)
    document_frequency = models.IntegerField()
    

class TopicModel(models.Model):
    dictionary = models.ForeignKey(Dictionary)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    time = models.DateTimeField(auto_now_add=True)

class Topic(models.Model):
    model = models.ForeignKey(TopicModel)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)


class AbstractWordVector(models.Model):
    class Meta:
        abstract = True
        
    word = models.ForeignKey(Word)
    weight = models.FloatField()
    
    @classmethod
    def create(cls, word_id, source_obj, weight):
        wv = cls(word_id=word_id, weight=weight)
        setattr(wv, cls.source_field, source_obj)
        return wv
            
    
class TopicWord(AbstractWordVector):
    topic = models.ForeignKey(Topic)
    source_field = 'topic'
    
class TextPrizmWord(AbstractWordVector):
    message = models.ForeignKey('textprizm.Message')
    source_field = 'message'
    
class TweetWord(AbstractWordVector):
    tweet = PositiveBigAutoForeignKey(settings.TWITTER_STREAM_TWEET_MODEL)
    source_field = 'tweet'
    
class DbTextIterator(object):
    def __init__(self, queryset, textfield='text'):
        self.queryset = queryset
        self.textfield = textfield
        self.current_position = 0
        self.current = None
        
    def __iter__(self):
        self.current_position = 0
        for obj in self.queryset.iterator():
            self.current = obj
            self.current_position += 1
            if self.current_position % 10000 == 0:
                logger.info("Iterating through database texts: item %d" % self.current_position)
                
            yield getattr(obj, self.textfield)


class Tokenizer(object):
    def __init__(self, texts=None, stoplist=None):
        self.texts = texts
        self.stoplist = stoplist
        self.max_length = Word._meta.get_field('text').max_length
        if self.stoplist is None:
            self.stoplist = []
        
    def __iter__(self):
        if self.texts is None:
            raise RuntimeError("Tokenizer can only iterate if given texts")
            
        for text in self.texts:
            yield self.tokenize(text)
            
    def tokenize(self, text):
        words = []
        for word in text.lower().split():
            if word not in self.stoplist:
                if len(word) >= self.max_length:
                    word = word[:self.max_length-1]
                words.append(word)
        return words