About
-------

MacroFusion is a neat little GUI for great tool Enfuse
(command line). It makes easy fusion few photos to one with great
DOF (Deep of Field) or DR (Dynamic Range). It can be useful for every macro
lovers or landscapers. 

MacroFusion is a fork of EnfuseGui of Chez Gholyo. Rebranding is due to
conflict with another EnfuseGui (for MacOS).

GNU GPL.

(c) Dariusz Duma <dhor@toxic.net.pl>

Dev branch Note:
The update to enfuse 4.2 has broken some commands (enfuse updated their commands and deprecated some which are used in macrofusion), as a result the CIECAM02 color profile option, cache size, block size and possably other options will not work. If you need these commands downgrade enfuse to 4.0. 


Install
---------

You need:

- python (>=3)
- Pillow (fork of PIL) (python3-imaging)
- gexiv2 (gir1.2-gexiv2)
- exiftool (libimage-exiftool-perl)
- enfuse (>=4.0)
- hugin-tools (with align_image_stack)

Local (archive .tar.gz):
------
Unpack, go to the directory 'macrofusion-0.X', run ./macrofusion.py

System wide:
-------
Use PPA or .deb packages (the only packages so far).

PPA (Ubuntu Trusty, Mint 17) ### Does not work for mint 18 so probably wont for Xenial Xerus either

sudo add-apt-repository ppa:dhor/myway

(https://launchpad.net/~dhor/+archive/myway)

Mint and Debian users also can use that .deb.


Translations
--------------

To translate MicroFusion, use microfusion.pot (original strings) and Poeditor (or any utility
you like). Import strings from .pot file and save them as .po.
Send it to me after you've done - thanks in advance.


Question and answers
---------------------

Q: Who needs ugly GUI for great command-line tool? 
A: Users that use Linux on a daily basis.

Q: Enfuse in text mode is very simply to use.
A: That's right. But we have XXI century - time to use mouse.

Q: What a stupid idea - put photos together. Who cares.
A: That's right, but the other platforms have tools to do that, so why don't do
   that on Linux? Photographers care.

