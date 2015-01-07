# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Code',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('active_instances', models.PositiveIntegerField(default=0)),
                ('code_type', models.IntegerField(default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CodeInstance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('added', models.DateTimeField()),
                ('task_id', models.PositiveIntegerField()),
                ('intensity', models.FloatField()),
                ('flag', models.IntegerField()),
                ('code', models.ForeignKey(to='textprizm.Code')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DataSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('created', models.DateTimeField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('idx', models.IntegerField()),
                ('time', models.DateTimeField()),
                ('type', models.IntegerField()),
                ('message', models.TextField()),
                ('codes', models.ManyToManyField(to='textprizm.Code', through='textprizm.CodeInstance')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Participant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Schema',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Session',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('started', models.DateTimeField()),
                ('ended', models.DateTimeField()),
                ('set', models.ForeignKey(to='textprizm.DataSet')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('full_name', models.CharField(max_length=250)),
                ('email', models.CharField(max_length=250)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='message',
            name='participant',
            field=models.ForeignKey(related_name='messages', to='textprizm.Participant'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='message',
            name='session',
            field=models.ForeignKey(to='textprizm.Session'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codeinstance',
            name='message',
            field=models.ForeignKey(to='textprizm.Message'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='codeinstance',
            name='user',
            field=models.ForeignKey(to='textprizm.User'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='code',
            name='schema',
            field=models.ForeignKey(related_name='codes', to='textprizm.Schema'),
            preserve_default=True,
        ),
    ]
