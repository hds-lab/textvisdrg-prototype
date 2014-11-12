from django.db import models

# Create your models here.
class Schema(models.Model):
    
    name = models.CharField(max_length=200)
    description = models.TextField()


class Code(models.Model):
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    active_instances = models.PositiveIntegerField(default=0)
    schema = models.ForeignKey(Schema, related_name="codes")
    code_type = models.IntegerField(default=0)

    def __unicode__(self):
        if self.description:
            return "%s/%s (%d): %s" % (self.schema_id, self.name, self.id, self.description)
        else:
            return "%s/%s (%d)" % (self.schema_id, self.name, self.id)
        

class DataSet(models.Model):
    
    name = models.CharField(max_length=100)
    created = models.DateTimeField()


class Session(models.Model):
    
    set = models.ForeignKey(DataSet)
    started = models.DateTimeField()
    ended = models.DateTimeField()

    def __unicode__(self):
        return "%d (%s - %s)" % (self.id, str(self.started), str(self.ended))
        
class Participant(models.Model):
    
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __unicode__(self):
        return self.name

class Message(models.Model):
    
    session = models.ForeignKey(Session)
    idx = models.IntegerField()
    time = models.DateTimeField()
    type = models.IntegerField()
    participant = models.ForeignKey(Participant, related_name='messages')
    message = models.TextField()

    codes = models.ManyToManyField(Code, through='CodeInstance')

    @classmethod
    def get_between(cls, start, end):
        """
        Get messages that are inclusively between the two messages, or two dates.

        Takes into account the exact ordering of messages,
        meaning that you won't get messages at the same time but after the last message, for example.
        """

        if isinstance(start, Message):
            after_first = ~models.Q(session=start.session) | models.Q(idx__gte=start.idx)
            after_first = models.Q(time__gte=start.time) & after_first
        else:
            after_first = models.Q(time__gte=start)

        if isinstance(end, Message):
            before_last = ~models.Q(session=end.session) | models.Q(idx__lte=end.idx)
            before_last = models.Q(time__lte=end.time) & before_last
        else:
            before_last = models.Q(time__lte=end)

        return cls.objects.filter(after_first, before_last)


class User(models.Model):
    
    name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=250)
    email = models.CharField(max_length=250)

    def __unicode__(self):
        return self.name
        
class AbstractCodeInstance(models.Model):
    class Meta:
        abstract = True

    code = models.ForeignKey(Code)
    message = models.ForeignKey(Message)
    added = models.DateTimeField()


class CodeInstance(AbstractCodeInstance):
    
    user = models.ForeignKey(User)
    task_id = models.PositiveIntegerField()
    intensity = models.FloatField()
    flag = models.IntegerField()
