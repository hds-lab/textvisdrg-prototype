#!/usr/bin/env python
import os
import sys

from textvis import env_file

if __name__ == "__main__":
    env_file.load()
    
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "textvis.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
