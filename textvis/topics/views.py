from django.shortcuts import render
from django.views.generic import ListView, DetailView

import models

# Create your views here.
class TopicModelIndexView(ListView):
    context_object_name = 'topic_models'
    queryset = models.TopicModel.objects.all()
    template_name = 'topics/models.html'


class TopicModelDetailView(DetailView):
    pk_url_kwarg = 'model_id'
    context_object_name = 'topic_model'
    model = models.TopicModel
    template_name = 'topics/model_detail.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(TopicModelDetailView, self).get_context_data(**kwargs)

        # Add in a QuerySet of words for each topic
        words_for_topics = {}
        max_words = 0
        topics = context['topic_model'].topics.all().prefetch_related('words')
        for topic in topics:
            words = list(topic.words.order_by('-probability').prefetch_related('word'))
            words_for_topics[topic.id] = words
            max_words = max(max_words, len(words))

        # transpose the word lists
        word_rows = []
        for word_i in range(max_words):
            row = []

            for topic in topics:
                words = words_for_topics[topic.id]
                if word_i < len(words):
                    row.append(words[word_i])
                else:
                    row.append(None)

            word_rows.append(row)

        context['word_rows'] = word_rows

        return context


class TopicDetailView(DetailView):
    pk_url_kwarg = 'topic_id'
    context_object_name = 'topic'
    model = models.Topic
    template_name = 'topics/topic_detail.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(TopicDetailView, self).get_context_data(**kwargs)
        context['topic_model'] = self.object.model
        context['topic_words'] = self.object.words.prefetch_related('word')
        return context


class TopicWordDetailView(DetailView):
    pk_url_kwarg = 'word_id'
    context_object_name = 'word'
    model = models.TopicWord
    template_name = 'topics/topic_detail.html'

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(TopicWordDetailView, self).get_context_data(**kwargs)
        topic = self.object.topic
        context['topic'] = topic
        context['topic_model'] = topic.model
        context['topic_words'] = topic.words.prefetch_related('word')
        return context
