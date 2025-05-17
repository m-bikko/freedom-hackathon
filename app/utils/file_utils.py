#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
from datetime import datetime, timedelta

def cleanup_old_files(directory, days=1):
    """
    Remove files older than specified days from the directory
    
    Parameters:
    -----------
    directory: str
        Directory path to clean up
    days: int
        Files older than this many days will be removed
    """
    if not os.path.exists(directory):
        return
    
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            if mod_time < cutoff:
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Error removing file {filepath}: {e}")