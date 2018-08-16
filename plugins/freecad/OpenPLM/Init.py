# coding: utf-8

r"""UI-Free stuff for OpenPLM Workbench"""

# Get the Parameter Group of this module
ParGrp = App.ParamGet("System parameter:Modules").GetGroup("Mod/OpenPLM")

# Set the needed information
ParGrp.SetString("HelpIndex",
                 "http://apps.sourceforge.net/mediawiki/free-cad/index.php"
                 "?title=OpenPLM_Module")
ParGrp.SetString("WorkBenchName",
                 "OpenPLM")
ParGrp.SetString("WorkBenchModule",
                 "OpenPLM.py")  # TODO : -> openplm.py?
