# OpenPLM module

r"""OpenPLM FreeCAD Workbench"""

# (c) 2013 LinObject SAS

# ***************************************************************************
# *   (c) LinObject SAS (contact@linobject.com) 2013                        *
# *                                                                         *
# *   This file is part of the OpenPLM plugin for FreeCAD.                  *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License (GPL)            *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this plugin; if not, write to the Free Software    *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# *   LinObject SAS 2013                                                    *
# ***************************************************************************/

import os

# Authors
# Pierre Cosquer <pcosquer@linobject.com>
# Alejandro Galech <agalech@linobject.com>

__title__ = "FreeCAD OpenPLM Workbench - Init file"
__author__ = "Pierre Cosquer <pcosquer@linobject.com>"
__url__ = ["http://openplm.org", "http://free-cad.sourceforge.net"]

# adding the OpenPLM module scripts to FreeCAD

path1 = FreeCAD.ConfigGet("AppHomePath") + "Mod/OpenPLM/"
path2 = FreeCAD.ConfigGet("UserAppData") + "Mod/OpenPLM/"
if os.path.exists(path2):
    draftpath = path2
else:
    draftpath = path1
Gui.addIconPath(draftpath)


class OpenPLMWorkbench(Workbench):
    r"""the OpenPLM Workbench"""

    # The workbench name as it appears in the workbenches list
    MenuText = "OpenPLM"
    ToolTip = "The OpenPLM module"
    user_app_data = App.getUserAppDataDir()
    # Msg("User app data dir : %s\n" % user_app_data)
    Icon = user_app_data + "Mod/OpenPLM/logo_small.png"

    def Initialize(self):
        self.initialized = False
        Log('Loading OpenPLM GUI...\n')
        import openplm
        openplm.PLUGIN.workbench = self

        from openplm import OpenPLMLogin, OpenPLMCheckOut, OpenPLMDownload, \
            OpenPLMForget, OpenPLMCheckIn, OpenPLMRevise, OpenPLMAttach, \
            OpenPLMCreate, OpenPLMConfigure

        commands = {"OpenPLM_Login": OpenPLMLogin(),
                    "OpenPLM_CheckOut": OpenPLMCheckOut(),
                    "OpenPLM_Download": OpenPLMDownload(),
                    "OpenPLM_Forget": OpenPLMForget(),
                    "OpenPLM_CheckIn": OpenPLMCheckIn(),
                    "OpenPLM_Revise": OpenPLMRevise(),
                    "OpenPLM_AttachToPart": OpenPLMAttach(),
                    "OpenPLM_Create": OpenPLMCreate(),
                    "OpenPLM_Configure": OpenPLMConfigure()}

        # for k, v in commands.items():
        #    FreeCADGui.addCommand(k, v)

        # creates a new toolbar with your commands
        self.appendToolbar("OpenPLM commands toolbar", commands.keys())

        # creates a new menu
        self.appendMenu("OpenPLM", commands.keys())

        # self.cmdList = ["OpenPLM_Login", "Separator"]
        #
        # self.appendMenu("OpenPLM", self.cmdList)
        #
        # self.cmdList2 = ["OpenPLM_CheckOut",
        #                  "OpenPLM_Download",
        #                  "OpenPLM_Forget",
        #                  "OpenPLM_CheckIn",
        #                  "OpenPLM_Revise",
        #                  "OpenPLM_AttachToPart",
        #                  "OpenPLM_Create"]
        # self.appendMenu("OpenPLM", self.cmdList2)
        #
        # self.cmdList3 = ["Separator", "OpenPLM_Configure"]
        # self.appendMenu("OpenPLM", self.cmdList3)

        # self.initialized = True

    def Activated(self):
        r"""code which should be computed when a user
        switches to this workbench"""
        Msg("OpenPLM workbench activated\n")

    def Deactivated(self):
        r"""code which should be computed when this workbench is deactivated"""
        Msg("OpenPLM workbench activated\n")

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(OpenPLMWorkbench())
# Gui.activateWorkbench("OpenPLMWorkbench")
