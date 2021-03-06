# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------
# Copyright (c) 2009  Jendrik Seipp
# 
# RedNotebook is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# RedNotebook is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with RedNotebook; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
# -----------------------------------------------------------------------

# For Python 2.5 compatibility.
from __future__ import with_statement

import os
import sys
import logging
import re

try:
    import yaml
except ImportError:
    logging.error('PyYAML not found. Please install python-yaml or PyYAML')
    sys.exit(1)

# The presence of the yaml module has been checked
try:
    from yaml import CLoader as Loader
    from yaml import CDumper as Dumper
    #logging.info('Using libyaml for loading and dumping')
except ImportError:
    from yaml import Loader, Dumper
    logging.info('Using pyyaml for loading and dumping')
    
from rednotebook.data import Month
    
    
    
class Storage(object):
    def __init__(self):
        pass
        
    def load_all_months_from_disk(self, data_dir):
        '''
        Load all months and return a directory mapping year-month values
        to month objects
        '''
        # Format: 2010-05.txt
        date_exp = re.compile(r'(\d{4})-(\d{2})\.txt')
        
        months = {}
        
        logging.debug('Starting to load files in dir "%s"' % data_dir)
        files = sorted(os.listdir(data_dir))
        for file in files:
            match = date_exp.match(file)
            if match:
                year_string = match.group(1)
                month_string = match.group(2)
                year_month = year_string + '-' + month_string
                
                path = os.path.join(data_dir, file)
                
                month = self._load_month_from_disk(path)
                if month:
                    months[year_month] = month
        logging.debug('Finished loading files in dir "%s"' % data_dir)
        return months
    
    
    def _load_month_from_disk(self, path):
        '''
        Load the month file at path and return a month object
        
        If an error occurs, return None
        '''
        # path: /something/somewhere/2009-01.txt
        # file_name: 2009-01.txt
        file_name = os.path.basename(path)
        
        try:
            # Get Year and Month from filename
            year_and_month, extension = os.path.splitext(file_name)
            year_number, month_number = year_and_month.split('-')
            year_number = int(year_number)
            month_number = int(month_number)
            assert month_number in range(1,13)
        except Exception:
            msg = 'Error: %s is an incorrect filename. ' \
                'Filenames have to have the following form: ' \
                '2009-01.txt for January 2009 ' \
                '(year_with4Digits-month_with2Digits.txt)' % file_name
            logging.error(msg)
            return
        
        month_file_string = path
        
        try:
            # Try to read the contents of the file
            with open(month_file_string, 'rb') as month_file:
                logging.debug('Start loading file "%s"' % month_file_string)
                month_contents = yaml.load(month_file, Loader=Loader)
                logging.debug('Finished loading file "%s"' % month_file_string)
                month = Month(year_number, month_number, month_contents)
                return month
        except yaml.YAMLError, exc:
            logging.error('Error in file %s:\n%s' % (month_file_string, exc))
        except IOError:
            #If that fails, there is nothing to load, so just display an error message
            logging.error('Error: The file %s could not be read' % month_file_string)
        except Exception, err:
            logging.error('An error occured while reading %s:' % month_file_string)
            logging.error('%s' % err)
        
        
    def save_months_to_disk(self, months, dir, frame, exit_imminent=False, changing_journal=False, saveas=False):
        '''
        Do the actual saving and return if something has been saved
        '''
        something_saved = False
        for year_and_month, month in months.items():
            # We always need to save everything when we are "saving as"
            if month.edited or saveas:
                something_saved = True
                month_file_string = os.path.join(dir, year_and_month + '.txt')
                with open(month_file_string, 'w') as month_file:
                    month_content = {}
                    for day_number, day in month.days.iteritems():
                        # do not add empty days
                        if not day.empty:
                            month_content[day_number] = day.content
                    
                    try:
                        # yaml.dump(month_content, month_file, Dumper=Dumper)
                        # This version produces readable unicode and no python directives
                        yaml.safe_dump(month_content, month_file, allow_unicode=True)
                        month.edited = False
                    except OSError, err:
                        frame.show_save_error_dialog(exit_imminent)
                    except IOError, err:
                        frame.show_save_error_dialog(exit_imminent)
        return something_saved
