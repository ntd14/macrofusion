#!/usr/bin/env python3
# -*- coding: utf-8 -*-


# License : GPLv3 : http://gplv3.fsf.org/

try:

    import os, sys
    import os.path
    import subprocess
    import shutil
    import time
    import threading   
    import multiprocessing
    import re
    import configparser
    import operator
    import cairo
    import random
    import urllib.parse
    import signal
    import tempfile

    from gi import require_version
    require_version('Gtk', '3.0')
    require_version('Gdk', '3.0')
    require_version('GExiv2', '0.10')
    from gi.repository import Gdk, Gtk, GObject, GdkPixbuf, GExiv2

except:    
    print('An error occured. Python or one of its sub modules is absent...\nIt would be wise to check your python installation.')
    sys.exit(1)    

try:
    from PIL import Image
except:
    print('Python Imaging Library is missing.')

# Bad, bad, really bad coder... Global variables...
global session_images_bak
session_images_bak=[]
global session_options_bak
session_options_bak=[]

APP = 'MacroFusion'
__VERSION__='0.7.5'
__LICENSE__='GPL'
__COPYRIGHT__='Dariusz Duma'
__WEBSITE__='http://sourceforge.net/p/macrofusion'

if os.path.exists('/usr/share/mfusion/ui/ui.xml') \
    and os.path.exists('/usr/share/mfusion/ui/progress.xml') \
    and os.path.exists('/usr/share/pixmaps/macrofusion.png') \
    and os.path.exists('/usr/share/mfusion/images/logoSplash.png'):
    # print ("System wide install!")
    DIR = '/usr/share/locale/'
    IMG = '/usr/share/pixmaps/'
    IMG2 = '/usr/share/mfusion/images/'
    UI = '/usr/share/mfusion/ui/'
elif os.path.exists(sys.path[0] + "/ui/ui.xml"):
    # print ("Local run!")
    DIR = sys.path[0] + '/locale/'
    IMG = sys.path[0] + '/images/'
    IMG2 = sys.path[0] + '/images/'
    UI = sys.path[0] + '/ui/'
else:
    print ("That's me, your MacroFusion. Make your mind - local or system wide install?")
    sys.exit(1)
    
import locale
from locale import gettext as _
locale.bindtextdomain(APP, DIR)
locale.textdomain(APP)

GObject.threads_init()

def toggled_cb(cell, path, user_data):
    model, column = user_data
    model[path][column] = not model[path][column]
    return

# PLEASE REAPAIR!! Python-imaging can't open .tiff (or some of them)    
def create_thumbnail(chemin,taille):
    outfile=data.preview_folder + '/' + os.path.split(chemin)[1]
    try:
        im = GdkPixbuf.Pixbuf.new_from_file_at_size(chemin, taille[0], taille[1])
#        pb = Gtk.gdk.pixbuf_new_from_file(chemin)
#        im = Interface.pixbuf2Image(Interface(),pb)
#        im = Image.open(chemin)
#        im.thumbnail(taille)
#        im.save(outfile, "JPEG")
        im.savev(outfile, "jpeg", [], [])
    except IOError:
        print(_("Generating %s thumbnail failed.") % chemin)
    return outfile


####################################################
########Classe des données##########################
####################################################
class data:
    """Données utiles"""
    def __init__(self):
        self.install_folder=sys.path[0]                                                #On recupere le folder d'install
        
        self.config_folder = (os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config/mfusion'))
        self.default_folder = os.path.expanduser('~/')
        self.temp_folder = tempfile.gettempdir()
        self.default_file = ""
        self.align_prefix = "aligned"
        self.update_folders()

    def update_folders(self):        
        # save tmp files in current working folder
        self.enfuse_folder  = self.temp_folder
        self.preview_folder = self.temp_folder + "/preview"
        if not os.path.exists(self.config_folder):
            os.makedirs(self.config_folder)
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)
        if not os.path.exists(self.enfuse_folder):
            os.makedirs(self.enfuse_folder)
        if not os.path.exists(self.preview_folder):
            os.makedirs(self.preview_folder)

    def check_install(self, name):
        a=False
        for dir in os.environ['PATH'].split(":"):
            prog = os.path.join(dir, name)
            if os.path.exists(prog): 
                a=True
        return a


##############################################################
###########Classe de l'interface##############################
##############################################################

class Interface:
    """Interface pour le logiciel d'exposition-fusion enfuse"""

    def __init__(self):
        
        # Set default icon
        Gtk.Window.set_default_icon_from_file(IMG + 'macrofusion.png') 
        
        self.cpus = multiprocessing.cpu_count()
        if not data.check_install("enfuse"):
            self.messageinthebottle(_("Can't find Enfuse.\nPlease check enblend/enfuse is installed.\nStopping..."))
            sys.exit()
		        
        # Check cpus
        if self.cpus > 1 and data.check_install("enfuse-mp"):
            print("Will use all the powers of your CPU!")
            self.enfuser = "enfuse-mp"
        else:  
            self.enfuser = "enfuse"
        
	    #Set the Glade file
        self.gui = Gtk.Builder()
        self.gui.set_translation_domain(APP)
        self.gui.add_from_file(UI + "ui.xml")

        
        #Dans la foulee on chope la fenetre principale, ca sert a rien c'est pour
        #montrer qu'on peut le faire c'est tout ^^
        self.win=self.gui.get_object("mainwindow")
        self.win.set_title('MacroFusion' + __VERSION__)
                
        #On chope le reste, et ca, ca va servir...
        self.listeimages = self.gui.get_object("listeimages")
        self.buttonaddfile = self.gui.get_object("buttonaddfile")
        self.buttondelfile = self.gui.get_object("buttondelfile")
        self.statusbar = self.gui.get_object("status1")
        self.statusbar.push(1,(_("CPU Cores: %s") % self.cpus))

        self.hscaleexp = self.gui.get_object("hscaleexp")
        self.ajus_exp = Gtk.Adjustment(value=1, lower=0, upper=1, step_incr=0.1, page_incr=0.1, page_size=0)
        self.hscaleexp.set_adjustment(self.ajus_exp)
        self.spinbuttonexp = self.gui.get_object("spinbuttonexp")
        self.spinbuttonexp.set_digits(1)
        self.spinbuttonexp.set_value(1)
        self.spinbuttonexp.set_adjustment(self.ajus_exp)
        
        self.hscalecont = self.gui.get_object("hscalecont")
        self.ajus_cont = Gtk.Adjustment(value=0, lower=0, upper=1, step_incr=0.1, page_incr=0.1, page_size=0)
        self.hscalecont.set_adjustment(self.ajus_cont)
        self.spinbuttoncont = self.gui.get_object("spinbuttoncont")
        self.spinbuttoncont.set_digits(1)
        self.spinbuttoncont.set_value(0)
        self.spinbuttoncont.set_adjustment(self.ajus_cont)
        
        self.hscalesat = self.gui.get_object("hscalesat")
        self.ajus_sat = Gtk.Adjustment(value=0.2, lower=0, upper=1, step_incr=0.1, page_incr=0.1, page_size=0)
        self.hscalesat.set_adjustment(self.ajus_sat)
        self.spinbuttonsat = self.gui.get_object("spinbuttonsat")
        self.spinbuttonsat.set_digits(1)
        self.spinbuttonsat.set_value(0.2)
        self.spinbuttonsat.set_adjustment(self.ajus_sat)
        
        self.hscalemu = self.gui.get_object("hscalemu")
        self.ajus_mu = Gtk.Adjustment(value=0.5, lower=0, upper=1, step_incr=0.01, page_incr=0.1, page_size=0)
        self.hscalemu.set_adjustment(self.ajus_mu)
        self.spinbuttonmu = self.gui.get_object("spinbuttonmu")
        self.spinbuttonmu.set_digits(2)
        self.spinbuttonmu.set_value(0.5)
        self.spinbuttonmu.set_adjustment(self.ajus_mu)
        
        self.hscalesigma = self.gui.get_object("hscalesigma")
        self.ajus_sigma = Gtk.Adjustment(value=0.2, lower=0, upper=1, step_incr=0.01, page_incr=0.1, page_size=0)
        self.hscalesigma.set_adjustment(self.ajus_sigma)
        self.spinbuttonsigma = self.gui.get_object("spinbuttonsigma")
        self.spinbuttonsigma.set_digits(2)
        self.spinbuttonsigma.set_value(0.2)
        self.spinbuttonsigma.set_adjustment(self.ajus_sigma)

        self.spinbuttonlargeurprev = self.gui.get_object("spinbuttonlargeurprev")
        self.ajus_largeup = Gtk.Adjustment(value=640, lower=128, upper=1280, step_incr=1, page_incr=1, page_size=0)
        self.spinbuttonlargeurprev.set_adjustment(self.ajus_largeup)

        self.spinbuttonhauteurprev = self.gui.get_object("spinbuttonhauteurprev")
        self.ajus_hauteup = Gtk.Adjustment(value=640, lower=128, upper=1280, step_incr=1, page_incr=1, page_size=0)
        self.spinbuttonhauteurprev.set_adjustment(self.ajus_hauteup)
        
        self.buttonpreview = self.gui.get_object("buttonpreview")
        self.checkbuttontiff = self.gui.get_object("checkbuttontiff")
        self.checkbuttonjpeg = self.gui.get_object("checkbuttonjpeg")
        self.buttonfusion = self.gui.get_object("buttonfusion")   
        self.buttonbeforeafter = self.gui.get_object("buttonbeforeafter")   
        self.buttonedit = self.gui.get_object("buttoneditw")
        
        self.imagepreview = self.gui.get_object("imagepreview")
        self.imagepreview.set_from_file(IMG2 + "logoSplash.png")
        
        self.progressbar = self.gui.get_object("progressbar")
        
        self.checkbuttonexif = self.gui.get_object("checkbuttonexif")

        #valeurs des options et configurations :
        self.check_pyramidelevel = self.gui.get_object("check_pyramidelevel")
        self.spinbuttonlevel = self.gui.get_object("spinbuttonlevel")
        self.check_hardmask = self.gui.get_object("check_hardmask")
        self.check_contwin = self.gui.get_object("check_contwin")
        self.spinbuttoncontwin = self.gui.get_object("spinbuttoncontwin")
        
        self.check_courb = self.gui.get_object("check_courb")
        self.check_prctcourb = self.gui.get_object("check_prctcourb")
        self.spinbuttoncourb = self.gui.get_object("spinbuttoncourb")
        self.check_detecbord = self.gui.get_object("check_detecbord")
        self.spinbuttonEdge = self.gui.get_object("spinbuttonEdge")
        # self.spinbuttonEdge.set_value(self.conf.getint('prefs', 'w'))
        
        self.spinbuttonLceS = self.gui.get_object("spinbuttonLceS")
        self.spinbuttonLceF = self.gui.get_object("spinbuttonLceF")
        self.check_lces = self.gui.get_object("check_lces")
        self.check_lcef = self.gui.get_object("check_lcef")
        
        self.check_ciecam = self.gui.get_object("check_ciecam")
        self.check_desatmeth = self.gui.get_object("check_desatmeth")
        self.combobox_desatmet = self.gui.get_object("combobox_desatmet")
        self.spinbuttonlargeurprev = self.gui.get_object("spinbuttonlargeurprev")
        self.spinbuttonhauteurprev = self.gui.get_object("spinbuttonhauteurprev")
        self.checkbuttoncache = self.gui.get_object("checkbuttoncache")
        self.spinbuttoncache = self.gui.get_object("spinbuttoncache")
        self.checkbuttonbloc = self.gui.get_object("checkbuttonbloc")
        self.spinbuttonbloc = self.gui.get_object("spinbuttonbloc")
        self.checkbuttontaillefinale = self.gui.get_object("checkbuttontaillefinale")
        self.spinbuttonlargeurfinale = self.gui.get_object("spinbuttonlargeurfinale")
        self.spinbuttonhauteurfinale = self.gui.get_object("spinbuttonhauteurfinale")
        self.spinbuttonxoff = self.gui.get_object("spinbuttonxoff")
        self.spinbuttonyoff = self.gui.get_object("spinbuttonyoff")
        self.checkbuttonjpegorig = self.gui.get_object("checkbuttonjpegorig")
        self.hscalecomprjpeg = self.gui.get_object("hscalecomprjpeg")
        self.combtiff = self.gui.get_object("combtiff")

        self.checkbutton_a5_align = self.gui.get_object("checkbutton_a5_align")
        self.checkbutton_a5_crop = self.gui.get_object("checkbutton_a5_crop")
        self.checkbutton_a5_shift = self.gui.get_object("checkbutton_a5_shift")
        self.checkbutton_a5_field = self.gui.get_object("checkbutton_a5_field")                
        self.buttonabout = self.gui.get_object("buttonabout")
        
        self.entryedit_field = self.gui.get_object("entry_editor")                
        
        self.combobox_desatmet.set_active(0)
        self.combtiff.set_active(0)
        
        if not data.check_install('exiftool'):
            self.checkbuttonexif.set_sensitive(False)
            self.messageinthebottle(_("Exiftool is missing!\n\n Cannot copy exif info."))
        if not data.check_install('align_image_stack'):
            self.checkbutton_a5_align.set_sensitive(False)
            self.checkbutton_a5_crop.set_sensitive(False)
            self.checkbutton_a5_field.set_sensitive(False)
            self.checkbutton_a5_shift.set_sensitive(False)
            #self.checkbutton_a5_align.set_sensitive(False)
            self.messageinthebottle(_("Hugin tools (align_image_stack) are missing !\n\n Cannot auto align images."))            
            
        # Read values from config
        self.conf = configparser.ConfigParser()
        if os.path.isfile(data.config_folder + '/mfusion.cfg'):
            self.conf.read(data.config_folder + '/mfusion.cfg')
        if self.conf.has_option('prefs', 'pwidth'):
            self.spinbuttonlargeurprev.set_value(self.conf.getint('prefs', 'pwidth'))
        if self.conf.has_option('prefs', 'pheight'):
            self.spinbuttonhauteurprev.set_value(self.conf.getint('prefs', 'pheight'))
        if self.conf.has_option('prefs', 'cachebutton'):
            self.checkbuttoncache.set_active(self.conf.getboolean('prefs', 'cachebutton'))
        if self.conf.has_option('prefs', 'cachesize'):
            self.spinbuttoncache.set_value(self.conf.getint('prefs', 'cachesize'))
        if self.conf.has_option('prefs', 'blocbutton'):
            self.checkbuttonbloc.set_active(self.conf.getboolean('prefs', 'blocbutton'))
        if self.conf.has_option('prefs', 'blocsize'):
            self.spinbuttonbloc.set_value(self.conf.getint('prefs', 'blocsize'))
        if self.conf.has_option('prefs', 'outsize'):
            self.checkbuttontaillefinale.set_active(self.conf.getboolean('prefs', 'outsize'))
        if self.conf.has_option('prefs', 'outwidth'):
            self.spinbuttonlargeurfinale.set_value(self.conf.getint('prefs', 'outwidth'))
        if self.conf.has_option('prefs', 'outheight'):  
            self.spinbuttonhauteurfinale.set_value(self.conf.getint('prefs', 'outheight'))
        if self.conf.has_option('prefs', 'xoff'):
            self.spinbuttonxoff.set_value(self.conf.getint('prefs', 'xoff'))
        if self.conf.has_option('prefs', 'yoff'):  
            self.spinbuttonyoff.set_value(self.conf.getint('prefs', 'yoff'))
        if self.conf.has_option('prefs', 'jpegdef'):  
            self.checkbuttonjpegorig.set_active(self.conf.getboolean('prefs', 'jpegdef'))
        if self.conf.has_option('prefs', 'jpegcompr'):  
            self.hscalecomprjpeg.set_value(self.conf.getfloat('prefs', 'jpegcompr'))
        if self.conf.has_option('prefs', 'tiffcomp'):  
            self.combtiff.set_active(self.conf.getint('prefs', 'tiffcomp'))
        if self.conf.has_option('prefs', 'exif'):  
            self.checkbuttonexif.set_active(self.conf.getboolean('prefs', 'exif'))
        if self.conf.has_option('prefs', 'default_folder'):  
            data.default_folder = self.conf.get('prefs', 'default_folder')
            if not os.path.isdir(data.default_folder):
                print("Default folder '%s' doesn't exist, using '%s'" % (data.default_folder, data.config_folder))
                data.default_folder = os.path.expanduser('~/')
            data.update_folders()
        if self.conf.has_option('prefs', 'editor'):           
            self.entryedit_field.set_text(self.conf.get('prefs', 'editor'))
        else:
            self.entryedit_field.set_text("gimp")

        #On relie les signaux (cliques sur boutons, cochage des cases, ...) aux fonctions appropriées
        dic = { "on_mainwindow_destroy"         : self.exit_app,
                "on_buttoncancel_clicked"       : self.exit_app,
                "on_menufilequit_activate"      : self.exit_app,
                "on_menufileopen_activate"      : self.add,
                "on_buttonaddfile_clicked"      : self.add,
                "on_menufileadd_activate"       : self.add,
                "on_buttondelfile_clicked"      : self.delete,
                "on_menufiledelete_activate"    : self.delete,
                "on_menufileclear_activate"     : self.clear,
                "on_buttonpreview_clicked"      : self.preview,
                "on_menufilesave_activate"      : self.fusion,
                "on_buttonfusion_clicked"       : self.fusion,
                "on_buttoneditw_clicked"        : self.sendto,
                "on_buttonbeforeafter_pressed"  : self.baswitch,
                "on_buttonbeforeafter_released" : self.baswitch,
                "on_entry_editor_activate"      : self.check_editor,
                "on_hscaleexp_format_value"     : self.apropos,
                "on_buttonabout_clicked"        : self.apropos
        }
        #Auto-connection des signaux       
        self.gui.connect_signals(dic)
        
        #initialisation de la liste d'images a fusionner
        self.inittreeview()
      
    def exit_app(self, action):
        # cancel = self.autosave_image()
        # if cancel:
        #    return True
        self.stop_now = True
        self.closing_app = True
        self.save_settings()
        self.cleanup()
        sys.exit(0)        
    
    def check_editor(self, action):
        if not data.check_install(self.entryedit_field.get_text()):
            Gui.messageinthebottle(_("No such application!\n\n Cannot find ") + self.entryedit_field.get_text() + (_(".\n\n Revert to default value.")))
            self.entryedit_field.set_text("gimp")
            return False
        return True
        
    def cleanup(self):
        for self.files in os.walk(data.preview_folder):
            for self.filename in self.files[2]:
                os.remove(data.preview_folder + "/" + self.filename)
        
    def inittreeview(self):
        """initialisation de la liste d'images a importer"""
        self.liststoreimport = Gtk.ListStore(bool, str, GdkPixbuf.Pixbuf, str)                    #création de la listestore qui contiendra les noms d'images
        self.listeimages.set_model(self.liststoreimport)                        #on donne la liststore au l'afficheur treeview
        self.listeimages.set_property('tooltip-column', 3)
        
        self.colonneselect = Gtk.TreeViewColumn('')                             #Premiere colonne :
        self.listeimages.append_column(self.colonneselect)                      #on l'ajoute au TreeView
        self.select=Gtk.CellRendererToggle()                                    #On creer le cellrender pour avoir des boutons toggle
        self.colonneselect.pack_start(self.select, True)                        #on met le cellrender dans la colonne
        self.colonneselect.add_attribute(self.select, 'active', 0)              #on met les boutons actifs par défaut
        
        # self.colonneimages = Gtk.TreeViewColumn(_('Image'))                        #deuxieme colonne, titre 'Image'
        # self.listeimages.append_column(self.colonneimages)                      #on rajoute la colonne dans le treeview
        # self.cell = Gtk.CellRendererText()                                      #Ce sera des cellules de texte
        # self.colonneimages.pack_start(self.cell, True)                          #que l'on met dans la colonne
        # self.colonneimages.add_attribute(self.cell, 'text', 1)                  #et on specifie que c'est du texte simple
       
        self.colonneimages2 = Gtk.TreeViewColumn(_("Thumbnail"))                        #deuxieme colonne, titre 'Image'
        self.listeimages.append_column(self.colonneimages2)                      #on rajoute la colonne dans le treeview
        self.cell2 = Gtk.CellRendererPixbuf()                                      #Ce sera des cellules de texte
        self.colonneimages2.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.colonneimages2.pack_start(self.cell2, True)                          #que l'on met dans la colonne
        self.colonneimages2.add_attribute(self.cell2, 'pixbuf', 2)
        self.cell2.set_property('visible', 1)
        
        self.listeimages.set_rules_hint(True)
        self.select.connect("toggled", toggled_cb, (self.liststoreimport, 0))   #Pour que les boutons de selection marchent

        # enable drag and drop destination for files
        self.listeimages.enable_model_drag_dest([ ('STRING', 0, 0) ], Gdk.DragAction.DEFAULT)
        self.listeimages.connect("drag_data_received", self.drag_data_received)

    def drag_data_received(self, treeview, context, x, y, selection, info, etime):
        files = selection.get_text().split()
        # remove 'file:' part and unnecessary slashes or backslashes in path
        files = [os.path.normpath(x.lstrip("file:")) for x in files]
        # get rid of 'file:' and replace %xx escapes
        files = [urllib.parse.unquote(x) for x in files]
        (path, file) = os.path.split(files[0])
        (filename, ext) = os.path.splitext(file)
        data.default_file = filename+"-fused"+ext
        self.put_files_to_the_list(files)
        
    def add(self, widget):
        FenOuv=OpenFiles_Dialog(self.liststoreimport)
        self.liststoreimport=FenOuv.get_model()

    def delete(self, widget):
        self.treeselectionsuppr=self.listeimages.get_selection()                #pour récupérer quels files sont selectionnés
        self.treeselectionsuppr.set_mode(Gtk.SelectionMode.MULTIPLE)            #Pour pouvoir en selectionner plusieurs
        (model, pathlist) = self.treeselectionsuppr.get_selected_rows()
        for i in pathlist:
            print(i)
            treeiter = model.get_iter(i)
            self.liststoreimport.remove(treeiter) 
            
    def clear(self, widget):
        self.liststoreimport.clear()
            
    def preview(self, widget):
        self.taille=(self.spinbuttonlargeurprev.get_value(), self.spinbuttonhauteurprev.get_value())
        self.name=data.preview_folder + "/" + "preview.tif"
        item=0
        if len(self.liststoreimport)>0:
            self.ref=list(zip(*self.liststoreimport))[0] 
            for item2 in self.ref:
                if item2:
                    item+=1
                    if item>1:
                        self.thread_preview = Thread_Preview(self.taille, self.get_options(), self.get_options_align(), self.liststoreimport) 
                        self.thread_preview.start()
                        timer = GObject.timeout_add (100, self.pulsate)
                        break
        if item<=1:
            self.messageinthebottle(_("Please add or activate at least two images.\n\n Cannot do anything smart with the one or no image."))


    def get_options_align(self):
        self.options_align = ['--gpu']
        if self.checkbutton_a5_align.get_active():
            if self.checkbutton_a5_crop.get_active():
                self.options_align.append('-C')
            if self.checkbutton_a5_shift.get_active():
                self.options_align.append('-i')
            if self.checkbutton_a5_field.get_active():
                self.options_align.append('-m')
        return self.options_align

    def get_options(self):
        options=["--exposure-weight=" + str(self.spinbuttonexp.get_value()), 
                 "--exposure-mu=" + str(self.spinbuttonmu.get_value()), 
                 "--exposure-sigma=" + str(self.spinbuttonsigma.get_value()),
                 "--saturation-weight=" + str(self.spinbuttonsat.get_value()),
                 "--contrast-weight=" + str(self.spinbuttoncont.get_value())]
        if self.check_pyramidelevel.get_active():            
            options.append('--levels=' + str(self.spinbuttonlevel.get_value_as_int()))
        if self.check_hardmask.get_active():
            options.append('--hard-mask')
        if self.check_contwin.get_active():
            options.append('--contrast-window-size=' + str(self.spinbuttoncontwin.get_value_as_int()))
        if self.check_courb.get_active():
            if self.check_prctcourb.get_active():
                options.append('--contrast-min-curvature=' + str(self.spinbuttoncourb.get_value()) + "%")
            else:
                options.append('--contrast-min-curvature=' + str(self.spinbuttoncourb.get_value()))
        if self.check_detecbord.get_active():
            opts='--contrast-edge-scale=' + str(self.spinbuttonEdge.get_value()) + ':'
            if self.check_lces.get_active():
                opts+=str(self.spinbuttonLceS.get_value()) + '%:'
            else:
                opts+=str(self.spinbuttonLceS.get_value()) + ':'
            if self.check_lcef.get_active():
                opts+=str(self.spinbuttonLceF.get_value()) + '%'
            else:
                opts+=str(self.spinbuttonLceF.get_value()) + ''
            options.append(opts)
             # + str(self.spinbuttonLceF.get_value()) + '%')
        if self.check_ciecam.get_active():
            options.append('-c')
        if self.check_desatmeth.get_active():
            opt={-1:None, 0:"average", 1:'l-star', 2:'lightness', 3:'value', 4:'luminance'}
            options.append('--gray-projector=' + opt[self.combobox_desatmet.get_active()])
        if not self.checkbuttoncache.get_active():
            options.append('-m ' + str(self.spinbuttoncache.get_value_as_int()))
        if not self.checkbuttonbloc.get_active():
            options.append('-b ' + str(self.spinbuttonbloc.get_value_as_int()))
        if not self.checkbuttontaillefinale.get_active():
            options.append('-f ' + str(self.spinbuttonlargeurfinale.get_value_as_int()) + 'x'
                                 + str(self.spinbuttonhauteurfinale.get_value_as_int()) + 'x'
                                 + str(self.spinbuttonxoff.get_value_as_int()) + 'x'
                                 + str(self.spinbuttonyoff.get_value_as_int()))
        if self.name.endswith(('.tif', '.tiff', '.TIF', '.TIFF')):
            tiffopt={0:"NONE", 1:"PACKBITS", 2:"LZW", 3:"DEFLATE"}
            options.append("--compression=" + tiffopt[self.combtiff.get_active()])
        if self.name.endswith(('.jpg', '.jpeg', '.JPG', '.JPEG')) and (not self.checkbuttonjpegorig.get_active()):
            options.append("--compression=" + str(int(self.hscalecomprjpeg.get_value())))       
        return options
        
    def pulsate(self):
        if self.thread_preview.isAlive():           #Tant que le thread est en cours, 
            self.progressbar.set_text(_("Calculating preview..."))
            self.progressbar.pulse()               #on fait pulser la barre
            return True                            #et on renvoie True pour que gobject.timeout recommence
        else:
            self.progressbar.set_fraction(1)
            self.progressbar.set_text(_("Preview generated"))
            self.imagepreview.set_from_file(data.preview_folder + "/" + "preview.tif")
            return False

    def baswitch(self, widget):
        if (not int(self.buttonbeforeafter.get_relief())) and (os.path.exists(data.preview_folder + "/preview_.tif")):
            self.buttonbeforeafter.props.relief = Gtk.ReliefStyle.NONE
            self.imagepreview.set_from_file(data.preview_folder + "/preview_.tif")
        elif os.path.exists(data.preview_folder + "/preview_.tif"):
            self.buttonbeforeafter.props.relief = Gtk.ReliefStyle.NORMAL
            self.imagepreview.set_from_file(data.preview_folder + "/preview.tif")
        
    def fusion(self,widget):
        FenPar=SaveFiles_Dialog()
        self.name = FenPar.get_name()
        if self.name:
            if not re.search('\\.jpeg$|\\.jpg$|\\.tiff$|\\.tif$', self.name, flags=re.IGNORECASE):
                self.name+=".jpg"
            self.start('')
    
    def sendto(self, widget):
        self.name=(data.preview_folder + "/sendto.tif")
        
        if not self.check_editor(0):
            return
        if self.start(self.name) == -1:
            self.messageinthebottle(_("No preview, no output, no edit.\n\n Game Over."))
            return
        
    def messageinthebottle(self, message):
        self.messaga=Gtk.MessageDialog(parent=None, flags=0, type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, message_format=(message))
        if self.messaga.run() == Gtk.ResponseType.OK:
            self.messaga.destroy()

    def get_exif(self, file):
        tags2=''
        try:
             im = GExiv2.Metadata(file)
             tags_keys = im.get_exif_tags()
             if 'Exif.Image.Model' in tags_keys:
                 tags2 = (_("<i>Model:</i>\t\t\t") + im['Exif.Image.Model'] + "\n")
             if 'Exif.Image.DateTimeOriginal' in tags_keys:
                 tags2 += (_("<i>Date:</i>\t\t\t") + im['Exif.Image.DateTimeOriginal'] + "\n")
             if 'Exif.Photo.FocalLength' in tags_keys:
                 tags2 += (_("<i>Focal length:</i>\t\t") + im['Exif.Photo.FocalLength'] + "mm \n")
             if 'Exif.Photo.FNumber' in tags_keys:
                 tags2 += (_("<i>Aperture:</i>\t\t\tF/") + im['Exif.Photo.FNumber'] + "\n")
             if 'Exif.Photo.ExposureTime' in tags_keys:
                 tags2 += (_("<i>Exposure Time:</i>\t\t") + im['Exif.Photo.ExposureTime'] + " s. \n")
        except IOError:
            print ("failed to identify", file)
        return tags2
               
    def start(self, issend):        
        self.issend=issend
        self.liste_images=[]
        self.liste_aligned=[]
        index = 0
        for item in self.liststoreimport:
            if item[0]:
               self.liste_images.append(item[1])
               self.liste_aligned.append(data.preview_folder + "/" + data.align_prefix + format(index, "04d") + ".tif")
               index += 1
        if not Gui.checkbutton_a5_align.get_active():
            self.liste_aligned=self.liste_images
        if self.liste_images.count(self.name):
           self.messageinthebottle(_("Can't overwrite input image!\n\n Please change the output filename."))
           return -1                            
        if len(self.liste_images) <= 1:
            self.messageinthebottle(_("Please add or activate at least two images.\n\n Cannot do anything smart with the one or no image."))
            return -1
        command_align = ['align_image_stack', '--gpu', '-a', data.preview_folder + '/' + data.align_prefix] + self.get_options_align() + self.liste_images
        command_fuse = [Gui.enfuser, "-o", self.name] + self.get_options() + self.liste_aligned
        ProFus = Progress_Fusion(command_fuse, command_align, self.liste_aligned, self.issend)
        
    def apropos(self, widget):
        self.fen=AproposFen()
        
    def save_settings(self):
        conf = configparser.ConfigParser()
        conf.add_section('prefs')
        # conf.set('prefs', 'w', self.spinbuttonEdge.get_value_as_int())
        conf.set('prefs', 'pwidth', str(self.spinbuttonlargeurprev.get_value_as_int()))
        conf.set('prefs', 'pheight', str(self.spinbuttonhauteurprev.get_value_as_int()))
        conf.set('prefs', 'cachebutton', str(self.checkbuttoncache.get_active()))
        conf.set('prefs', 'cachesize', str(self.spinbuttoncache.get_value_as_int()))
        conf.set('prefs', 'blocbutton', str(self.checkbuttonbloc.get_active()))
        conf.set('prefs', 'blocsize', str(self.spinbuttonbloc.get_value_as_int()))
        conf.set('prefs', 'outsize', str(self.checkbuttontaillefinale.get_active()))
        conf.set('prefs', 'outwidth', str(self.spinbuttonlargeurfinale.get_value_as_int()))
        conf.set('prefs', 'outheight', str(self.spinbuttonhauteurfinale.get_value_as_int()))
        conf.set('prefs', 'xoff', str(self.spinbuttonxoff.get_value_as_int()))
        conf.set('prefs', 'yoff', str(self.spinbuttonyoff.get_value_as_int()))
        conf.set('prefs', 'jpegdef', str(self.checkbuttonjpegorig.get_active()))
        conf.set('prefs', 'jpegcompr', str(int(self.hscalecomprjpeg.get_value())))
        conf.set('prefs', 'tiffcomp', str(self.combtiff.get_active()))
        conf.set('prefs', 'exif', str(self.checkbuttonexif.get_active()))
        conf.set('prefs', 'editor',  str(self.entryedit_field.get_text()))
        conf.set('prefs', 'default_folder', data.default_folder)
        conf.write(open(data.config_folder+ '/mfusion.cfg', 'w'))
        return

    def pixbuf2Image(self, pb):
        width,height = pb.get_width(),pb.get_height()
        return Image.frombytes("RGB",(width,height),pb.get_pixels() )

    def put_files_to_the_list(self, files):
        self.files=files
        self.tags2=''
        self.badfiles=[]
        for file in self.files:
            if re.search('\\.jpg$|\\.jpeg$|\\.tiff$|\\.tif$', file, flags=re.IGNORECASE):
                pb = GdkPixbuf.Pixbuf.new_from_file(file)
                im = self.pixbuf2Image(pb)
                self.size=im.size
                # self.tags2 = Gui.get_exif(file)
                if not self.tags2:
                    self.tags2=''
                self.tooltip=("\n" + _("<b>Filename:</b> ") + os.path.basename(file) + "\n"+_("<b>Resolution:</b> ") + str(str(self.size[0]) + "x" + str(self.size[1])) + "\n" + self.tags2)
                self.liststoreimport.append([1, file, GdkPixbuf.Pixbuf.new_from_file_at_size(file, 128, 128), self.tooltip])
            else:
                self.badfiles.append(file)
        if len(self.badfiles)>0:
            message=_("Only JPEG and TIFF files are allowed.\n\nCannot open:\n")
            for itz in self.badfiles:
                message+=itz + "\n"
            Gui.messageinthebottle(message)
        return 
        
####################################################################
###########Classe pour choisir les images a fusionner###############
####################################################################
    
class OpenFiles_Dialog:
    """La classe qui ouvre la fenetre de choix de files, et qui retourne le ListStore par la methode get_model"""
    def __init__(self,model):
        """Lance la fenetre de selection et créé la listsore a partir des files selectionnés"""
        self.filter=Gtk.FileFilter()
        self.filter.add_mime_type("image/jpeg")
        self.filter.add_mime_type("image/tiff")
        self.liststoreimport=model #on repart de l'ancien modele

        self.file_dialog = Gtk.FileChooserDialog(_("Add images..."), 
                                                    None, 
                                                    Gtk.FileChooserAction.OPEN,
                                                    (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.file_dialog.set_select_multiple(True)
        self.file_dialog.set_current_folder(data.default_folder)
        self.file_dialog.set_filter(self.filter)
        self.file_dialog.use_preview = True
        self.previewidget = Gtk.Image()
        self.file_dialog.set_preview_widget(self.previewidget)
        self.file_dialog.connect("update-preview", self.update_thumb_preview, self.previewidget)
                 
        if (self.file_dialog.run() == Gtk.ResponseType.OK):
            self.files = self.file_dialog.get_filenames()
            self.tags2=''
            self.badfiles=[]
            (path, file) = os.path.split(self.files[0])
            (filename, ext) = os.path.splitext(file)
            data.default_file = filename+"-fused"+ext
            Gui.put_files_to_the_list(self.files)

        data.default_folder = self.file_dialog.get_current_folder()
        data.update_folders()
        self.file_dialog.destroy()
    
    def update_thumb_preview(self, file_chooser, preview):
        if not self.file_dialog.use_preview:
            return
        filename = file_chooser.get_preview_filename()
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 320, 320)
            self.previewidget.set_from_pixbuf(pixbuf)
            self.have_preview = True
        except:
            self.have_preview = False
        self.file_dialog.set_preview_widget_active(self.have_preview)
        return
                 
    def get_model(self):
        """ Retourne la liststore """
        if self.liststoreimport:
            return self.liststoreimport
        else:
            return None
            
#####################################################################
#########Classe pour la fenetre pour choisir le fichier final########
#####################################################################

class SaveFiles_Dialog:
    """La classe qui ouvre la fenetre de choix pour enregistrer le fichier"""          
    def __init__(self):
        
        self.file_dialog = Gtk.FileChooserDialog(_("Save file..."), 
                                                   None, 
                                                   Gtk.FileChooserAction.SAVE,
                                                   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK))
        self.file_dialog.set_current_folder(data.default_folder)
        self.file_dialog.set_current_name(data.default_file)
        self.file_dialog.set_do_overwrite_confirmation(True)
        if (self.file_dialog.run() == Gtk.ResponseType.OK):
            self.resultat = self.file_dialog.get_filename()

        data.default_folder = self.file_dialog.get_current_folder()
        self.file_dialog.destroy()

    def get_name(self):
        try:
            return self.resultat
        except AttributeError:
            return ""

#####################################################################
#########Thread pour la prévisualisation#############################
#####################################################################
            
class Thread_Preview(threading.Thread):
    def __init__(self, taille, options, options_align, liste):
        threading.Thread.__init__ (self)
        self.taille=taille
        self.options=options
        self.liste=liste
        self.options_align=options_align
            
    def run(self):
        images_a_fusionner=[]
        images_a_align=[]
        index = 0
        global session_images_bak
        global session_options_bak 
           
        for item in self.liste:
            if item[0]:
                chemin_miniature=create_thumbnail(item[1],(int(self.taille[0]), int(self.taille[1])))
                images_a_align.append(chemin_miniature)
                images_a_fusionner.append(data.preview_folder + "/test" + format(index, "04d") + ".tif")
                index += 1
        if (len(images_a_fusionner))<=1:
            Gui.messageinthebottle(_("Please add two or more images.\n\n Cannot do anything smart with the one image."))
            return
        if not Gui.checkbutton_a5_align.get_active():
            images_a_fusionner=images_a_align
        if os.path.exists(data.preview_folder + "/preview.tif"):
            shutil.copy(data.preview_folder + "/" + "preview.tif", data.preview_folder + "/" + "preview_.tif")
        if Gui.checkbutton_a5_align.get_active()                                        \
           and (len(images_a_align) != len(session_images_bak)                          \
           or len(self.options_align) != len(session_options_bak)                       \
           or len(list(axz for axz in images_a_align if axz not in session_images_bak)) \
           or len(list(axz2 for axz2 in self.options_align if axz2 not in session_options_bak))):
            command=["align_image_stack", "-a", data.preview_folder + "/test"] + self.options_align + images_a_align
            Gui.statusbar.push(15, _(":: Align photos..."))
            preview_process=subprocess.Popen(command, stdout=subprocess.PIPE)
            preview_process.wait()
            session_options_bak=self.options_align
            session_images_bak=images_a_align
            Gui.statusbar.pop(15)
        Gui.statusbar.push(15, _(":: Fusing photos..."))
        print (self.options)

        command=[Gui.enfuser, "-o", data.preview_folder + "/" + "preview.tif"] + self.options + images_a_fusionner
        preview_process=subprocess.Popen(command, stdout=subprocess.PIPE)
        preview_process.wait()
        Gui.statusbar.pop(15)
        
        
#######################################################################
#########Fenetre de progression lors de la fusion finale###############
#######################################################################
        
class Progress_Fusion:
    def __init__(self, command_fuse, command_align, liste_aligned, issend):
        
        #self.progress = Gtk.glade.XML(fname=UI + "progress.xml", domain=APP)
        self.progress = Gtk.Builder()
        self.progress.add_from_file(UI + "progress.xml") 
        self.progress_win = self.progress.get_object("dialog1")
        self.progress_label = self.progress.get_object("progress_label")
        self.info_label = self.progress.get_object("info_label")
        self.progress_bar = self.progress.get_object("progressbar1")
        self.progress_stop_button = self.progress.get_object("stop_button")
        self.dic1 = { "on_stop_button_clicked"  : self.close_progress, 
                      "on_dialog1_destroy"      : self.close_progress }
        self.progress.connect_signals(self.dic1)        
        self.info_label.set_text(_('Fusion images...'))
       
        self.thread_fusion = Thread_Fusion(command_fuse, command_align, liste_aligned, issend)  #On prepare le thread qui va faire tout le boulot
        self.thread_fusion.start()                                     #On le lance
        timer = GObject.timeout_add (100, self.pulsate)
        
    def pulsate(self):
        if self.thread_fusion.isAlive():            #Tant que le thread est en cours, 
            self.progress_bar.set_text(_("Fusion, please wait..."))
            self.progress_bar.pulse()               #on fait pulser la barre
            return True                             #et on renvoie True pour que gobject.timeout recommence
        else:
            self.progress_bar.set_fraction(1)
            self.progress_bar.set_text(_("Fused !"))
            self.close_progress(self)
            return False
            
    def close_progress(self, widget):
        self.progress_win.destroy()
            
            
              
##############################################################################
###########Thread de fusion des vraies images#################################
##############################################################################

class Thread_Fusion(threading.Thread):
    def __init__(self, command_fuse, command_align, liste_aligned, issend):
        threading.Thread.__init__ (self)
        self.command_fuse = command_fuse
        self.command_align = command_align
        self.issend = issend
        self.liste_aligned = liste_aligned
        
    def run(self):
        if Gui.checkbutton_a5_align.get_active():            
            align_process=subprocess.Popen(self.command_align, stdout=subprocess.PIPE)
            align_process.wait()
            
        fusion_process=subprocess.Popen(self.command_fuse, stdout=subprocess.PIPE)
        fusion_process.wait()
        
        if Gui.checkbuttonexif.get_active():
            exif_copy = subprocess.Popen(["exiftool", "-tagsFromFile", Gui.liste_images[0], "-overwrite_original", Gui.name])
            exif_copy.wait()
        if len(self.issend) > 0:
            subprocess.Popen([Gui.entryedit_field.get_text(), self.issend], stdout=subprocess.PIPE)


########################################    
#### Classe de la fenêtre a propos  ####
########################################  

class AproposFen:
    def __init__(self):
        self.aboutdialog = Gtk.AboutDialog()
        self.aboutdialog.set_name("MacroFusion")
        self.aboutdialog.set_modal(True)
        self.aboutdialog.set_position(Gtk.WindowPosition.CENTER)
        self.aboutdialog.set_version(__VERSION__)
        self.aboutdialog.set_comments('A GTK Gui for the excellent Enfuse.\n\n2014 (c) Dariusz Duma\n<dhor@toxic.net.pl>')
        # self.aboutdialog.set_copyright(__COPYRIGHT__)
        self.aboutdialog.set_website(__WEBSITE__)
        self.pixbuf=GdkPixbuf.Pixbuf.new_from_file(IMG + "macrofusion.png")
        self.aboutdialog.set_logo(self.pixbuf)
        self.aboutdialog.connect("response", self.close_about)
        self.aboutdialog.show()
        
        
    def close_about(self, widget, event):
        self.aboutdialog.destroy()

        
###########################################################    
####  Initialisation et appel de la classe principale  ####
###########################################################            
                        
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    data = data()                                              
    Gui  = Interface()
                                                                       
    if (len(sys.argv)>1):     
        files=sys.argv[1:]
        Gui.put_files_to_the_list(files)
#        if len(Gui.liststoreimport)==0:
#            Gui.messageinthebottle(_("\nCan work only with JPEG or TIFF files."))

    Gtk.main()
