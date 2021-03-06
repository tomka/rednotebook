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

from __future__ import with_statement

import os
import zipfile
import subprocess
import logging
import codecs
from glob import glob



#from http://www.py2exe.org/index.cgi/HowToDetermineIfRunningFromExe
import imp, os, sys

def main_is_frozen():
    return (hasattr(sys, "frozen") or # new py2exe
        hasattr(sys, "importers") # old py2exe
        or imp.is_frozen("__main__")) # tools/freeze

def get_main_dir():
    if main_is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(sys.argv[0])
#--------------------------------------------------------------------------------------------------------


if not main_is_frozen():
    app_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../'))
    app_dir = os.path.normpath(app_dir)
else:
    app_dir = get_main_dir()
    


image_dir = os.path.join(app_dir, 'images')
frame_icon_dir = os.path.join(image_dir, 'rednotebook-icon')
files_dir = os.path.join(app_dir, 'files')
gui_dir = os.path.join(app_dir, 'gui')

user_home_dir = os.path.expanduser('~')


class Filenames(dict):
    '''
    Dictionary for dirnames and filenames
    '''
    def __init__(self, config):
        for key, value in globals().items():
            # Exclude "get_main_dir()"
            if key.lower().endswith('dir') and type(value) is str:
                value = os.path.abspath(value)
                self[key] = value
                setattr(self, key, value)
        
        self.portable = bool(config.read('portable', 0))
        
        self.journal_user_dir = self.get_user_dir(config)
        
        self.data_dir = self.default_data_dir
        
        # Is this the first run of RedNotebook?
        self.is_first_start = not os.path.exists(self.journal_user_dir)
            
        # Assert that all dirs and files are in place so that logging can take start
        make_directories([self.journal_user_dir, self.data_dir, self.template_dir,
                        self.temp_dir])
        make_files([(self.config_file, ''), (self.log_file, '')])
        
        self.last_pic_dir = self.user_home_dir
        self.last_file_dir = self.user_home_dir
        
    def get_user_dir(self, config):
        custom = config.read('userDir', '')
        
        if custom:
            # If a custom user dir has been set,
            # construct the absolute path (if not absolute already) 
            # and use it
            if not os.path.isabs(custom):
                custom = os.path.join(self.app_dir, custom)
            user_dir = custom
        else:
            if self.portable:
                user_dir = os.path.join(self.app_dir, 'user')
            else:
                user_dir = os.path.join(self.user_home_dir, '.rednotebook')
        
        return user_dir
        
        

        
    def __getattribute__(self, attr):
        user_paths = dict((('template_dir', 'templates'),
                        ('temp_dir', 'tmp'),
                        ('default_data_dir', 'data'),
                        ('config_file', 'configuration.cfg'),
                        ('log_file', 'rednotebook.log'),
                        ))
                            
        if attr in user_paths:
            return os.path.join(self.journal_user_dir, user_paths.get(attr))
        
        return dict.__getattribute__(self, attr)
    


def make_directory(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)
        
def make_directories(dirs):
    for dir in dirs:
        make_directory(dir)
        
def make_file(file, content=''):
    if not os.path.exists(file):
        with codecs.open(file, 'w', encoding='utf-8') as f:
            f.write(content)
            
def make_files(file_content_pairs):
    for file, content in file_content_pairs:
        if len(content) > 0:
            make_file(file, content)
        else:
            make_file(file)
            
def make_file_with_dir(file, content):
    dir = os.path.dirname(file)
    make_directory(dir)
    make_file(file, content)
    
def get_relative_path(from_dir, to_dir):
    '''
    Try getting the relative path from from_dir to to_dir
    The relpath method is only available in python >= 2.6
    if we run python <= 2.5, return the absolute path to to_dir
    '''
    if getattr(os.path, 'relpath', None):
        # If the data is saved on two different windows partitions,
        # return absolute path to to_dir
        drive1, tail = os.path.splitdrive(from_dir)
        drive2, tail = os.path.splitdrive(to_dir)
        
        # drive1 and drive2 are always empty strings on Unix
        if not drive1.upper() == drive2.upper():
            return to_dir
        
        return os.path.relpath(to_dir, from_dir)
    else:
        return to_dir
    
def write_archive(archive_file_name, files, base_dir='', arc_base_dir=''):
    """
    use base_dir for relative filenames, in case you don't 
    want your archive to contain '/home/...'
    """
    archive = zipfile.ZipFile(archive_file_name, "w")
    for file in files:
        archive.write(file, os.path.join(arc_base_dir, file[len(base_dir):]))
    archive.close()

def get_icons():
    return glob(os.path.join(frame_icon_dir, '*.png'))

def uri_is_local(uri):
    return uri.startswith('file://')


def get_journal_title(dir):
    '''
    returns the last dir name in path
    '''
    # Remove double slashes and last slash
    dir = os.path.normpath(dir)
    dir = os.path.abspath(dir)
    
    upper_dir = os.path.join(dir, '../')
    upper_dir = os.path.abspath(upper_dir)
    
    upper_dir_length = len(upper_dir)
    if upper_dir_length > 1:
        title = dir[upper_dir_length+1:]
    else:
        title = dir[upper_dir_length:]
    return title


def get_platform_info():
    import platform
    import gtk
    import yaml
    
    functions = [platform.machine, platform.platform, platform.processor, \
                platform.python_version, platform.release, platform.system,]
    values = map(lambda function: function(), functions)
    functions = map(lambda function: function.__name__, functions)
    names_values = zip(functions, values)
    
    lib_values = [('GTK version', gtk, 'gtk_version'),
                    ('PyGTK version', gtk, 'pygtk_version'),
                    ('Yaml version', yaml, '__version__'),]
    
    for name, object, value in lib_values:
        try:
            names_values.append((name, getattr(object, value)))
        except AttributeError, err:
            logging.info('%s could not be determined' % name)
            
    vals = ['%s: %s' % (name, val) for name, val in names_values]
    return 'System info: ' + ', '.join(vals)
    

def system_call(args):
    '''
    Asynchronous system call
    
    subprocess.call runs synchronously
    '''
    subprocess.Popen(args)
    


def open_url(url):
    '''
    Opens a file with the platform's preferred method
    '''
        
    # Try opening the file locally
    if sys.platform == 'win32':
        try:
            logging.info('Trying to open %s with "os.startfile"' % url)
            # os.startfile is only available on windows
            os.startfile(os.path.normpath(url))
            return
        except OSError:
            logging.exception('Opening %s with "os.startfile" failed' % url)
    
    elif sys.platform == 'darwin':
        try:
            logging.info('Trying to open %s with "open"' % url)
            system_call(['open', url])
            return
        except OSError, subprocess.CalledProcessError:
            logging.exception('Opening %s with "open" failed' % url)
    
    else:
        try:
            subprocess.check_call(['xdg-open', '--version'])
            logging.info( 'Trying to open %s with xdg-open' % url)
            system_call(['xdg-open', url])
            return
        except OSError, subprocess.CalledProcessError:
            logging.exception('Opening %s with xdg-open failed' % url)
        
    # If everything failed, try the webbrowser
    import webbrowser
    try:
        logging.info('Trying to open %s with webbrowser' % url)
        webbrowser.open(url)
    except webbrowser.Error:
        logging.exception('Failed to open web browser')
        
        
def read_yaml_file(filename, loader=None):
    '''
    Unused
    
    Try to read the contents of the file, if an error occurs, return None
    '''
    import yaml
    if loader is None:
        loader = yaml.Loader
        
    try:
        # Try to read the contents of the file
        with open(filename, 'r') as file:
            logging.debug('Start loading file "%s"' % filename)
            content = yaml.load(file, Loader=loader)
            logging.debug('Finished loading file "%s"' % filename)
            return content
    except yaml.YAMLError, exc:
        logging.error('Error in file "%s":\n%s' % (filename, exc))
    except IOError, err:
        #If that fails, there is nothing to load, so just display an error message
        logging.error('Error: The file "%s" could not be read:' % filename)
        logging.error('%s' % err)
    except Exception, err:
        logging.error('An error occured while reading "%s":' % filename)
        logging.error('%s' % err)
        
    return None
    
def read_file(filename):
    '''
    Tries to read a given file
    
    Returns None if an error is encountered
    '''
    encodings = ['utf-8']#, 'latin1', 'latin2']
    
    try:
        import chardet
    except ImportError:
        logging.info("chardet not found. Let's hope all your files are unicode")
        chardet = None
        
    if chardet:
        with open(filename, 'rb') as file:
            content = file.read()
        guess = chardet.detect(content)
        logging.debug('Chardet guesses %s for %s' % (guess, filename))
        encoding = guess.get('encoding')
        
        # chardet makes error here sometimes
        if encoding in ['MacCyrillic', 'ISO-8859-7']:
            encoding = 'ISO-8859-2'
            
        if encoding:
            encodings.insert(0, encoding)
    
    for encoding in encodings:
        try:
            file = codecs.open(filename, 'rb', encoding=encoding, errors='replace')
            data = file.read()
            file.close()
            return data
        except ValueError, err:
            logging.info(err)
        except Exception, e:
            logging.error(e)
    return ''
