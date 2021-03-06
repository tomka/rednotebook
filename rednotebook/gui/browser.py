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

import sys
import os
import logging
import warnings

import gtk
import gobject

# Testing
if __name__ == '__main__':
    sys.path.insert(0, '../../')
    # Fix for pywebkitgtk 1.1.5
    #gtk.gdk.threads_init() # only initializes threading in the glib/gobject module
    gobject.threads_init() # also initializes the gdk threads
    

from rednotebook.util import filesystem

webkit = None

def windows_webkit_import():
    global webkit
    
    cwd = os.getcwd()
    
    if filesystem.main_is_frozen():
        gtk_bin_dir = filesystem.app_dir
    else:
        gtk_bin_dir = r'C:\GTK'
        
    try:
        # It seems the dlls are only found if we are in the bin dir
        # during import
        os.chdir(gtk_bin_dir)
    except WindowsError:
        logging.error('Changing dir to "%s" failed' % gtk_bin_dir)
        return
    
    try:
        import webkit
    except ImportError:
        logging.info('webkit not found. For a nicer preview install python-webkit or pywebkitgtk')
    os.chdir(cwd)

if False and sys.platform == 'win32':
    windows_webkit_import()
else:
    try:
        import webkit
    except ImportError:
        logging.info('webkit not found. For a nicer preview install python-webkit or pywebkitgtk')
    
    
    
def can_print_pdf():
    if not webkit:
        return False
        
    try:
        printer = HtmlPrinter()
    except TypeError, err:
        logging.info('UrlPrinter could not be created: "%s"' % err)
        return False
    
    frame = printer._webview.get_main_frame()
    
    can_print_full = hasattr(frame, 'print_full')
    
    if not can_print_full:
        msg = 'For direct PDF export, please install pywebkitgtk version 1.1.5 or later.'
        logging.info(msg)
    
    return can_print_full
    

def print_pdf(html, filename):
    printer = HtmlPrinter()
    printer.print_html(html, filename)



class HtmlPrinter(object):
    '''
    Idea and some code taken from interwibble, 
    "A non-interactive tool for converting any given website to PDF"
    
    (http://github.com/eeejay/interwibble/)
    '''
    PAPER_SIZES = {'a3'     : gtk.PAPER_NAME_A3,
                   'a4'     : gtk.PAPER_NAME_A4,
                   'a5'     : gtk.PAPER_NAME_A5,
                   'b5'     : gtk.PAPER_NAME_B5,
                   'executive' : gtk.PAPER_NAME_EXECUTIVE,
                   'legal'   : gtk.PAPER_NAME_LEGAL,
                   'letter' : gtk.PAPER_NAME_LETTER}
                   
    def __init__(self, paper='a4'):
        self._webview = webkit.WebView()
        webkit_settings = self._webview.get_settings()
        webkit_settings.set_property('enable-plugins', False)
        try:
            self._webview.connect('load-error', self._load_error_cb)
        except TypeError, err:
            logging.info(err)
        self._paper_size = gtk.PaperSize(self.PAPER_SIZES[paper])
        
    def print_html(self, html, outfile):
        handler = self._webview.connect(
            'load-finished', self._load_finished_cb, outfile)
        self._print_status('Loading URL...')
        self._webview.load_html_string(html, 'file:///')
        
        while gtk.events_pending():
            gtk.main_iteration()
            

    def _load_finished_cb(self, view, frame, outfile):
        self._print_status('Loading done')
        print_op = gtk.PrintOperation()
        print_settings = print_op.get_print_settings() or gtk.PrintSettings()
        print_settings.set_paper_size(self._paper_size)
        print_op.set_print_settings(print_settings)
        print_op.set_export_filename(os.path.abspath(outfile))
        self._print_status('Exporting PDF...')
        print_op.connect('end-print', self._end_print_cb)
        try:
            frame.print_full(print_op, gtk.PRINT_OPERATION_ACTION_EXPORT)
            while gtk.events_pending():
                gtk.main_iteration()
        except gobject.GError, e:
            self._print_error(e.message)

    def _load_error_cb(self, view, frame, url, gp):
        self._print_error("Error loading %s" % url)
    
    def _end_print_cb(self, *args):
        self._print_status('Exporting done')

    def _print_error(self, status):
        logging.error(status)
        
    def _print_status(self, status):
        logging.info(status)
    

class HtmlView(gtk.ScrolledWindow):
    def __init__(self, *args, **kargs):
        gtk.ScrolledWindow.__init__(self, *args, **kargs)
        self.webview = webkit.WebView()
        self.add(self.webview)
        
        #self.webview.connect('populate-popup', self.on_populate_popup)
        self.webview.connect('button-press-event', self.on_button_press)
        self.nav_signal = self.webview.connect('navigation-requested', self.on_navigate)
        
        self.search_text = ''
        self.webview.connect('load-finished', self.on_load_finished)
        
        self.show_all()
        
    def load_html(self, html):
        self.loading_html = True
        html = self.webview.load_html_string(html, 'file:///')
        self.loading_html = False
                                
    def get_html(self):
        self.webview.execute_script("document.title=document.document_element.inner_h_t_m_l;")
        return self.webview.get_main_frame().get_title()

    def set_editable(self, editable):
        self.webview.set_editable(editable)
        
    def set_font_size(self, size):
        if size <= 0:
            zoom = 1.0
        else:
            zoom = size / 10.0
        # It seems webkit shows text a little bit bigger
        zoom *= 0.90
        self.webview.set_zoom_level(zoom)
        
    def highlight(self, string):
        # Not possible for all versions of pywebkitgtk
        try:
            # Remove results from last highlighting
            self.webview.unmark_text_matches()
                
            # Mark all occurences of "string", case-insensitive, no limit
            matches = self.webview.mark_text_matches(string, False, 0)
            self.webview.set_highlight_text_matches(True)
        except AttributeError, err:
            logging.info(err)
        
    def on_populate_popup(self, webview, menu):
        '''
        Unused
        '''
        
    def on_button_press(self, webview, event):
        '''
        We don't want the context menus
        '''
        # Right mouse click
        if event.button == 3:
            #self.webview.emit_stop_by_name('button_press_event')
            # Stop processing that event
            return True
            
    def on_navigate(self, webview, frame, request):
        '''
        We want to load files and links externally
        '''
        if self.loading_html:
            # Keep processing
            return False
            
        uri = request.get_uri()
        logging.info('Clicked URI "%s"' % uri)
        filesystem.open_url(uri)
        
        # Stop processing that event
        return True
        
    def on_load_finished(self, webview, frame):
        '''
        We use this method to highlight searched text.
        Whenever new searched text is entered it is saved in the HtmlView
        instance and highlighted, when the html is loaded.
        
        Trying to highlight text while the page is still being loaded
        does not work.
        '''
        if self.search_text:
            self.highlight(self.search_text)
        else:
            self.webview.set_highlight_text_matches(False)
    
if __name__ == '__main__':
    logging.get_logger('').set_level(logging.DEBUG)
    sys.path.insert(0, os.path.abspath("./../../"))
    from rednotebook.util import markup
    text = 'PDF export works 1 www.heise.de'
    html = markup.convert(text, 'xhtml')
    
    win = gtk.Window()
    win.connect("destroy", lambda w: gtk.main_quit())
    win.set_default_size(600,400)
    
    vbox = gtk.VBox()
    
    def test_export():
        pdf_file = '/tmp/export-test.pdf'
        print_pdf(html, pdf_file)
        #os.system("evince " + pdf_file)
    
    button = gtk.Button("Export")
    button.connect('clicked', lambda button: test_export())
    vbox.pack_start(button, False, False)
    
    html_view = HtmlView()
    
    def high(view, frame):
        html_view.highlight("work")
    html_view.webview.connect('load-finished', high)
    
    
    html_view.load_html(html)
    
    html_view.set_editable(True)
    vbox.pack_start(html_view)
    
    win.add(vbox)
    win.show_all()
    
    gtk.main()
    
