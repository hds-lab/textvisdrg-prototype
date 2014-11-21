from django.db import models
from django.conf import settings
from django.apps import apps as django_apps

from twitter_stream.fields import PositiveBigAutoForeignKey, PositiveBigIntegerField

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

class Dictionary(models.Model):
    name = models.CharField(max_length=100)
    dataset = models.CharField(max_length=450)
    stoplist = models.CharField(max_length=100)
    tokenizer = models.CharField(max_length=100)

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

    def _populate_from_gensim_dictionary(self, gensim_dict):

        self.num_docs = gensim_dict.num_docs
        self.num_pos = gensim_dict.num_pos
        self.num_nnz = gensim_dict.num_nnz
        self.save()

        logger.info("Saving gensim dictionary '%s' in the database" % self.name)

        batch = []
        count = 0
        print_freq = 10000
        batch_size = 1000
        total_words = len(gensim_dict.token2id)
        
        for token, id in gensim_dict.token2id.iteritems():
            word = Word(dictionary=self,
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
        
        return self
        
    @classmethod
    def _create_from_texts(cls, tokenized_texts, name, dataset, stoplist, tokenizer):
        from gensim.corpora import Dictionary as GensimDictionary
        
        # build a dictionary
        logger.info("Building a dictionary from texts")
        dictionary = GensimDictionary(tokenized_texts)
        
        # Remove extremely rare words
        logger.info("Dictionary contains %d words. Filtering..." % len(dictionary.token2id))
        dictionary.filter_extremes(no_below=2, no_above=0.5, keep_n=None)
        dictionary.compactify()
        logger.info("Dictionary contains %d words." % len(dictionary.token2id))

        dict_model = cls(name=name,
                         dataset=dataset,
                         stoplist=stoplist,
                         tokenizer=tokenizer)
        dict_model.save()

        dict_model._populate_from_gensim_dictionary(dictionary)

        return dict_model

    def _vectorize_corpus(self, queryset, tokenizer, wv_class, textfield='text'):

        import math

        logger.info("Saving document word vectors in corpus.")

        total_documents = self.num_docs
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
                document_freq = gdict.dfs[word_index]
                tfidf = word_freq * math.log(total_documents, document_freq)
                batch.append(wv_class.create(dictionary=self,
                                             word_id=word_id,
                                             word_index=word_index,
                                             count=word_freq,
                                             tfidf=tfidf,
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


    def _build_lda(self, name, corpus, num_topics=30):
        from gensim.models import LdaMulticore

        gdict = self.gensim_dictionary

        lda = LdaMulticore(corpus=corpus,
                           num_topics=num_topics,
                           workers=3,
                           id2word=gdict)

        model = TopicModel(name=name, dictionary=self)
        model.save()

        topics = lda.show_topics(num_topics=num_topics, num_words=200, formatted=False)
        for i in range(num_topics):
            topic = lda.show_topic(i, topn=200)
            alpha = lda.alpha[i]

            topicm = Topic(model=model, name="?", alpha=alpha)
            topicm.save()

            words = []
            for prob, word_text in topic:
                word_index = gdict.token2id[word_text]
                word_id = self.get_word_id(word_index)
                tw = TopicWord(topic=topicm,
                               word_id=word_id, word_index=word_index,
                               probability=prob)
                words.append(tw)
            TopicWord.objects.bulk_create(words)
            
        lda.save("lda_out_%d.model" % model.id)
        
        
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
    model = models.ForeignKey(TopicModel, related_name='topics')
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=200)
    alpha = models.FloatField()


class AbstractWordVector(models.Model):
    class Meta:
        abstract = True
        index_together = ['dictionary', 'source']

    dictionary = models.ForeignKey(Dictionary, db_index=False)
    word = models.ForeignKey(Word)
    word_index = models.IntegerField()
    count = models.FloatField()
    tfidf = models.FloatField()

    @classmethod
    def create(cls, dictionary, word_id, word_index, source_obj, count, tfidf):
        return cls(dictionary=dictionary,
                   word_id=word_id, word_index=word_index,
                   count=count, tfidf=tfidf,
                   source=source_obj)

    
class TopicWord(models.Model):
    word = models.ForeignKey(Word)
    word_index = models.IntegerField()
    probability = models.FloatField()
    topic = models.ForeignKey(Topic, related_name='words')
    
class TextPrizmWord(AbstractWordVector):
    source = models.ForeignKey('textprizm.Message')
    
class TweetWord(AbstractWordVector):
    source = PositiveBigAutoForeignKey(settings.TWITTER_STREAM_TWEET_MODEL)
