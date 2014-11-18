from django.conf import settings
from models import Dictionary, TextPrizmWord, TweetWord, Word
from django.apps import apps as django_apps

import nltk

import logging
logger = logging.getLogger(__name__)

__all__ = ['get_twitter_context', 'get_chat_context', 'Dictionary']

_stoplist = None
def get_stoplist():
    global _stoplist
    if not _stoplist:
        from nltk.corpus import stopwords
        _stoplist = stopwords.words('english')
    return _stoplist



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


class DbWordVectorIterator(object):
    def __init__(self, dictionary, wv_class, freq_field='tfidf'):
        self.dictionary = dictionary
        self.wv_class = wv_class
        self.freq_field = freq_field

    def __iter__(self):
        qset = self.wv_class.objects.filter(dictionary=self.dictionary).order_by('source')
        current_position = 0

        current_source = None
        current_vector = []
        for wv in qset.iterator():
            source_id = wv.source_id
            word_idx = wv.word_index
            freq = getattr(wv, self.freq_field)

            if current_source is None:
                current_source = source_id
                current_vector = []

            if current_source != source_id:
                yield current_vector
                current_vector = []
                current_source = source_id
                current_position += 1

                if current_position % 10000 == 0:
                    logger.info("Iterating through database word-vectors: item %d" % current_position)

            current_vector.append((word_idx, freq))

        # one more extra one
        yield current_vector

    def __len__(self):
        from django.db.models import Count
        count = self.wv_class.objects.filter(dictionary=self.dictionary).aggregate(Count('source', distinct=True))
        if count:
            return count['source__count']



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
        for word in self.split(text.lower()):
            if word not in self.stoplist:
                if len(word) >= self.max_length:
                    word = word[:self.max_length-1]
                words.append(word)
        return words

    def split(self, text):
        return text.split()

class WordTokenizer(Tokenizer):
    def split(self, text):
        return nltk.word_tokenize(text)

class TaskContext(object):

    def __init__(self, name, queryset, textfield, word_vector_class, tokenizer, stoplist=None):
        self.name = name
        self.queryset = queryset
        self.textfield = textfield
        self.word_vector_class = word_vector_class
        self.tokenizer = tokenizer
        self.stoplist = stoplist

    def queryset_str(self):
        return str(self.queryset.query)

    def find_dictionary(self):
        results = Dictionary.objects.filter(name=self.name,
                                            tokenizer=self.tokenizer.__name__,
                                            dataset=self.queryset_str(),
                                            stoplist=self.stoplist is not None)

        return results.last()


    def build_dictionary(self):

        texts = DbTextIterator(self.queryset, textfield=self.textfield)

        tokenized_texts = self.tokenizer(texts, stoplist=self.stoplist)

        return Dictionary._create_from_texts(tokenized_texts=tokenized_texts,
                                             name=self.name,
                                             tokenizer=self.tokenizer.__name__,
                                             dataset=self.queryset_str(),
                                             stoplist=self.stoplist is not None)

    def bows_exist(self, dictionary):
        return self.word_vector_class.objects.filter(dictionary=dictionary).exists()


    def build_bows(self, dictionary):

        texts = DbTextIterator(self.queryset, textfield=self.textfield)
        tokenized_texts = self.tokenizer(texts, stoplist=self.stoplist)

        dictionary._vectorize_corpus(queryset=self.queryset,
                                     tokenizer=tokenized_texts,
                                     wv_class=self.word_vector_class,
                                     textfield=self.textfield)

    def build_lda(self, dictionary):
        corpus = DbWordVectorIterator(dictionary, self.word_vector_class)
        dictionary._build_lda(self.name, corpus)



def get_chat_context(name):

    Message = django_apps.get_model('textprizm.Message')
    queryset = Message.objects.filter(type=0, participant_id__gt=2)
    textfield = "message"

    return TaskContext(name=name, queryset=queryset,
                       textfield=textfield,
                       word_vector_class=TextPrizmWord,
                       tokenizer=WordTokenizer,
                       stoplist=get_stoplist())


def get_twitter_context(name):

    Tweet = django_apps.get_model(settings.TWITTER_STREAM_TWEET_MODEL)
    queryset = Tweet.objects.all()
    textfield = 'text'

    return TaskContext(name=name, queryset=queryset,
                       textfield=textfield,
                       word_vector_class=TweetWord,
                       tokenizer=WordTokenizer,
                       stoplist=get_stoplist())

