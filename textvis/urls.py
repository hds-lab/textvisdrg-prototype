from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'textvis.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^stream/', include('twitter_stream.urls', namespace="twitter_stream")),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^topics/', include('textvis.topics.urls'))
)
